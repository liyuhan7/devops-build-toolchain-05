"""孙鲲华 241250109：正确 Finding 缺少 evidence 锚点必须被拒绝。"""
import importlib.util
from pathlib import Path
import unittest


gate_path = Path(__file__).resolve().parents[2] / "scripts/buildchecker/gate.py"
spec = importlib.util.spec_from_file_location("gate_241250109", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class MissingEvidenceTests(unittest.TestCase):
    def report(self):
        return {
            "trace_id": "e7-241250109-missing-evidence",
            "status": "SUCCEEDED",
            "clean_exit_code": 0,
            "build_exit_code": 0,
            "findings": [
                {"type": "MISSING", "target": "main.o", "dependency": "config.h",
                 "evidence": ["trace/t.11:3"]},
                {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h",
                 "evidence": ["make-db.txt:2"]},
            ],
        }

    def test_complete_evidence_passes(self):
        gate.evaluate("original-1", 1, self.report())

    def test_empty_evidence_is_rejected(self):
        for index in (0, 1):
            with self.subTest(finding=self.report()["findings"][index]["type"]):
                report = self.report()
                report["findings"][index]["evidence"] = []
                with self.assertRaisesRegex(ValueError, "evidence"):
                    gate.evaluate("original-1", 1, report)

    def test_missing_evidence_key_is_rejected(self):
        for index in (0, 1):
            with self.subTest(finding=self.report()["findings"][index]["type"]):
                report = self.report()
                del report["findings"][index]["evidence"]
                with self.assertRaisesRegex(ValueError, "evidence"):
                    gate.evaluate("original-1", 1, report)


if __name__ == "__main__":
    unittest.main()
