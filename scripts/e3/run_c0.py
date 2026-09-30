"""在独立副本验证 C0，并保留真实命令、输出及环境记录。"""

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
import uuid


ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*"), key=lambda p: p.relative_to(directory).as_posix()):
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode() + b"\0")
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", required=True)
    parser.add_argument("--revision", help="已提交 C0 的完整 SHA；尚未提交时不填")
    args = parser.parse_args()
    if args.revision and (len(args.revision) != 40 or any(c not in "0123456789abcdef" for c in args.revision)):
        parser.error("revision 必须是 40 位小写 Git SHA")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence = ROOT / "evidence/e3/c0" / run_id
    evidence.mkdir(parents=True)
    commands = []
    checks = []
    run = {
        "case_id": "fzy-c0-options", "provenance": "ACTUAL_RUN", "run_id": run_id,
        "operator": args.operator, "started_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "architecture": platform.machine(),
        "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
        "experiment_commit": args.revision, "configuration_id": "fzy-c0-options-linux-v1",
        "source_tree_sha256": source_digest(ROOT / "fixtures/e3/echecker/project"),
        "source_digest_algorithm": "sha256-sorted-posix-path-lf-v1",
        "environment_reference": os.environ.get("E3_ENVIRONMENT_REFERENCE"),
        "status": "RUNNING"
    }
    write_json(evidence / "run.json", run)

    def execute(label, argv, cwd, stdin=None):
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(argv, cwd=cwd, input=stdin, text=True,
                                    capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = subprocess.CompletedProcess(argv, 125, "", str(exc))
        (evidence / (label + ".stdout.log")).write_text(result.stdout, encoding="utf-8")
        (evidence / (label + ".stderr.log")).write_text(result.stderr, encoding="utf-8")
        commands.append({"label": label, "argv": argv, "cwd": str(cwd), "stdin": stdin,
                         "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
                         "exit_code": result.returncode, "stdout": label + ".stdout.log",
                         "stderr": label + ".stderr.log"})
        write_json(evidence / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"{label} 失败：退出码 {result.returncode}，查看对应 stderr 日志")
        return result.stdout

    def require(condition, label):
        checks.append({"check": label, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(label)

    try:
        require(platform.system() == "Linux", "使用 Linux 环境")
        for name, argv in [("os", ["cat", "/etc/os-release"]), ("gcc", ["gcc", "--version"]),
                           ("make", ["make", "--version"]), ("python", [sys.executable, "--version"]),
                           ("git", ["git", "--version"])]:
            execute("environment-" + name, argv, ROOT)
        work = ROOT / "work/e3" / run_id
        upstream = work / "upstream"
        project = work / "c0"
        upstream.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "fixtures/e3/fzy", upstream)
        shutil.copytree(ROOT / "fixtures/e3/echecker/project", project)
        execute("upstream-build", ["make", "CC=gcc"], upstream)
        execute("upstream-tests", ["make", "CC=gcc", "check"], upstream)
        execute("c0-command", ["make", "CC=gcc", "-n", "-B", "src/options.o"], project)
        execute("c0-build", ["make", "CC=gcc"], project)
        require((project / "fzy").is_file(), "生成 fzy 可执行文件")
        require(not (project / "src/options.d").exists(), "选定对象没有自动依赖文件")
        execute("c0-tests", ["make", "CC=gcc", "check"], project)
        expected = json.loads((ROOT / "fixtures/e3/echecker/expected.json").read_text(encoding="utf-8"))
        deps = execute("c0-project-dependencies", ["gcc", "-MM", "src/options.c"], project)
        dependency_paths = deps.replace("\\\n", " ").split(":", 1)[1].split()
        dependency_paths = {os.path.normpath(path) for path in dependency_paths}
        require(dependency_paths == set(expected["expected_graph"]["src/options.o"]),
                "编译器项目依赖与 C0 人工图一致")
        declaration = execute("c0-make-database", ["make", "CC=gcc", "-pn", "src/options.o"], project)
        target_line = next(line for line in declaration.splitlines() if line.startswith("src/options.o:"))
        require(set(target_line.split(":", 1)[1].split()) == dependency_paths,
                "Make 声明与编译器项目依赖一致")
        for index, case in enumerate(expected["functional_cases"]):
            output = execute(f"c0-functional-{index}", ["./fzy", "-e", case["query"]], project, case["stdin"])
            require(output == case["stdout"], f"功能案例 {index} 输出符合人工预期")
        version = execute("c0-version", ["./fzy", "--version"], project)
        require(" " + expected["version_token"] + " " in version, "版本宏符合配置")
        obj = project / "src/options.o"
        before = obj.stat().st_mtime_ns
        header = project / "src/options.h"
        # 文件系统时间分辨率可能较低，明确使头文件晚于对象文件。
        timestamp = max(before + 2_000_000_000, header.stat().st_mtime_ns)
        os.utime(header, ns=(timestamp, timestamp))
        rebuilt = execute("c0-header-rebuild", ["make", "CC=gcc"], project)
        require("-c -o src/options.o src/options.c" in rebuilt and obj.stat().st_mtime_ns != before,
                "仅更新头文件后普通 make 重新编译选定对象")
        output = execute("c0-after-header", ["./fzy", "-e", "apple"], project, "apple\nbanana\n")
        require(output == "apple\n", "头文件重编译后功能仍正确")
        run["status"] = "PASSED"
    except (RuntimeError, OSError, ValueError, StopIteration) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc)
    run["checks"] = checks
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(evidence / "run.json", run)
    write_json(evidence / "commands.json", commands)
    observations = ["# C0 实际观察", "", "人工预期：fixtures/e3/echecker/expected.json（TEAM_ORACLE）。",
                    "", "本记录来源：ACTUAL_RUN。", "", "| 检查 | 实际结果 |", "|---|---|"]
    observations.extend(f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks)
    observations.extend(["", "运行状态：" + run["status"] + "。",
                         "", "失败原因：" + run.get("failure", "无") + "。",
                         "", "Git 提交标签：" + (args.revision or "尚未提交，需用户完成提交后另作带 SHA 的运行记录") + "。"])
    (evidence / "observations.md").write_text("\n".join(observations) + "\n", encoding="utf-8")
    print("EVIDENCE_DIR=" + str(evidence))
    print("STATUS=" + run["status"])
    return 0 if run["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
