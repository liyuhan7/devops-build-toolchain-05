"""B 组入口在共享仓库中仍指向 DRAFT 的输入与证据。"""
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/draft"))

from draft.autobuild import prepare_candidate
from scripts.draft import gate, lab


class DraftLabLayoutTests(unittest.TestCase):
    def test_shared_repository_selects_draft(self):
        self.assertEqual(lab.ROOT, ROOT)
        self.assertEqual(lab.TRACK, "B")
        self.assertEqual(lab.SERVICE, "draft")
        self.assertEqual(gate.ROOT, ROOT)
        self.assertEqual(gate.SERVICE_TEST_ARGS[-1], "services/draft/tests")

    def test_recorded_candidate_matches_fixture_outside_build_context(self):
        fixture = ROOT / "fixtures/draft"
        candidate = ROOT / "fixtures/ci-candidates/context-driven.Dockerfile"
        self.assertNotIn(fixture, candidate.parents)
        prepare_candidate(
            (fixture / "Dockerfile.broken").read_text(encoding="utf-8"),
            candidate.read_text(encoding="utf-8"),
        )

    def test_doctor_saves_evidence_under_requested_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(lab, "ROOT", root), patch.object(lab.sys, "platform", "linux"), \
                 patch.object(lab.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
                self.assertEqual(lab.main(["doctor", "--out", "work/draft/check-01"]), 0)
            output = root / "work/draft/check-01"
            self.assertTrue((output / "invocation.json").is_file())
            self.assertEqual(run.call_args.args[0][-2:], ["--out", str(output / "env.json")])

    def test_candidate_flag_is_limited_to_replay_stages(self):
        with patch.object(lab.sys, "platform", "linux"):
            with self.assertRaises(SystemExit) as error:
                lab.main(["doctor", "--replay"])
        self.assertEqual(error.exception.code, 2)

    def test_recorded_candidate_is_the_verified_e6_build_file(self):
        import hashlib
        candidate = ROOT / "fixtures/ci-candidates/context-driven.Dockerfile"
        provenance = ROOT / "fixtures/ci-candidates/provenance.json"
        self.assertTrue(candidate.is_file())
        record = json.loads(provenance.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(candidate.read_bytes()).hexdigest(), record["build_dockerfile_sha256"])
        self.assertIn("FROM ", candidate.read_text(encoding="utf-8"))

    def test_replay_records_candidate_provenance_before_running_gate(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "fixtures/ci-candidates/context-driven.Dockerfile"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("FROM example.invalid/image@sha256:" + "a" * 64 + "\n", encoding="utf-8")
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            (candidate.parent / "provenance.json").write_text(json.dumps({
                "candidate_file": candidate.name,
                "build_dockerfile_sha256": digest,
            }), encoding="utf-8")
            with patch.object(lab, "ROOT", root), patch.object(lab, "RECORDED_CANDIDATE", candidate), \
                    patch.object(lab.sys, "platform", "linux"), \
                    patch.object(lab, "execute", return_value=0) as execute:
                self.assertEqual(lab.main(["e7", "--replay", "--out", "work/draft/e7/B05-test"]), 0)
            invocation = json.loads((root / "work/draft/e7/B05-test/invocation.json").read_text())
            self.assertEqual(invocation["candidate_sha256"], digest)
            self.assertEqual(invocation["candidate_provenance"].replace("\\", "/"),
                             "fixtures/ci-candidates/provenance.json")
            self.assertIn("scripts/draft/gate.py", execute.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
