"""验证 EChecker 复用现有镜像、BuildChecker 编排和日志记录。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.echecker import lab


class RunnerTests(unittest.TestCase):
    def test_build_delegates_to_existing_a_group_entry(self):
        with patch.object(lab, "buildchecker_main", return_value=0) as build:
            self.assertEqual(lab.main(["build", "--image", "team:a", "--out", "work/test",
                                       "--base-image", "fixed:image"]), 0)
        self.assertEqual(build.call_args.args[0], ["build", "--out", "work/test", "--image", "team:a",
                                                 "--build-timeout", "1200", "--base-image", "fixed:image"])

    def run_stage(self, stage, inspect_code=0, runner_code=0):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name)
        (output / "image").mkdir()
        (output / "image/stdout.log").write_text(json.dumps([{
            "Id": "sha256:fixed", "Config": {"Labels": {"org.opencontainers.image.revision": "image-source"}}}]))
        with patch.object(lab, "fresh_output", return_value=output), \
             patch.object(lab.subprocess, "check_output", side_effect=["source\n", ""]), \
             patch.object(lab, "run_logged", side_effect=[inspect_code, runner_code]) as run:
            code = lab.main([stage, "--image", "team:a", "--out", "work/test"])
        return code, output, run

    def test_e8_uses_repository_layout_shared_image_and_trace_capability(self):
        code, output, run = self.run_stage("e8")
        self.assertEqual(code, 0)
        command = run.call_args_list[1].args[0]
        self.assertIn("SYS_PTRACE", command)
        self.assertIn("sha256:fixed", command)
        self.assertEqual(command[-6:], ["python3", "-m", "scripts.echecker.scenarios", "e8", "--out", "/evidence/result"])
        self.assertNotIn("/course", " ".join(command))
        meta = json.loads((output / "invocation.json").read_text())
        self.assertEqual(meta["image_source_commit"], "image-source")

    def test_e9_preserves_runner_failure(self):
        code, output, _ = self.run_stage("e9", runner_code=7)
        self.assertEqual(code, 7)
        self.assertEqual(json.loads((output / "invocation.json").read_text())["exit_code"], 7)

    def test_missing_image_does_not_start_experiment(self):
        code, output, run = self.run_stage("e8", inspect_code=1)
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, 1)
        self.assertFalse((output / "evidence").exists())

    def test_test_stage_runs_service_and_runner_tests_in_existing_image(self):
        _, _, run = self.run_stage("test")
        shell = run.call_args_list[1].args[0][-1]
        self.assertIn("services/echecker/tests", shell)
        self.assertIn("tests/echecker_lab", shell)


if __name__ == "__main__":
    unittest.main()
