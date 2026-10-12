import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/e3"))

from run_c0 import reconstruct_c0, source_digest


UPSTREAM = ROOT / "fixtures/e3/fzy"
PROJECT = ROOT / "fixtures/e3/echecker/project"
C0_PATCH = ROOT / "fixtures/e3/echecker/c0.patch"
C1_PATCH = ROOT / "fixtures/e3/echecker/c1.patch"
C2_PATCH = ROOT / "fixtures/e3/echecker/c2.patch"
C2_EXPECTED = ROOT / "fixtures/e3/echecker/c2-expected.json"
C2_RUNNER = ROOT / "scripts/e3/run_c2.py"


def apply_patch(workspace, patch):
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    try:
        checked = subprocess.run(
            ["git", "apply", "--check", "--ignore-whitespace", str(patch)],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if checked.returncode:
            raise AssertionError(checked.stderr)
        subprocess.run(
            ["git", "apply", "--ignore-whitespace", str(patch)],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        shutil.rmtree(workspace / ".git", ignore_errors=True)


def normalized_files(directory, suffixes=None):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes().replace(b"\r\n", b"\n")
        for path in directory.rglob("*")
        if path.is_file() and (suffixes is None or path.suffix in suffixes)
    }


class E3C2BaselineTests(unittest.TestCase):
    def test_c2_runner_exposes_reproducible_cli(self):
        result = subprocess.run(
            [sys.executable, str(C2_RUNNER), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--operator", result.stdout)

    def test_c2_changes_only_makefile_version(self):
        with tempfile.TemporaryDirectory() as directory:
            c0 = Path(directory) / "c0"
            c1 = Path(directory) / "c1"
            c2 = Path(directory) / "c2"
            reconstruct_c0(UPSTREAM, C0_PATCH, c0)
            shutil.copytree(c0, c1)
            apply_patch(c1, C1_PATCH)
            shutil.copytree(c1, c2)
            apply_patch(c2, C2_PATCH)

            self.assertEqual(normalized_files(c1, {".c", ".h"}), normalized_files(c2, {".c", ".h"}))
            changed = {
                path
                for path, content in normalized_files(c1).items()
                if normalized_files(c2).get(path) != content
            }
            self.assertEqual(changed, {"Makefile"})
            self.assertEqual(set(normalized_files(c1)), set(normalized_files(c2)))
            self.assertTrue((c1 / "Makefile").read_text(encoding="utf-8").startswith("VERSION=1.1\n"))
            self.assertTrue((c2 / "Makefile").read_text(encoding="utf-8").startswith("VERSION=1.2-e3\n"))
            self.assertEqual(source_digest(c2), source_digest(PROJECT))

    def test_c2_keeps_c1_finding_unchanged(self):
        expected = json.loads(C2_EXPECTED.read_text(encoding="utf-8"))
        versions = json.loads((ROOT / "fixtures/e3/echecker/commits.json").read_text(encoding="utf-8"))
        self.assertEqual(expected["provenance"], "TEAM_ORACLE")
        self.assertEqual(expected["source_commit"], versions["versions"]["C2"]["commit_sha"])
        self.assertEqual(expected["delta"]["introduced"], [])
        self.assertEqual(expected["delta"]["resolved"], [])
        self.assertEqual(expected["delta"]["unchanged"], ["ec-c1-options-marker-001"])
        self.assertEqual(len(expected["findings"]), 1)
        self.assertEqual(expected["findings"][0]["category"], "MISSING")
        self.assertEqual(expected["findings"][0]["dependency"]["name"], "src/e3_c1_marker.h")
        self.assertEqual(expected["command_change"]["before"], "1.1")
        self.assertEqual(expected["command_change"]["after"], "1.2-e3")


if __name__ == "__main__":
    unittest.main()
