"""从固定 C0 验证 MD/RD 的增量行为，保存输入身份和真实命令。"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid

from run_c0 import reconstruct_c0, source_digest, write_json

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.operator.strip():
        parser.error("operator 不得为空")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = (args.output or ROOT / "evidence/e3/buildchecker" / run_id).resolve()
    if evidence.exists():
        parser.error("证据目录已存在，请指定新目录")
    evidence.mkdir(parents=True)
    work = ROOT / "work/e3/buildchecker" / run_id
    work.parent.mkdir(parents=True, exist_ok=True)
    patch = ROOT / "fixtures/e3/buildchecker/md-rd.patch"
    c0_patch = ROOT / "fixtures/e3/echecker/c0.patch"
    projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))["fzy"]
    commands, checks = [], []
    run = {
        "case_id": "fzy-c0-options-md-rd", "provenance": "ACTUAL_RUN",
        "operator": args.operator, "run_id": run_id, "started_at": now(), "status": "RUNNING",
        "base_commit": "0769e815259ab2cae12a21be43256c05906215e0",
        "upstream_commit": projects["upstream_commit"], "configuration_id": "fzy-c0-options-linux-v1",
        "target": "src/options.o", "platform": platform.platform(), "architecture": platform.machine(),
        "environment_reference": os.environ.get("E3_ENVIRONMENT_REFERENCE"),
        "patch": "fixtures/e3/buildchecker/md-rd.patch",
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "source_digest_algorithm": "sha256-sorted-posix-path-lf-v1", "checks": checks,
    }
    write_json(evidence / "run.json", run)

    def execute(label, argv, cwd=work, stdin=None):
        started = now()
        print("执行：" + label, flush=True)
        try:
            result = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = subprocess.CompletedProcess(argv, 125, b"", str(exc).encode("utf-8"))
        (evidence / (label + ".stdout.log")).write_bytes(result.stdout)
        (evidence / (label + ".stderr.log")).write_bytes(result.stderr)
        (evidence / (label + ".exit")).write_text(str(result.returncode) + "\n", encoding="utf-8")
        commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
                         "stdin": stdin.decode("utf-8") if stdin is not None else None,
                         "environment": {}, "started_at": started, "finished_at": now(),
                         "exit_code": result.returncode, "stdout": label + ".stdout.log",
                         "stderr": label + ".stderr.log"})
        write_json(evidence / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"{label} 退出码 {result.returncode}；查看对应 stderr 日志")
        return result.stdout

    def require(condition, label):
        checks.append({"check": label, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(label)

    def mtime(label):
        value = (work / "src/options.o").stat().st_mtime_ns
        (evidence / (label + ".mtime")).write_text(str(value) + "\n", encoding="utf-8")
        return value

    try:
        require(platform.system() == "Linux", "使用 Linux 构建环境")
        git = ["git", "-c", "safe.directory=" + str(ROOT)]
        run["experiment_commit"] = execute("git-revision", git + ["rev-parse", "HEAD"], ROOT).decode().strip()
        run["worktree_dirty"] = bool(execute("git-status", git + ["status", "--porcelain"], ROOT))
        run["runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name, argv in [("os", ["cat", "/etc/os-release"]), ("gcc", ["gcc", "--version"]),
                           ("make", ["make", "--version"]), ("python", [sys.executable, "--version"]),
                           ("git", ["git", "--version"])]:
            execute("environment-" + name, argv, ROOT)
        require(source_digest(ROOT / "fixtures/e3/fzy") == projects["source_tree_sha256"], "上游源码摘要一致")
        reconstruct_c0(ROOT / "fixtures/e3/fzy", c0_patch, work, execute)
        run["c0_source_tree_sha256"] = source_digest(work)
        run["c0_patch_sha256"] = hashlib.sha256(c0_patch.read_bytes()).hexdigest()
        require(run["c0_source_tree_sha256"] == projects["c0_source_tree_sha256"], "冻结 C0 源码摘要一致")
        shutil.copyfile(patch, evidence / "md-rd.patch")
        # Patch 只作用于独立 C0 副本，Git 元数据不属于实验输入。
        execute("sample-git-init", ["git", "init", "-q"])
        try:
            execute("patch-check", ["git", "apply", "--check", "--ignore-whitespace", str(patch)])
            execute("patch", ["git", "apply", "--ignore-whitespace", str(patch)])
        finally:
            if (work / ".git").exists():
                shutil.rmtree(work / ".git")
        run["sample_source_tree_sha256"] = source_digest(work)
        execute("initial-clean", ["make", "clean"])
        execute("initial-build", ["make", "CC=gcc"])
        tests = execute("initial-tests", ["make", "CC=gcc", "check"])
        require(b"Pass: 32, fail: 0, skip: 0." in tests, "32 项项目测试通过")
        require(execute("initial-functional", ["./fzy", "-e", "apple"], stdin=b"apple\nbanana\n") == b"apple\n", "初始功能标准输出为 apple")
        require(b"E3_MD_MARKER=one" in execute("initial-version", ["./fzy", "--version"]), "初始标记为 one")
        before = mtime("initial-options")
        time.sleep(1.1)
        execute("md-header-change", [sys.executable, "-c", "from pathlib import Path; p=Path('src/e3_md_marker.h'); p.write_text(p.read_text().replace('E3_MD_MARKER=one','E3_MD_MARKER=two'))"])
        execute("md-ordinary-make", ["make", "CC=gcc"])
        require(mtime("md-ordinary-options") == before, "MD 普通构建保留旧对象")
        require(b"E3_MD_MARKER=one" in execute("md-ordinary-version", ["./fzy", "--version"]), "MD 普通构建保留 one")
        execute("md-clean", ["make", "clean"])
        execute("md-clean-build", ["make", "CC=gcc"])
        clean_version = execute("md-clean-version", ["./fzy", "--version"])
        require(b"E3_MD_MARKER=two" in clean_version, "MD clean 构建读取 two")
        before = mtime("rd-before-options")
        time.sleep(1.1)
        execute("rd-header-change", [sys.executable, "-c", "from pathlib import Path; p=Path('src/e3_rd_unused.h'); p.write_text(p.read_text().replace('Deliberately','Deliberately touched'))"])
        execute("rd-ordinary-make", ["make", "CC=gcc"])
        require(mtime("rd-after-options") > before, "RD 普通构建发生额外重编译")
        require(execute("rd-version", ["./fzy", "--version"]) == clean_version, "RD 版本输出保持不变")
        require(execute("rd-functional", ["./fzy", "-e", "apple"], stdin=b"apple\nbanana\n") == b"apple\n", "RD 功能标准输出为 apple")
        run["status"] = "PASSED"
    except (Exception, KeyboardInterrupt) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc) or "运行被中断"
    finally:
        run["finished_at"] = now()
        write_json(evidence / "run.json", run)
        write_json(evidence / "commands.json", commands)
        rows = "\n".join(f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks)
        (evidence / "observations.md").write_text(
            "# MD/RD 实际观察\n\n预期：固定 C0 注入一条 MISSING 和一条 REDUNDANT（TEAM_ORACLE）。\n"
            "来源：ACTUAL_RUN。普通构建与 clean 构建分别保留对象状态进行对照。\n\n"
            "| 检查 | 实际结果 |\n|---|---|\n" + rows +
            f"\n\n状态：{run['status']}。失败原因：{run.get('failure', '无')}。\n", encoding="utf-8")
        print(f"STATUS={run['status']}\nEVIDENCE_DIR={evidence}")
    return 0 if run["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
