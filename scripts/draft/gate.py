"""用已记录候选和显式故障注入运行真实 Docker 门禁。"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SERVICE_TEST_ARGS = ["pytest", "-c", "services/draft/pytest.ini", "services/draft/tests"]

def evaluate(name, code, report):
    if name == "invalid-candidate":
        if code != 1 or report.get("status") != "FAILED" or "required project/build/runtime" not in report.get("error", "") or report.get("attempts"):
            raise ValueError("Changed CMD candidate was not rejected before building")
        return
    if not report.get("trace_id"):
        raise ValueError("Missing trace_id")
    attempts = report.get("attempts", [])
    if len(attempts) != 2 or [a.get("iteration") for a in attempts] != [1, 2]:
        detail = report.get("error", "No workflow error supplied")
        classification = attempts[0].get("failure_class", "UNKNOWN") if attempts else "NOT_STARTED"
        raise ValueError(f"Workflow stopped before two ordered attempts ({classification}): {detail}")
    if attempts[0].get("build_exit_code") != 1 or attempts[0].get("failure_class") != "MISSING_MAKE":
        raise ValueError("Baseline did not reach missing make; inspect network/build logs")
    if name == "build-failed":
        if code != 1 or report.get("status") != "FAILED" or attempts[1].get("build_exit_code") != 1 or "Repair candidate build failed" not in report.get("error", "") or "verification" in report:
            raise ValueError("Failed repair build did not stop verification")
        return
    if attempts[1].get("build_exit_code") != 0:
        if report.get("status") == "TIMED_OUT":
            raise ValueError("Candidate BUILD timed out before runtime fault could be tested; inspect downloads and build budget")
        raise ValueError("Candidate build failed before runtime fault could be tested")
    if name == "runtime-timeout":
        if code != 1 or report.get("status") != "TIMED_OUT" or "Docker client command exceeded" not in report.get("error", ""):
            raise ValueError("Runtime timeout did not produce the expected terminal state")
        return
    verification = report.get("verification", {})
    if verification.get("exit_code") != 0 or verification.get("actual_output") != "hello E3\n":
        raise ValueError("Unexpected program exit/output")
    if verification.get("command", [None])[-1] != attempts[1].get("image_id"):
        raise ValueError("Verified image differs from built image")
    if name == "success":
        if code != 0 or report.get("status") != "SUCCEEDED" or verification.get("output_matches") is not True or verification.get("expected_output") != "hello E3":
            raise ValueError("Success workflow did not pass verification")
    elif name == "wrong-output":
        if code != 1 or report.get("status") != "FAILED" or verification.get("output_matches") is not False or verification.get("expected_output") != "intentionally wrong output":
            raise ValueError("Output mismatch was not rejected")
    else:
        raise ValueError("Unknown oracle")

def run_logged(command, folder, timeout=720):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    with (folder / "stdout.log").open("w", encoding="utf-8") as out, (folder / "stderr.log").open("w", encoding="utf-8") as err:
        try:
            return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            cid = folder / "service-container-id.txt"
            if cid.exists():
                subprocess.run(["docker", "rm", "-f", cid.read_text().strip()], timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            raise ValueError("Outer service timed out; inspect saved logs and Docker daemon")

def check_artifacts(name, evidence, report):
    if name == "invalid-candidate":
        if (evidence / "project").exists():
            raise ValueError("Invalid candidate unexpectedly created a build project")
        return
    if (evidence / "project/Dockerfile.reference").exists():
        raise ValueError("Reference answer leaked into build context")
    logs = (evidence / "iter-01/build-stdout.log").read_text() + (evidence / "iter-01/build-stderr.log").read_text()
    if not re.search(r"/bin/sh:.*\bmake: not found", logs):
        raise ValueError("Missing actual baseline failure log")
    if name in ("success", "wrong-output"):
        image = json.loads((evidence / "iter-02/image-inspect.json").read_text())[0]["Id"]
        if image != report["attempts"][1]["image_id"]:
            raise ValueError("Saved image ID mismatch")
        if (evidence / "verify.log").read_text() != report["verification"]["actual_output"]:
            raise ValueError("Saved stdout mismatch")
    elif name == "build-failed":
        logs = (evidence / "iter-02/build-stdout.log").read_text() + (evidence / "iter-02/build-stderr.log").read_text()
        if "exit code: 23" not in logs:
            raise ValueError("Injected exit-23 failure not found in actual log")
    elif name == "runtime-timeout":
        cid = (evidence / "verify-container-id.txt").read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise ValueError("No valid runtime container ID to check cleanup")
        code = run_logged(["docker", "container", "inspect", cid], evidence / "cleanup-check", timeout=30)
        if code == 0:
            raise ValueError("Timed-out runtime container still exists")
        error = (evidence / "cleanup-check/stderr.log").read_text().lower()
        if "no such" not in error:
            raise ValueError("Cleanup check failed for an unrelated reason")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="draft-lab:local")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--build-timeout", type=int, default=300)
    parser.add_argument("--case", action="append", choices=("success", "wrong-output", "invalid-candidate", "build-failed", "runtime-timeout"), help="Run selected cases only; repeat flag for multiple cases")
    parser.add_argument("--inject-bad-oracle", action="store_true")
    args = parser.parse_args()
    if args.build_timeout <= 0:
        parser.error("Build timeout must be positive")
    cases = list(dict.fromkeys(args.case or ("success", "wrong-output", "invalid-candidate", "build-failed", "runtime-timeout")))
    if os.name != "posix":
        parser.error("Run on the Ubuntu host using Docker CLI")
    fixture, candidate, output = ROOT / "fixtures/draft", Path(args.candidate).resolve(), Path(args.out).resolve()
    if not fixture.is_dir() or not candidate.is_file():
        parser.error("Fixture or recorded candidate missing")
    if output == fixture or fixture in output.parents or (output.exists() and any(output.iterdir())):
        parser.error("Output must be fresh and outside the original fixture")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        if run_logged(["docker", "image", "inspect", args.image], output / "image", 30) != 0:
            raise ValueError("Service image unavailable")
        print("[unit-tests] Running service tests...", flush=True)
        unit = output / "unit-tests"
        unit.mkdir()
        code = run_logged(["docker", "run", "--rm", "--network", "none", "--cidfile", str(unit / "service-container-id.txt"), args.image, *SERVICE_TEST_ARGS], unit, 120)
        rows.append({"case": "unit-tests", "passed": code == 0, "exit_code": code})
        if code != 0:
            raise ValueError("Service unit tests failed")
        candidate_text = candidate.read_text(encoding="utf-8")
        for name in cases:
            print(f"[{name}] Running real workflow; build logs are saved...", flush=True)
            case = output / name
            case.mkdir()
            source, evidence = case / "fixture", case / "evidence"
            shutil.copytree(fixture, source)
            evidence.mkdir()
            text = candidate_text
            if name == "invalid-candidate":
                if 'CMD ["./hello"]' not in text:
                    raise ValueError("Recorded candidate CMD differs; review injection")
                text = text.replace('CMD ["./hello"]', 'CMD ["echo", "hello E3"]')
            elif name == "build-failed":
                if "RUN make" not in text:
                    raise ValueError("Recorded candidate build differs; review injection")
                text = text.replace("RUN make", "RUN exit 23\nRUN make")
            elif name == "runtime-timeout":
                # 只改变 CMD，保持 COPY 输入不变以复用依赖层；故障注入不代表新模型回复。
                old_cmd = 'CMD ["./hello"]'
                delayed_cmd = 'CMD ["sh", "-c", "sleep 10; exec ./hello"]'
                broken_path = source / "Dockerfile.broken"
                broken_text = broken_path.read_text(encoding="utf-8")
                if old_cmd not in text or old_cmd not in broken_text:
                    raise ValueError("Fixture/candidate CMD differs; review timeout injection")
                text = text.replace(old_cmd, delayed_cmd)
                broken_path.write_text(broken_text.replace(old_cmd, delayed_cmd), encoding="utf-8")
                (case / "fault-injection.json").write_text(json.dumps({
                    "type": "DELAYED_CONTAINER_START", "delay_seconds": 10,
                    "verify_timeout_seconds": 1, "source_files_changed": [],
                    "changed_files": ["fixture/Dockerfile.broken", "candidate.Dockerfile"],
                    "note": "Controlled test mutation, not an additional model response"
                }, indent=2), encoding="utf-8")
            path = case / "candidate.Dockerfile"
            path.write_text(text, encoding="utf-8")
            expected = "intentionally wrong output" if name == "wrong-output" else "hello E3"
            # Buildx 可能通过客户端读取仓库凭据，服务容器需联网；构建产物运行时仍断网。
            command = ["docker", "run", "--rm", "--network", "bridge", "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
                       "--group-add", str(Path("/var/run/docker.sock").stat().st_gid), "-v", "/var/run/docker.sock:/var/run/docker.sock",
                       "--cidfile", str(case / "service-container-id.txt"),
                       "--mount", f"type=bind,src={source},dst=/fixture,readonly",
                       "--mount", f"type=bind,src={path},dst=/candidate.Dockerfile,readonly",
                       "--mount", f"type=bind,src={evidence},dst=/evidence", args.image,
                       "python3", "-m", "draft", "auto-build", "--fixture", "/fixture", "--candidate", "/candidate.Dockerfile",
                       "--out", "/evidence", "--expected-output", expected, "--timeout", str(args.build_timeout), "--verify-timeout", "1" if name == "runtime-timeout" else "30"]
            code = run_logged(command, case, timeout=2 * args.build_timeout + 120)
            row = {"case": name, "passed": False, "exit_code": code}
            try:
                report = json.loads((case / "stdout.log").read_text(encoding="utf-8"))
                evaluate(name, code, report)
                if name != "invalid-candidate":
                    if json.loads((evidence / "result.json").read_text()) != report:
                        raise ValueError("Saved report differs from CLI report")
                check_artifacts(name, evidence, report)
                if args.inject_bad_oracle and name == "success":
                    raise ValueError("Intentional failing oracle: valid output was required to be different")
                row.update(passed=True, workflow_status=report["status"], trace_id=report.get("trace_id", ""))
            except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
                row["error"] = str(exc)
            rows.append(row)
            print(f"[{name}] {'PASS' if row['passed'] else 'FAIL'}; workflow exit={code}", flush=True)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        rows.append({"case": "runner", "passed": False, "error": str(exc)})
    passed = len(rows) == len(cases) + 1 and all(row["passed"] for row in rows)
    result = {"passed": passed, "image": args.image, "cases": rows, "intentional_failure": args.inject_bad_oracle,
              "selected_cases": cases, "build_timeout_seconds": args.build_timeout,
              "scope": "Recorded candidate replay for selected real workflow cases; not model generation or a three-project benchmark"}
    (output / "gate-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case", "passed", "exit_code", "workflow_status", "trace_id", "error"])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
