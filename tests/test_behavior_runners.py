"""用真实构建和受控故障，验证复跑脚本不会把失败误报为通过。"""

import difflib
import subprocess
import unittest
from unittest.mock import patch

from baseline_support import LINUX_TOOLS, REAL_RUN, command, invoke, load_runner, sandbox
from run_c0 import reconstruct_c0


@unittest.skipUnless(LINUX_TOOLS, "需要 Linux、gcc、Make、Git、Bash 和 coreutils")
class BehaviorRunnerTests(unittest.TestCase):
    def test_include_runner_accepts_real_incremental_and_clean_control(self):
        with sandbox() as root:
            code, run, commands, _ = invoke(load_runner("run_c1", root))
            self.assertEqual((code, run["status"]), (0, "PASSED"), run.get("failure"))
            self.assertGreaterEqual(len(run["checks"]), 13)
            self.assertTrue(all(item["passed"] for item in run["checks"]))
            self.assertIn("clean-functional-after-change", {item["label"] for item in commands})

    def test_include_runner_rejects_corrupt_behavior_and_command_failures(self):
        scenarios = ("build-failure", "build-timeout", "wrong-output", "missing-object",
                     "missing-target", "wrong-graph", "malformed-graph", "unexpected-rebuild-output", "stale-clean-output")
        for scenario in scenarios:
            with self.subTest(scenario=scenario), sandbox() as root:
                module = load_runner("run_c1", root)
                versions = 0

                def injected(argv, **kwargs):
                    nonlocal versions
                    if argv == ["make", "CC=gcc"] and scenario == "build-failure":
                        return subprocess.CompletedProcess(argv, 2, "", "受控构建失败")
                    if argv == ["make", "CC=gcc"] and scenario == "build-timeout":
                        raise subprocess.TimeoutExpired(argv, 180)
                    result = REAL_RUN(argv, **kwargs)
                    if argv == ["./fzy", "-e", "apple"] and scenario == "wrong-output":
                        result.stdout = "banana\n"
                    if argv == ["make", "CC=gcc", "-pn", "src/options.o"] and scenario == "missing-target":
                        result.stdout = "other.o: other.c\n"
                    if argv == ["gcc", "-MM", "src/options.c"] and scenario == "wrong-graph":
                        result.stdout = "options.o: src/options.c\n"
                    if argv == ["gcc", "-MM", "src/options.c"] and scenario == "malformed-graph":
                        result.stdout = "invalid dependency output\n"
                    if argv == ["./fzy", "--version"]:
                        versions += 1
                        if scenario == "missing-object" and versions == 1:
                            (kwargs["cwd"] / "src/options.o").unlink()
                        if scenario == "unexpected-rebuild-output" and versions == 2:
                            result.stdout = result.stdout.replace("MARKER=one", "MARKER=two")
                        if scenario == "stale-clean-output" and versions == 3:
                            result.stdout = result.stdout.replace("MARKER=two", "MARKER=one")
                    return result

                with patch.object(module.subprocess, "run", side_effect=injected):
                    code, run, commands, out = invoke(module)
                self.assertEqual((code, run["status"]), (1, "FAILED"), scenario)
                expected_failure = {"build-failure": "initial-build", "build-timeout": "initial-build",
                                    "wrong-output": "初始功能断言通过", "missing-object": "src/options.o",
                                    "missing-target": "Make 输出包含选定目标声明", "wrong-graph": "C1 编译器实际依赖与人工图一致",
                                    "malformed-graph": "编译器依赖输出包含目标分隔符",
                                    "unexpected-rebuild-output": "普通 make 保留旧产物", "stale-clean-output": "clean 构建读取头文件新值"}
                self.assertIn(expected_failure[scenario], run.get("failure", ""), scenario)
                self.assertNotIn("clean-functional-after-change", {item["label"] for item in commands})
                self.assertTrue(all((out / item[key]).is_file() for item in commands for key in ("stdout", "stderr")))

    def test_command_runner_accepts_real_command_invalidation_control(self):
        with sandbox() as root:
            code, run, commands, _ = invoke(load_runner("run_c2", root))
            self.assertEqual((code, run["status"]), (0, "PASSED"), run.get("failure"))
            self.assertGreaterEqual(len(run["checks"]), 17)
            self.assertIn("c2-clean-functional", {item["label"] for item in commands})

    def test_command_runner_rejects_wrong_incremental_and_clean_results(self):
        for scenario in ("same-command", "new-ordinary-version", "old-clean-version", "test-failure"):
            with self.subTest(scenario=scenario), sandbox() as root:
                module = load_runner("run_c2", root)
                first_command = None

                def injected(argv, **kwargs):
                    nonlocal first_command
                    result = REAL_RUN(argv, **kwargs)
                    cwd = kwargs.get("cwd")
                    if argv == ["make", "CC=gcc", "-n", "-B", "src/options.o"]:
                        if first_command is None:
                            first_command = result.stdout
                        elif scenario == "same-command":
                            result.stdout = first_command
                    if argv == ["./fzy", "--version"]:
                        if scenario == "new-ordinary-version" and cwd.name == "c1-to-c2" and "VERSION=1.2-e3" in (cwd / "Makefile").read_text():
                            result.stdout = result.stdout.replace(" 1.1 ", " 1.2-e3 ")
                        if scenario == "old-clean-version" and cwd.name == "c2-clean":
                            result.stdout = result.stdout.replace(" 1.2-e3 ", " 1.1 ")
                    if scenario == "test-failure" and argv == ["make", "CC=gcc", "check"]:
                        result.returncode = 2
                    return result

                with patch.object(module.subprocess, "run", side_effect=injected):
                    code, run, _, _ = invoke(module)
                self.assertEqual((code, run["status"]), (1, "FAILED"), scenario)
                expected_failure = {"same-command": "C1/C2 编译命令发生变化", "new-ordinary-version": "普通 make 保留 C1 版本输出",
                                    "old-clean-version": "C2 clean build 输出新版本", "test-failure": "c1-tests"}
                self.assertIn(expected_failure[scenario], run.get("failure", ""))

    def test_repair_runner_accepts_reference_and_rejects_bad_candidates_with_recovery(self):
        for scenario in ("reference", "inapplicable", "build-failure", "test-failure", "missing-edge", "command-timeout", "recovery-failure"):
            with self.subTest(scenario=scenario), sandbox() as root:
                module = load_runner("verify_repair", root)
                reference = module.CASE / "reference.patch"
                source = reference.read_text()
                base = root / "candidate-base"
                reconstruct_c0(root / "fixtures/e3/fzy", root / "fixtures/e3/echecker/c0.patch", base)
                command(["git", "apply", "--ignore-whitespace", str(module.CASE / "fault.patch")], base)
                original = (base / "Makefile").read_text()
                repaired = original.replace("src/options.o: src/options.c src/options.h config.h\n",
                                            "src/options.o: src/options.c src/options.h config.h src/e3_mdfixer_marker.h\n")
                if scenario == "inapplicable":
                    source = source.replace("-src/options.o:", "-nonexistent.o:")
                elif scenario in ("build-failure", "test-failure", "recovery-failure"):
                    recipe = ("\t$(DEBUGGER) ./test/fzytest" if scenario == "test-failure" else
                              "\t$(CC) $(CPPFLAGS) $(filter-out -MD -MMD -MP,$(CFLAGS)) -c -o $@ $<")
                    repaired = repaired.replace(recipe, "\tfalse")
                    source = "".join(difflib.unified_diff(original.splitlines(True), repaired.splitlines(True),
                                                       fromfile="a/Makefile", tofile="b/Makefile"))
                elif scenario == "missing-edge":
                    source = source.replace("+src/options.o: src/options.c src/options.h config.h src/e3_mdfixer_marker.h",
                                            "+src/options.o: src/options.c src/options.h config.h # still missing")
                reference.write_text(source, encoding="utf-8", newline="\n")
                bounded = module.run_bounded
                build_count = 0

                def injected(argv, **kwargs):
                    nonlocal build_count
                    if tuple(argv) == ("make", "CC=gcc"):
                        build_count += 1
                        if scenario == "command-timeout" and build_count == 3:
                            return bounded(["python3", "-u", "-c", "import time; print('partial'); time.sleep(30)"],
                                           cwd=kwargs["cwd"], timeout=0.2)
                        if scenario == "recovery-failure" and build_count == 4:
                            return subprocess.CompletedProcess(argv, 2, "", "受控恢复构建失败")
                    return bounded(argv, **kwargs)

                with patch.object(module, "run_bounded", side_effect=injected):
                    code, run, commands, out = invoke(module)
                if scenario == "reference":
                    self.assertEqual((code, run["status"]), (0, "PASSED"), run.get("failure"))
                    self.assertNotIn("recovery", run)
                else:
                    self.assertEqual((code, run["status"]), (1, "FAILED"))
                    failure = {"inapplicable": "参考 Patch 可应用", "build-failure": "补丁应用后构建并更新为 two",
                               "test-failure": "修复后上游测试", "missing-edge": "人工依赖复核",
                               "command-timeout": "补丁应用后构建并更新为 two", "recovery-failure": "补丁应用后构建并更新为 two"}[scenario]
                    self.assertEqual(run["failure"], failure)
                    if scenario == "recovery-failure":
                        self.assertEqual(run["recovery"]["status"], "FAILED")
                        self.assertIn("恢复后构建", run["recovery"]["failure"])
                        continue
                    self.assertEqual(run["recovery"]["status"], "PASSED", run)
                    self.assertEqual(run["recovery"]["workspace_digest"], run["candidate_base_workspace_digest"])
                    self.assertIn("recovery-functional", {item["label"] for item in commands})
                    if scenario == "command-timeout":
                        timed_out = next(item for item in commands if item["label"] == "repaired-build")
                        self.assertEqual(timed_out["exit_code"], 124)
                        self.assertTrue(timed_out["timed_out"])
                        self.assertIn("partial", (out / timed_out["stdout"]).read_text())


if __name__ == "__main__":
    unittest.main()
