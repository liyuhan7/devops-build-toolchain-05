"""使用实际解析器输出验证公共结果和失败边界；上游数据均为测试夹具。"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from buildchecker.contract_output import read_json, validate_handoff, verify_job, write_job, write_json
from buildchecker.fullcheck import analyze

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def case(tmp_path):
    request = read_json(ROOT / "contracts/buildchecker/full-check.request.json")
    request["configuration"].update(working_directory="src", targets=["unit.o"],
                                    build_command=["make", "unit.o"], timeout_seconds=30, environment={})
    evidence = tmp_path / "evidence"
    traces = evidence / "trace"
    traces.mkdir(parents=True)
    (traces / "t.10").write_text('execve("/usr/bin/make", ["make", "unit.o"], []) = 0\n'
                                'clone(child_stack=NULL, flags=SIGCHLD) = 11\n')
    (traces / "t.11").write_text('execve("/usr/bin/cc", ["cc", "-c", "unit.c"], []) = 0\n'
                                'openat(AT_FDCWD, "unit.c", O_RDONLY) = 3\n'
                                'openat(AT_FDCWD, "needed.h", O_RDONLY) = 4\n'
                                'openat(AT_FDCWD, "unit.o", O_WRONLY|O_CREAT, 0666) = 5\n')
    (evidence / "make-db.txt").write_text('# Files\nunit.o: unit.c unused.h\n# files hash-table stats:\n')
    result = analyze(traces, evidence / "make-db.txt", "/course/project")
    for name, key in (("actual-graph.json", "actual_graph"), ("declared-graph.json", "declared_graph")):
        write_json(evidence / name, result[key])
    config = request["configuration"]
    raw = {"status": "SUCCEEDED", "trace_id": request["trace_id"], "findings": result["findings"],
           "observed_targets": result["observed_targets"], "clean_exit_code": 0, "build_exit_code": 0,
           "input_sha256": {"Makefile": "0" * 64}, "created_at": "2026-10-30T01:00:00Z",
           "finished_at": "2026-10-30T01:00:01Z"}
    raw.update({key: config[key] for key in ("clean_command", "build_command", "timeout_seconds", "environment")})
    write_json(evidence / "findings.json", raw)
    return request, evidence, tmp_path / "public"


def test_success_with_findings_keeps_raw_report_and_verifiable_four_artifacts(case):
    request, evidence, output = case
    before = (evidence / "findings.json").read_bytes()
    job = write_job(request, evidence, output)
    assert job["status"] == "SUCCEEDED" and job["error"] is None
    assert len(job["output_artifacts"]) == 4
    assert {(f["category"], f["target"], f["dependency"]["name"]) for f in job["findings"]} == {
        ("MISSING", "src/unit.o", "src/needed.h"), ("REDUNDANT", "src/unit.o", "src/unused.h")}
    assert all(f["location"] == {"path": "src/Makefile"} for f in job["findings"])
    assert verify_job(request, output / "job.json") == job
    assert (evidence / "findings.json").read_bytes() == before


def test_output_digest_detects_changed_payload(case):
    request, evidence, output = case
    write_job(request, evidence, output)
    with (output / "build.log").open("a") as stream:
        stream.write("tampered\n")
    with pytest.raises(ValueError, match="ARTIFACT_INTEGRITY_ERROR"):
        verify_job(request, output / "job.json")


def test_no_findings_exports_an_empty_successful_baseline(case):
    request, evidence, output = case
    write_json(evidence / "declared-graph.json", read_json(evidence / "actual-graph.json"))
    raw = read_json(evidence / "findings.json")
    raw["findings"] = []
    write_json(evidence / "findings.json", raw)
    job = write_job(request, evidence, output)
    assert job["status"] == "SUCCEEDED" and job["findings"] == []
    assert read_json(output / "report.json")["summary"] == {"missing_count": 0, "redundant_count": 0}


def test_payload_provenance_is_checked_even_with_an_updated_digest(case):
    request, evidence, output = case
    job = write_job(request, evidence, output)
    graph = read_json(output / "actual-graph.json")
    graph["source_commit"] = "b" * 40
    write_json(output / "actual-graph.json", graph)
    data = (output / "actual-graph.json").read_bytes()
    item = next(a for a in job["output_artifacts"] if a["kind"] == "ACTUAL_DEPENDENCY_GRAPH")
    item.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    write_json(output / "job.json", job)
    with pytest.raises(ValueError, match="内部来源"):
        verify_job(request, output / "job.json")


def test_missing_trace_evidence_cannot_be_published(case):
    request, evidence, output = case
    (evidence / "trace/t.11").unlink()
    with pytest.raises(KeyError):
        write_job(request, evidence, output)
    assert not (output / "job.json").exists()


@pytest.mark.parametrize("code,phase,status", [("CLEAN_FAILED", "CLEAN", "FAILED"),
    ("BUILD_FAILED", "BUILD", "FAILED"), ("BUILD_TIMEOUT", "BUILD", "TIMED_OUT"),
    ("TRACE_FAILED", "TRACE", "FAILED"), ("DECLARED_GRAPH_PARSE_FAILED", "PARSE", "FAILED")])
def test_execution_failure_only_exports_diagnostic_log(case, code, phase, status):
    request, evidence, output = case
    raw = read_json(evidence / "findings.json")
    raw.update(status=status, public_error_code=code, error_phase=phase, error="test execution failure")
    write_json(evidence / "findings.json", raw)
    job = write_job(request, evidence, output)
    assert job["status"] == "FAILED" and job["findings"] == []
    assert job["error"]["code"] == code and job["error"]["phase"] == phase
    assert [a["kind"] for a in job["output_artifacts"]] == ["BUILD_LOG"]
    assert not (output / "report.json").exists()


def test_configuration_and_trace_mismatch_rejected_before_export(case):
    request, evidence, output = case
    request["trace_id"] = "another-run"
    with pytest.raises(ValueError, match="trace_id"):
        write_job(request, evidence, output)
    assert not output.exists()


def test_incomplete_finding_set_fails_real_payload_check(case):
    request, evidence, output = case
    raw = read_json(evidence / "findings.json")
    raw["findings"] = []
    write_json(evidence / "findings.json", raw)
    with pytest.raises(ValueError, match="差集"):
        write_job(request, evidence, output)


def draft_input(request, folder):
    """只用于协议测试，不代表真实 DRAFT 成功记录。"""
    draft = read_json(ROOT / "contracts/draft/draft.response.json")
    image = next(a for a in draft["output_artifacts"] if a["kind"] == "CONTAINER_IMAGE")
    image_bytes = b'{"schemaVersion":2,"config":{},"layers":[]}'
    image["sha256"] = hashlib.sha256(image_bytes).hexdigest()
    image["uri"] = "oci://registry.example.org/test@sha256:" + image["sha256"]
    manifest = {"repository_url": request["repository"]["url"], "source_commit": request["repository"]["commit"],
                "working_directory": "src", "dockerfile_path": "Dockerfile", "context_path": ".",
                "image_uri": image["uri"], "configuration_id": request["configuration"]["configuration_id"],
                "configuration_digest": request["configuration"]["configuration_id"],
                "build": {"command": "make unit.o", "exit_code": 0},
                "validation": {"command": "./app", "exit_code": 0}, "iteration_count": 1,
                "final_validation_passed": True}
    folder.mkdir()
    write_json(folder / "environment-manifest.json", manifest)
    (folder / "image-manifest.json").write_bytes(image_bytes)
    (folder / "build.log").write_text("test build\n")
    (folder / "validation.log").write_text("test validation\n")
    names = ["environment-manifest.json", "image-manifest.json", "build.log", "validation.log"]
    for item, name in zip(draft["output_artifacts"], names):
        data = (folder / name).read_bytes()
        item.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    request["input_artifacts"] = [copy.deepcopy(image)]
    return draft


def test_draft_handoff_checks_actual_downloaded_payloads(case, tmp_path):
    request, _, _ = case
    folder = tmp_path / "upstream"
    draft = draft_input(request, folder)
    assert validate_handoff(request, draft, folder)["final_validation_passed"] is True
    (folder / "validation.log").write_text("changed")
    with pytest.raises(ValueError, match="ARTIFACT_INTEGRITY_ERROR"):
        validate_handoff(request, draft, folder)


@pytest.mark.parametrize("mutation", ["failed-job", "failed-validation", "image-id", "wrong-commit", "manifest-commit"])
def test_invalid_draft_handoff_is_rejected(case, tmp_path, mutation):
    request, _, _ = case
    folder = tmp_path / "upstream"
    draft = draft_input(request, folder)
    if mutation == "failed-job":
        draft["status"] = "RUNNING"
    elif mutation == "wrong-commit":
        draft["output_artifacts"][0]["source_commit"] = "a" * 40
    else:
        manifest = read_json(folder / "environment-manifest.json")
        if mutation == "manifest-commit":
            manifest["source_commit"] = "b" * 40
        elif mutation == "failed-validation":
            manifest["validation"]["exit_code"] = 1
        else:
            manifest["image_uri"] = "sha256:" + "a" * 64
        write_json(folder / "environment-manifest.json", manifest)
        data = (folder / "environment-manifest.json").read_bytes()
        draft["output_artifacts"][0].update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    with pytest.raises(ValueError):
        validate_handoff(request, draft, folder)
