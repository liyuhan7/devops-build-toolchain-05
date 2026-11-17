"""241830149 个人扩展：条件编译与配置身份驱动的依赖变化。"""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.echecker.scenarios import commit, fixture
from services.echecker.echecker import core


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class ConditionalDependencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "sample"
        fixture(self.project)
        (self.project / "config.h").write_text(
            '#define VALUE 1\n#ifdef MODE\n#include "extra.h"\n#endif\n', encoding="utf-8")
        commit(self.project, "conditional extra header")

    def test_inactive_conditional_header_reuses_only_observed_edges(self):
        """E8：出现 include 文本不等于当前配置真正读取了头文件。"""
        baseline = core.scan(self.project)
        expected_actual = {"main.o": ["config.h", "main.c"], "helper.o": ["helper.c"]}
        expected_findings = [
            {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
            {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"},
        ]
        self.assertEqual(baseline["actual"], expected_actual)
        self.assertEqual(baseline["findings"], expected_findings)

        incremental = core.scan(self.project, baseline)

        self.assertEqual(incremental["actual"], expected_actual)
        self.assertEqual(incremental["findings"], expected_findings)
        self.assertEqual(incremental["reused"], ["main.o", "helper.o"])
        self.assertEqual(incremental["refreshed"], [])
        self.assertEqual(incremental["added"], [])
        self.assertEqual(incremental["resolved"], [])
        full = core.scan(self.project)
        for key in ("actual", "declared", "findings"):
            self.assertEqual(incremental[key], full[key])

    def test_macro_toggle_refreshes_edges_and_resolves_missing_on_return(self):
        """E9：仅切换编译宏也能引入和消除实际依赖，不能复用旧图。"""
        baseline = core.scan(self.project)
        source_bytes = {p.name: p.read_bytes() for p in self.project.iterdir() if p.suffix in (".c", ".h")}
        makefile = self.project / "Makefile"
        original = makefile.read_text(encoding="utf-8")
        previous = baseline

        for flags in ("-O0 -DMODE=1", "-O0"):
            with self.subTest(flags=flags):
                makefile.write_text(original.replace("CFLAGS = -O0", "CFLAGS = " + flags), encoding="utf-8")
                commit(self.project, "configuration " + flags)
                incremental = core.scan(self.project, previous)

                self.assertNotEqual(incremental["commit"], previous["commit"])
                self.assertEqual(source_bytes, {p.name: p.read_bytes() for p in self.project.iterdir()
                                               if p.suffix in (".c", ".h")})
                for key in ("directives", "recipes", "compiler"):
                    self.assertEqual(incremental["key"][key], previous["key"][key])
                self.assertEqual(incremental["key"]["flags"], flags)
                self.assertEqual(incremental["reused"], [])
                self.assertEqual(incremental["refreshed"], ["main.o", "helper.o"])
                self.assertEqual(incremental["actual"]["helper.o"], ["helper.c"])
                self.assertEqual(incremental["declared"], {
                    "main.o": ["main.c", "unused.h"], "helper.o": ["helper.c"]})

                if flags == "-O0 -DMODE=1":
                    self.assertEqual(incremental["actual"]["main.o"], ["config.h", "extra.h", "main.c"])
                    self.assertEqual(incremental["added"], [["MISSING", "main.o", "extra.h"]])
                    self.assertEqual(incremental["resolved"], [])
                    self.assertEqual(incremental["findings"], [
                        {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
                        {"type": "MISSING", "target": "main.o", "dependency": "extra.h"},
                        {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"},
                    ])
                else:
                    self.assertEqual(incremental["actual"], {
                        "main.o": ["config.h", "main.c"], "helper.o": ["helper.c"]})
                    self.assertEqual(incremental["added"], [])
                    self.assertEqual(incremental["resolved"], [["MISSING", "main.o", "extra.h"]])
                    self.assertEqual(incremental["findings"], [
                        {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
                        {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"},
                    ])
                full = core.scan(self.project)
                for key in ("actual", "declared", "findings"):
                    self.assertEqual(incremental[key], full[key])
                previous = incremental


if __name__ == "__main__":
    unittest.main()
