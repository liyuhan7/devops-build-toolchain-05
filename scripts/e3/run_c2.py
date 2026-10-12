"""在 Linux 独立副本复现 EChecker C2 的编译命令变化。"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import uuid

from run_c0 import reconstruct_c0, source_digest, write_json


ROOT = Path(__file__).resolve().parents[2]
C0_PATCH = ROOT / "fixtures/e3/echecker/c0.patch"
C1_PATCH = ROOT / "fixtures/e3/echecker/c1.patch"
C2_PATCH = ROOT / "fixtures/e3/echecker/c2.patch"


def source_files(directory):
    """读取影响 C1/C2 源码等价性的 C/H 文件，并规范化行尾。"""
    return {
        path.relative_to(directory).as_posix(): path.read_bytes().replace(b"\r\n", b"\n")
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in {".c", ".h"} and path.name != "config.h"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", required=True, help="实际执行者姓名")
    parser.add_argument("--revision", help="只包含 C2 配置变化的完整 Git SHA；提交前验证可不填")
    args = parser.parse_args()
    if args.revision and not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision 必须是 40 位小写 Git SHA")

    metadata = json.loads((ROOT / "fixtures/e3/echecker/commits.json").read_text(encoding="utf-8"))
    versions = metadata["versions"]
    expected = json.loads((ROOT / "fixtures/e3/echecker/c2-expected.json").read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = ROOT / "evidence/e3/echecker" / run_id
    evidence.mkdir(parents=True)
    commands = []
    checks = []
    run = {
        "case_id": "fzy-c2-options-command",
        "provenance": "ACTUAL_RUN",
        "run_id": run_id,
        "operator": args.operator,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "upstream_commit": metadata["upstream_commit"],
        "base_commit": versions["C1"]["commit_sha"],
        "experiment_commit": args.revision or versions["C2"]["commit_sha"],
        "previous_configuration_id": versions["C1"]["configuration_id"],
        "configuration_id": versions["C2"]["configuration_id"],
        "target": "src/options.o",
        "status": "RUNNING",
    }
    write_json(evidence / "run.json", run)

    def execute(label, argv, cwd, stdin=None):
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(
                argv,
                cwd=cwd,
                input=stdin,
                text=True,
                capture_output=True,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = subprocess.CompletedProcess(argv, 125, "", str(exc))
        (evidence / f"{label}.stdout.log").write_text(result.stdout, encoding="utf-8")
        (evidence / f"{label}.stderr.log").write_text(result.stderr, encoding="utf-8")
        commands.append(
            {
                "label": label,
                "argv": argv,
                "cwd": str(cwd),
                "stdin": stdin,
                "started_at": started,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": result.returncode,
                "stdout": f"{label}.stdout.log",
                "stderr": f"{label}.stderr.log",
            }
        )
        write_json(evidence / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"{label} 失败：退出码 {result.returncode}")
        return result.stdout

    def require(condition, label, actual=None):
        check = {"check": label, "passed": bool(condition)}
        if actual is not None:
            check["actual"] = actual
        checks.append(check)
        if not condition:
            raise RuntimeError(label)

    def apply_patch(label, workspace, patch):
        execute(f"{label}-git-init", ["git", "init", "-q"], workspace)
        try:
            execute(
                f"{label}-patch-check",
                ["git", "apply", "--check", "--ignore-whitespace", str(patch)],
                workspace,
            )
            execute(
                f"{label}-patch-apply",
                ["git", "apply", "--ignore-whitespace", str(patch)],
                workspace,
            )
        finally:
            if (workspace / ".git").exists():
                shutil.rmtree(workspace / ".git")

    try:
        require(platform.system() == "Linux", "使用 Linux 环境")
        for name, argv in [
            ("os", ["cat", "/etc/os-release"]),
            ("gcc", ["gcc", "--version"]),
            ("make", ["make", "--version"]),
            ("python", [sys.executable, "--version"]),
            ("git", ["git", "--version"]),
        ]:
            execute("environment-" + name, argv, ROOT)

        work = ROOT / "work/e3" / run_id
        c1_to_c2 = work / "c1-to-c2"
        c2_reference = work / "c2-reference"
        c2_clean = work / "c2-clean"
        work.mkdir(parents=True)
        reconstruct_c0(ROOT / "fixtures/e3/fzy", C0_PATCH, c1_to_c2, execute)
        apply_patch("c1", c1_to_c2, C1_PATCH)
        require(source_digest(c1_to_c2) == versions["C1"]["source_tree_sha256"], "重建的 C1 与固定摘要一致")
        c1_sources = source_files(c1_to_c2)
        shutil.copytree(c1_to_c2, c2_reference)
        apply_patch("c2-reference", c2_reference, C2_PATCH)
        require(
            source_digest(c2_reference) == source_digest(ROOT / "fixtures/e3/echecker/project"),
            "C1 加 C2 Patch 与签入的 C2 项目一致",
        )

        execute("c1-configure", ["make", "CC=gcc", "config.h"], c1_to_c2)
        c1_command = execute("c1-command", ["make", "CC=gcc", "-n", "-B", "src/options.o"], c1_to_c2)
        execute("c1-clean", ["make", "clean"], c1_to_c2)
        execute("c1-build", ["make", "CC=gcc"], c1_to_c2)
        execute("c1-tests", ["make", "CC=gcc", "check"], c1_to_c2)
        output = execute("c1-functional", ["./fzy", "-e", "apple"], c1_to_c2, "apple\nbanana\n")
        require(output == "apple\n", "C1 功能断言通过", output)
        c1_version = execute("c1-version", ["./fzy", "--version"], c1_to_c2)
        require(" 1.1 " in c1_version and "E3_C1_MARKER=one" in c1_version, "C1 版本输出正确", c1_version.strip())
        c1_options_mtime = (c1_to_c2 / "src/options.o").stat().st_mtime_ns

        apply_patch("c2", c1_to_c2, C2_PATCH)
        require(source_files(c1_to_c2) == c1_sources, "C2 的 .c/.h 与 C1 完全一致")
        require((c1_to_c2 / "Makefile").read_text(encoding="utf-8").startswith("VERSION=1.2-e3\n"), "C2 Makefile 使用新 VERSION")
        c2_command = execute("c2-command", ["make", "CC=gcc", "-n", "-B", "src/options.o"], c1_to_c2)
        require(c1_command != c2_command, "C1/C2 编译命令发生变化")
        require("1.1" in c1_command and "1.2-e3" in c2_command, "VERSION 编译宏按预期变化")

        execute("c2-configure", ["make", "CC=gcc", "config.h"], c1_to_c2)
        actual_graph = execute("c2-actual-dependencies", ["gcc", "-MM", "src/options.c"], c1_to_c2)
        actual = {os.path.normpath(path) for path in actual_graph.replace("\\\n", " ").split(":", 1)[1].split()}
        declared_graph = execute("c2-declared-dependencies", ["make", "CC=gcc", "-pn", "src/options.o"], c1_to_c2)
        target_line = next(line for line in declared_graph.splitlines() if line.startswith("src/options.o:"))
        declared = {os.path.normpath(path) for path in target_line.split(":", 1)[1].split()}
        expected_actual = {os.path.normpath(path) for path in expected["scope"]["actual_project_inputs"]}
        expected_declared = {os.path.normpath(path) for path in expected["scope"]["declared_inputs"]}
        require(actual == expected_actual, "C2 编译器实际依赖与 C1 一致", sorted(actual))
        require(declared == expected_declared, "C2 Make 声明与 C1 一致", sorted(declared))
        require(actual - declared == {os.path.normpath("src/e3_c1_marker.h")}, "C1 的 MISSING 在 C2 保持 unchanged")

        ordinary = execute("c2-ordinary-build", ["make", "CC=gcc"], c1_to_c2)
        require((c1_to_c2 / "src/options.o").stat().st_mtime_ns == c1_options_mtime, "保留 C1 对象时普通 make 未重编译目标", ordinary.strip())
        ordinary_version = execute("c2-ordinary-version", ["./fzy", "--version"], c1_to_c2)
        require(" 1.1 " in ordinary_version and "E3_C1_MARKER=one" in ordinary_version, "普通 make 保留 C1 版本输出", ordinary_version.strip())

        shutil.copytree(c1_to_c2, c2_clean)
        execute("c2-clean", ["make", "clean"], c2_clean)
        clean_build = execute("c2-clean-build", ["make", "CC=gcc"], c2_clean)
        require("-DVERSION=\\\"1.2-e3\\\"" in clean_build, "C2 clean build 使用新 VERSION 编译宏")
        clean_version = execute("c2-clean-version", ["./fzy", "--version"], c2_clean)
        require(" 1.2-e3 " in clean_version and "E3_C1_MARKER=one" in clean_version, "C2 clean build 输出新版本", clean_version.strip())
        execute("c2-clean-tests", ["make", "CC=gcc", "check"], c2_clean)
        output = execute("c2-clean-functional", ["./fzy", "-e", "apple"], c2_clean, "apple\nbanana\n")
        require(output == "apple\n", "C2 clean build 后功能断言通过", output)
        run["status"] = "PASSED" if run["experiment_commit"] else "PASSED_PRECOMMIT"
    except (RuntimeError, OSError, ValueError, StopIteration, KeyError) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc)

    run["checks"] = checks
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(evidence / "run.json", run)
    write_json(evidence / "commands.json", commands)
    observations = [
        "# C2 实际观察",
        "",
        "人工预期：`fixtures/e3/echecker/c2-expected.json`（`TEAM_ORACLE`）。",
        "",
        "本记录来源：`ACTUAL_RUN`。",
        "",
        "| 检查 | 实际结果 |",
        "|---|---|",
    ]
    observations.extend(f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks)
    observations.extend(["", "运行状态：" + run["status"] + "。", "", "失败原因：" + run.get("failure", "无") + "。"])
    if not run["experiment_commit"]:
        observations.extend(["", "说明：C2 尚未形成用户提交，本记录用于提交前验证；提交后需重新运行并回填真实 SHA。"]) 
    (evidence / "observations.md").write_text("\n".join(observations) + "\n", encoding="utf-8")
    print("EVIDENCE_DIR=" + str(evidence))
    print("STATUS=" + run["status"])
    return 0 if run["status"] in {"PASSED", "PASSED_PRECOMMIT"} else 1


if __name__ == "__main__":
    sys.exit(main())
