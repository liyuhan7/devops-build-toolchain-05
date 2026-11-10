"""在当前仓库布局中运行 A 组构建、论文复现、检测与验证。"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.buildchecker.runtime import SERVICE_TEST_ARGS, docker_user_args, run_logged


def student_image(image=None):
    if image:
        return image
    sid = subprocess.check_output(["git", "config", "--local", "user.name"], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r"[0-9]{6,16}", sid):
        raise ValueError("请先用 git config --local user.name 设置本人数字学号，或显式传入 --image")
    return f"buildchecker-lab:{sid}"


def fresh_output(value=None):
    name = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    output = (ROOT / value).resolve() if value else ROOT / "work/buildchecker" / name
    work = (ROOT / "work").resolve()
    if work not in output.parents:
        raise ValueError("输出目录必须位于本仓库 work/ 内")
    if output.exists() and any(output.iterdir()):
        raise ValueError("请使用新的输出目录，保留此前证据")
    output.mkdir(parents=True, exist_ok=True)
    return output


def container(image, folder, mounts=(), trace=False):
    command = ["docker", "run", "--rm", "--network", "none", *docker_user_args(),
               "-e", "HOME=/tmp", "--cidfile", str(folder / "container-id.txt")]
    if trace:
        command += ["--cap-add", "SYS_PTRACE"]
    for mount in mounts:
        command += ["--mount", mount]
    return command + [image]


def collect_e5(image, output):
    evidence = output / "evidence"
    evidence.mkdir()
    # 镜像保留仓库 /repo 布局；采集只操作宿主机 work/ 中的独立样例副本。
    shell = """set -eu
cp -R /repo/fixtures/md-rd/. /evidence/
cd /evidence
mkdir trace
make clean
strace -ff -s 4096 -o trace/t -e trace=%file,%process make -p app > make-db.txt 2> build-stderr.log
./app > program-output.txt
grep -n config.h trace/t.*
grep -n '^main.o:' make-db.txt
cat program-output.txt
"""
    command = container(image, output / "runner", [f"type=bind,src={evidence},dst=/evidence"], trace=True)
    return run_logged(command + ["bash", "-c", shell], output / "runner")


def detect(image, output, fixed=False, timeout=120):
    fixture = output / "fixture"
    shutil.copytree(ROOT / "fixtures/md-rd", fixture)
    if fixed:
        path = fixture / "Makefile"
        text = path.read_text(encoding="utf-8")
        if "main.o: main.c unused.h" not in text:
            raise ValueError("样例声明已变化，请核对修复规则")
        path.write_text(text.replace("main.o: main.c unused.h", "main.o: main.c config.h"), encoding="utf-8")
    evidence = output / "evidence"
    evidence.mkdir()
    mounts = [f"type=bind,src={fixture},dst=/fixture,readonly", f"type=bind,src={evidence},dst=/evidence"]
    command = container(image, output / "runner", mounts, trace=True)
    return run_logged(command + ["python3", "-m", "buildchecker", "full-check", "--fixture", "/fixture",
                                "--out", "/evidence", "--fail-on-findings", "--timeout", str(timeout)],
                      output / "runner", timeout + 60)


def main(argv=None):
    parser = argparse.ArgumentParser(description="A 组 BuildChecker 实验入口，不根据 B 组目录推断轨道")
    parser.add_argument("stage", choices=["doctor", "build", "e5", "e6", "gate"])
    parser.add_argument("--out", help="本仓库 work/ 下的新目录")
    parser.add_argument("--image", help="覆盖默认的 buildchecker-lab:本人学号")
    parser.add_argument("--base-image", help="仅 build：覆盖 Dockerfile BASE_IMAGE，例如同 digest 的官方镜像引用")
    parser.add_argument("--fixed", action="store_true", help="只修复 E6 的独立 Makefile 副本")
    parser.add_argument("--build-timeout", type=int, default=1200)
    parser.add_argument("--timeout", type=int, default=120, help="E6 clean/build 共用总执行预算（秒）")
    args = parser.parse_args(argv)
    if args.stage == "doctor" and sys.platform != "linux":
        parser.error("doctor 检查课程 Linux 服务器环境；其他阶段可使用 Windows Docker Linux 引擎")
    if args.fixed and args.stage != "e6":
        parser.error("--fixed 仅用于 e6")
    if args.base_image and args.stage != "build":
        parser.error("--base-image 仅用于 build")
    if args.timeout <= 0 or args.build_timeout <= 0:
        parser.error("超时预算必须为正整数")
    image = student_image(args.image) if args.stage != "doctor" else args.image
    output = fresh_output(args.out)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)
    (output / "source-commit.txt").write_text(revision + "\n", encoding="utf-8")
    (output / "worktree-status.txt").write_text(status, encoding="utf-8")
    meta = {"track": "A", "stage": args.stage, "fixed": args.fixed, "image": image,
            "source_commit": revision, "time_utc": datetime.now(timezone.utc).isoformat(),
            "profile": "single-make-teaching"}
    invocation = output / "invocation.json"
    invocation.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EVIDENCE_DIR={output}", flush=True)
    if args.stage == "doctor":
        code = run_logged([sys.executable, str(ROOT / "scripts/doctor.py"), "--group", "A",
                           "--out", str(output / "env.json")], output / "doctor")
    elif args.stage == "build":
        build_args = ["--build-arg", "BASE_IMAGE=" + args.base_image] if args.base_image else []
        code = run_logged(["docker", "build", "--load", "--progress=plain", *build_args, "-f", "services/buildchecker/Dockerfile",
                           "--label", f"org.opencontainers.image.revision={revision}",
                           "--label", f"io.devops.buildchecker.dirty={str(bool(status)).lower()}",
                           "-t", image, "."], output / "build", args.build_timeout)
        if code == 0:
            code = run_logged(["docker", "image", "inspect", image], output / "image")
        if code == 0:
            code = run_logged(["docker", "run", "--rm", "--network", "none", image, "cat", "/opt/toolchain.lock"], output / "toolchain")
        if code == 0:
            code = run_logged(container(image, output / "unit-tests") + SERVICE_TEST_ARGS, output / "unit-tests")
    else:
        # 镜像 ID 与源码 SHA 分别记录，避免后续写报告的提交被当作镜像中的源码版本。
        code = run_logged(["docker", "image", "inspect", image], output / "image")
        if code == 0:
            image_info = json.loads((output / "image/stdout.log").read_text(encoding="utf-8"))[0]
            image_id = image_info["Id"]
            meta["image_id"] = image_id
            labels = image_info.get("Config", {}).get("Labels") or {}
            meta["image_source_commit"] = labels.get("org.opencontainers.image.revision")
            meta["image_worktree_dirty"] = labels.get("io.devops.buildchecker.dirty")
            if args.stage == "e5":
                code = collect_e5(image_id, output)
            elif args.stage == "e6":
                code = detect(image_id, output, args.fixed, args.timeout)
            else:
                code = run_logged([sys.executable, str(ROOT / "scripts/buildchecker/gate.py"), "--image", image_id,
                                   "--out", str(output / "gate")], output / "driver", 1800)
    meta["exit_code"] = code
    invocation.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"ERROR: {exc}")
