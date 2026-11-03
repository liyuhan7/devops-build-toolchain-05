"""用确定性 Docker 响应检查流程编排；真实构建由 E7 门禁验证。"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from draft import autobuild as workflow

BASE = 'FROM python:3.13-slim\nWORKDIR /work\nCOPY main.c Makefile ./\nRUN make\nCMD ["./hello"]\n'
PIN = "FROM python:3.13-slim@sha256:" + "a" * 64
CANDIDATE = BASE.replace("FROM python:3.13-slim", PIN).replace("RUN make", "RUN apt-get install -y build-essential\nRUN make")
IMAGE = "sha256:" + "b" * 64

class WorkflowFailureTests(unittest.TestCase):
    def exercise(self, mode):
        self.calls = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "Dockerfile.broken").write_text(BASE)
            (fixture / "Dockerfile.reference").write_text("not a candidate")
            (fixture / "main.c").write_text("source")
            candidate = root / "candidate"
            candidate.write_text(CANDIDATE)

            def fake_execute(argv, stdout, stderr, timeout):
                self.calls.append(argv)
                stdout, stderr = Path(stdout), Path(stderr)
                stdout.write_text("")
                stderr.write_text("")
                if argv[1] == "build":
                    if stdout.parent.name == "iter-01":
                        if mode == "build-timeout":
                            raise TimeoutError("stub build timeout")
                        if mode == "baseline-success":
                            return 0
                        text = {"infrastructure": "failed to resolve source metadata: EOF", "empty": "", "unknown": "compiler crashed"}.get(mode, "/bin/sh: 1: make: not found")
                        stderr.write_text(text)
                        return 1
                    if mode == "repair-failed":
                        stderr.write_text("candidate build failed")
                        return 1
                    return 0
                if argv[1:3] == ["image", "inspect"]:
                    stdout.write_text(json.dumps([{"Id": IMAGE}]))
                    return 0
                if argv[1] == "run":
                    Path(argv[argv.index("--cidfile") + 1]).write_text("c" * 64)
                    if mode == "verify-timeout":
                        raise TimeoutError("stub verify timeout")
                    stdout.write_text("wrong answer\n" if mode == "wrong-output" else "hello E3\n")
                    return 7 if mode == "runtime-failed" else 0
                if argv[1] == "rm":
                    return 0
                raise AssertionError(f"Unexpected command: {argv}")

            with patch.object(workflow, "os", SimpleNamespace(name="posix")), patch.object(workflow, "execute", fake_execute):
                result = workflow.auto_build(fixture, candidate, root / "output", "hello E3")
            saved = json.loads((root / "output/result.json").read_text())
            self.assertEqual(saved, result)
            self.assertFalse((root / "output/project/Dockerfile.reference").exists())
            self.assertLessEqual(len(result["attempts"]), 2)
            return result

    def test_success_uses_built_image(self):
        report = self.exercise("success")
        self.assertEqual(report["status"], "SUCCEEDED")
        self.assertEqual(report["verification"]["command"][-1], IMAGE)

    def test_network_error_aborts_before_repair(self):
        report = self.exercise("infrastructure")
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["attempts"][0]["failure_class"], "INFRASTRUCTURE")
        self.assertEqual(len(report["attempts"]), 1)

    def test_empty_log_is_not_reproduction(self):
        report = self.exercise("empty")
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(len(report["attempts"]), 1)

    def test_unknown_error_is_not_reproduction(self):
        report = self.exercise("unknown")
        self.assertEqual(report["attempts"][0]["failure_class"], "OTHER_BUILD_ERROR")
        self.assertEqual(report["status"], "FAILED")

    def test_initial_success_is_not_missing_make(self):
        self.assertEqual(self.exercise("baseline-success")["status"], "FAILED")

    def test_repair_failure_has_no_verification(self):
        report = self.exercise("repair-failed")
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["attempts"][1]["build_exit_code"], 1)
        self.assertNotIn("verification", report)

    def test_zero_exit_with_wrong_output_fails(self):
        report = self.exercise("wrong-output")
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["verification"]["exit_code"], 0)
        self.assertFalse(report["verification"]["output_matches"])

    def test_correct_output_with_nonzero_exit_fails(self):
        report = self.exercise("runtime-failed")
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(report["verification"]["output_matches"])

    def test_build_timeout_is_terminal(self):
        self.assertEqual(self.exercise("build-timeout")["status"], "TIMED_OUT")

    def test_runtime_timeout_attempts_cleanup(self):
        self.assertEqual(self.exercise("verify-timeout")["status"], "TIMED_OUT")
        self.assertTrue(any(argv[1] == "rm" for argv in self.calls))

    def test_cli_failure_exit(self):
        from draft.cli import main
        with patch("draft.cli.auto_build", return_value={"status": "FAILED", "error": "stub failure"}):
            self.assertEqual(main(["auto-build", "--candidate", "x", "--out", "y", "--expected-output", "hello E3"]), 1)

if __name__ == "__main__":
    unittest.main()
