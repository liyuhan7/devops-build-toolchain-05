"""管泽昊 241830149：重复 Finding 不得被集合去重掩盖。"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


gate_path = Path(__file__).resolve().parents[2] / "scripts/buildchecker/gate.py"
spec = importlib.util.spec_from_file_location("gate_241830149", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class DuplicateFindingTests(unittest.TestCase):
    def report(self):
        return {
            "trace_id": "e7-241830149-duplicate-finding",
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

    def test_unique_findings_pass_in_either_order(self):
        for name in ("original-1", "original-2", "original-3"):
            for reverse in (False, True):
                with self.subTest(case=name, reverse=reverse):
                    report = self.report()
                    if reverse:
                        report["findings"].reverse()
                    gate.evaluate(name, 1, report)

    def test_duplicate_finding_is_rejected_even_with_exact_expected_set(self):
        for name in ("original-1", "original-2", "original-3"):
            for index in (0, 1):
                with self.subTest(case=name, duplicate=self.report()["findings"][index]["type"]):
                    report = self.report()
                    report["findings"].append(deepcopy(report["findings"][index]))
                    # 两条预期发现均保留，只追加重复项，单靠集合比较无法检出。
                    with self.assertRaisesRegex(ValueError, "Oracle mismatch"):
                        gate.evaluate(name, 1, report)

    def test_different_evidence_does_not_make_duplicate_finding_unique(self):
        for index in (0, 1):
            with self.subTest(duplicate=self.report()["findings"][index]["type"]):
                report = self.report()
                duplicate = deepcopy(report["findings"][index])
                duplicate["evidence"] = ["another-valid-anchor:9"]
                report["findings"].append(duplicate)
                with self.assertRaisesRegex(ValueError, "Oracle mismatch"):
                    gate.evaluate("original-1", 1, report)


if __name__ == "__main__":
    unittest.main()
