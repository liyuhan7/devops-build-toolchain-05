"""以独立边集验证课程增量算法与现有 BuildChecker 的调用边界。"""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from services.echecker.echecker import core
from services.echecker.echecker.cli import main
from scripts.echecker.scenarios import commit, fixture


@unittest.skipUnless(shutil.which("gcc") and shutil.which("git"), "需要 GCC 与 Git")
class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "sample"
        fixture(self.project)

    def test_known_edges_use_existing_buildchecker_comparison(self):
        with patch.object(core, "compare_graphs", wraps=core.compare_graphs) as compare:
            result = core.scan(self.project)
        compare.assert_called_once()
        self.assertEqual(result["actual"], {"main.o": ["config.h", "main.c"], "helper.o": ["helper.c"]})
        self.assertEqual(result["findings"], [
            {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
            {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}])

    def test_unchanged_does_not_repeat_dependency_collection(self):
        old = core.scan(self.project)
        with patch.object(core, "run", wraps=core.run) as run:
            result = core.scan(self.project, old)
        self.assertFalse(any("-MM" in call.args[0] for call in run.call_args_list))
        self.assertEqual(result["reused"], ["main.o", "helper.o"])
        self.assertEqual(result["refreshed"], [])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["resolved"], [])

    def test_body_change_reuses_edges_across_real_commits(self):
        old = core.scan(self.project)
        source = self.project / "main.c"
        source.write_text(source.read_text().replace("VALUE+helper()", "VALUE+helper()+0"))
        commit(self.project, "body change")
        result = core.scan(self.project, old)
        self.assertNotEqual(result["commit"], old["commit"])
        self.assertEqual(result["reused"], ["main.o", "helper.o"])
        self.assertEqual(result["findings"], old["findings"])

    def test_include_addition_introduces_exact_missing_edge(self):
        old = core.scan(self.project)
        source = self.project / "main.c"
        source.write_text('#include "extra.h"\n' + source.read_text())
        commit(self.project, "include extra")
        result = core.scan(self.project, old)
        self.assertEqual(result["added"], [["MISSING", "main.o", "extra.h"]])
        self.assertEqual(set(result["refreshed"]), {"main.o", "helper.o"})
        self.assertEqual(result["actual"]["main.o"], ["config.h", "extra.h", "main.c"])

    def test_declaration_repair_reuses_graph_and_resolves_both_missing(self):
        source = self.project / "main.c"
        source.write_text('#include "extra.h"\n' + source.read_text())
        commit(self.project, "include extra")
        old = core.scan(self.project)
        makefile = self.project / "Makefile"
        makefile.write_text(makefile.read_text().replace("main.c unused.h", "main.c unused.h config.h extra.h"))
        commit(self.project, "repair declarations")
        result = core.scan(self.project, old)
        self.assertEqual(result["actual"], old["actual"])
        self.assertEqual(result["reused"], ["main.o", "helper.o"])
        self.assertEqual(sorted(result["resolved"]), [
            ["MISSING", "main.o", "config.h"], ["MISSING", "main.o", "extra.h"]])
        self.assertEqual(result["findings"], [{"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}])

    def test_indirect_include_matches_full_scan_and_independent_edges(self):
        old = core.scan(self.project)
        (self.project / "config.h").write_text('#include "extra.h"\n#define VALUE 1\n')
        (self.project / "extra.h").write_text('#include "leaf.h"\n')
        (self.project / "leaf.h").write_text('#define LEAF 7\n')
        commit(self.project, "nested headers")
        result = core.scan(self.project, old)
        full = core.scan(self.project)
        self.assertEqual(result["actual"]["main.o"], ["config.h", "extra.h", "leaf.h", "main.c"])
        self.assertEqual(result["added"], [["MISSING", "main.o", "extra.h"], ["MISSING", "main.o", "leaf.h"]])
        for key in ("actual", "declared", "findings"):
            self.assertEqual(result[key], full[key])

    def test_flags_change_refreshes_but_keeps_findings(self):
        old = core.scan(self.project)
        makefile = self.project / "Makefile"
        makefile.write_text(makefile.read_text().replace("-O0", "-O1"))
        commit(self.project, "compiler flags")
        result = core.scan(self.project, old)
        self.assertEqual(set(result["refreshed"]), {"main.o", "helper.o"})
        self.assertEqual(result["findings"], old["findings"])
        self.assertEqual(result["added"], [])

    def test_unsupported_flags_and_foreign_baseline_are_rejected(self):
        old = core.scan(self.project)
        old["schema_version"] = "other-profile"
        with self.assertRaisesRegex(ValueError, "INVALID_BASELINE_PROFILE"):
            core.scan(self.project, old)
        makefile = self.project / "Makefile"
        makefile.write_text(makefile.read_text().replace("-O0", "-include unknown.h"))
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_FLAGS"):
            core.scan(self.project)

    def test_baseline_consumes_repository_buildchecker_and_checks_full_projection(self):
        expected = core.scan(self.project)
        evidence = self.root / "buildchecker"

        def collect(project, output):
            self.assertEqual(project, self.project)
            output.mkdir()
            for label in ("actual", "declared"):
                core.save(output / (label + "-graph.json"), [
                    {"target": target, "dependency": dep}
                    for target, deps in expected[label].items() for dep in deps])
            return {"status": "SUCCEEDED", "trace_id": "test-trace", "findings": expected["findings"]}

        with patch.object(core, "full_check", side_effect=collect) as full_check:
            result = core.build_baseline(self.project, evidence)
        full_check.assert_called_once_with(self.project, evidence)
        self.assertEqual(result["baseline_trace_id"], "test-trace")
        self.assertEqual(result["actual"], expected["actual"])
        with patch.object(core, "full_check", return_value={"status": "FAILED"}):
            with self.assertRaisesRegex(ValueError, "BUILDCHECKER_FAILED"):
                core.build_baseline(self.project, self.root / "failed")

    def test_projection_mismatch_is_not_published_as_baseline(self):
        evidence = self.root / "bad-buildchecker"
        evidence.mkdir()
        core.save(evidence / "actual-graph.json", [])
        with patch.object(core, "full_check", return_value={"status": "SUCCEEDED"}):
            with self.assertRaisesRegex(ValueError, "GRAPH_MISMATCH"):
                core.build_baseline(self.project, evidence)

    def test_cli_preserves_previous_output(self):
        output = self.root / "report.json"
        args = ["--project", str(self.project), "--out", str(output)]
        self.assertEqual(main(args), 0)
        before = output.read_bytes()
        self.assertEqual(main(args), 1)
        self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
