import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/e3"))

from run_c0 import reconstruct_c0, source_digest


UPSTREAM = ROOT / "fixtures/e3/fzy"
C0_PROJECT = ROOT / "fixtures/e3/echecker/project"
C0_PATCH = ROOT / "fixtures/e3/echecker/c0.patch"
C1_PATCH = ROOT / "fixtures/e3/echecker/c1.patch"
C1_EXPECTED = ROOT / "fixtures/e3/echecker/c1-expected.json"
C1_RUNNER = ROOT / "scripts/e3/run_c1.py"


class E3C1BaselineTests(unittest.TestCase):
    def test_c0_runner_reconstructs_frozen_c0_after_project_advances(self):
        projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            c0 = Path(directory) / "c0"
            reconstruct_c0(UPSTREAM, C0_PATCH, c0)
            self.assertEqual(source_digest(c0), projects["fzy"]["c0_source_tree_sha256"])
            self.assertFalse((c0 / "src/e3_c1_marker.h").exists())

    def test_c1_runner_exposes_reproducible_cli(self):
        result = subprocess.run(
            [sys.executable, str(C1_RUNNER), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--operator", result.stdout)

    def test_c1_patch_introduces_one_observable_missing_dependency(self):
        self.assertTrue(C1_PATCH.is_file(), "C1 Patch 必须存在")
        self.assertTrue(C1_EXPECTED.is_file(), "C1 人工预期必须存在")

        expected = json.loads(C1_EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(expected["provenance"], "TEAM_ORACLE")
        self.assertEqual(expected["delta"]["introduced"], ["ec-c1-options-marker-001"])
        self.assertEqual(expected["delta"]["resolved"], [])
        self.assertEqual(expected["delta"]["unchanged"], [])

        with tempfile.TemporaryDirectory() as directory:
            c0 = Path(directory) / "c0"
            project = Path(directory) / "project"
            shutil.copytree(UPSTREAM, c0)

            def apply_patch(workspace, patch):
                subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
                applied = subprocess.run(
                    ["git", "apply", "--check", "--ignore-whitespace", str(patch)],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(applied.returncode, 0, applied.stderr)
                subprocess.run(
                    ["git", "apply", "--ignore-whitespace", str(patch)],
                    cwd=workspace,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                shutil.rmtree(workspace / ".git")

            apply_patch(c0, C0_PATCH)
            shutil.copytree(c0, project)
            apply_patch(project, C1_PATCH)
            self.assertEqual(
                sorted(path.relative_to(project) for path in project.rglob("*") if path.is_file()),
                sorted(path.relative_to(C0_PROJECT) for path in C0_PROJECT.rglob("*") if path.is_file()),
            )

            source = (project / "src/options.c").read_text(encoding="utf-8")
            makefile = (project / "Makefile").read_text(encoding="utf-8")
            header = project / "src/e3_c1_marker.h"
            self.assertTrue(header.is_file())
            self.assertIn('#include "e3_c1_marker.h"', source)
            self.assertIn("E3_C1_MARKER", source)

            rule = re.search(r"^src/options\.o:\s*(.+)$", makefile, re.MULTILINE)
            self.assertIsNotNone(rule)
            declared = rule.group(1).split()
            self.assertNotIn("src/e3_c1_marker.h", declared)

            finding = expected["findings"][0]
            self.assertEqual(finding["category"], "MISSING")
            self.assertEqual(finding["target"], "src/options.o")
            self.assertEqual(finding["dependency"]["name"], "src/e3_c1_marker.h")


if __name__ == "__main__":
    unittest.main()
