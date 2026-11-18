"""在统一项目镜像中运行 E8-E10 教学实验。"""
import argparse
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["build", "test", "e8", "e9", "e10"])
    parser.add_argument("--track", choices=["A", "B"], default="B")
    parser.add_argument("--out")
    args = parser.parse_args()

    student_id = subprocess.check_output(
        ["git", "config", "--local", "user.name"], cwd=ROOT, text=True
    ).strip()
    if not re.fullmatch(r"[0-9]{6,16}", student_id):
        parser.error("git user.name 必须是本人数字学号")
    image = f"course-e8e10:{student_id}"

    if args.stage == "build":
        command = [
            "docker", "build", "--progress=plain", "-f",
            str(ROOT / "services/mdfixer/Dockerfile"), "-t", image, str(ROOT),
        ]
    elif args.stage == "test":
        command = [
            "docker", "run", "--rm", "--network", "none", image,
            "python3", "-m", "unittest", "discover", "-s", "tests/e8e10",
            "-p", "test_profile.py", "-v",
        ]
    else:
        if not args.out:
            parser.error("--out 是必需参数")
        work = (ROOT / "work").resolve()
        output = (ROOT / args.out).resolve()
        if output == work or not output.is_relative_to(work):
            parser.error("--out 必须是 work/ 下的新目录")
        if output.exists():
            parser.error("输出目录已存在，请保留旧证据并使用新目录")
        work.mkdir(parents=True, exist_ok=True)
        command = [
            "docker", "run", "--rm", "--network", "none", "--cap-add", "SYS_PTRACE",
            "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
            "-v", f"{work}:/repo/work", "-w", "/repo", image,
            "python3", "scripts/e8e10/lab.py", args.stage, "--track", args.track,
            "--out", "/repo/work/" + output.relative_to(work).as_posix(),
        ]
    print(f"IMAGE={image}", flush=True)
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
