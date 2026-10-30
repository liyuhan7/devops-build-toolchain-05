"""用编译器和 Make 验证人工样本的依赖状态，不冒充工具输出。"""

import os
from pathlib import Path
import time
import unittest

from baseline_support import LINUX_TOOLS, command, sandbox
from run_c0 import reconstruct_c0


@unittest.skipUnless(LINUX_TOOLS, "需要 Linux、gcc、Make、Git、Bash 和 coreutils")
class DependencyStateTests(unittest.TestCase):
    def project(self, root, sample=None):
        project = root / "project"
        reconstruct_c0(root / "fixtures/e3/fzy", root / "fixtures/e3/echecker/c0.patch", project)
        if sample:
            command(["git", "apply", "--ignore-whitespace", str(root / sample)], project)
        command(["make", "CC=gcc", "config.h"], project)
        return project

    def graph(self, project, target="src/options.o"):
        source = str(Path(target).with_suffix(".c"))
        actual_text = command(["gcc", "-MM", "-Ideps", source], project)
        actual = {os.path.normpath(path) for path in actual_text.replace("\\\n", " ").split(":", 1)[1].split()}
        declared_text = command(["make", "CC=gcc", "-pn", target], project)
        rule = next(line for line in declared_text.splitlines() if line.startswith(target + ":"))
        declared = {os.path.normpath(path) for path in rule.split(":", 1)[1].split()}
        return {(target, path) for path in actual - declared}, {(target, path) for path in declared - actual}

    def test_healthy_missing_redundant_and_mixed_states(self):
        missing = ("src/options.o", "src/e3_md_marker.h")
        redundant = ("src/options.o", "src/e3_rd_unused.h")
        for state in ("healthy", "missing", "redundant", "mixed"):
            with self.subTest(state=state), sandbox() as root:
                project = self.project(root, None if state == "healthy" else "fixtures/e3/buildchecker/md-rd.patch")
                makefile = project / "Makefile"
                source = makefile.read_text()
                if state == "missing":
                    source = source.replace(" config.h src/e3_rd_unused.h\n", " config.h\n")
                elif state == "redundant":
                    source = source.replace(" config.h src/e3_rd_unused.h\n", " config.h src/e3_md_marker.h src/e3_rd_unused.h\n")
                makefile.write_text(source)
                expected_missing = {missing} if state in ("missing", "mixed") else set()
                expected_redundant = {redundant} if state in ("redundant", "mixed") else set()
                self.assertEqual(self.graph(project), (expected_missing, expected_redundant))
                command(["make", "CC=gcc"], project)
                version = command(["./fzy", "--version"], project)
                if state == "redundant":
                    obj = project / "src/options.o"
                    before = obj.stat().st_mtime_ns
                    header = project / "src/e3_rd_unused.h"
                    timestamp = max(time.time_ns(), before + 1)
                    os.utime(header, ns=(timestamp, timestamp))
                    command(["make", "CC=gcc"], project)
                    self.assertGreater(obj.stat().st_mtime_ns, before)
                    self.assertEqual(command(["./fzy", "--version"], project), version)

    def test_same_configuration_introduced_unchanged_resolved_and_empty_deltas(self):
        with sandbox() as root:
            project = self.project(root)
            healthy = self.graph(project)[0]
            self.assertEqual(healthy, set())
            self.assertEqual(self.graph(project)[0] - healthy, set(), "无变更时不应引入依赖问题")
            command(["git", "apply", "--ignore-whitespace", str(root / "fixtures/e3/echecker/c1.patch")], project)
            initial = self.graph(project)[0]
            edge = ("src/options.o", "src/e3_c1_marker.h")
            self.assertEqual(initial - healthy, {edge})
            compile_command = command(["make", "CC=gcc", "-n", "-B", "src/options.o"], project)
            command(["make", "CC=gcc"], project)
            before = (project / "src/options.o").stat().st_mtime_ns
            (project / "README.md").write_text("不影响编译的文档变更\n")
            unchanged = self.graph(project)[0]
            self.assertEqual((unchanged - initial, initial - unchanged, initial & unchanged), (set(), set(), {edge}))
            command(["make", "CC=gcc"], project)
            self.assertEqual((project / "src/options.o").stat().st_mtime_ns, before)
            makefile = project / "Makefile"
            makefile.write_text(makefile.read_text().replace("src/options.o: src/options.c src/options.h config.h\n",
                                                          "src/options.o: src/options.c src/options.h config.h src/e3_c1_marker.h\n"))
            resolved = self.graph(project)[0]
            self.assertEqual((resolved - unchanged, unchanged - resolved, resolved & unchanged), (set(), {edge}, set()))
            self.assertEqual(command(["make", "CC=gcc", "-n", "-B", "src/options.o"], project), compile_command)
            header = project / "src/e3_c1_marker.h"
            header.write_text(header.read_text().replace("MARKER=one", "MARKER=two"))
            timestamp = max(time.time_ns(), before + 1)
            os.utime(header, ns=(timestamp, timestamp))
            command(["make", "CC=gcc"], project)
            self.assertGreater((project / "src/options.o").stat().st_mtime_ns, before)
            self.assertIn("MARKER=two", command(["./fzy", "--version"], project))

    def test_shared_missing_header_keeps_two_distinct_target_edges(self):
        with sandbox() as root:
            project = self.project(root)
            marker = "src/shared_probe.h"
            (project / marker).write_text("/* shared dependency probe */\n")
            makefile = project / "Makefile"
            source = makefile.read_text()
            for target in ("src/options.o", "src/match.o"):
                # 先取得该目标完整的实际依赖，再注入同一个未声明头文件。
                unit = project / Path(target).with_suffix(".c")
                dependencies = command(["gcc", "-MM", "-Ideps", str(unit.relative_to(project))], project)
                inputs = dependencies.replace("\\\n", " ").split(":", 1)[1].split()
                unit.write_text('#include "shared_probe.h"\n' + unit.read_text())
                if target == "src/match.o":
                    source += "\n" + target + ": " + " ".join(inputs) + "\n\t$(CC) $(CPPFLAGS) $(filter-out -MD -MMD -MP,$(CFLAGS)) -c -o $@ $<\n"
            makefile.write_text(source)
            edges = set()
            for target in ("src/options.o", "src/match.o"):
                missing, redundant = self.graph(project, target)
                self.assertEqual(missing, {(target, marker)})
                self.assertEqual(redundant, set())
                edges |= missing
            self.assertEqual(len(edges), 2)
            command(["make", "CC=gcc"], project)


if __name__ == "__main__":
    unittest.main()
