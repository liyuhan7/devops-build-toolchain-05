"""使用 Python 标准库校验仓库中的 JSON 契约。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
REQUIRED_SCHEMA_FIELDS = {"$schema", "$id", "title", "type"}
ECHECKER_ROOT = CONTRACTS_ROOT / "echecker"
BUILDCHECKER_ROOT = CONTRACTS_ROOT / "buildchecker"
DRAFT_ROOT = CONTRACTS_ROOT / "draft"
NEGATIVE_ROOT = CONTRACTS_ROOT / "negative"
GIT_EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def iter_references(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from iter_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_references(child)


def decode_pointer_token(token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            decoded.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValueError(f"invalid JSON Pointer escape in token {token!r}")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def contains_anchor(value: Any, anchor: str) -> bool:
    if isinstance(value, dict):
        if value.get("$anchor") == anchor or value.get("$dynamicAnchor") == anchor:
            return True
        return any(contains_anchor(child, anchor) for child in value.values())
    if isinstance(value, list):
        return any(contains_anchor(child, anchor) for child in value)
    return False


def resolve_fragment(document: Any, fragment: str) -> None:
    fragment = unquote(fragment)
    if not fragment:
        return
    if not fragment.startswith("/"):
        if not contains_anchor(document, fragment):
            raise ValueError(f"anchor {fragment!r} does not exist")
        return

    current = document
    for raw_token in fragment[1:].split("/"):
        token = decode_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"object key {token!r} does not exist")
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError(f"invalid array index {token!r}")
            index = int(token)
            if index >= len(current):
                raise ValueError(f"array index {index} is out of range")
            current = current[index]
            continue
        raise ValueError(f"cannot descend through scalar at token {token!r}")


def validate_buildchecker_semantics() -> list[str]:
    """Check the cross-document invariants consumed by EChecker and MDFixer."""
    errors: list[str] = []
    negative_files = (
        NEGATIVE_ROOT / "finding-commit-mismatch.json",
        NEGATIVE_ROOT / "finding-configuration-mismatch.json",
    )

    for path in negative_files:
        if not path.is_file():
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: required negative case is missing")
            continue
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: cannot parse negative case: {exc}")
            continue
        if not isinstance(case, dict):
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: negative case root must be an object")
            continue
        request = case.get("request")
        finding = case.get("finding")
        if not isinstance(request, dict) or not isinstance(finding, dict):
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: request and finding objects are required")
            continue
        request_commit = request.get("repository", {}).get("commit")
        finding_commit = finding.get("source_commit")
        request_config = request.get("configuration", {}).get("configuration_id")
        finding_config = finding.get("configuration_id")
        if path.name == "finding-commit-mismatch.json" and request_commit == finding_commit:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: commit must be deliberately mismatched")
        if path.name == "finding-configuration-mismatch.json" and request_config == finding_config:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: configuration must be deliberately mismatched")
        if case.get("expected_rejection") is not True:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: expected_rejection must be true")

    request_path = BUILDCHECKER_ROOT / "full-check.request.json"
    response_path = BUILDCHECKER_ROOT / "full-check.response.json"
    failed_path = BUILDCHECKER_ROOT / "full-check.failed.json"
    if not all(path.is_file() for path in (request_path, response_path, failed_path)):
        return errors

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        failed = json.loads(failed_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"contracts/buildchecker: cannot parse semantic examples: {exc}")
        return errors

    if not all(isinstance(document, dict) for document in (request, response, failed)):
        errors.append("contracts/buildchecker: semantic examples must have object roots")
        return errors

    if response.get("status") != "SUCCEEDED" or response.get("error") is not None:
        errors.append("full-check.response.json: successful report must have SUCCEEDED and null error")
    if failed.get("status") != "FAILED" or not isinstance(failed.get("error"), dict):
        errors.append("full-check.failed.json: failed report must have FAILED and an error object")
    repository = request.get("repository")
    configuration = request.get("configuration")
    findings = response.get("findings")
    output_artifacts = response.get("output_artifacts")
    if not isinstance(repository, dict) or not isinstance(configuration, dict):
        errors.append("full-check.request.json: repository and configuration must be objects")
        return errors
    if not isinstance(findings, list) or not isinstance(output_artifacts, list):
        errors.append("full-check.response.json: findings and output_artifacts must be arrays")
        return errors
    expected_commit = repository.get("commit")
    expected_config = configuration.get("configuration_id")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"full-check.response.json: finding[{index}] must be an object")
            continue
        if finding.get("source_commit") != expected_commit:
            errors.append(f"full-check.response.json: finding[{index}] source_commit does not match request")
        if finding.get("configuration_id") != expected_config:
            errors.append(f"full-check.response.json: finding[{index}] configuration_id does not match request")
        if finding.get("category") not in {"MISSING", "REDUNDANT"}:
            errors.append(f"full-check.response.json: finding[{index}] has an unsupported category")
    for index, artifact in enumerate(output_artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"full-check.response.json: output_artifacts[{index}] must be an object")
            continue
        if artifact.get("source_commit") != expected_commit:
            errors.append(f"full-check.response.json: output_artifacts[{index}] source_commit does not match request")
        if artifact.get("configuration_digest") != expected_config:
            errors.append(f"full-check.response.json: output_artifacts[{index}] configuration_digest does not match request")
        if artifact.get("produced_by_job_id") != response.get("job_id"):
            errors.append(f"full-check.response.json: output_artifacts[{index}] producer does not match job_id")
    return errors


def validate_draft_semantics() -> list[str]:
    """Check the DRAFT output invariants required by BuildChecker."""
    errors: list[str] = []
    request_path = DRAFT_ROOT / "draft.request.json"
    response_path = DRAFT_ROOT / "draft.response.json"
    failed_path = DRAFT_ROOT / "draft.failed.json"
    required_paths = (request_path, response_path, failed_path)
    if not all(path.is_file() for path in required_paths):
        for path in required_paths:
            if not path.is_file():
                errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: required DRAFT example is missing")
        return errors

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        failed = json.loads(failed_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"contracts/draft: cannot parse semantic examples: {exc}"]

    if not all(isinstance(document, dict) for document in (request, response, failed)):
        return ["contracts/draft: semantic examples must have object roots"]

    source_commit = request.get("source_commit")
    if not isinstance(source_commit, str) or len(source_commit) != 40:
        errors.append("draft.request.json: source_commit must be a complete 40-character SHA")
    elif source_commit == GIT_EMPTY_TREE_SHA:
        errors.append("draft.request.json: source_commit must identify a commit, not Git's empty tree")

    docker = request.get("docker")
    if not isinstance(docker, dict):
        errors.append("draft.request.json: docker must be an object")
    else:
        for field in ("dockerfile_path", "context_path"):
            if not docker.get(field):
                errors.append(f"draft.request.json: docker.{field} is required")

    if response.get("status") != "SUCCEEDED" or response.get("error") is not None:
        errors.append("draft.response.json: successful handoff must have SUCCEEDED and null error")
    if response.get("trace_id") != request.get("trace_id"):
        errors.append("draft.response.json: trace_id does not match the request")
    if failed.get("status") != "FAILED" or not isinstance(failed.get("error"), dict):
        errors.append("draft.failed.json: failed result must have FAILED and an error object")

    configuration = request.get("configuration")
    expected_configuration = (
        configuration.get("configuration_digest")
        if isinstance(configuration, dict)
        else None
    )
    artifacts = response.get("output_artifacts")
    if not isinstance(artifacts, list):
        errors.append("draft.response.json: output_artifacts must be an array")
    else:
        required_kinds = {
            "DRAFT_ENVIRONMENT_MANIFEST",
            "CONTAINER_IMAGE",
            "BUILD_LOG",
            "VALIDATION_LOG",
        }
        kinds = {
            artifact.get("kind")
            for artifact in artifacts
            if isinstance(artifact, dict)
        }
        missing_kinds = sorted(required_kinds - kinds)
        if missing_kinds:
            errors.append(
                "draft.response.json: missing required artifacts: "
                + ", ".join(missing_kinds)
            )
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"draft.response.json: output_artifacts[{index}] must be an object")
                continue
            if artifact.get("source_commit") != source_commit:
                errors.append(f"draft.response.json: output_artifacts[{index}] source_commit does not match request")
            if artifact.get("configuration_digest") != expected_configuration:
                errors.append(f"draft.response.json: output_artifacts[{index}] configuration_digest does not match request")
            if artifact.get("produced_by_job_id") != response.get("job_id"):
                errors.append(f"draft.response.json: output_artifacts[{index}] producer does not match job_id")
            if artifact.get("kind") == "CONTAINER_IMAGE":
                image_uri = artifact.get("uri")
                if not isinstance(image_uri, str) or not image_uri.startswith("oci://") or "@sha256:" not in image_uri:
                    errors.append("draft.response.json: CONTAINER_IMAGE must use an immutable OCI digest")

    common_handoff_fields = {
        "trace_id",
        "job_id",
        "status",
        "source_commit",
        "working_directory",
        "dockerfile_path",
        "context_path",
        "configuration_digest",
        "image_uri",
        "build_exit_code",
        "validation_exit_code",
        "final_validation_passed",
    }
    negative_cases = {
        "draft-missing-commit.json": "source_commit",
        "draft-missing-image.json": "image_uri",
    }
    for filename, missing_field in negative_cases.items():
        path = NEGATIVE_ROOT / filename
        if not path.is_file():
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: required negative case is missing")
            continue
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: cannot parse negative case: {exc}")
            continue
        if not isinstance(case, dict) or not isinstance(case.get("handoff"), dict):
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: handoff object is required")
            continue
        handoff = case["handoff"]
        if case.get("expected_rejection") is not True:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: expected_rejection must be true")
        if missing_field in handoff:
            errors.append(f"{path.relative_to(REPOSITORY_ROOT)}: {missing_field} must be deliberately absent")
        other_missing = sorted((common_handoff_fields - {missing_field}) - handoff.keys())
        if other_missing:
            errors.append(
                f"{path.relative_to(REPOSITORY_ROOT)}: unexpected missing fields: "
                + ", ".join(other_missing)
            )

    return errors


def validate() -> list[str]:
    errors: list[str] = []
    schema_ids: dict[str, Path] = {}
    json_files = sorted(CONTRACTS_ROOT.rglob("*.json"))
    documents: dict[Path, Any] = {}

    if not json_files:
        return ["No JSON contracts found under contracts/."]

    for path in json_files:
        relative_path = path.relative_to(REPOSITORY_ROOT)
        try:
            documents[path.resolve()] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative_path}: cannot parse JSON: {exc}")

    for path in json_files:
        document = documents.get(path.resolve())
        if document is None:
            continue
        relative_path = path.relative_to(REPOSITORY_ROOT)

        if path.name.endswith(".schema.json"):
            if not isinstance(document, dict):
                errors.append(f"{relative_path}: schema root must be an object")
                continue

            missing = sorted(REQUIRED_SCHEMA_FIELDS - document.keys())
            if missing:
                errors.append(
                    f"{relative_path}: missing schema fields: {', '.join(missing)}"
                )

            schema_id = document.get("$id")
            if isinstance(schema_id, str):
                previous = schema_ids.get(schema_id)
                if previous is not None:
                    errors.append(
                        f"{relative_path}: duplicate $id also used by "
                        f"{previous.relative_to(REPOSITORY_ROOT)}"
                    )
                else:
                    schema_ids[schema_id] = path

        for reference in iter_references(document):
            target, separator, fragment = reference.partition("#")
            if target.startswith(("https://", "http://")):
                continue
            target_path = (
                path.resolve()
                if not target
                else (path.parent / unquote(target)).resolve()
            )
            if not target_path.is_file():
                errors.append(f"{relative_path}: unresolved local $ref: {reference}")
                continue
            target_document = documents.get(target_path)
            if target_document is None:
                errors.append(
                    f"{relative_path}: local $ref target is not valid JSON: {reference}"
                )
                continue
            if separator:
                try:
                    resolve_fragment(target_document, fragment)
                except ValueError as exc:
                    errors.append(
                        f"{relative_path}: unresolved local $ref {reference}: {exc}"
                    )

    errors.extend(validate_buildchecker_semantics())
    errors.extend(validate_draft_semantics())
    errors.extend(validate_echecker_semantics())
    errors.extend(validate_mdfixer_semantics())

    if not errors:
        schema_count = sum(path.name.endswith(".schema.json") for path in json_files)
        print(f"Validated {len(json_files)} JSON file(s), including {schema_count} schema(s).")
        print("PASS: DRAFT success response satisfies the BuildChecker handoff rules.")
        print("PASS: draft-missing-commit.json is correctly rejected.")
        print("PASS: draft-missing-image.json is correctly rejected.")
        print("PASS: MDFixer provenance, repair gates, and three negative cases satisfy the contract.")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


def _load_json_example(path: Path, errors: list[str]) -> Any | None:
    relative_path = path.relative_to(REPOSITORY_ROOT)
    if not path.is_file():
        errors.append(f"{relative_path}: required example is missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{relative_path}: cannot parse JSON: {exc}")
        return None


def _artifact_map(artifacts: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(artifacts, list):
        return {}
    return {
        artifact["kind"]: artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("kind"), str)
    }


def _is_commit_mismatch_case(case: dict[str, Any]) -> bool:
    request = case.get("request")
    if not isinstance(request, dict):
        return False
    repository = request.get("repository")
    baseline = request.get("baseline")
    return (
        isinstance(repository, dict)
        and isinstance(baseline, dict)
        and repository.get("base_commit") != baseline.get("source_commit")
    )


def _is_configuration_mismatch_case(case: dict[str, Any]) -> bool:
    request = case.get("request")
    if not isinstance(request, dict):
        return False
    configuration = request.get("configuration")
    baseline = request.get("baseline")
    artifacts = request.get("input_artifacts")
    if not isinstance(configuration, dict) or not isinstance(baseline, dict):
        return False
    configuration_id = configuration.get("configuration_id")
    if baseline.get("configuration_id") != configuration_id:
        return True
    return isinstance(artifacts, list) and any(
        isinstance(artifact, dict)
        and artifact.get("configuration_digest") != configuration_id
        for artifact in artifacts
    )


def _validate_echecker_negative_case(
    path: Path, expected_code: str, demonstrates_case: Any
) -> list[str]:
    errors: list[str] = []
    relative_path = path.relative_to(REPOSITORY_ROOT)
    case = _load_json_example(path, errors)
    if case is None:
        return errors
    if not isinstance(case, dict):
        return [f"{relative_path}: root must be an object"]
    if case.get("expected_rejection") is not True:
        errors.append(f"{relative_path}: expected_rejection must be true")
    if case.get("expected_error_code") != expected_code:
        errors.append(f"{relative_path}: expected_error_code must be {expected_code}")
    if not demonstrates_case(case):
        errors.append(f"{relative_path}: case does not demonstrate {expected_code}")
    return errors


def validate_echecker_semantics() -> list[str]:
    """Check EChecker provenance, failure, and MDFixer handoff invariants."""
    errors: list[str] = []
    request = _load_json_example(ECHECKER_ROOT / "incremental-check.request.json", errors)
    response = _load_json_example(ECHECKER_ROOT / "incremental-check.response.json", errors)
    failed = _load_json_example(ECHECKER_ROOT / "incremental-check.failed.json", errors)
    if errors:
        return errors
    if not all(isinstance(document, dict) for document in (request, response, failed)):
        return ["contracts/echecker: all examples must have object roots"]

    repository = request.get("repository")
    configuration = request.get("configuration")
    baseline = request.get("baseline")
    input_artifacts = request.get("input_artifacts")
    if not isinstance(repository, dict) or not isinstance(configuration, dict):
        errors.append("incremental-check.request.json: repository and configuration must be objects")
        return errors
    if not isinstance(baseline, dict):
        errors.append("incremental-check.request.json: baseline must be an object")
        return errors
    if not isinstance(input_artifacts, list):
        errors.append("incremental-check.request.json: input_artifacts must be an array")
        return errors

    base_commit = repository.get("base_commit")
    current_commit = repository.get("commit")
    configuration_id = configuration.get("configuration_id")
    if base_commit == current_commit:
        errors.append("incremental-check.request.json: base_commit and commit must differ")
    if baseline.get("source_commit") != base_commit:
        errors.append("incremental-check.request.json: baseline source_commit does not match base_commit")
    if baseline.get("configuration_id") != configuration_id:
        errors.append("incremental-check.request.json: baseline configuration does not match request")
    if baseline.get("trace_id") != request.get("trace_id"):
        errors.append("incremental-check.request.json: baseline trace_id does not match request")

    artifacts_by_kind = _artifact_map(input_artifacts)
    required_kinds = {
        "ACTUAL_DEPENDENCY_GRAPH",
        "DECLARED_DEPENDENCY_GRAPH",
        "FULL_CHECK_REPORT",
        "CONTAINER_IMAGE",
    }
    for kind in sorted(required_kinds - artifacts_by_kind.keys()):
        errors.append(f"incremental-check.request.json: missing input artifact {kind}")
    for kind in sorted(required_kinds - {"CONTAINER_IMAGE"}):
        artifact = artifacts_by_kind.get(kind)
        if artifact is None:
            continue
        if artifact.get("produced_by_job_id") != baseline.get("job_id"):
            errors.append(f"incremental-check.request.json: {kind} must come from baseline job")
        if artifact.get("source_commit") != base_commit:
            errors.append(f"incremental-check.request.json: {kind} source_commit does not match baseline")
        if artifact.get("configuration_digest") != configuration_id:
            errors.append(f"incremental-check.request.json: {kind} configuration does not match request")
    image = artifacts_by_kind.get("CONTAINER_IMAGE")
    if image is not None:
        if image.get("source_commit") != current_commit:
            errors.append("incremental-check.request.json: current image source_commit does not match commit")
        if image.get("configuration_digest") != configuration_id:
            errors.append("incremental-check.request.json: current image configuration does not match request")

    if response.get("status") != "SUCCEEDED" or response.get("error") is not None:
        errors.append("incremental-check.response.json: successful result must have SUCCEEDED and null error")
    if response.get("job_type") != "E_CHECKER" or response.get("trace_id") != request.get("trace_id"):
        errors.append("incremental-check.response.json: job_type and trace_id must match request")
    response_input_artifacts = _artifact_map(response.get("input_artifacts"))
    if set(response_input_artifacts) != set(artifacts_by_kind):
        errors.append("incremental-check.response.json: input artifact kinds do not match request")
    findings = response.get("findings")
    output_artifacts = response.get("output_artifacts")
    if not isinstance(findings, list) or not isinstance(output_artifacts, list):
        errors.append("incremental-check.response.json: findings and output_artifacts must be arrays")
    else:
        categories: set[str] = set()
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                errors.append(f"incremental-check.response.json: finding[{index}] must be an object")
                continue
            if finding.get("source_commit") != current_commit:
                errors.append(f"incremental-check.response.json: finding[{index}] source_commit does not match current commit")
            if finding.get("configuration_id") != configuration_id:
                errors.append(f"incremental-check.response.json: finding[{index}] configuration does not match request")
            if finding.get("category") not in {"MISSING", "REDUNDANT"}:
                errors.append(f"incremental-check.response.json: finding[{index}] has an unsupported category")
            else:
                categories.add(finding["category"])
        for index, artifact in enumerate(output_artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"incremental-check.response.json: output_artifacts[{index}] must be an object")
                continue
            if artifact.get("source_commit") != current_commit:
                errors.append(f"incremental-check.response.json: output_artifacts[{index}] source_commit does not match current commit")
            if artifact.get("configuration_digest") != configuration_id:
                errors.append(f"incremental-check.response.json: output_artifacts[{index}] configuration does not match request")
            if artifact.get("produced_by_job_id") != response.get("job_id"):
                errors.append(f"incremental-check.response.json: output_artifacts[{index}] producer does not match job_id")
        if categories != {"MISSING", "REDUNDANT"}:
            errors.append("incremental-check.response.json: sample must demonstrate MISSING and REDUNDANT findings")

    if failed.get("status") != "FAILED" or not isinstance(failed.get("error"), dict):
        errors.append("incremental-check.failed.json: failed result must have FAILED and an error object")
    if failed.get("findings") != [] or failed.get("output_artifacts") != []:
        errors.append("incremental-check.failed.json: failed result cannot expose findings or output artifacts")

    errors.extend(_validate_echecker_negative_case(
        NEGATIVE_ROOT / "incremental-missing-baseline.json",
        "INVALID_REQUEST",
        lambda case: "baseline" not in case.get("request", {}),
    ))
    errors.extend(_validate_echecker_negative_case(
        NEGATIVE_ROOT / "incremental-commit-mismatch.json",
        "BASELINE_COMMIT_MISMATCH",
        _is_commit_mismatch_case,
    ))
    errors.extend(_validate_echecker_negative_case(
        NEGATIVE_ROOT / "incremental-configuration-mismatch.json",
        "CONFIGURATION_MISMATCH",
        _is_configuration_mismatch_case,
    ))
    return errors

def object_at(value, key):
    child = value.get(key) if isinstance(value, dict) else None
    return child if isinstance(child, dict) else {}


def array_at(value, key):
    child = value.get(key) if isinstance(value, dict) else None
    return child if isinstance(child, list) else []


def hex_value(value, length):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None


def safe_path(value):
    return (isinstance(value, str) and bool(value) and not value.startswith("/")
            and "\\" not in value and ":" not in value
            and ".." not in PurePosixPath(value).parts)


def artifacts(value, key):
    return {a.get("kind"): a for a in array_at(value, key)
            if isinstance(a, dict) and isinstance(a.get("kind"), str)}


def check_request(request, upstream, report):
    """Return stable rejection codes for a repair request and its upstream evidence."""
    if not all(isinstance(v, dict) for v in (request, upstream, report)):
        return ["INVALID_REQUEST"]
    finding = object_at(request, "finding")
    commit = object_at(request, "repository").get("commit")
    config = object_at(request, "configuration").get("configuration_id")
    if (request.get("job_type") != "MD_FIXER" or request.get("contract_version") != "1.0.0"
            or not hex_value(commit, 40) or not isinstance(config, str) or not config
            or not hex_value(finding.get("source_commit"), 40)
            or not finding.get("finding_id") or not finding.get("configuration_id")):
        return ["INVALID_REQUEST"]
    if finding.get("category") != "MISSING" or request.get("finding_delta") != "introduced":
        return ["FINDING_NOT_REPAIRABLE"]
    if (finding.get("source_commit") != commit or finding.get("configuration_id") != config):
        return ["PROVENANCE_MISMATCH"]
    introduced = array_at(object_at(report, "delta"), "introduced")
    if (upstream.get("status") != "SUCCEEDED" or upstream.get("error") is not None
            or upstream.get("job_type") != "E_CHECKER"
            or finding not in array_at(upstream, "findings")
            or report.get("findings") != upstream.get("findings")
            or {"current_finding_id": finding["finding_id"]} not in introduced):
        return ["FINDING_NOT_REPAIRABLE"]
    if (not request.get("trace_id") or request["trace_id"] != upstream.get("trace_id")
            or report.get("trace_id") != request["trace_id"]
            or report.get("source_commit") != commit
            or report.get("configuration_id") != config
            or report.get("produced_by_job_id") != upstream.get("job_id")):
        return ["PROVENANCE_MISMATCH"]
    inputs = artifacts(request, "input_artifacts")
    if not {"INCREMENTAL_CHECK_REPORT", "DECLARED_DEPENDENCY_GRAPH"} <= inputs.keys():
        return ["INVALID_REQUEST"]
    if len(inputs) != len(array_at(request, "input_artifacts")):
        return ["INVALID_REQUEST"]
    for a in inputs.values():
        if (a not in array_at(upstream, "output_artifacts") or a.get("source_commit") != commit
                or a.get("configuration_digest") != config
                or a.get("produced_by_job_id") != upstream.get("job_id")):
            return ["PROVENANCE_MISMATCH"]
    declaration = object_at(request, "declaration")
    policy = object_at(request, "repair_policy")
    if (not safe_path(declaration.get("path"))
            or declaration.get("path") != object_at(finding, "location").get("path")
            or declaration.get("target") != finding.get("target")
            or declaration.get("path") not in array_at(policy, "allowed_paths")
            or policy.get("strategy") != "ADD_MISSING_DEPENDENCY"
            or policy.get("allow_source_changes") is not False
            or type(policy.get("maximum_changed_files")) is not int
            or policy["maximum_changed_files"] < 1):
        return ["INVALID_REQUEST"]
    validation = object_at(request, "validation")
    for name in ("build_command", "test_command", "recheck_command"):
        command = validation.get(name)
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            return ["INVALID_REQUEST"]
    if type(validation.get("timeout_seconds")) is not int or validation["timeout_seconds"] <= 0:
        return ["INVALID_REQUEST"]
    return []


def check_result(request, response, manifest, report):
    """Accept only a successful repair whose evidence agrees across all payloads."""
    if not all(isinstance(v, dict) for v in (request, response, manifest, report)):
        return ["INVALID_RESULT"]
    commit = object_at(request, "repository").get("commit")
    config = object_at(request, "configuration").get("configuration_id")
    if (response.get("status") != "SUCCEEDED" or response.get("error") is not None
            or response.get("job_type") != "MD_FIXER" or not response.get("job_id")
            or not response.get("finished_at") or response.get("findings") != []):
        return ["INVALID_RESULT"]
    outputs = artifacts(response, "output_artifacts")
    required = {"GIT_PATCH", "REPAIR_MANIFEST", "BUILD_LOG", "TEST_LOG", "RECHECK_REPORT"}
    if not required <= outputs.keys() or len(outputs) != len(array_at(response, "output_artifacts")):
        return ["INVALID_RESULT"]
    if (artifacts(response, "input_artifacts") != artifacts(request, "input_artifacts")
            or len(array_at(response, "input_artifacts")) != len(array_at(request, "input_artifacts"))):
        return ["PROVENANCE_MISMATCH"]
    for doc, job_key in ((response, "job_id"), (manifest, "job_id"), (report, "mdfixer_job_id")):
        if (doc.get("trace_id") != request.get("trace_id")
                or doc.get(job_key) != response["job_id"] or doc.get("contract_version") != "1.0.0"):
            return ["PROVENANCE_MISMATCH"]
    ids = []
    for a in outputs.values():
        ids.append(a.get("artifact_id"))
        if (not a.get("artifact_id") or not a.get("uri") or not hex_value(a.get("sha256"), 64)
                or a.get("source_commit") != commit or a.get("configuration_digest") != config
                or a.get("produced_by_job_id") != response["job_id"]):
            return ["PROVENANCE_MISMATCH"]
    if len(set(ids)) != len(ids):
        return ["INVALID_RESULT"]
    patch = outputs["GIT_PATCH"]
    snapshot = object_at(manifest, "workspace_snapshot")
    rechecked = object_at(report, "workspace_snapshot")
    if (manifest.get("source_commit") != commit or manifest.get("configuration_id") != config
            or report.get("configuration_id") != config
            or object_at(manifest, "patch_artifact") != {"artifact_id": patch["artifact_id"], "sha256": patch["sha256"]}
            or snapshot.get("mode") != "PATCH_OVERLAY"
            or rechecked.get("patch_artifact_id") != patch["artifact_id"]):
        return ["PROVENANCE_MISMATCH"]
    for s in (snapshot, rechecked):
        digest = s.get("workspace_digest")
        if (s.get("base_commit") != commit or s.get("patch_sha256") != patch["sha256"]
                or s.get("commit_created") is not False or not isinstance(digest, str)
                or not digest.startswith("sha256:") or not hex_value(digest[7:], 64)):
            return ["PROVENANCE_MISMATCH"]
    if snapshot["workspace_digest"] != rechecked["workspace_digest"]:
        return ["PROVENANCE_MISMATCH"]
    finding_id = object_at(request, "finding").get("finding_id")
    policy = object_at(request, "repair_policy")
    changed = array_at(manifest, "changed_files")
    if (manifest.get("finding_id") != finding_id or manifest.get("strategy") != policy.get("strategy")
            or not changed or len(changed) > policy.get("maximum_changed_files", 0)
            or any(not isinstance(f, dict) or not safe_path(f.get("path"))
                   or f.get("path") not in array_at(policy, "allowed_paths") for f in changed)):
        return ["REPAIR_REJECTED"]
    gates = object_at(manifest, "gates")
    for name, code in (("patch_apply", "PATCH_APPLY_FAILED"), ("build", "VALIDATION_FAILED"),
                       ("test", "VALIDATION_FAILED"), ("recheck", "REVALIDATION_FAILED")):
        gate = object_at(gates, name)
        if gate.get("status") != "PASSED" or type(gate.get("exit_code")) is not int or gate["exit_code"] != 0:
            return [code]
        command = gate.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            return [code]
        if name in ("build", "test"):
            if (command != object_at(request, "validation").get(name + "_command")
                    or gate.get("log_artifact_id") != outputs[name.upper() + "_LOG"]["artifact_id"]):
                return ["PROVENANCE_MISMATCH"]
    if object_at(gates, "patch_apply")["command"][:3] != ["git", "apply", "--check"]:
        return ["PATCH_APPLY_FAILED"]
    command = object_at(gates, "recheck")["command"]
    prefix = object_at(request, "validation").get("recheck_command")
    expected_command = (prefix if isinstance(prefix, list) else []) + [
        "--base-commit", commit, "--patch-sha256", patch["sha256"], "--configuration", config]
    if (command != expected_command or command[:2] != ["echecker", "workspace-check"]
            or object_at(gates, "recheck").get("report_artifact_id") != outputs["RECHECK_REPORT"]["artifact_id"]):
        return ["PROVENANCE_MISMATCH"]
    checker = object_at(report, "checker")
    original = object_at(report, "original_finding")
    remaining = report.get("remaining_findings")
    if (checker.get("job_type") != "E_CHECKER" or checker.get("execution_mode") != "PATCHED_WORKSPACE"
            or type(checker.get("exit_code")) is not int or checker["exit_code"] != 0
            or original != {"finding_id": finding_id, "category": "MISSING", "result": "RESOLVED"}
            or type(report.get("remaining_missing")) is not int or report["remaining_missing"] != 0
            or not isinstance(remaining, list)
            or any(not isinstance(f, dict) or f.get("category") != "REDUNDANT" for f in remaining)):
        return ["REVALIDATION_FAILED"]
    return []


def validate_mdfixer_semantics() -> list[str]:
    root = CONTRACTS_ROOT
    try:
        def read(path):
            return json.loads((root / path).read_text(encoding="utf-8"))
        request = read("mdfixer/repair.request.json")
        response = read("mdfixer/repair.response.json")
        manifest = read("mdfixer/repair.manifest.json")
        report = read("mdfixer/recheck.report.json")
        upstream = read("echecker/incremental-check.response.json")
        evidence = read("mdfixer/validation/upstream-report.excerpt.json")
        errors = check_request(request, upstream, evidence) + check_result(request, response, manifest, report)
        rejected = read("mdfixer/repair.rejected.json")
        if (rejected.get("status") != "FAILED" or not rejected.get("finished_at")
                or rejected.get("job_type") != "MD_FIXER" or not rejected.get("job_id")
                or rejected.get("trace_id") != request.get("trace_id")
                or rejected.get("input_artifacts") != request.get("input_artifacts")
                or rejected.get("findings") != []
                or object_at(rejected, "error").get("code") != "REPAIR_REJECTED"
                or object_at(rejected, "error").get("phase") != "PLAN"
                or object_at(rejected, "error").get("retryable") is not False
                or not object_at(object_at(rejected, "error"), "details").get("reason_code")
                or "GIT_PATCH" in artifacts(rejected, "output_artifacts")):
            errors.append("repair.rejected.json: invalid rejection result")
        for filename, code in (("repair-redundant-finding.json", "FINDING_NOT_REPAIRABLE"),
                               ("repair-commit-mismatch.json", "PROVENANCE_MISMATCH"),
                               ("repair-validation-failed.json", "VALIDATION_FAILED")):
            case = read("negative/" + filename)
            if filename == "repair-validation-failed.json":
                actual = check_result(request, response, case.get("manifest"), report)
                repaired = json.loads(json.dumps(case.get("manifest")))
                repaired["gates"]["test"]["exit_code"] = manifest["gates"]["test"]["exit_code"]
                baseline = manifest
            else:
                actual = check_request(case.get("request"), upstream, evidence)
                repaired = json.loads(json.dumps(case.get("request")))
                field = "category" if filename == "repair-redundant-finding.json" else "source_commit"
                repaired["finding"][field] = request["finding"][field]
                baseline = request
            if (case.get("expected_rejection") is not True or case.get("expected_error_code") != code
                    or actual != [code] or repaired != baseline):
                errors.append(f"{filename}: must fail only for the specified single-field mutation ({code})")
        return ["MDFixer: " + e for e in errors]
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return [f"MDFixer: invalid or missing example: {exc}"]


if __name__ == "__main__":
    raise SystemExit(main())
