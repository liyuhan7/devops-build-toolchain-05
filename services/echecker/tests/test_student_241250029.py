"""241250029 个人扩展：目标级头文件依赖与头文件删除的失败边界。"""
from pathlib import Path
import shutil
import tempfile
import unittest

from services.echecker.echecker import core
from scripts.echecker.scenarios import commit, fixture


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class HelperHeaderDependencyTests(unittest.TestCase):
    """E8 扩展：第二个翻译单元也能独立引入头文件依赖。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "sample"
        fixture(self.project)

    def test_helper_include_adds_only_its_own_missing_edge(self):
        old = core.scan(self.project)
        helper = self.project / "helper.c"
        helper.write_text('#include "config.h"\n' + helper.read_text(encoding="utf-8"), encoding="utf-8")
        commit(self.project, "helper includes config")

        result = core.scan(self.project, old)

        # 只核对 helper.o 的新增边，main.o 的实际图不受另一个翻译单元影响。
        self.assertEqual(result["actual"]["helper.o"], ["config.h", "helper.c"])
        self.assertEqual(result["actual"]["main.o"], old["actual"]["main.o"])
        # config.h 的 MD 已由 main.o 记录，新增发现只能来自 helper.o。
        self.assertEqual(result["added"], [["MISSING", "helper.o", "config.h"]])
        self.assertEqual(set(result["refreshed"]), {"main.o", "helper.o"})
        self.assertEqual(result["findings"], [
            {"type": "MISSING", "target": "helper.o", "dependency": "config.h"},
            {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
            {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}])

        # 增量结果必须与同一提交的全量扫描一致。
        full = core.scan(self.project)
        for key in ("actual", "declared", "findings"):
            self.assertEqual(result[key], full[key])


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class HeaderIncludeLifecycleTests(unittest.TestCase):
    """E9 扩展：头文件内部 include 的加入与删除应可逆。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "sample"
        fixture(self.project)

    def test_header_include_added_then_removed_restores_baseline(self):
        baseline = core.scan(self.project)
        header = self.project / "config.h"
        original = header.read_text(encoding="utf-8")

        header.write_text('#include "extra.h"\n' + original, encoding="utf-8")
        commit(self.project, "config includes extra")
        added = core.scan(self.project, baseline)
        self.assertEqual(added["actual"]["main.o"], ["config.h", "extra.h", "main.c"])
        self.assertEqual(added["added"], [["MISSING", "main.o", "extra.h"]])
        self.assertEqual(set(added["refreshed"]), {"main.o", "helper.o"})

        header.write_text(original, encoding="utf-8")
        commit(self.project, "config drops extra")
        removed = core.scan(self.project, added)
        # 撤销后实际图与声明图都应回到基线，只留下 extra.h 这条已解决发现。
        self.assertEqual(removed["actual"], baseline["actual"])
        self.assertEqual(removed["resolved"], [["MISSING", "main.o", "extra.h"]])
        self.assertEqual(removed["added"], [])
        self.assertEqual(removed["findings"], baseline["findings"])
        self.assertEqual(set(removed["refreshed"]), {"main.o", "helper.o"})

        full = core.scan(self.project)
        for key in ("actual", "declared", "findings"):
            self.assertEqual(removed[key], full[key])


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class MissingHeaderFailureTests(unittest.TestCase):
    """E9 失败边界：被包含头文件消失时不得复用历史图。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "sample"
        fixture(self.project)

    def test_deleted_header_fails_instead_of_reusing_history(self):
        old = core.scan(self.project)
        (self.project / "config.h").unlink()
        commit(self.project, "delete config")

        # 缓存键变化会触发重新预处理，GCC 的失败必须向上传播。
        with self.assertRaisesRegex(ValueError, "COMMAND_FAILED"):
            core.scan(self.project, old)


if __name__ == "__main__":
    unittest.main()
