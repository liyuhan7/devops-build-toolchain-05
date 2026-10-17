"""验证六类契约边界，变异只作用于临时副本。"""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import validate
from scripts.contract_checks import ContractSchemas, evidence_errors


class ContractBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="contract-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.contracts = self.root / "contracts"
        shutil.copytree(validate.CONTRACTS_ROOT, self.contracts)
        self.originals = {str(p.relative_to(self.contracts)): p.read_text(encoding="utf-8")
                          for p in self.contracts.rglob("*.json")}
        roots = dict(REPOSITORY_ROOT=self.root, CONTRACTS_ROOT=self.contracts,
                     DRAFT_ROOT=self.contracts / "draft", BUILDCHECKER_ROOT=self.contracts / "buildchecker",
                     ECHECKER_ROOT=self.contracts / "echecker", NEGATIVE_ROOT=self.contracts / "negative")
        patched = patch.multiple(validate, **roots)
        patched.start()
        self.addCleanup(patched.stop)

    def read(self, relative):
        return json.loads((self.contracts / relative).read_text(encoding="utf-8"))

    def errors(self):
        with redirect_stdout(StringIO()):
            return validate.validate()

    def mutate(self, relative, mutation):
        document = self.read(relative)
        mutation(document)
        (self.contracts / relative).write_text(json.dumps(document), encoding="utf-8")

    def restore(self):
        for relative, text in self.originals.items():
            (self.contracts / relative).write_text(text, encoding="utf-8")

    def test_all_production_examples_and_negative_cases_pass(self):
        self.assertEqual(self.errors(), [])

    def test_schema_rejects_missing_unknown_mistyped_and_wrong_service_fields(self):
        examples = [
            ("buildchecker/full-check.response.json", lambda d: d.pop("finished_at")),
            ("draft/draft.response.json", lambda d: d.update(unknown_payload=True)),
            ("buildchecker/full-check.response.json", lambda d: d.update(job_type="MD_FIXER")),
            ("echecker/incremental-check.request.json", lambda d: d["configuration"].update(timeout_seconds=True)),
            ("draft/draft.request.json", lambda d: d.update(source_commit="A" * 40)),
            ("buildchecker/full-check.request.json", lambda d: d["repository"].update(commit="0123456")),
            ("buildchecker/full-check.response.json", lambda d: d.update(created_at="yesterday")),
        ]
        for relative, mutation in examples:
            with self.subTest(relative=relative, mutation=mutation):
                self.restore()
                self.mutate(relative, mutation)
                self.assertTrue(self.errors())

    def test_artifact_kind_and_id_duplicates_and_missing_kinds_are_rejected(self):
        for relative, field in [("echecker/incremental-check.request.json", "input_artifacts"),
                                ("draft/draft.response.json", "output_artifacts"),
                                ("buildchecker/full-check.response.json", "output_artifacts")]:
            for change in ("duplicate_kind", "duplicate_id", "missing_kind"):
                with self.subTest(relative=relative, change=change):
                    self.restore()
                    def mutation(doc):
                        values = doc[field]
                        if change == "duplicate_kind":
                            extra = deepcopy(values[-1])
                            extra["artifact_id"] += "-duplicate"
                            values.append(extra)
                        elif change == "duplicate_id":
                            values[-1]["artifact_id"] = values[0]["artifact_id"]
                        else:
                            values.pop()
                    self.mutate(relative, mutation)
                    self.assertTrue(self.errors())

    def test_echecker_preserves_all_input_metadata(self):
        for key, value in (("uri", "https://different.example.org/image"), ("sha256", "a" * 64),
                           ("produced_by_job_id", "another-job")):
            with self.subTest(key=key):
                self.restore()
                self.mutate("echecker/incremental-check.response.json",
                            lambda d: d["input_artifacts"][-1].update({key: value}))
                self.assertTrue(self.errors())

    def test_echecker_artifact_order_does_not_change_identity(self):
        self.mutate("echecker/incremental-check.response.json", lambda d: d["input_artifacts"].reverse())
        self.assertEqual(self.errors(), [])

    def test_configuration_reuse_cannot_hide_different_build_options(self):
        self.mutate("echecker/incremental-check.request.json",
                    lambda d: d["configuration"]["environment"].update(CFLAGS="-O2"))
        self.assertTrue(self.errors())

    def test_mdfixer_requires_actual_graph_and_referenced_log(self):
        upstream = self.read("echecker/incremental-check.response.json")
        report = self.read("mdfixer/validation/upstream-report.excerpt.json")
        original = self.read("mdfixer/repair.request.json")
        for missing in ("ACTUAL_DEPENDENCY_GRAPH", "BUILD_LOG"):
            with self.subTest(kind=missing):
                request = deepcopy(original)
                request["input_artifacts"] = [a for a in request["input_artifacts"] if a["kind"] != missing]
                self.assertEqual(validate.check_request(request, upstream, report), ["INVALID_REQUEST"])

    def test_evidence_syntax_unknown_id_invalid_escape_and_reversed_lines(self):
        for reference in ("arbitrary text", "artifact:missing#/edges/0",
                          "artifact:bc-actual-graph#/bad~2key", "artifact:bc-log#L30-L10"):
            with self.subTest(reference=reference):
                self.restore()
                self.mutate("buildchecker/full-check.response.json",
                            lambda d: d["findings"][1].update(evidence=[reference]))
                self.assertTrue(self.errors())

    def test_negative_case_must_not_mix_in_an_unrelated_error(self):
        for relative, mutation in [
            ("negative/finding-commit-mismatch.json", lambda d: d["request"]["configuration"].pop("configuration_id")),
            ("negative/incremental-commit-mismatch.json", lambda d: d["request"].pop("changed_paths")),
            ("negative/draft-missing-image.json", lambda d: d["handoff"].pop("context_path")),
        ]:
            with self.subTest(relative=relative):
                self.restore()
                self.mutate(relative, mutation)
                self.assertTrue(self.errors())

    def test_registered_schemas_work_without_network_retrieval(self):
        schemas = ContractSchemas(self.contracts)
        self.assertEqual(schemas.errors(self.read("echecker/incremental-check.response.json"), "job.schema.json"), [])

    def test_supplied_payloads_validate_pointer_and_log_bounds(self):
        response = self.read("buildchecker/full-check.response.json")
        finding = deepcopy(response["findings"][0])
        payloads = {"bc-actual-graph": {"edges": [{"target": "build/app"}]},
                    "bc-log": "first\nsecond\n"}
        finding["evidence"] = ["artifact:bc-actual-graph#/edges/0", "artifact:bc-log#L1-L2"]
        self.assertEqual(evidence_errors([finding], response["output_artifacts"], payloads, True), [])
        for reference in ("artifact:bc-actual-graph#/edges/8", "artifact:bc-log#L1-L3"):
            finding["evidence"] = [reference]
            self.assertTrue(evidence_errors([finding], response["output_artifacts"], payloads, True))
        self.assertTrue(evidence_errors([finding], response["output_artifacts"], {}, True))


if __name__ == "__main__":
    unittest.main()
