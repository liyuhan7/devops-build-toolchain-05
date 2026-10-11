"""在 Linux 独立副本复现 EChecker C1 的新增缺失依赖。"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

from run_c0 import source_digest, write_json


ROOT = Path(__file__).resolve().parents[2]
C1_COMMIT = "563f9c5b797aff1174f726f029e67cd352400a24"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", required=True, help="实际执行者姓名")
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = ROOT / "evidence/e3/echecker" / run_id
    evidence.mkdir(parents=True)
    commands = []
    checks = []
    run = {
        "case_id": "fzy-c1-options-include",
        "provenance": "ACTUAL_RUN",
        "run_id": run_id,
        "operator": args.operator,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
        "base_commit": "0769e815259ab2cae12a21be43256c05906215e0",
        "experiment_commit": C1_COMMIT,
        "configuration_id": "fzy-c0-options-linux-v1",
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
        c0 = work / "c0"
        c1 = work / "c1"
        work.mkdir(parents=True)
        shutil.copytree(ROOT / "fixtures/e3/fzy", c0)
        execute("c0-git-init", ["git", "init", "-q"], c0)
        execute("c0-patch-check", ["git", "apply", "--check", str(ROOT / "fixtures/e3/echecker/c0.patch")], c0)
        execute("c0-patch-apply", ["git", "apply", str(ROOT / "fixtures/e3/echecker/c0.patch")], c0)
        shutil.rmtree(c0 / ".git")
        shutil.copytree(c0, c1)
        execute("c1-git-init", ["git", "init", "-q"], c1)
        execute(
            "c1-patch-check",
            ["git", "apply", "--check", "--ignore-whitespace", str(ROOT / "fixtures/e3/echecker/c1.patch")],
            c1,
        )
        execute(
            "c1-patch-apply",
            ["git", "apply", "--ignore-whitespace", str(ROOT / "fixtures/e3/echecker/c1.patch")],
            c1,
        )
        shutil.rmtree(c1 / ".git")
        require(
            source_digest(c1) == source_digest(ROOT / "fixtures/e3/echecker/project"),
            "C0 加 C1 Patch 与签入的 C1 项目一致",
        )

        expected = json.loads((ROOT / "fixtures/e3/echecker/c1-expected.json").read_text(encoding="utf-8"))
        execute("c1-configure", ["make", "CC=gcc", "config.h"], c1)
        actual_graph = execute("c1-actual-dependencies", ["gcc", "-MM", "src/options.c"], c1)
        actual = {
            os.path.normpath(path)
            for path in actual_graph.replace("\\\n", " ").split(":", 1)[1].split()
        }
        expected_actual = {os.path.normpath(path) for path in expected["scope"]["actual_project_inputs"]}
        require(actual == expected_actual, "C1 编译器实际依赖与人工图一致", sorted(actual))

        declared_graph = execute("c1-declared-dependencies", ["make", "CC=gcc", "-pn", "src/options.o"], c1)
        target_line = next(line for line in declared_graph.splitlines() if line.startswith("src/options.o:"))
        declared = {os.path.normpath(path) for path in target_line.split(":", 1)[1].split()}
        expected_declared = {os.path.normpath(path) for path in expected["scope"]["declared_inputs"]}
        require(declared == expected_declared, "C1 Make 声明与人工图一致", sorted(declared))
        require(actual - declared == {os.path.normpath("src/e3_c1_marker.h")}, "只新增一条 MISSING", sorted(actual - declared))

        execute("c1-command", ["make", "CC=gcc", "-n", "-B", "src/options.o"], c1)
        execute("initial-clean", ["make", "clean"], c1)
        execute("initial-build", ["make", "CC=gcc"], c1)
        execute("initial-tests", ["make", "CC=gcc", "check"], c1)
        output = execute("initial-functional", ["./fzy", "-e", "apple"], c1, "apple\nbanana\n")
        require(output == "apple\n", "初始功能断言通过", output)
        version = execute("initial-version", ["./fzy", "--version"], c1)
        require("E3_C1_MARKER=one" in version, "初始版本读取新增头文件", version.strip())
        require(not (c1 / "src/options.d").exists(), "选定对象没有自动依赖文件")

        obj = c1 / "src/options.o"
        before = obj.stat().st_mtime_ns
        header = c1 / "src/e3_c1_marker.h"
        header.write_text(header.read_text(encoding="utf-8").replace("E3_C1_MARKER=one", "E3_C1_MARKER=two"), encoding="utf-8")
        timestamp = max(before + 2_000_000_000, header.stat().st_mtime_ns)
        os.utime(header, ns=(timestamp, timestamp))
        incremental = execute("incremental-build", ["make", "CC=gcc"], c1)
        require(obj.stat().st_mtime_ns == before, "只改新增头文件时普通 make 未重编译目标", incremental.strip())
        version = execute("incremental-version", ["./fzy", "--version"], c1)
        require("E3_C1_MARKER=one" in version, "普通 make 保留旧产物", version.strip())

        execute("clean-after-change", ["make", "clean"], c1)
        clean_build = execute("clean-build-after-change", ["make", "CC=gcc"], c1)
        require("-c -o src/options.o src/options.c" in clean_build, "clean 构建重新编译目标")
        version = execute("clean-version-after-change", ["./fzy", "--version"], c1)
        require("E3_C1_MARKER=two" in version, "clean 构建读取头文件新值", version.strip())
        execute("clean-tests-after-change", ["make", "CC=gcc", "check"], c1)
        output = execute("clean-functional-after-change", ["./fzy", "-e", "apple"], c1, "apple\nbanana\n")
        require(output == "apple\n", "clean 构建后功能断言通过", output)
        run["status"] = "PASSED"
    except (RuntimeError, OSError, ValueError, StopIteration, KeyError) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc)

    run["checks"] = checks
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(evidence / "run.json", run)
    write_json(evidence / "commands.json", commands)
    observations = [
        "# C1 实际观察",
        "",
        "人工预期：`fixtures/e3/echecker/c1-expected.json`（`TEAM_ORACLE`）。",
        "",
        "本记录来源：`ACTUAL_RUN`。",
        "",
        "| 检查 | 实际结果 |",
        "|---|---|",
    ]
    observations.extend(f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks)
    observations.extend(["", "运行状态：" + run["status"] + "。", "", "失败原因：" + run.get("failure", "无") + "。"])
    (evidence / "observations.md").write_text("\n".join(observations) + "\n", encoding="utf-8")
    print("EVIDENCE_DIR=" + str(evidence))
    print("STATUS=" + run["status"])
    return 0 if run["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
