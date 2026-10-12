"""构建固定 DRAFT 环境，并保存镜像身份、退出码和容器功能证据。"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import uuid

from run_c0 import source_digest, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = "ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3"


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.operator.strip():
        parser.error("operator 不得为空")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    out = (args.output or ROOT / "evidence/e3/draft" / run_id).resolve()
    if out.exists():
        parser.error("证据目录已存在，请指定新目录")
    out.mkdir(parents=True)
    context = ROOT / "work/e3/draft-container" / run_id / "context"
    context.mkdir(parents=True)
    commands, checks = [], []
    run = {
        "case_id": "fzy-draft-container", "provenance": "ACTUAL_RUN", "run_id": run_id,
        "operator": args.operator, "started_at": now(), "status": "RUNNING",
        "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
        "configuration_id": "fzy-upstream-linux-v1", "base_image": BASE,
        "host_platform": platform.platform(), "host_architecture": platform.machine(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "images": {}, "checks": checks,
    }
    write_json(out / "run.json", run)

    def execute(label, argv, cwd=ROOT, required=True, timeout=1800):
        print("执行：" + label, flush=True)
        started = now()
        rc = 125
        with (out / (label + ".stdout.log")).open("wb") as stdout, (out / (label + ".stderr.log")).open("wb") as stderr:
            try:
                process = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr)
                deadline = time.monotonic() + timeout
                heartbeat = time.monotonic() + 30
                try:
                    while process.poll() is None:
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"{label} 超过 {timeout} 秒")
                        if time.monotonic() >= heartbeat:
                            print(f"执行中：{label}；日志目录：{out}", flush=True)
                            heartbeat = time.monotonic() + 30
                        time.sleep(0.5)
                    rc = process.returncode
                except (Exception, KeyboardInterrupt):
                    process.kill()
                    process.wait()
                    raise
            except (OSError, TimeoutError, KeyboardInterrupt) as exc:
                stderr.write((str(exc) or "运行被中断").encode("utf-8"))
                rc = 130 if isinstance(exc, KeyboardInterrupt) else 125
        commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
                         "environment": {}, "started_at": started, "finished_at": now(),
                         "exit_code": rc, "stdout": label + ".stdout.log", "stderr": label + ".stderr.log"})
        write_json(out / "commands.json", commands)
        (out / (label + ".exit")).write_text(str(rc) + "\n", encoding="utf-8")
        if rc == 130 or (required and rc):
            raise RuntimeError(f"{label} 退出码 {rc}；查看对应 stderr 日志")
        return (out / (label + ".stdout.log")).read_bytes()

    def require(condition, label):
        checks.append({"check": label, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(label)

    def inspect(label, image):
        item = json.loads(execute(label, ["docker", "image", "inspect", image]))[0]
        require(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", item.get("Id", ""))), label + " 镜像 ID 有效")
        return {"id": item["Id"], "repo_digests": item.get("RepoDigests", []),
                "os": item.get("Os"), "architecture": item.get("Architecture")}

    try:
        run["experiment_commit"] = execute("git-revision", ["git", "rev-parse", "HEAD"]).decode().strip()
        run["worktree_dirty"] = bool(execute("git-status", ["git", "status", "--porcelain"]))
        projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))["fzy"]
        require(source_digest(ROOT / "fixtures/e3/fzy") == projects["source_tree_sha256"], "固定上游源码摘要一致")
        # 上下文只包含构建所需的受控文件；LF 规范化在独立副本内完成。
        files = execute("context-files", ["git", "ls-files", "-z", "fixtures/e3/fzy", "fixtures/e3/draft",
                                          "scripts/e3/verify_fzy.sh"]).decode("utf-8").split("\0")
        manifest = {}
        for name in filter(None, files):
            data = (ROOT / name).read_bytes()
            if b"\0" not in data:
                data = data.replace(b"\r\n", b"\n")
            destination = context / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            manifest[name] = hashlib.sha256(data).hexdigest()
        write_json(out / "context-manifest.json", manifest)
        run["context_sha256"] = source_digest(context)
        run["source_tree_sha256"] = source_digest(context / "fixtures/e3/fzy")
        run["context_line_endings"] = "LF"
        for kind in ("broken", "reference"):
            dockerfile = context / ("fixtures/e3/draft/Dockerfile." + kind)
            source = dockerfile.read_text(encoding="utf-8")
            require(re.findall(r"^FROM\s+(\S+)", source, re.MULTILINE) == [BASE], kind + " 使用同一固定基础镜像")
            (out / ("Dockerfile." + kind)).write_text(source, encoding="utf-8", newline="\n")
        execute("docker-version", ["docker", "version", "--format", "{{json .}}"])
        require(execute("docker-platform", ["docker", "info", "--format", "{{.OSType}}"]).strip() == b"linux", "Docker 使用 Linux 容器引擎")
        execute("base-cache-inspect", ["docker", "image", "inspect", BASE], required=False)
        if commands[-1]["exit_code"]:
            execute("base-pull", ["docker", "pull", BASE])
        run["images"]["base"] = inspect("base-inspect", BASE)
        digest = BASE.split("@", 1)[1]
        require(any(value.endswith("@" + digest) for value in run["images"]["base"]["repo_digests"]), "基础镜像 RepoDigest 与固定摘要一致")
        require(run["images"]["base"]["os"] == "linux", "基础镜像为 Linux")
        broken_tag = "devops-e3-draft-broken:" + run_id.lower()
        reference_tag = "devops-e3-draft-reference:" + run_id.lower()
        execute("broken-build", ["docker", "build", "--progress=plain", "-f", "fixtures/e3/draft/Dockerfile.broken", "-t", broken_tag, "."], context, required=False)
        broken_rc = commands[-1]["exit_code"]
        error = (out / "broken-build.stderr.log").read_text(encoding="utf-8", errors="replace")
        broken_ok = broken_rc != 0 and bool(re.search(r"\b(?:make|gcc):\s*(?:not found|command not found|未找到)", error, re.IGNORECASE))
        run["broken_build"] = {"status": "PASSED" if broken_ok else "FAILED", "exit_code": broken_rc}
        require(broken_ok, "失败候选在项目构建步骤报告工具缺失")
        iid = out / "reference-image.id"
        execute("reference-build", ["docker", "build", "--progress=plain", "--iidfile", str(iid), "-f", "fixtures/e3/draft/Dockerfile.reference", "-t", reference_tag, "."], context)
        run["reference_build"] = {"status": "PASSED", "exit_code": 0}
        image_id = iid.read_text(encoding="utf-8").strip()
        require(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id)), "本次构建产生有效镜像 ID")
        run["images"]["reference"] = inspect("reference-inspect", image_id)
        execute("container-validation", ["docker", "run", "--rm", "--network", "none", "--workdir", "/repo",
                                          "--mount", f"type=bind,src={out},dst=/evidence",
                                          "-e", "E3_ENVIRONMENT_REFERENCE=" + image_id, image_id,
                                          "bash", "scripts/e3/verify_fzy.sh", "--operator", args.operator,
                                          "--revision", run["experiment_commit"], "--output", "/evidence/functional"])
        functional = json.loads((out / "functional/run.json").read_text(encoding="utf-8"))
        functional_checks = functional.get("checks", [])
        require(functional.get("status") == "PASSED" and len(functional_checks) >= 20
                and all(item.get("passed") is True for item in functional_checks), "容器功能检查通过且详细证据已导出")
        functional_commands = json.loads((out / "functional/commands.json").read_text(encoding="utf-8"))
        require(bool(functional_commands) and all((out / "functional" / item[key]).is_file()
                for item in functional_commands for key in ("stdout", "stderr")), "功能命令的 stdout/stderr 文件齐全")
        run["container_validation"] = {"exit_code": 0, "status": "PASSED", "evidence": "functional/run.json"}
        run["status"] = "PASSED"
    except (Exception, KeyboardInterrupt) as exc:
        run["status"] = "FAILED"
        run["failure"] = str(exc) or "运行被中断"
    finally:
        run["finished_at"] = now()
        write_json(out / "run.json", run)
        write_json(out / "commands.json", commands)
        rows = "\n".join(f"| {item['check']} | {'通过' if item['passed'] else '失败'} |" for item in checks)
        (out / "observations.md").write_text(
            "# DRAFT 容器实际观察\n\n来源：ACTUAL_RUN。\n\n"
            "预期：失败候选报告构建工具缺失；参考候选在同一固定源码上完成构建、测试和功能验证。\n\n"
            "| 检查 | 实际结果 |\n|---|---|\n" + rows +
            f"\n\n状态：{run['status']}。失败原因：{run.get('failure', '无')}。\n"
            "\n完整命令、退出码与镜像身份见 commands.json、run.json；功能详情见 functional/。\n", encoding="utf-8")
        print(f"STATUS={run['status']}\nEVIDENCE_DIR={out}")
    return 0 if run["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
