"""正常检测报告必须保留可追踪标识。"""
import unittest

from scripts.buildchecker.gate import evaluate


class TraceIdOracleTests(unittest.TestCase):
    def test_normal_reports_require_trace_id(self):
        findings = [
            {"type": "MISSING", "target": "main.o", "dependency": "config.h",
             "evidence": ["test:config-read"]},
            {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h",
             "evidence": ["test:make-declaration"]},
        ]
        cases = [(f"original-{index}", 1, findings) for index in range(1, 4)]
        cases.append(("fixed", 0, []))

        for case, code, expected_findings in cases:
            report = {"trace_id": "student-241840198", "status": "SUCCEEDED",
                      "clean_exit_code": 0, "build_exit_code": 0,
                      "findings": expected_findings}
            # 正向对照保证拒绝原因只有追踪标识，其他判定条件均有效。
            with self.subTest(case=case, trace_id="valid"):
                self.assertIsNone(evaluate(case, code, report))

            for state in ("missing", "empty", "null"):
                invalid_report = report.copy()
                if state == "missing":
                    invalid_report.pop("trace_id")
                else:
                    invalid_report["trace_id"] = "" if state == "empty" else None
                with self.subTest(case=case, trace_id=state):
                    with self.assertRaisesRegex(ValueError, "^Missing trace_id$"):
                        evaluate(case, code, invalid_report)


if __name__ == "__main__":
    unittest.main()
