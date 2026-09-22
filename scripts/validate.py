"""使用 Python 标准库校验仓库中的 JSON 契约。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
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

    if not errors:
        schema_count = sum(path.name.endswith(".schema.json") for path in json_files)
        print(f"Validated {len(json_files)} JSON file(s), including {schema_count} schema(s).")
        print("PASS: DRAFT success response satisfies the BuildChecker handoff rules.")
        print("PASS: draft-missing-commit.json is correctly rejected.")
        print("PASS: draft-missing-image.json is correctly rejected.")

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

if __name__ == "__main__":
    raise SystemExit(main())
