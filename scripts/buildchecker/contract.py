"""在已验证的 DRAFT 镜像中运行 A 组检测，导出与校验公共 Job。"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "services/buildchecker")]
from buildchecker.contract_output import read_json, validate_handoff, verify_job, write_job, write_json
from scripts.buildchecker.lab import fresh_output
from scripts.buildchecker.runtime import run_logged


def source_snapshot(repository, request, output):
    """git archive 只读取指定 commit，不使用当前工作区的未提交内容。"""
    commit = request["repository"]["commit"]
    repository = Path(repository).resolve()
    actual = subprocess.check_output(["git", "rev-parse", commit + "^{commit}"], cwd=repository, text=True).strip()
    if actual != commit:
        raise ValueError("请求必须指定实际 commit 对象")
    origin = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repository, text=True).strip()
    if origin.startswith("git@github.com:"):
        origin = "https://github.com/" + origin.split(":", 1)[1]
    if origin.rstrip("/").removesuffix(".git") != request["repository"]["url"].rstrip("/").removesuffix(".git"):
        raise ValueError("本地仓库 origin 与请求 repository.url 不一致")
    data = subprocess.check_output(["git", "archive", "--format=zip", commit], cwd=repository)
    output = Path(output)
    output.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            target = (output / entry.filename).resolve()
            if output.resolve() not in target.parents or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("教学检测不支持归档越界路径或软链接")
        archive.extractall(output)
        for entry in archive.infolist():
            if not entry.is_dir():
                (output / entry.filename).chmod((entry.external_attr >> 16) & 0o777)
    fixture = (output / request["configuration"]["working_directory"]).resolve()
    if not fixture.is_dir() or (fixture != output.resolve() and output.resolve() not in fixture.parents):
        raise ValueError("请求 working_directory 不存在或越界")
    return fixture


def run_request(args):
    if sys.platform != "linux":
        raise ValueError("公共运行入口需要 Linux Docker 宿主机；verify 可跨平台执行")
    request = read_json(args.request)
    draft = read_json(args.draft_job)
    manifest = validate_handoff(request, draft, args.draft_files)
    config = request["configuration"]
    # 课程解析器仅保证默认 Makefile 的直接目标入口，不推测 -C/-f 的路径语义。
    if config["build_command"] != ["make", *config["targets"]]:
        raise ValueError("公共教学入口支持 build_command=['make', *targets]；编译变量通过 environment 提供")
    output = fresh_output(args.out)
    fixture = source_snapshot(args.repository, request, output / "source")
    image = manifest["image_uri"].removeprefix("oci://")
    if run_logged(["docker", "image", "inspect", image], output / "image") != 0:
        raise ValueError("DRAFT 的不可变镜像未在本地准备好；本入口不自动拉取镜像")
    info = read_json(output / "image/stdout.log")[0]
    if image not in (info.get("RepoDigests") or []):
        raise ValueError("镜像 RepoDigests 不包含 DRAFT manifest digest")
    # 注入检查器，不要求 B 组在自己的镜像中安装 A 组 Python 包。
    # Python3、strace、Make 必须由实际环境提供；缺少时保留日志并明确失败。
    context = output / "context"
    context.mkdir()
    write_json(context / "request.json", request)
    evidence = output / "evidence"
    evidence.mkdir()
    checker = output / "checker"
    shutil.copytree(ROOT / "services/buildchecker/buildchecker", checker / "buildchecker",
                    ignore=shutil.ignore_patterns("__pycache__"))
    command = ["docker", "run", "--rm", "--pull", "never", "--network", "none",
               "--user", f"{os.getuid()}:{os.getgid()}", "--cap-add", "SYS_PTRACE", "--entrypoint", "python3",
               "-e", "HOME=/tmp", "-e", "PYTHONPATH=/checker",
               "--cidfile", str(output / "runner/container-id.txt"),
               "--mount", f"type=bind,src={checker},dst=/checker,readonly",
               "--mount", f"type=bind,src={fixture},dst=/fixture,readonly",
               "--mount", f"type=bind,src={context},dst=/context,readonly",
               "--mount", f"type=bind,src={evidence},dst=/evidence", info["Id"],
               "-m", "buildchecker", "full-check", "--fixture", "/fixture", "--out", "/evidence",
               "--request", "/context/request.json"]
    # 请求已由宿主校验；容器只需标准库检测器，不依赖 DRAFT 镜像安装 jsonschema。
    created_at = datetime.now(timezone.utc).isoformat()
    code = run_logged(command, output / "runner", config["timeout_seconds"] + 60)
    finished_at = datetime.now(timezone.utc).isoformat()
    write_json(output / "invocation.json", {"request": request, "draft_job_id": draft["job_id"],
               "image_uri": manifest["image_uri"], "image_id": info["Id"], "exit_code": code,
               "detector_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (checker / "buildchecker").glob("*.py")}})
    if not (evidence / "findings.json").is_file():
        raw = {"status": "FAILED", "trace_id": request["trace_id"], "findings": [],
               "created_at": created_at, "finished_at": finished_at,
               "public_error_code": "BUILD_TIMEOUT" if code == 124 else "TRACE_FAILED", "error_phase": "TRACE",
               "error": f"容器退出 {code}，未生成完整检测报告；见本次 runner 日志",
               **{key: config[key] for key in ("clean_command", "build_command", "timeout_seconds", "environment")}}
        write_json(evidence / "findings.json", raw)
        for source, target in (("stdout.log", "clean.log"), ("stderr.log", "build-stderr.log")):
            shutil.copyfile(output / "runner" / source, evidence / target)
    raw = read_json(evidence / "findings.json")
    expected = {p.relative_to(fixture).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in fixture.rglob("*") if p.is_file()
                and not any(part in {".git", "work", "__pycache__"} or part == ".env" or part.startswith(".env.")
                            for part in p.relative_to(fixture).parts)}
    if ("input_sha256" in raw and raw["input_sha256"] != expected
            or raw["status"] == "SUCCEEDED" and "input_sha256" not in raw):
        raise ValueError("检测输入与固定 commit 源码副本不一致")
    if raw["status"] == "SUCCEEDED" and code != 0:
        raise ValueError("检测报告与容器退出码不一致")
    job = write_job(request, evidence, output / "public")
    print("JOB_PATH=" + str(output / "public/job.json"))
    return 0 if job["status"] == "SUCCEEDED" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="使用真实成功 DRAFT 交接运行检测；需要本地已准备的 OCI 镜像")
    run.add_argument("--request", required=True)
    run.add_argument("--draft-job", required=True)
    run.add_argument("--draft-files", required=True, help="四类上游载荷的本地目录，文件名见 A 组指南")
    run.add_argument("--repository", required=True, help="待检项目的本地 Git 仓库")
    run.add_argument("--out", required=True, help="本工具链仓库 work/ 内的新目录")
    verify = sub.add_parser("verify", help="校验公共结果的本地 Artifact 实际内容")
    verify.add_argument("--request", required=True)
    verify.add_argument("--job", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "verify":
            job = verify_job(read_json(args.request), args.job)
            print(json.dumps({"verified": True, "job_id": job["job_id"], "status": job["status"]}))
            return 0
        return run_request(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
