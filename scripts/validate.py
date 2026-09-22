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


if __name__ == "__main__":
    raise SystemExit(main())
