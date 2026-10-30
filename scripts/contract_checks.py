"""公共 Schema、产物集合与证据定位的离线检查。"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


COMMIT = r"^[0-9a-f]{40}$"
EVIDENCE = r"^artifact:([^#\s]+)#(/[^\s]*|L[1-9][0-9]*-L[1-9][0-9]*)$"
INPUT_KINDS = {
    "DRAFT": set(),
    "BUILD_CHECKER": {"CONTAINER_IMAGE"},
    "E_CHECKER": {"ACTUAL_DEPENDENCY_GRAPH", "DECLARED_DEPENDENCY_GRAPH", "FULL_CHECK_REPORT", "CONTAINER_IMAGE"},
    "MD_FIXER": {"INCREMENTAL_CHECK_REPORT", "ACTUAL_DEPENDENCY_GRAPH", "DECLARED_DEPENDENCY_GRAPH", "BUILD_LOG"},
}
OUTPUT_KINDS = {
    "DRAFT": {"DRAFT_ENVIRONMENT_MANIFEST", "CONTAINER_IMAGE", "BUILD_LOG", "VALIDATION_LOG"},
    "BUILD_CHECKER": {"ACTUAL_DEPENDENCY_GRAPH", "DECLARED_DEPENDENCY_GRAPH", "FULL_CHECK_REPORT", "BUILD_LOG"},
    "E_CHECKER": {"ACTUAL_DEPENDENCY_GRAPH", "DECLARED_DEPENDENCY_GRAPH", "INCREMENTAL_CHECK_REPORT", "BUILD_LOG"},
    "MD_FIXER": {"GIT_PATCH", "REPAIR_MANIFEST", "BUILD_LOG", "TEST_LOG", "RECHECK_REPORT"},
}


class ContractSchemas:
    """按 $id 注册本地资源，禁止隐式联网读取 Schema。"""

    def __init__(self, root: Path):
        self.documents = {}
        for path in sorted((root / "common").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            self.documents[path.name] = schema
        self.registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in self.documents.values()
        )

    def errors(self, value, name, definition=None):
        schema = self.documents[name]
        if definition:
            schema = {"$ref": schema["$id"] + "#/$defs/" + definition}
        formats = FormatChecker(formats=["date-time", "uri"])
        validator = Draft202012Validator(schema, registry=self.registry, format_checker=formats)
        return [f"{'/'.join(map(str, e.absolute_path)) or '/'}: {e.message}"
                for e in validator.iter_errors(value)]


def artifact_errors(values, required=None):
    """先检查数量与唯一性，再允许调用方建立 kind 索引。"""
    if not isinstance(values, list) or any(not isinstance(a, dict) for a in values):
        return ["Artifact 集合必须是对象数组"]
    kinds = [a.get("kind") for a in values]
    ids = [a.get("artifact_id") for a in values]
    if any(not isinstance(x, str) or not x for x in kinds + ids):
        return ["Artifact kind 和 ID 必须为非空字符串"]
    errors = []
    if any(n != 1 for n in Counter(kinds).values()):
        errors.append("Artifact kind 不得重复")
    if len(ids) != len(set(ids)):
        errors.append("Artifact ID 不得重复")
    if required is not None and set(kinds) != required:
        errors.append("Artifact 类型必须恰好为：" + ", ".join(sorted(required)))
    return errors


def evidence_errors(findings, artifacts, payloads=None, require_payloads=False):
    """本地载荷存在时检查定位；未提供载荷不能声称已验证内容位置。"""
    payloads = payloads or {}
    by_id = {a.get("artifact_id"): a for a in artifacts if isinstance(a, dict)}
    errors = []
    for finding in findings:
        for reference in finding.get("evidence", []):
            match = re.fullmatch(EVIDENCE, reference) if isinstance(reference, str) else None
            if not match:
                errors.append("无效的 evidence 定位：" + str(reference))
                continue
            artifact_id, fragment = match.groups()
            artifact = by_id.get(artifact_id)
            if artifact is None:
                errors.append("evidence 引用了不存在的 Artifact：" + artifact_id)
                continue
            is_json = artifact.get("media_type", "").split(";")[0] == "application/json"
            if fragment.startswith("/") != is_json:
                errors.append("evidence 定位与产物媒体类型不符：" + reference)
                continue
            try:
                if fragment.startswith("/"):
                    tokens = unquote(fragment)[1:].split("/")
                    for token in tokens:
                        if re.search(r"~(?![01])", token):
                            raise ValueError("JSON Pointer 转义非法")
                    if artifact_id in payloads:
                        current = payloads[artifact_id]
                        for token in tokens:
                            token = token.replace("~1", "/").replace("~0", "~")
                            if isinstance(current, list):
                                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                                    raise ValueError("数组索引非法")
                                current = current[int(token)]
                            elif isinstance(current, dict):
                                current = current[token]
                            else:
                                raise ValueError("无法定位标量的子项")
                else:
                    first, last = map(int, re.fullmatch(r"L([0-9]+)-L([0-9]+)", fragment).groups())
                    if first > last:
                        raise ValueError("日志范围倒置")
                    if artifact_id in payloads and last > len(payloads[artifact_id].splitlines()):
                        raise ValueError("日志行号越界")
                if require_payloads and artifact_id not in payloads:
                    raise ValueError("缺少可读取的证据载荷")
            except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
                errors.append(f"evidence 无法定位 {reference}：{exc}")
    return errors


def relative_path(value):
    return (isinstance(value, str) and bool(value) and not value.startswith("/")
            and "\\" not in value and ":" not in value
            and ".." not in PurePosixPath(value).parts)


def request_errors(request, kind, schemas):
    errors = schemas.errors(request, "request.schema.json", kind)
    if errors:
        return errors
    if kind != "DRAFT":
        errors.extend(artifact_errors(request["input_artifacts"], INPUT_KINDS[kind]))
    paths = [request.get("working_directory")] if kind == "DRAFT" else [request["configuration"]["working_directory"]]
    if kind == "DRAFT":
        paths.extend(request["docker"][k] for k in ("dockerfile_path", "context_path"))
        if request["configuration"]["configuration_id"] != request["configuration"]["configuration_digest"]:
            errors.append("DRAFT 配置 ID 与配置来源标识不一致")
    if kind == "E_CHECKER":
        paths.extend(request["changed_paths"])
    if kind == "MD_FIXER":
        paths.extend([request["declaration"]["path"], *request["repair_policy"]["allowed_paths"]])
    if any(not relative_path(path) for path in paths):
        errors.append("请求路径必须位于仓库工作目录内")
    return errors


def finding_codes(request, finding, schemas):
    if request_errors(request, "BUILD_CHECKER", schemas) or schemas.errors(finding, "finding.schema.json"):
        return ["INVALID_REQUEST"]
    if finding["source_commit"] != request["repository"]["commit"]:
        return ["COMMIT_MISMATCH"]
    if finding["configuration_id"] != request["configuration"]["configuration_id"]:
        return ["CONFIGURATION_MISMATCH"]
    return []


def handoff_codes(handoff):
    required = {"trace_id", "job_id", "status", "source_commit", "working_directory", "dockerfile_path",
                "context_path", "configuration_id", "configuration_digest", "image_uri", "build_exit_code",
                "validation_exit_code", "final_validation_passed"}
    if not isinstance(handoff, dict) or set(handoff) != required:
        return ["INVALID_REQUEST"]
    if (not re.fullmatch(COMMIT, str(handoff["source_commit"]))
            or any(not relative_path(handoff[k]) for k in ("working_directory", "dockerfile_path", "context_path"))
            or not handoff["trace_id"] or not handoff["job_id"]):
        return ["INVALID_REQUEST"]
    if handoff["configuration_digest"] != handoff["configuration_id"]:
        return ["CONFIGURATION_MISMATCH"]
    if not re.fullmatch(r"oci://[^\s]+@sha256:[0-9a-f]{64}", str(handoff["image_uri"])):
        return ["INVALID_DRAFT_RESULT"]
    if (handoff["status"] != "SUCCEEDED" or handoff["final_validation_passed"] is not True
            or any(type(handoff[k]) is not int or handoff[k] != 0 for k in ("build_exit_code", "validation_exit_code"))):
        return ["INVALID_DRAFT_RESULT"]
    return []


def incremental_codes(request, schemas):
    if request_errors(request, "E_CHECKER", schemas):
        return ["INVALID_REQUEST"]
    base = request["repository"]["base_commit"]
    config = request["configuration"]["configuration_id"]
    baseline = request["baseline"]
    if base != baseline["source_commit"]:
        return ["BASELINE_COMMIT_MISMATCH"]
    for artifact in request["input_artifacts"]:
        expected = request["repository"]["commit"] if artifact["kind"] == "CONTAINER_IMAGE" else base
        if artifact["source_commit"] != expected:
            return ["COMMIT_MISMATCH" if artifact["kind"] == "CONTAINER_IMAGE" else "BASELINE_COMMIT_MISMATCH"]
        if artifact["configuration_digest"] != config:
            return ["CONFIGURATION_MISMATCH"]
        if artifact["kind"] != "CONTAINER_IMAGE" and artifact["produced_by_job_id"] != baseline["job_id"]:
            return ["INVALID_BASELINE_RESULT"]
    if baseline["configuration_id"] != config:
        return ["CONFIGURATION_MISMATCH"]
    if baseline["trace_id"] != request["trace_id"]:
        return ["TRACE_MISMATCH"]
    if base == request["repository"]["commit"]:
        return ["BASE_NOT_ANCESTOR"]
    return []
