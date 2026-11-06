"""验证仓库目录适配、身份隔离和本地命令证据。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.buildchecker.runtime import run_logged

path = Path(__file__).resolve().parents[2] / "scripts/buildchecker/lab.py"
spec = importlib.util.spec_from_file_location("buildchecker_lab_runner", path)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class RunnerTests(unittest.TestCase):
    def test_local_student_identity_selects_a_image(self):
        with patch.object(lab.subprocess, "check_output", return_value="241250001\n"):
            self.assertEqual(lab.student_image(), "buildchecker-lab:241250001")
        with patch.object(lab.subprocess, "check_output", side_effect=subprocess.CalledProcessError(1, "git")):
            self.assertEqual(lab.student_image("explicit:test"), "explicit:test")

    def test_non_student_identity_cannot_share_default_tag(self):
        with patch.object(lab.subprocess, "check_output", return_value="local\n"):
            with self.assertRaises(ValueError):
                lab.student_image()

    def test_output_stays_in_work_and_previous_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lab, "ROOT", Path(directory)):
            output = lab.fresh_output("work/buildchecker/e5-test")
            (output / "evidence.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                lab.fresh_output("work/buildchecker/e5-test")
            with self.assertRaises(ValueError):
                lab.fresh_output("docs")
            self.assertEqual((output / "evidence.txt").read_text(), "keep")

    def test_collection_uses_repository_image_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(lab.os, "getuid", return_value=1000, create=True), \
                 patch.object(lab.os, "getgid", return_value=1000, create=True), \
                 patch.object(lab, "run_logged", return_value=0) as execute:
                self.assertEqual(lab.collect_e5("sha256:test", output), 0)
            command = execute.call_args.args[0]
            self.assertIn("/repo/fixtures/md-rd", command[-1])
            self.assertNotIn("/app/", command[-1])
            self.assertIn("SYS_PTRACE", command)

    def test_command_failure_keeps_real_output_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            command = [sys.executable, "-c", "print('recorded'); raise SystemExit(7)"]
            self.assertEqual(run_logged(command, folder), 7)
            self.assertEqual(json.loads((folder / "exit-code.json").read_text()), {"exit_code": 7})
            self.assertEqual(json.loads((folder / "command.json").read_text()), command)
            self.assertEqual((folder / "stdout.log").read_text().strip(), "recorded")
