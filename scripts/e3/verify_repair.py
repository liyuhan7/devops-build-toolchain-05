#!/usr/bin/env python3
"""在隔离副本中验证 MDFixer 固定输入和 Target 参考修复。"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from run_c0 import source_digest


ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "fixtures/e3/mdfixer"
BASE = ROOT / "fixtures/e3/echecker/project"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workspace_digest(directory):
    """只计入固定 C0 文件与故障头文件，排除编译产物。"""
    paths = [path.relative_to(BASE) for path in BASE.rglob("*") if path.is_file()]
    paths.append(Path("src/e3_mdfixer_marker.h"))
    result = hashlib.sha256()
    for relative in sorted(paths, key=lambda item: item.as_posix()):
        result.update(relative.as_posix().encode() + b"\0")
        result.update((directory / relative).read_bytes().replace(b"\r\n", b"\n"))
        result.update(b"\0")
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = (args.output or ROOT / "evidence/e3/mdfixer" / run_id).resolve()
    work = ROOT / "work/e3" / run_id / "project"
    if output.exists() or work.exists():
        parser.error("证据或运行目录已存在，请选择新目录")
    if platform.system() != "Linux":
        parser.error("行为验证需要 Linux（可使用 WSL 或 Linux 容器）")

    oracle = json.loads((CASE / "fixed-md.json").read_text(encoding="utf-8"))
    projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))
    if source_digest(BASE) != projects["fzy"]["c0_source_tree_sha256"]:
        parser.error("C0 源码摘要与固定项目清单不一致")
    fault = CASE / oracle["patch"]["path"]
    reference = CASE / "reference.patch"
    if digest(fault) != oracle["patch"]["sha256"]:
        parser.error("故障 Patch 摘要与固定报告不一致")

    output.mkdir(parents=True)
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE, work)
    commands = []
    checks = []
    run = {
        "case_id": oracle["case_id"],
        "provenance": "ACTUAL_RUN",
        "run_id": run_id,
        "operator": args.operator,
        "started_at": now(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
        "base_commit": oracle["source_commit"],
        "configuration_id": oracle["configuration_id"],
        "fault_patch_sha256": digest(fault),
        "reference_patch_sha256": digest(reference),
        "status": "RUNNING",
        "checks": checks,
    }

    def save():
        (output / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def command(label, *argv, stdin=None, cwd=work):
        started = now()
        result = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True, check=False)
        (output / f"{label}.stdout.log").write_text(result.stdout, encoding="utf-8")
        (output / f"{label}.stderr.log").write_text(result.stderr, encoding="utf-8")
        commands.append({
            "label": label, "argv": list(argv), "cwd": str(cwd), "stdin": stdin,
            "started_at": started, "finished_at": now(), "exit_code": result.returncode,
            "stdout": f"{label}.stdout.log", "stderr": f"{label}.stderr.log",
        })
        save()
        return result

    def check(label, passed):
        checks.append({"check": label, "passed": bool(passed)})
        save()
        if not passed:
            raise RuntimeError(label)

    try:
        for name, argv in (
            ("os", ["uname", "-a"]), ("gcc", ["gcc", "--version"]),
            ("make", ["make", "--version"]), ("git", ["git", "--version"]),
        ):
            check(f"环境命令 {name}", command(f"environment-{name}", *argv).returncode == 0)

        patch_directory = "--directory=" + work.relative_to(ROOT).as_posix()
        check("故障 Patch 可应用", command("fault-check", "git", "apply", "--check", "--verbose", patch_directory, "--ignore-whitespace", str(fault), cwd=ROOT).returncode == 0)
        check("故障 Patch 应用", command("fault-apply", "git", "apply", "--verbose", patch_directory, "--ignore-whitespace", str(fault), cwd=ROOT).returncode == 0)
        check("故障源码和头文件已写入", (work / "src/e3_mdfixer_marker.h").is_file() and '"e3_mdfixer_marker.h"' in (work / "src/options.c").read_text(encoding="utf-8"))
        run["fault_workspace_digest"] = workspace_digest(work)
        check("故障样本首次构建", command("before-build", "make", "CC=gcc").returncode == 0)
        before = command("before-version", "./fzy", "--version")
        check("初始版本包含 one", before.returncode == 0 and "MDFIXER_MARKER=one" in before.stdout)
        check("故障样本上游测试", command("before-check", "make", "CC=gcc", "check").returncode == 0)
        functional = command("before-functional", "./fzy", "-e", "apple", stdin="apple\nbanana\n")
        check("故障样本功能输出", functional.returncode == 0 and functional.stdout == "apple\n")

        header = work / "src/e3_mdfixer_marker.h"
        time.sleep(1.1)
        header.write_text('#define MDFIXER_MARKER "MDFIXER_MARKER=two"\n', encoding="utf-8")
        check("故障头文件晚于对象", header.stat().st_mtime_ns > (work / "src/options.o").stat().st_mtime_ns)
        before_incremental = command("before-incremental", "make", "CC=gcc")
        stale = command("before-stale-version", "./fzy", "--version")
        check("修复前漏重建并保留 one", before_incremental.returncode == 0 and "src/options.o" not in before_incremental.stdout and stale.returncode == 0 and "MDFIXER_MARKER=one" in stale.stdout)

        check("参考 Patch 可应用", command("reference-check", "git", "apply", "--check", "--verbose", patch_directory, "--ignore-whitespace", str(reference), cwd=ROOT).returncode == 0)
        check("参考 Patch 应用", command("reference-apply", "git", "apply", "--verbose", patch_directory, "--ignore-whitespace", str(reference), cwd=ROOT).returncode == 0)
        run["repair_candidate_workspace_digest"] = workspace_digest(work)
        rule = (work / "Makefile").read_text(encoding="utf-8")
        check("人工依赖复核", "src/options.o: src/options.c src/options.h config.h src/e3_mdfixer_marker.h" in rule)
        repaired = command("repaired-build", "make", "CC=gcc")
        repaired_version = command("repaired-version", "./fzy", "--version")
        check("补丁应用后构建并更新为 two", repaired.returncode == 0 and "src/options.o" in repaired.stdout and repaired_version.returncode == 0 and "MDFIXER_MARKER=two" in repaired_version.stdout)
        check("修复后上游测试", command("repaired-check", "make", "CC=gcc", "check").returncode == 0)
        functional = command("repaired-functional", "./fzy", "-e", "apple", stdin="apple\nbanana\n")
        check("修复后功能输出", functional.returncode == 0 and functional.stdout == "apple\n")

        time.sleep(1.1)
        header.write_text('#define MDFIXER_MARKER "MDFIXER_MARKER=three"\n', encoding="utf-8")
        run["final_workspace_digest"] = workspace_digest(work)
        check("再次修改的头文件晚于对象", header.stat().st_mtime_ns > (work / "src/options.o").stat().st_mtime_ns)
        incremental = command("repaired-incremental", "make", "CC=gcc")
        current = command("repaired-incremental-version", "./fzy", "--version")
        check("不 clean 的增量重建得到 three", incremental.returncode == 0 and "src/options.o" in incremental.stdout and current.returncode == 0 and "MDFIXER_MARKER=three" in current.stdout)
        check("修复后 clean", command("repaired-clean", "make", "veryclean").returncode == 0)
        check("修复后 clean build", command("repaired-clean-build", "make", "CC=gcc").returncode == 0)
        clean_version = command("repaired-clean-version", "./fzy", "--version")
        check("修复后 clean build 保留 three", clean_version.returncode == 0 and "MDFIXER_MARKER=three" in clean_version.stdout)
        run["status"] = "PASSED"
    except (OSError, RuntimeError) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc)
    finally:
        run["finished_at"] = now()
        save()
        lines = ["# MDFixer 修复验证观察", "", "人工预期：fixtures/e3/mdfixer/fixed-md.json（TEAM_ORACLE）。本记录来源：ACTUAL_RUN。", "", "| 检查 | 结果 |", "|---|---|"]
        lines += [f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks]
        lines += ["", f"运行状态：{run['status']}。", f"失败原因：{run.get('failure', '无')}。", "", "本案例只做人工依赖复核，未运行真实 MDFixer/EChecker。"]
        (output / "observations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"EVIDENCE_DIR={output}")
        print(f"STATUS={run['status']}")
    return 0 if run["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
