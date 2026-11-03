"""确保 Git 转义路径不会让源码绕过扫描。"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.secret_scan import files, scan_text

class ScanPathTests(unittest.TestCase):
    def test_unicode_tracked_filename_is_scanned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            expected = root / "中文报告.md"
            expected.write_text("controlled input", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            paths, in_git = files(root)
            self.assertTrue(in_git)
            self.assertEqual(paths, [expected])
            self.assertTrue(paths[0].is_file())

    def test_function_call_token_assignment_is_not_a_secret(self):
        self.assertEqual(scan_text("token = decode_pointer_token(raw_token)", "code.py"), [])

    def test_quoted_token_literal_remains_detected(self):
        line = 'token = "' + "A" * 24 + '"'
        self.assertTrue(scan_text(line, "config.py"))
