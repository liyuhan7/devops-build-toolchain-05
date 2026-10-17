"""超时必须返回失败、保留输出，并停止编译子进程。"""

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from baseline_support import SCRIPTS
from bounded_command import run_bounded


class BoundedCommandTests(unittest.TestCase):
    def test_exit_code_and_both_output_streams_are_preserved(self):
        result = run_bounded([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"], cwd=SCRIPTS, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (3, "out\n", "err\n"))

    def test_timeout_is_not_reported_as_success_and_keeps_partial_output(self):
        result = run_bounded([sys.executable, "-u", "-c", "import time; print('before-timeout'); time.sleep(30)"], cwd=SCRIPTS, timeout=0.5)
        self.assertEqual(result.returncode, 124)
        self.assertIn("before-timeout", result.stdout)
        self.assertIn("超时", result.stderr)

    def test_missing_command_is_a_recordable_failure(self):
        result = run_bounded([str(SCRIPTS / "nonexistent-command")], cwd=SCRIPTS, timeout=5)
        self.assertEqual(result.returncode, 125)
        self.assertTrue(result.stderr)

    @unittest.skipUnless(os.name == "posix", "进程组终止使用 POSIX 接口")
    def test_timeout_also_stops_descendant_process(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "escaped-child"
            child = f"import time; from pathlib import Path; time.sleep(1.5); Path({str(marker)!r}).write_text('escaped')"
            parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', sys.argv[1]]); time.sleep(30)"
            started = time.monotonic()
            result = run_bounded([sys.executable, "-c", parent, child], cwd=directory, timeout=0.3)
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(result.returncode, 124)
            time.sleep(1.5)
            self.assertFalse(marker.exists(), "超时的子进程仍在继续写文件")
