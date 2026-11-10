"""将同次检测的原始证据转换为现有公共契约，不改变课程报告。"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import uuid
from urllib.parse import urlsplit

from scripts.contract_checks import (
    ContractSchemas, OUTPUT_KINDS, artifact_errors, evidence_errors, handoff_codes, request_errors,
)

ROOT = Path(__file__).resolve().parents[3]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(errors):
    if errors:
        raise ValueError("; ".join(errors))


def validate_handoff(request, draft, files):
    """files 是已下载的四类 DRAFT 载荷；URI 与上游元数据保持原样。"""
    schemas = ContractSchemas(ROOT / "contracts")
    require(request_errors(request, "BUILD_CHECKER", schemas))
    require(schemas.errors(draft, "job.schema.json"))
    require(artifact_errors(draft["output_artifacts"], OUTPUT_KINDS["DRAFT"]))
    if (draft["job_type"] != "DRAFT" or draft["status"] != "SUCCEEDED"
            or draft["error"] is not None or draft["findings"]
            or draft["trace_id"] != request["trace_id"]):
        raise ValueError("INVALID_DRAFT_RESULT: 需要同一 trace_id 的成功 DRAFT Job")
    commit = request["repository"]["commit"]
    config = request["configuration"]
    names = {"DRAFT_ENVIRONMENT_MANIFEST": "environment-manifest.json", "CONTAINER_IMAGE": "image-manifest.json",
             "BUILD_LOG": "build.log", "VALIDATION_LOG": "validation.log"}
    by_kind = {item["kind"]: item for item in draft["output_artifacts"]}
    for kind, item in by_kind.items():
        expected_media = {"DRAFT_ENVIRONMENT_MANIFEST": "application/json",
                          "CONTAINER_IMAGE": "application/vnd.oci.image.manifest.v1+json",
                          "BUILD_LOG": "text/plain", "VALIDATION_LOG": "text/plain"}[kind]
        if item["media_type"].split(";")[0] != expected_media:
            raise ValueError("DRAFT Artifact 媒体类型不一致：" + kind)
        if (item["source_commit"] != commit or item["configuration_digest"] != config["configuration_id"]
                or item["produced_by_job_id"] != draft["job_id"]):
            raise ValueError("DRAFT Artifact 的 commit、配置或生产 Job 不一致")
        data = (Path(files) / names[kind]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"] or item.get("size_bytes", len(data)) != len(data):
            raise ValueError("ARTIFACT_INTEGRITY_ERROR: " + kind)
    image = by_kind["CONTAINER_IMAGE"]
    if request["input_artifacts"] != [image]:
        raise ValueError("请求必须原样引用成功 DRAFT 的 CONTAINER_IMAGE")
    manifest = read_json(Path(files) / "environment-manifest.json")
    handoff = {key: manifest[key] for key in (
        "source_commit", "working_directory", "dockerfile_path", "context_path", "configuration_id",
        "configuration_digest", "image_uri", "final_validation_passed")}
    handoff.update(trace_id=draft["trace_id"], job_id=draft["job_id"], status=draft["status"],
                   build_exit_code=manifest["build"]["exit_code"],
                   validation_exit_code=manifest["validation"]["exit_code"])
    require(handoff_codes(handoff))
    if (manifest["repository_url"] != request["repository"]["url"]
            or manifest["source_commit"] != commit
            or manifest["configuration_id"] != config["configuration_id"]
            or manifest["working_directory"] != config["working_directory"]
            or manifest["image_uri"] != image["uri"]
            or not image["uri"].endswith("@sha256:" + image["sha256"])
            or shlex.split(manifest["build"]["command"]) != config["build_command"]):
        raise ValueError("DRAFT 环境清单与检测请求不一致")
    oci = read_json(Path(files) / "image-manifest.json")
    if oci.get("schemaVersion") != 2 or not isinstance(oci.get("config"), dict) or not isinstance(oci.get("layers"), list):
        raise ValueError("需要平台对应的 OCI image manifest，不能用本地 image ID 或镜像索引代替")
    return manifest


def write_job(request, evidence, output):
    """调用方必须先验证 DRAFT，并在该镜像和固定源码副本中运行检测。"""
    schemas = ContractSchemas(ROOT / "contracts")
    require(request_errors(request, "BUILD_CHECKER", schemas))
    evidence, output = Path(evidence).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("公共输出目录必须为空")
    raw = read_json(evidence / "findings.json")
    config = request["configuration"]
    for key, expected in (("trace_id", request["trace_id"]), ("clean_command", config["clean_command"]),
                          ("build_command", config["build_command"]), ("environment", config["environment"]),
                          ("timeout_seconds", config["timeout_seconds"])):
        if raw.get(key) != expected:
            raise ValueError("原始检测与请求不一致：" + key)
    if raw["status"] not in {"SUCCEEDED", "FAILED", "TIMED_OUT"}:
        raise ValueError("检测尚未终结")
    succeeded = raw["status"] == "SUCCEEDED"
    if succeeded and (raw.get("clean_exit_code") != 0 or raw.get("build_exit_code") != 0):
        raise ValueError("不完整构建不能发布成功 Job")
    job_id = "bc-" + uuid.uuid4().hex
    context = {"contract_version": request["contract_version"], "trace_id": request["trace_id"],
               "source_commit": request["repository"]["commit"], "configuration_id": config["configuration_id"],
               "produced_by_job_id": job_id}
    artifacts, payloads = [], {}
    output.mkdir(parents=True, exist_ok=True)

    def artifact(name, kind, payload, media="application/json"):
        path = output / name
        if media == "application/json":
            write_json(path, payload)
        else:
            path.write_text(payload, encoding="utf-8")
        data = path.read_bytes()
        item = {"artifact_id": job_id + "-" + kind.lower(), "kind": kind, "uri": path.as_uri(),
                "media_type": media, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
                "produced_by_job_id": job_id, "source_commit": context["source_commit"],
                "configuration_digest": config["configuration_id"], "created_at": raw["finished_at"]}
        artifacts.append(item)
        payloads[item["artifact_id"]] = payload
        return item["artifact_id"]

    # 原始 trace 和数据库合并进入同一日志，保持成功结果四类 Artifact 的约定。
    log_lines = ["trace_id=" + request["trace_id"], json.dumps(raw, ensure_ascii=False)]
    anchors = {}
    for path in [evidence / "clean.log", evidence / "clean-stderr.log", evidence / "make-db.txt",
                 evidence / "build-stderr.log", *sorted((evidence / "trace").glob("t.*"))]:
        if path.is_file():
            name = path.relative_to(evidence).as_posix()
            log_lines.append("=== " + name + " ===")
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                log_lines.append(line)
                anchors[name, number] = len(log_lines)
    log_id = artifact("build.log", "BUILD_LOG", "\n".join(log_lines) + "\n", "text/plain")
    findings = []
    prefix = PurePosixPath(config["working_directory"])

    def repo_path(path):
        from scripts.contract_checks import relative_path
        if not relative_path(path):
            raise ValueError("检测输出含非仓库相对路径：" + str(path))
        return (prefix / path).as_posix()

    if succeeded:
        graphs = {}
        for label in ("actual", "declared"):
            edges = [{"target": repo_path(edge["target"]), "dependency": repo_path(edge["dependency"])}
                     for edge in read_json(evidence / (label + "-graph.json"))]
            graph = {**context, "graph_type": label.upper(),
                     "targets": [repo_path(t) for t in raw["observed_targets"]], "edges": edges}
            graphs[label] = (artifact(label + "-graph.json", label.upper() + "_DEPENDENCY_GRAPH", graph), edges)
        makefile = next((name for name in ("GNUmakefile", "makefile", "Makefile")
                         if name in raw["input_sha256"]), None)
        if makefile is None:
            raise ValueError("公共适配需要默认 Makefile；不推测自定义声明位置")
        for number, finding in enumerate(raw["findings"], 1):
            category = finding["type"]
            present, absent = ("actual", "declared") if category == "MISSING" else ("declared", "actual")
            edge = {"target": repo_path(finding["target"]), "dependency": repo_path(finding["dependency"])}
            if category not in {"MISSING", "REDUNDANT"} or edge in graphs[absent][1]:
                raise ValueError("Finding 与两图差集不一致")
            references = [f"artifact:{graphs[present][0]}#/edges/{graphs[present][1].index(edge)}",
                          f"artifact:{graphs[absent][0]}#/edges"]
            for entry in finding["evidence"]:
                name = entry.get("artifact", entry.get("trace_file"))
                # 课程 trace 证据使用文件名 t.PID；声明证据使用 make-db.txt。
                if name.startswith("t."):
                    name = "trace/" + name
                line = anchors[name, entry["line"]]
                references.append(f"artifact:{log_id}#L{line}-L{line}")
            findings.append({"finding_id": f"{job_id}-finding-{number}", "source_commit": context["source_commit"],
                             "configuration_id": config["configuration_id"], "target": edge["target"],
                             "location": {"path": repo_path(makefile)}, "category": category, "severity": "WARNING",
                             "message": ("实际观察到未声明的依赖：" if category == "MISSING" else
                                         "当前配置下未观察到已声明依赖：") + edge["dependency"],
                             "dependency": {"ecosystem": "make", "name": edge["dependency"], "scope": "build"},
                             "evidence": list(dict.fromkeys(references))})
        report = {**context, "configuration": config, "findings": findings,
                  "actual_graph_artifact_id": graphs["actual"][0], "declared_graph_artifact_id": graphs["declared"][0],
                  "summary": {"missing_count": sum(f["category"] == "MISSING" for f in findings),
                              "redundant_count": sum(f["category"] == "REDUNDANT" for f in findings)}}
        for phase in ("clean", "build"):
            report[phase] = {"command": config[phase + "_command"], "exit_code": raw[phase + "_exit_code"],
                             "log_artifact_id": log_id}
        artifact("report.json", "FULL_CHECK_REPORT", report)
    job = {"contract_version": request["contract_version"], "trace_id": request["trace_id"], "job_id": job_id,
           "job_type": "BUILD_CHECKER", "status": "SUCCEEDED" if succeeded else "FAILED", "progress_percent": 100,
           "created_at": raw["created_at"], "updated_at": raw["finished_at"], "finished_at": raw["finished_at"],
           "input_artifacts": request["input_artifacts"], "output_artifacts": artifacts, "findings": findings,
           "error": None if succeeded else {"code": raw["public_error_code"], "phase": raw["error_phase"],
                     "message": raw["error"], "retryable": False, "details": {"log_artifact_id": log_id}}}
    pending = output / "job.pending.json"
    write_json(pending, job)
    verify_job(request, pending)
    pending.replace(output / "job.json")
    return job


def validate_job(request, job, payloads, schemas=None):
    """对真实载荷执行 Schema、来源、集合及 evidence 校验。"""
    schemas = schemas or ContractSchemas(ROOT / "contracts")
    require(schemas.errors(job, "job.schema.json"))
    require(artifact_errors(job["output_artifacts"], OUTPUT_KINDS["BUILD_CHECKER"]
                            if job["status"] == "SUCCEEDED" else {"BUILD_LOG"}))
    for item in job["output_artifacts"]:
        if (item["source_commit"] != request["repository"]["commit"]
                or item["configuration_digest"] != request["configuration"]["configuration_id"]
                or item["produced_by_job_id"] != job["job_id"]):
            raise ValueError("输出 Artifact 来源不一致")
    for item in job["input_artifacts"]:
        if (item["source_commit"] != request["repository"]["commit"]
                or item["configuration_digest"] != request["configuration"]["configuration_id"]):
            raise ValueError("输入 Artifact 来源不一致")
    require(evidence_errors(job["findings"], job["output_artifacts"], payloads, require_payloads=True))
    if (job["trace_id"] != request["trace_id"] or job["input_artifacts"] != request["input_artifacts"]
            or job["job_type"] != "BUILD_CHECKER" or job["contract_version"] != request["contract_version"]):
        raise ValueError("Job 与请求不一致")
    from datetime import datetime
    if not (datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
            <= datetime.fromisoformat(job["finished_at"].replace("Z", "+00:00"))
            == datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00"))):
        raise ValueError("终态 Job 时间顺序不一致")
    if job["status"] != "SUCCEEDED":
        if job["status"] != "FAILED" or job["findings"]:
            raise ValueError("执行失败不得交接残缺 Finding")
        return
    by_kind = {a["kind"]: a for a in job["output_artifacts"]}
    graphs = {}
    for kind in ("ACTUAL_DEPENDENCY_GRAPH", "DECLARED_DEPENDENCY_GRAPH", "FULL_CHECK_REPORT"):
        payload = payloads[by_kind[kind]["artifact_id"]]
        for key, expected in (("contract_version", request["contract_version"]), ("trace_id", request["trace_id"]),
                              ("source_commit", request["repository"]["commit"]),
                              ("configuration_id", request["configuration"]["configuration_id"]),
                              ("produced_by_job_id", job["job_id"])):
            if payload.get(key) != expected:
                raise ValueError("产物内部来源不一致：" + key)
        if kind.endswith("GRAPH"):
            if payload.get("graph_type") != kind.split("_")[0]:
                raise ValueError("图类型不一致")
            from scripts.contract_checks import relative_path
            targets, edges = payload["targets"], payload["edges"]
            if len(set(targets)) != len(targets) or any(not relative_path(t) for t in targets):
                raise ValueError("图目标非法或重复")
            pairs = [(e["target"], e["dependency"]) for e in edges]
            if len(set(pairs)) != len(pairs) or any(not relative_path(p) for pair in pairs for p in pair):
                raise ValueError("图边非法或重复")
            graphs[kind] = set(pairs)
    report = payloads[by_kind["FULL_CHECK_REPORT"]["artifact_id"]]
    if report["configuration"] != request["configuration"] or report["findings"] != job["findings"]:
        raise ValueError("完整报告与请求或 Job Finding 不一致")
    for key, kind in (("actual_graph_artifact_id", "ACTUAL_DEPENDENCY_GRAPH"),
                      ("declared_graph_artifact_id", "DECLARED_DEPENDENCY_GRAPH")):
        if report[key] != by_kind[kind]["artifact_id"]:
            raise ValueError("报告引用的图不一致")
    for phase in ("clean", "build"):
        if report[phase] != {"command": request["configuration"][phase + "_command"], "exit_code": 0,
                              "log_artifact_id": by_kind["BUILD_LOG"]["artifact_id"]}:
            raise ValueError("报告命令或退出状态不一致")
    expected = {("MISSING", *edge) for edge in graphs["ACTUAL_DEPENDENCY_GRAPH"] - graphs["DECLARED_DEPENDENCY_GRAPH"]}
    # 声明图包含未构建的逻辑目标；只比较本次实际观察到的 recipe 目标。
    actual_payload = payloads[by_kind["ACTUAL_DEPENDENCY_GRAPH"]["artifact_id"]]
    expected |= {("REDUNDANT", *edge) for edge in graphs["DECLARED_DEPENDENCY_GRAPH"] - graphs["ACTUAL_DEPENDENCY_GRAPH"]
                 if edge[0] in actual_payload["targets"]}
    actual = []
    for finding in job["findings"]:
        if (finding["source_commit"] != request["repository"]["commit"]
                or finding["configuration_id"] != request["configuration"]["configuration_id"]
                or finding["dependency"]["ecosystem"] != "make" or finding["dependency"].get("scope") != "build"):
            raise ValueError("Finding 来源或依赖语义不一致")
        actual.append((finding["category"], finding["target"], finding["dependency"]["name"]))
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("Finding 不等于两图在实际构建范围内的差集")
    if report["summary"] != {"missing_count": sum(f[0] == "MISSING" for f in actual),
                              "redundant_count": sum(f[0] == "REDUNDANT" for f in actual)}:
        raise ValueError("报告统计与 Finding 不一致")


def verify_job(request, job_path):
    """验证同机 file URI 产物的实际字节、内容来源和证据位置。"""
    job = read_json(job_path)
    schemas = ContractSchemas(ROOT / "contracts")
    require(request_errors(request, "BUILD_CHECKER", schemas))
    require(schemas.errors(job, "job.schema.json"))
    payloads = {}
    for item in job["output_artifacts"]:
        uri = urlsplit(item["uri"])
        if uri.scheme != "file" or uri.netloc:
            raise ValueError("本地校验入口只读取同机 file URI；远程产物需由发布端另行提供")
        from urllib.request import url2pathname
        data = Path(url2pathname(uri.path)).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"] or item.get("size_bytes", len(data)) != len(data):
            raise ValueError("ARTIFACT_INTEGRITY_ERROR: " + item["artifact_id"])
        text = data.decode("utf-8")
        expected_media = "text/plain" if item["kind"] == "BUILD_LOG" else "application/json"
        if item["media_type"].split(";")[0] != expected_media:
            raise ValueError("Artifact 媒体类型不一致")
        payloads[item["artifact_id"]] = json.loads(text) if expected_media == "application/json" else text
    validate_job(request, job, payloads, schemas)
    return job
