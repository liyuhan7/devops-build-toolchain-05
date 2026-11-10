"""E7 个人判定测试：拒绝正确两条发现之外的多报。"""
import importlib.util
from pathlib import Path
import unittest

gate_path = Path(__file__).resolve().parents[2] / "scripts/buildchecker/gate.py"
spec = importlib.util.spec_from_file_location("gate", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def successful(findings):
    return {
        "trace_id": "test-241250029",
        "status": "SUCCEEDED",
        "build_exit_code": 0,
        "clean_exit_code": 0,
        "findings": findings,
    }


def finding(kind, target, dependency):
    return {
        "type": kind,
        "target": target,
        "dependency": dependency,
        "evidence": [{"source": "test"}],
    }


class ExtraFindingTests(unittest.TestCase):
    def test_exact_findings_pass(self):
        findings = [finding(kind, target, dep) for kind, target, dep in gate.EXPECTED]
        gate.evaluate("original-1", 1, successful(findings))

    def test_extra_finding_is_rejected(self):
        findings = [finding(kind, target, dep) for kind, target, dep in gate.EXPECTED]
        findings.append(finding("MISSING", "main.o", "extra.h"))
        with self.assertRaises(ValueError):
            gate.evaluate("original-1", 1, successful(findings))

    def test_missing_finding_is_rejected(self):
        findings = [finding("MISSING", "main.o", "config.h")]
        with self.assertRaises(ValueError):
            gate.evaluate("original-1", 1, successful(findings))


if __name__ == "__main__":
    unittest.main()
