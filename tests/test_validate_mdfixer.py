"""Mutate independent pieces of evidence to exercise the consumer's gates."""

import json
import unittest
from copy import deepcopy

from scripts.validate import CONTRACTS_ROOT, check_request, check_result, validate_mdfixer_semantics


class MDFixerSemanticsTests(unittest.TestCase):
    def setUp(self):
        def read(path):
            return json.loads((CONTRACTS_ROOT / path).read_text(encoding="utf-8"))
        self.request = read("mdfixer/repair.request.json")
        self.response = read("mdfixer/repair.response.json")
        self.manifest = read("mdfixer/repair.manifest.json")
        self.report = read("mdfixer/recheck.report.json")
        self.upstream = read("echecker/incremental-check.response.json")
        self.evidence = read("mdfixer/validation/upstream-report.excerpt.json")

    def result(self):
        return check_result(self.request, self.response, self.manifest, self.report)

    def request_result(self):
        return check_request(self.request, self.upstream, self.evidence)

    def test_production_examples_and_three_negative_fixtures(self):
        self.assertEqual(validate_mdfixer_semantics(), [])

    def test_failed_upstream_cannot_authorize_repair(self):
        self.upstream["status"] = "FAILED"
        self.assertEqual(self.request_result(), ["FINDING_NOT_REPAIRABLE"])

    def test_client_introduced_claim_requires_report_evidence(self):
        self.evidence["delta"]["introduced"] = []
        self.assertEqual(self.request_result(), ["FINDING_NOT_REPAIRABLE"])

    def test_unknown_finding_cannot_authorize_repair(self):
        self.request["finding"]["finding_id"] = "not-in-report"
        self.assertEqual(self.request_result(), ["FINDING_NOT_REPAIRABLE"])

    def test_missing_commit_is_not_a_valid_mismatch(self):
        del self.request["finding"]["source_commit"]
        self.assertEqual(self.request_result(), ["INVALID_REQUEST"])

    def test_configuration_and_trace_mismatch(self):
        for key in ("configuration_id", "trace_id"):
            with self.subTest(key=key):
                original = deepcopy(self.evidence)
                self.evidence[key] = "another-value"
                self.assertEqual(self.request_result(), ["PROVENANCE_MISMATCH"])
                self.evidence = original

    def test_artifact_order_is_irrelevant(self):
        self.request["input_artifacts"].reverse()
        self.response["output_artifacts"].reverse()
        self.assertEqual(self.request_result(), [])
        self.assertEqual(self.result(), [])

    def test_every_output_kind_is_required(self):
        original = deepcopy(self.response["output_artifacts"])
        for missing in original:
            with self.subTest(kind=missing["kind"]):
                self.response["output_artifacts"] = [a for a in original if a != missing]
                self.assertEqual(self.result(), ["INVALID_RESULT"])

    def test_failed_job_cannot_be_consumed_as_success(self):
        self.response["status"] = "FAILED"
        self.assertEqual(self.result(), ["INVALID_RESULT"])

    def test_terminal_time_is_required(self):
        del self.response["finished_at"]
        self.assertEqual(self.result(), ["INVALID_RESULT"])

    def test_each_gate_rejects_failure_missing_and_boolean_exit_code(self):
        codes = {"patch_apply": "PATCH_APPLY_FAILED", "build": "VALIDATION_FAILED",
                 "test": "VALIDATION_FAILED", "recheck": "REVALIDATION_FAILED"}
        original = deepcopy(self.manifest)
        for gate, code in codes.items():
            for mutation in ("nonzero", "missing", "boolean", "status"):
                with self.subTest(gate=gate, mutation=mutation):
                    self.manifest = deepcopy(original)
                    if mutation == "missing":
                        del self.manifest["gates"][gate]
                    elif mutation == "status":
                        self.manifest["gates"][gate]["status"] = "FAILED"
                    else:
                        self.manifest["gates"][gate]["exit_code"] = False if mutation == "boolean" else 1
                    self.assertEqual(self.result(), [code])

    def test_patch_and_workspace_mismatch(self):
        for field, value in (("patch_sha256", "a" * 64), ("workspace_digest", "sha256:" + "a" * 64),
                             ("base_commit", "a" * 40), ("commit_created", True)):
            with self.subTest(field=field):
                original = deepcopy(self.report)
                self.report["workspace_snapshot"][field] = value
                self.assertEqual(self.result(), ["PROVENANCE_MISMATCH"])
                self.report = original

    def test_recheck_command_must_identify_patch(self):
        self.manifest["gates"]["recheck"]["command"][-3] = "a" * 64
        self.assertEqual(self.result(), ["PROVENANCE_MISMATCH"])

    def test_remaining_missing_cannot_be_hidden_by_zero_counter(self):
        self.report["remaining_findings"] = [deepcopy(self.request["finding"])]
        self.assertEqual(self.result(), ["REVALIDATION_FAILED"])

    def test_remaining_missing_requires_integer_zero(self):
        for value in (1, False, "0", None):
            with self.subTest(value=value):
                self.report["remaining_missing"] = value
                self.assertEqual(self.result(), ["REVALIDATION_FAILED"])

    def test_original_finding_must_be_resolved(self):
        self.report["original_finding"]["result"] = "UNCHANGED"
        self.assertEqual(self.result(), ["REVALIDATION_FAILED"])

    def test_changed_file_must_remain_within_policy(self):
        self.manifest["changed_files"][0]["path"] = "../Makefile"
        self.assertEqual(self.result(), ["REPAIR_REJECTED"])


if __name__ == "__main__":
    unittest.main()
