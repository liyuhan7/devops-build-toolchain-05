"""共用 A 组镜像、运行日志与身份约定的 EChecker 实验入口。"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.buildchecker.lab import container, fresh_output, main as buildchecker_main, student_image
from scripts.buildchecker.runtime import run_logged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["doctor", "build", "test", "e8", "e9"])
    parser.add_argument("--image", help="与 BuildChecker 共用 buildchecker-lab:本人学号")
    parser.add_argument("--out", help="本仓库 work/ 下的新目录")
    parser.add_argument("--base-image", help="build 阶段传给现有 A 组构建入口")
    parser.add_argument("--apt-mirror", help="build 阶段覆盖 A 组镜像的 APT 源前缀")
    parser.add_argument("--pip-index", help="build 阶段覆盖 A 组镜像的 PyPI 索引")
    parser.add_argument("--cache-from", help="build 阶段传给 buildx 的缓存来源")
    parser.add_argument("--cache-to", help="build 阶段传给 buildx 的缓存导出")
    parser.add_argument("--build-timeout", type=int, default=1200)
    args = parser.parse_args(argv)
    if args.base_image and args.stage != "build":
        parser.error("--base-image 仅用于 build")
    if (args.apt_mirror is not None or args.pip_index is not None) and args.stage != "build":
        parser.error("--apt-mirror 与 --pip-index 仅用于 build")
    if (args.cache_from is not None or args.cache_to is not None) and args.stage != "build":
        parser.error("--cache-from 与 --cache-to 仅用于 build")
    out = args.out or f"work/echecker/{args.stage}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    if args.stage in {"build", "doctor"}:
        command = [args.stage, "--out", out]
        if args.image:
            command += ["--image", args.image]
        if args.stage == "build":
            command += ["--build-timeout", str(args.build_timeout)]
            if args.base_image:
                command += ["--base-image", args.base_image]
            if args.apt_mirror is not None:
                command += ["--apt-mirror", args.apt_mirror]
            if args.pip_index is not None:
                command += ["--pip-index", args.pip_index]
            if args.cache_from is not None:
                command += ["--cache-from", args.cache_from]
            if args.cache_to is not None:
                command += ["--cache-to", args.cache_to]
        return buildchecker_main(command)
    image = student_image(args.image)
    output = fresh_output(out)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)
    (output / "source-commit.txt").write_text(revision + "\n", encoding="utf-8")
    (output / "worktree-status.txt").write_text(status, encoding="utf-8")
    meta = {"track": "A", "stage": args.stage, "source_commit": revision,
            "image": image, "time_utc": datetime.now(timezone.utc).isoformat()}
    save_path = output / "invocation.json"
    save_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("EVIDENCE_DIR=" + str(output), flush=True)
    code = run_logged(["docker", "image", "inspect", image], output / "image")
    if code == 0:
        info = json.loads((output / "image/stdout.log").read_text(encoding="utf-8"))[0]
        image_id = info["Id"]
        labels = info.get("Config", {}).get("Labels") or {}
        meta.update(image_id=image_id, image_source_commit=labels.get("org.opencontainers.image.revision"),
                    image_worktree_dirty=labels.get("io.devops.buildchecker.dirty"))
        if args.stage == "test":
            shell = ("python3 -m pytest -c services/echecker/pytest.ini services/echecker/tests && "
                     "python3 -m unittest discover -s tests/echecker_lab -v")
            command = container(image_id, output / "runner") + ["bash", "-c", shell]
        else:
            evidence = output / "evidence"
            evidence.mkdir()
            command = container(image_id, output / "runner",
                                [f"type=bind,src={evidence},dst=/evidence"], trace=args.stage == "e8")
            command += ["python3", "-m", "scripts.echecker.scenarios", args.stage, "--out", "/evidence/result"]
        code = run_logged(command, output / "runner", timeout=300)
    meta["exit_code"] = code
    save_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise SystemExit("ERROR: " + str(exc))
