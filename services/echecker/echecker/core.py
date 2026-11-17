"""预处理指令与配置驱动的依赖图复用，受限于课程显式 Make 样例。"""
import json
from pathlib import Path
import re
import subprocess
import time

from services.buildchecker.buildchecker.fullcheck import compare_graphs, full_check


TARGETS = {"main.o": "main.c", "helper.o": "helper.c"}
PROFILE = "GCC_LOCAL_HEADERS_EXPLICIT_MAKE"


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError("COMMAND_FAILED " + repr(command) + "\n" + result.stdout + result.stderr)
    return result.stdout


def declarations(project):
    """保留课程显式规则与简单变量子集，复杂 Make 语义由全量检测器处理。"""
    text = (project / "Makefile").read_text(encoding="utf-8")
    variables = dict(re.findall(r"^(\w+)\s*=\s*(.*)$", text, re.M))
    graph = {}
    for target in TARGETS:
        match = re.search(r"^" + re.escape(target) + r": ([^\n]*)$", text, re.M)
        if not match:
            raise ValueError("UNSUPPORTED_RULE " + target)
        dependencies = match[1]
        for _ in range(8):
            dependencies = re.sub(r"\$\((\w+)\)", lambda m: variables.get(m[1], m[0]), dependencies)
        if any(token in dependencies for token in ("$", "%", "|")):
            raise ValueError("UNSUPPORTED_DECLARATION")
        graph[target] = sorted(set(dependencies.split()))
    return graph, variables.get("CFLAGS", "")


def findings_for(actual, declared):
    """沿用现有 BuildChecker 的逐目标 MD/RD 判定，报告只保留教学字段。"""
    observed = {target: {"dependencies": dict.fromkeys(deps, {}), "output_evidence": {}}
                for target, deps in actual.items()}
    specified = {target: {"dependencies": dict.fromkeys(deps, {})}
                 for target, deps in declared.items()}
    result = compare_graphs(observed, specified, [])
    return [{key: finding[key] for key in ("type", "target", "dependency")}
            for finding in result["findings"]]


def scan(project, old=None):
    project = Path(project).resolve()
    started = time.perf_counter()
    declared, flags = declarations(project)
    if flags not in ("-O0", "-O1", "-O0 -DMODE=1"):
        raise ValueError("UNSUPPORTED_FLAGS")
    if old is not None and (old.get("profile") != PROFILE or old.get("schema_version") != "echecker-teaching-1"):
        raise ValueError("INVALID_BASELINE_PROFILE")
    # 所有本地预处理指令和配置共同决定缓存是否可复用。
    files = {p.name: p.read_text(encoding="utf-8") for p in sorted(project.iterdir())
             if p.suffix in (".c", ".h")}
    key = {"directives": {name: [line for line in text.splitlines() if line.lstrip().startswith("#")]
                          for name, text in files.items()},
           "recipes": [line for line in (project / "Makefile").read_text(encoding="utf-8").splitlines()
                       if line.startswith("\t")],
           "flags": flags, "compiler": run(["gcc", "--version"], project).splitlines()[0]}
    actual, reused, refreshed = {}, [], []
    for target, source in TARGETS.items():
        if old and old["key"] == key and target in old["actual"]:
            actual[target] = list(old["actual"][target])
            reused.append(target)
        else:
            output = run(["gcc", *flags.split(), "-MM", "-MT", target, source], project)
            actual[target] = sorted(set(output.replace("\\\n", " ").split(":", 1)[1].split()))
            refreshed.append(target)
    findings = findings_for(actual, declared)
    identity = lambda items: {(f["type"], f["target"], f["dependency"]) for f in items}
    current = identity(findings)
    previous = identity(old["findings"]) if old else set()
    return {"schema_version": "echecker-teaching-1", "profile": PROFILE,
            "commit": run(["git", "rev-parse", "HEAD"], project).strip(), "key": key,
            "actual": actual, "declared": declared, "findings": findings,
            "added": [list(item) for item in sorted(current - previous)],
            "resolved": [list(item) for item in sorted(previous - current)],
            "reused": reused, "refreshed": refreshed, "elapsed_s": time.perf_counter() - started}


def build_baseline(project, evidence):
    """消费本仓库 BuildChecker 实采结果，并独立核对 GCC 对象目标投影。"""
    report = scan(project)
    raw = full_check(project, evidence)
    if raw["status"] != "SUCCEEDED":
        raise ValueError("BUILDCHECKER_FAILED " + json.dumps(raw, ensure_ascii=False))
    evidence = Path(evidence)
    graphs = {}
    for label in ("actual", "declared"):
        edges = json.loads((evidence / (label + "-graph.json")).read_text(encoding="utf-8"))
        graphs[label] = {target: sorted({edge["dependency"] for edge in edges if edge["target"] == target})
                         for target in TARGETS}
        if graphs[label] != report[label]:
            raise ValueError("BUILDCHECKER_GCC_GRAPH_MISMATCH " + label)
    projected = [{key: f[key] for key in ("type", "target", "dependency")}
                 for f in raw["findings"] if f["target"] in TARGETS]
    if projected != report["findings"]:
        raise ValueError("BUILDCHECKER_GCC_FINDINGS_MISMATCH")
    report.update(graphs)
    report["findings"] = projected
    report["baseline_source"] = "services/buildchecker: actual-graph.json projected to object targets"
    report["baseline_trace_id"] = raw["trace_id"]
    return report
