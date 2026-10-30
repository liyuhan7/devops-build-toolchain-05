"""公共入口只从固定源码版本取输入，不污染成员工作区。"""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.buildchecker import contract


class SourceSnapshotTests(unittest.TestCase):
    def test_snapshot_uses_requested_commit_and_preserves_tracked_content(self):
        request = {"repository": {"commit": "a" * 40, "url": "https://github.com/team/source.git"},
                   "configuration": {"working_directory": "src"}}
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("src/Makefile", "tracked contents\n")
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(contract.subprocess, "check_output", side_effect=[
                "a" * 40 + "\n", "git@github.com:team/source.git\n", archive.getvalue()
            ]) as git:
                fixture = contract.source_snapshot(directory, request, Path(directory) / "source")
            self.assertEqual((fixture / "Makefile").read_text(), "tracked contents\n")
            self.assertEqual(git.call_args_list[-1].args[0], ["git", "archive", "--format=zip", "a" * 40])

    def test_unrelated_repository_is_rejected_before_extracting_sources(self):
        request = {"repository": {"commit": "a" * 40, "url": "https://github.com/team/source.git"}}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(contract.subprocess, "check_output", side_effect=[
                "a" * 40 + "\n", "https://github.com/other/source.git\n"
            ]):
                with self.assertRaisesRegex(ValueError, "origin"):
                    contract.source_snapshot(directory, request, Path(directory) / "source")
            self.assertFalse((Path(directory) / "source").exists())
