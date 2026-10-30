"""验证 Bash 入口对功能失败、缺产物和超时的真实判定。"""

import json
import os
import shutil
import unittest

from baseline_support import LINUX_TOOLS, REAL_RUN, sandbox


@unittest.skipUnless(LINUX_TOOLS, "需要 Linux、gcc、Make、Git、Bash 和 coreutils")
class FunctionalRunnerTests(unittest.TestCase):
    def test_functional_entry_distinguishes_success_from_failures(self):
        for scenario in ("success", "wrong-stdout", "missing-binary", "built-but-wrong-function", "wrong-stderr", "timeout"):
            with self.subTest(scenario=scenario), sandbox() as root:
                cases = root / "fixtures/e3/draft/cases"
                if scenario == "wrong-stdout":
                    (cases / "match-apple/expected_stdout").write_text("incorrect\n")
                if scenario == "wrong-stderr":
                    (cases / "invalid-lines-usage/expected_stderr_contains").write_text("nonexistent-error-token\n")
                environment = os.environ.copy()
                if scenario in ("missing-binary", "built-but-wrong-function", "timeout"):
                    tools = root / "fake-tools"
                    tools.mkdir()
                    real_make = shutil.which("make")
                    body = f'#!/bin/bash\nif [ "$1" = --version ]; then exec "{real_make}" "$@"; fi\n'
                    if scenario == "missing-binary":
                        body += "exit 0\n"
                    elif scenario == "timeout":
                        body += "echo before-timeout\nsleep 30\n"
                    else:
                        body += f'"{real_make}" "$@" || exit $?\n'
                        body += "if [ \"$2\" != check ]; then\ncat > fzy <<'SH'\n#!/bin/bash\nif [ \"$1\" = --version ]; then echo 1.1; else echo wrong-output; fi\nSH\nchmod +x fzy\nfi\n"
                    (tools / "make").write_text(body)
                    (tools / "make").chmod(0o755)
                    environment["PATH"] = str(tools) + os.pathsep + environment["PATH"]
                out = root / "test-output"
                result = REAL_RUN(["bash", str(root / "scripts/e3/verify_fzy.sh"), "--operator", "自动回归测试",
                                   "--output", str(out), "--command-timeout", "1" if scenario == "timeout" else "60"],
                                  env=environment, capture_output=True, text=True, timeout=120)
                run = json.loads((out / "run.json").read_text())
                commands = json.loads((out / "commands.json").read_text())
                expected = (0, "PASSED") if scenario == "success" else (1, "FAILED")
                self.assertEqual((result.returncode, run["status"]), expected, result.stderr)
                self.assertTrue(all((out / item[key]).is_file() for item in commands for key in ("stdout", "stderr")))
                if scenario == "success":
                    invalid = next(item for item in commands if item["label"] == "functional-invalid-lines-usage")
                    self.assertEqual(invalid["exit_code"], 1, "预期的非零退出码仍应通过外层测试")
                else:
                    self.assertTrue(any(not item["passed"] for item in run["checks"]))
                    self.assertTrue(run["failure"])
                if scenario == "built-but-wrong-function":
                    self.assertEqual(next(item for item in commands if item["label"] == "build")["exit_code"], 0)
                    self.assertTrue(any(item["check"] == "生成可执行的 fzy" and item["passed"] for item in run["checks"]))
                if scenario == "timeout":
                    build = next(item for item in commands if item["label"] == "build")
                    self.assertEqual(build["exit_code"], 124)
                    self.assertTrue(build["timed_out"])
                    self.assertIn("before-timeout", (out / build["stdout"]).read_text())
                    self.assertIn("超时", (out / build["stderr"]).read_text())


if __name__ == "__main__":
    unittest.main()
