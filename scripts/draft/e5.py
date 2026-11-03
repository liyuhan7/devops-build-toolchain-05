"""在 Linux 服务器上复现 DRAFT E5 的缺少 make 构建失败。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.draft.prompts import write_prompt_evidence


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fresh_output(value=None):
    run_id = f"e5-b-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    output = (ROOT / value).resolve() if value else ROOT / "work/draft/e5" / run_id
    work = (ROOT / "work").resolve()
    if work not in output.parents:
        raise ValueError("输出目录必须位于本仓库 work/ 内")
    if output.exists() and any(output.iterdir()):
        raise ValueError("请使用新的输出目录，保留此前证据")
    output.mkdir(parents=True, exist_ok=True)
    return output


def image_tag(run_id=None):
    run_id = run_id or uuid.uuid4().hex[:8]
    return f"draft-e5-broken:e5-b-{run_id}"


def validate_fixture(fixture):
    required = ("Dockerfile.broken", "Makefile", "main.c", "README.md")
    missing = [name for name in required if not (fixture / name).is_file()]
    if missing:
        raise ValueError("DRAFT 样例缺少文件：" + ", ".join(missing))
    dockerfile = (fixture / "Dockerfile.broken").read_text(encoding="utf-8")
    first = dockerfile.splitlines()[0] if dockerfile.splitlines() else ""
    if not re.fullmatch(r"FROM \S+@sha256:[0-9a-f]{64}", first):
        raise ValueError("Dockerfile.broken 的 FROM 必须固定完整 sha256 摘要")
    for instruction in ("WORKDIR /work", "COPY main.c Makefile ./", "RUN make", 'CMD ["./hello"]'):
        if instruction not in dockerfile:
            raise ValueError(f"Dockerfile.broken 缺少固定指令：{instruction}")
    return dockerfile


def run_logged(command, folder, timeout):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (folder / "stdout.log").open("w", encoding="utf-8") as stdout, (
        folder / "stderr.log"
    ).open("w", encoding="utf-8") as stderr:
        try:
            code = subprocess.run(
                command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=timeout
            ).returncode
        except subprocess.TimeoutExpired:
            code = 124
    (folder / "exit-code.json").write_text(
        json.dumps({"exit_code": code}) + "\n", encoding="utf-8"
    )
    return code


def git_text(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="B 组 DRAFT E5 真实失败与候选提示采集")
    parser.add_argument("--student-id", required=True, help="实际操作者学号")
    parser.add_argument("--name", required=True, help="实际操作者姓名")
    parser.add_argument("--out", help="本仓库 work/ 下的新目录")
    parser.add_argument("--fixture", default="fixtures/draft")
    parser.add_argument("--build-timeout", type=int, default=600)
    args = parser.parse_args(argv)
    if sys.platform != "linux":
        parser.error("请在 SSH 登录后的 Linux 课程服务器执行")
    if not re.fullmatch(r"[0-9]{6,16}", args.student_id):
        parser.error("--student-id 必须是 6 至 16 位数字学号")
    if args.build_timeout <= 0:
        parser.error("--build-timeout 必须为正整数")

    fixture = (ROOT / args.fixture).resolve()
    dockerfile = validate_fixture(fixture)
    output = fresh_output(args.out)
    project = output / "project"
    shutil.copytree(
        fixture,
        project,
        ignore=shutil.ignore_patterns("Dockerfile.reference", "hello", "*.log"),
    )
    iteration = output / "iter-01"
    iteration.mkdir()
    (iteration / "Dockerfile").write_text(dockerfile, encoding="utf-8")

    revision = git_text("rev-parse", "HEAD")
    branch = git_text("branch", "--show-current")
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, text=True
    )
    (output / "source-commit.txt").write_text(revision + "\n", encoding="utf-8")
    (output / "worktree-status.txt").write_text(status, encoding="utf-8")
    inputs = {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(project.iterdir())
        if path.is_file()
    }
    inputs["runner/scripts/draft/e5.py"] = sha256(Path(__file__))
    inputs["runner/scripts/draft/prompts.py"] = sha256(Path(__file__).with_name("prompts.py"))
    (output / "input-sha256.json").write_text(
        json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    tag = image_tag()
    metadata = {
        "stage": "E5",
        "track": "B-DRAFT",
        "operator": {"name": args.name, "student_id": args.student_id},
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": revision,
        "branch": branch,
        "fixture": str(fixture.relative_to(ROOT)),
        "base_image": dockerfile.splitlines()[0].removeprefix("FROM "),
        "candidate_generation": "PENDING_MANUAL_MODEL_RESPONSES",
        "candidate_validation": "PENDING_E6",
    }
    invocation = output / "invocation.json"
    invocation.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EVIDENCE_DIR={output}", flush=True)

    command = [
        "docker",
        "build",
        "--progress=plain",
        "--pull=false",
        "-f",
        str(iteration / "Dockerfile"),
        "-t",
        tag,
        str(project),
    ]
    code = run_logged(command, iteration / "build", args.build_timeout)
    log = "\n".join(
        (iteration / "build" / name).read_text(encoding="utf-8", errors="replace")
        for name in ("stdout.log", "stderr.log")
    )
    (iteration / "build-combined.log").write_text(log, encoding="utf-8")
    try:
        classification = write_prompt_evidence(
            iteration,
            dockerfile,
            log,
            (project / "README.md").read_text(encoding="utf-8"),
            code,
        )
    except ValueError:
        metadata["exit_code"] = 1
        metadata["build_exit_code"] = code
        invocation.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    metadata.update(
        {
            "exit_code": 0,
            "build_exit_code": code,
            "classification": classification["classification"],
        }
    )
    invocation.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("E5 目标故障已复现；两份提示已生成，候选仍待记录且不得在 E5 宣称验证通过。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"ERROR: {exc}")
