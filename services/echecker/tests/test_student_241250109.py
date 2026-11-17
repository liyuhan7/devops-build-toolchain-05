"""孙鲲华 241250109：头文件间接包含的失效与删除后的发现消解。"""
from pathlib import Path
import shutil
import tempfile
import unittest

from services.echecker.echecker.core import scan
from scripts.echecker.scenarios import commit, fixture


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class IndirectHeaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "sample"
        fixture(self.project)

    def test_indirect_include_adds_exact_missing_edge(self):
        old = scan(self.project)
        header = self.project / "config.h"
        header.write_text('#include "extra.h"\n' + header.read_text())
        commit(self.project, "config.h includes extra.h")
        result = scan(self.project, old)
        self.assertEqual(result["actual"]["main.o"], ["config.h", "extra.h", "main.c"])
        self.assertEqual(result["added"], [["MISSING", "main.o", "extra.h"]])
        self.assertEqual(set(result["refreshed"]), {"main.o", "helper.o"})
        full = scan(self.project)
        for key in ("actual", "declared", "findings"):
            self.assertEqual(result[key], full[key])

    def test_removing_indirect_include_resolves_edge(self):
        header = self.project / "config.h"
        header.write_text('#include "extra.h"\n' + header.read_text())
        commit(self.project, "config.h includes extra.h")
        before = scan(self.project)
        header.write_text(header.read_text().replace('#include "extra.h"\n', ""))
        commit(self.project, "config.h drops extra.h")
        after = scan(self.project, before)
        self.assertEqual(after["actual"]["main.o"], ["config.h", "main.c"])
        self.assertEqual(after["resolved"], [["MISSING", "main.o", "extra.h"]])
        self.assertEqual(set(after["refreshed"]), {"main.o", "helper.o"})
        self.assertEqual(sorted((f["type"], f["dependency"]) for f in after["findings"]),
                         [("MISSING", "config.h"), ("REDUNDANT", "unused.h")])


if __name__ == "__main__":
    unittest.main()
