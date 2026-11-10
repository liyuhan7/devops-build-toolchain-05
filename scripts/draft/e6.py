"""验证 E5 已记录候选的真实构建与程序输出。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SUPPORTED_DEBIAN_MIRRORS = {
    "mirrors.aliyun.com",
    "mirrors.tuna.tsinghua.edu.cn",
    "mirrors.ustc.edu.cn",
}

from scripts.draft.prompts import classify_missing_make
from scripts.draft.record_candidates import validate_candidate


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def image_tags(run_id):
    suffix = "e6-b-" + run_id[:10]
    return f"draft-e6-baseline:{suffix}", f"draft-e6-candidate:{suffix}"


def adapt_debian_mirror(candidate, mirror):
    """Inject a Debian source rewrite before the candidate's apt-get update."""
    if mirror not in SUPPORTED_DEBIAN_MIRRORS:
        raise ValueError("不支持的 Debian 镜像；请选择阿里云、清华或中科大镜像")
    newline = "\r\n" if "\r\n" in candidate else "\n"
    injection = (
        "sed -i 's#http://deb.debian.org#https://" + mirror
        + "#g' /etc/apt/sources.list.d/debian.sources \\" + newline + "    && apt-get update"
    )
    adapted, count = re.subn(r"(?im)^([ \t]*RUN[ \t]+)apt-get update\b",
                             lambda match: match.group(1) + injection, candidate, count=1)
    if count == 0:
        raise ValueError("候选 Dockerfile 未找到 RUN apt-get update，无法应用镜像适配")
    return adapted, count


def _under(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_e5_inputs(run_dir, root=ROOT):
    """检查 E5 运行状态、输入副本和选中候选的来源记录。"""
    root = Path(root).resolve()
    run_dir = Path(run_dir)
    run_dir = (root / run_dir).resolve() if not run_dir.is_absolute() else run_dir.resolve()
    e5_root = (root / "work/draft/e5").resolve()
    if not _under(run_dir, e5_root) or run_dir == e5_root:
        raise ValueError("E5 运行目录必须位于本仓库 work/draft/e5/ 内")

    invocation_path = run_dir / "invocation.json"
    provenance_path = run_dir / "candidates/provenance.json"
    baseline_path = run_dir / "iter-01/Dockerfile"
    project_path = run_dir / "project"
    manifest_path = run_dir / "input-sha256.json"
    required = (invocation_path, provenance_path, baseline_path, manifest_path)
    if any(not path.is_file() for path in required) or not project_path.is_dir():
        raise ValueError("E5 运行记录、候选来源或固定输入不完整")

    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if invocation.get("stage") != "E5" or invocation.get("track") != "B-DRAFT":
        raise ValueError("指定运行目录不是 B 组 DRAFT E5 记录")
    if invocation.get("exit_code") != 0 or invocation.get("classification") != "MISSING_MAKE":
        raise ValueError("E5 没有成功复现 MISSING_MAKE")

    selected = provenance.get("selected")
    if selected not in ("error-driven", "context-driven") or invocation.get("selected_candidate") != selected:
        raise ValueError("E5 选中候选与来源记录不一致")
    entry = provenance.get("candidates", {}).get(selected)
    if not isinstance(entry, dict):
        raise ValueError("候选来源记录中没有选中的候选")
    candidate_name = entry.get("candidate_file")
    if not isinstance(candidate_name, str) or not candidate_name:
        raise ValueError("候选来源记录缺少候选文件路径")
    candidate_source = run_dir / candidate_name
    candidate_path = candidate_source.resolve()
    if candidate_source.is_symlink() or not _under(candidate_path, run_dir) or not candidate_path.is_file():
        raise ValueError("候选文件路径无效或不在 E5 运行目录内")
    recorded_hash = entry.get("candidate_sha256")
    if not isinstance(recorded_hash, str) or sha256(candidate_path) != recorded_hash:
        raise ValueError("选中候选的 SHA-256 与 E5 来源记录不符")

    baseline = baseline_path.read_text(encoding="utf-8")
    candidate = candidate_path.read_text(encoding="utf-8")
    validate_candidate(candidate, baseline)
    if (project_path / "Dockerfile.broken").read_text(encoding="utf-8") != baseline:
        raise ValueError("E5 Dockerfile 与输入项目中的 Dockerfile.broken 不一致")

    input_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified_inputs = {}
    source_files = set()
    if any(path.is_symlink() for path in project_path.rglob("*")):
        raise ValueError("E5 项目输入包含不支持的符号链接")
    for relative, expected in input_manifest.items():
        if not relative.startswith("project/"):
            continue
        path = (run_dir / relative).resolve()
        if not _under(path, project_path.resolve()) or not path.is_file() or path.is_symlink():
            raise ValueError(f"E5 项目输入路径无效：{relative}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"E5 项目输入哈希不符：{relative}")
        name = relative.removeprefix("project/")
        verified_inputs[name] = actual
        source_files.add(name)
    if not verified_inputs:
        raise ValueError("E5 输入哈希清单中没有项目文件")
    actual_files = {path.relative_to(project_path).as_posix() for path in project_path.rglob("*") if path.is_file()}
    if actual_files != source_files:
        raise ValueError("E5 项目文件集合与输入哈希清单不一致")

    operator = invocation.get("operator", {})
    student_id = operator.get("student_id", "")
    if not re.fullmatch(r"[0-9]{6,16}", student_id):
        raise ValueError("E5 记录中的学号无效")
    if not re.fullmatch(r"[0-9a-f]{40}", invocation.get("source_commit", "")):
        raise ValueError("E5 记录中的源码提交 SHA 无效")
    return {
        "run_dir": run_dir,
        "invocation": invocation,
        "provenance": provenance,
        "selection": selected,
        "selection_reason": provenance.get("selection_reason", ""),
        "candidate": candidate_path,
        "candidate_sha256": recorded_hash,
        "baseline": baseline_path,
        "project": project_path,
        "input_sha256": verified_inputs,
        "student_id": student_id,
    }


def _cleanup_container(cid_file, folder):
    """超时后按 cidfile 清理由宿主机引擎启动的容器。"""
    cid_file = Path(cid_file)
    if not cid_file.is_file():
        return
    container_id = cid_file.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container_id):
        return
    command = ["docker", "rm", "-f", container_id]
    (folder / "cleanup-command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, timeout=20, check=False)
        (folder / "cleanup-stdout.log").write_text(result.stdout, encoding="utf-8")
        (folder / "cleanup-stderr.log").write_text(result.stderr, encoding="utf-8")
        (folder / "cleanup-exit-code.json").write_text(
            json.dumps({"exit_code": result.returncode}) + "\n", encoding="utf-8"
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        (folder / "cleanup-warning.txt").write_text(str(exc) + "\n", encoding="utf-8")


def run_logged(command, folder, timeout, cid_file=None):
    """保存命令输出和退出码；运行超时后尝试清理对应容器。"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (folder / "stdout.log").open("w", encoding="utf-8") as stdout, (
        folder / "stderr.log"
    ).open("w", encoding="utf-8") as stderr:
        try:
            code = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  stdout=stdout, stderr=stderr, timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            code = 124
    (folder / "exit-code.json").write_text(
        json.dumps({"exit_code": code}) + "\n", encoding="utf-8"
    )
    if code == 124 and cid_file is not None:
        _cleanup_container(cid_file, folder)
    return code


def _read_logs(folder):
    folder = Path(folder)
    return "\n".join((folder / name).read_text(encoding="utf-8", errors="replace")
                     for name in ("stdout.log", "stderr.log"))


def run_e6(e5_run, output, build_timeout=600, verify_timeout=60, root=ROOT, debian_mirror=None):
    """从 E5 来源记录重放两轮构建并验证候选镜像。"""
    root = Path(root).resolve()
    inputs = load_e5_inputs(e5_run, root=root)
    if build_timeout <= 0 or verify_timeout <= 0:
        raise ValueError("构建和运行超时必须为正整数")
    candidate_text = inputs["candidate"].read_bytes().decode("utf-8")
    adaptation = None
    build_candidate = candidate_text
    if debian_mirror is not None:
        build_candidate, replacement_count = adapt_debian_mirror(candidate_text, debian_mirror)
        adaptation = {
            "kind": "debian_sources_https_rewrite",
            "from": "http://deb.debian.org",
            "to": "https://" + debian_mirror,
            "replacement_count": replacement_count,
        }
    output = Path(output)
    output = (root / output).resolve() if not output.is_absolute() else output.resolve()
    work = (root / "work").resolve()
    if not _under(output, work) or output == work:
        raise ValueError("E6 证据目录必须位于本仓库 work/ 内")
    if output.exists() and any(output.iterdir()):
        raise ValueError("请使用新的 E6 证据目录，保留此前记录")
    output.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    project = output / "project"
    shutil.copytree(inputs["project"], project)
    iter1, iter2 = output / "iter-01", output / "iter-02"
    iter1.mkdir()
    iter2.mkdir()
    shutil.copy2(inputs["baseline"], iter1 / "Dockerfile")
    source_candidate = iter2 / "source-candidate.Dockerfile"
    shutil.copy2(inputs["candidate"], source_candidate)
    build_dockerfile = iter2 / "Dockerfile"
    if adaptation is None:
        shutil.copy2(source_candidate, build_dockerfile)
    else:
        build_dockerfile.write_bytes(build_candidate.encode("utf-8"))
    build_dockerfile_hash = sha256(build_dockerfile)
    provenance_snapshot = output / "source-provenance.json"
    provenance_snapshot.write_text(
        json.dumps(inputs["provenance"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "source-invocation.json").write_text(
        json.dumps(inputs["invocation"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(inputs["run_dir"] / "input-sha256.json", output / "source-input-sha256.json")
    input_hashes = {
        path.relative_to(project).as_posix(): sha256(path)
        for path in sorted(project.rglob("*")) if path.is_file()
    }
    invocation = {
        "stage": "E6", "track": "B-DRAFT", "time_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": inputs["invocation"].get("source_commit"),
        "e5_run": str(inputs["run_dir"].relative_to(root)),
        "selected_candidate": inputs["selection"], "candidate_sha256": inputs["candidate_sha256"],
        "debian_mirror": debian_mirror,
        "build_timeout_seconds": build_timeout, "verify_timeout_seconds": verify_timeout,
    }
    invocation_path = output / "invocation.json"
    invocation_path.write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "RUNNING", "stage": "E6", "trace_id": "e6-b-" + run_id,
        "source_commit": invocation["source_commit"], "operator": inputs["invocation"]["operator"],
        "selected_candidate": inputs["selection"], "selection_reason": inputs["selection_reason"],
        "candidate_sha256": inputs["candidate_sha256"], "build_dockerfile_sha256": build_dockerfile_hash,
        "build_adaptation": adaptation, "input_sha256": input_hashes, "attempts": [],
    }
    started = time.monotonic()
    try:
        base_tag, candidate_tag = image_tags(run_id)
        base_command = ["docker", "build", "--progress=plain", "--pull=false", "-f",
                        str(iter1 / "Dockerfile"), "-t", base_tag, str(project)]
        base_code = run_logged(base_command, iter1 / "build", build_timeout)
        base_classification = classify_missing_make(_read_logs(iter1 / "build"), base_code)
        result["attempts"].append({
            "iteration": 1, "role": "baseline", "tag": base_tag,
            "build_exit_code": base_code, "failure_class": base_classification["classification"],
        })
        if not base_classification["passed"]:
            raise ValueError("E6 基线未复现 MISSING_MAKE；检查构建日志和环境")

        candidate_command = ["docker", "build", "--progress=plain", "--pull=false", "-f",
                             str(iter2 / "Dockerfile"), "-t", candidate_tag, str(project)]
        candidate_code = run_logged(candidate_command, iter2 / "build", build_timeout)
        candidate_attempt = {
            "iteration": 2, "role": "candidate", "tag": candidate_tag,
            "build_exit_code": candidate_code,
        }
        result["attempts"].append(candidate_attempt)
        if candidate_code != 0:
            raise ValueError("E6 候选构建失败；检查 iter-02/build 日志")

        inspect_command = ["docker", "image", "inspect", candidate_tag, "--format", "{{.Id}}"]
        inspect_code = run_logged(inspect_command, iter2 / "image-inspect", 30)
        if inspect_code != 0:
            raise ValueError("无法读取候选镜像 ID")
        image_id = (iter2 / "image-inspect/stdout.log").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ValueError("Docker 返回的候选镜像 ID 格式无效")
        candidate_attempt["image_id"] = image_id

        cid_file = output / "verify-container-id.txt"
        verify_command = ["docker", "run", "--rm", "--network", "none", "--cpus", "1",
                          "--memory", "128m", "--pids-limit", "64", "--cidfile", str(cid_file), image_id]
        verify_code = run_logged(verify_command, output / "verify", verify_timeout, cid_file=cid_file)
        actual = (output / "verify/stdout.log").read_text(encoding="utf-8", errors="replace")
        verification = {
            "command": verify_command, "image_id": image_id, "exit_code": verify_code,
            "expected_output": "hello E3", "actual_output": actual,
            "output_matches": actual == "hello E3\n",
        }
        result["verification"] = verification
        if verify_code != 0 or not verification["output_matches"]:
            raise ValueError("候选镜像运行结果不符合 hello E3 或退出码非零")
        result["status"] = "SUCCEEDED"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        result.update(status="FAILED", error=str(exc))
    finally:
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        (output / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        invocation["status"] = result["status"]
        invocation["result"] = "result.json"
        invocation_path.write_text(
            json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="验证 E5 选中候选的真实构建和程序输出")
    parser.add_argument("--run-dir", required=True, help="完整的 E5 运行目录")
    parser.add_argument("--out", help="本仓库 work/draft/e6/ 下的新目录")
    parser.add_argument("--build-timeout", type=int, default=600)
    parser.add_argument("--verify-timeout", type=int, default=60)
    parser.add_argument("--debian-mirror", choices=sorted(SUPPORTED_DEBIAN_MIRRORS),
                        help="仅替换候选 Dockerfile 中 deb.debian.org 主机名，并保存原候选与派生文件哈希")
    args = parser.parse_args(argv)
    if sys.platform != "linux":
        parser.error("请在 SSH 登录后的 Linux 课程服务器执行")
    if args.build_timeout <= 0 or args.verify_timeout <= 0:
        parser.error("超时必须为正整数")
    try:
        inputs = load_e5_inputs(args.run_dir)
        if args.out:
            output = args.out
        else:
            suffix = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
            output = ROOT / "work/draft/e6" / f"e6-b-{suffix}"
        result = run_e6(args.run_dir, output, args.build_timeout, args.verify_timeout,
                        debian_mirror=args.debian_mirror)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SUCCEEDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
