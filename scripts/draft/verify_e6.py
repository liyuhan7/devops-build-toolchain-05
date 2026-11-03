"""独立核验 E6 构建与运行证据。"""
import argparse
import hashlib
import json
from pathlib import Path
import re

SUPPORTED_DEBIAN_MIRRORS = {
    "mirrors.aliyun.com",
    "mirrors.tuna.tsinghua.edu.cn",
    "mirrors.ustc.edu.cn",
}


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _under(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def verify(directory):
    """检查成功报告、Docker 日志、镜像身份及输入哈希。"""
    root = Path(directory).resolve()
    result = _read_json(root / "result.json")
    if result.get("status") != "SUCCEEDED":
        raise ValueError("E6 运行没有成功")
    attempts = result.get("attempts", [])
    if len(attempts) != 2 or [item.get("iteration") for item in attempts] != [1, 2]:
        raise ValueError("需要按顺序保存两轮构建")
    baseline, candidate = attempts
    if baseline.get("build_exit_code") in (None, 0) or baseline.get("failure_class") != "MISSING_MAKE":
        raise ValueError("第一轮没有重现 MISSING_MAKE")
    baseline_log = "\n".join((root / "iter-01/build" / name).read_text(encoding="utf-8", errors="replace")
                              for name in ("stdout.log", "stderr.log"))
    if not re.search(r"make: not found", baseline_log):
        raise ValueError("基线构建日志缺少 make: not found")
    if candidate.get("build_exit_code") != 0:
        raise ValueError("候选构建没有成功")
    if _read_json(root / "iter-01/build/exit-code.json").get("exit_code") != baseline["build_exit_code"]:
        raise ValueError("基线退出码证据与结果不一致")
    if _read_json(root / "iter-02/build/exit-code.json").get("exit_code") != candidate["build_exit_code"]:
        raise ValueError("候选构建退出码证据与结果不一致")

    source_candidate = root / "iter-02/source-candidate.Dockerfile"
    candidate_file = root / "iter-02/Dockerfile"
    source_bytes = source_candidate.read_bytes()
    build_bytes = candidate_file.read_bytes()
    if _sha256(source_candidate) != result.get("candidate_sha256"):
        raise ValueError("E5 原始候选 SHA-256 与报告不一致")
    adaptation = result.get("build_adaptation")
    if adaptation is None:
        expected_build = source_bytes
    else:
        mirror = adaptation.get("to")
        mirror_host = mirror.removeprefix("https://") if isinstance(mirror, str) else ""
        if (adaptation.get("kind") != "debian_sources_https_rewrite"
                or adaptation.get("from") != "http://deb.debian.org"
                or not mirror.startswith("https://")
                or mirror_host not in SUPPORTED_DEBIAN_MIRRORS):
            raise ValueError("E6 环境适配记录无效")
        source_text = source_bytes.decode("utf-8")
        newline = "\r\n" if "\r\n" in source_text else "\n"
        injection = (
            "sed -i 's#http://deb.debian.org#" + mirror
            + "#g' /etc/apt/sources.list.d/debian.sources \\" + newline + "    && apt-get update"
        )
        expected_text, replacement_count = re.subn(
            r"(?im)^([ \t]*RUN[ \t]+)apt-get update\b",
            lambda match: match.group(1) + injection,
            source_text,
            count=1,
        )
        if replacement_count == 0 or adaptation.get("replacement_count") != replacement_count:
            raise ValueError("E6 环境适配注入数量不一致")
        expected_build = expected_text.encode("utf-8")
    if build_bytes != expected_build:
        raise ValueError("E6 环境适配后的 Dockerfile 与原候选变换不符")
    if _sha256(candidate_file) != result.get("build_dockerfile_sha256"):
        raise ValueError("实际构建 Dockerfile SHA-256 与报告不一致")
    build_command = _read_json(root / "iter-02/build/command.json")
    dockerfile_argument = build_command[build_command.index("-f") + 1]
    if Path(dockerfile_argument).resolve() != candidate_file.resolve():
        raise ValueError("候选构建命令未使用已核验的 Dockerfile")
    provenance = _read_json(root / "source-provenance.json")
    selected = result.get("selected_candidate")
    if provenance.get("selected") != selected:
        raise ValueError("E5 来源记录中的候选选择与 E6 不一致")
    source_candidate = provenance.get("candidates", {}).get(selected, {})
    if source_candidate.get("candidate_sha256") != result.get("candidate_sha256"):
        raise ValueError("E5 候选来源 SHA-256 与 E6 不一致")

    image_id = candidate.get("image_id")
    if not isinstance(image_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("候选镜像 ID 无效")
    inspected = (root / "iter-02/image-inspect/stdout.log").read_text(encoding="utf-8").strip()
    if inspected != image_id:
        raise ValueError("Docker inspect 保存的镜像 ID 与候选构建不一致")
    if _read_json(root / "iter-02/image-inspect/exit-code.json").get("exit_code") != 0:
        raise ValueError("候选镜像 inspect 未成功")

    verification = result.get("verification", {})
    command = _read_json(root / "verify/command.json")
    exit_code = _read_json(root / "verify/exit-code.json").get("exit_code")
    actual = (root / "verify/stdout.log").read_text(encoding="utf-8", errors="replace")
    if command != verification.get("command") or command[-1] != image_id:
        raise ValueError("运行命令没有使用本轮构建的同一镜像 ID")
    if exit_code != 0 or verification.get("exit_code") != 0:
        raise ValueError("候选镜像运行退出码非零")
    if actual != "hello E3\n" or actual != verification.get("actual_output") or verification.get("output_matches") is not True:
        raise ValueError("程序输出与 hello E3 不符")

    project = (root / "project").resolve()
    hashes = result.get("input_sha256", {})
    if not hashes:
        raise ValueError("E6 输入哈希清单为空")
    for relative, expected in hashes.items():
        source = project / relative
        path = source.resolve()
        if source.is_symlink() or not _under(path, project) or not path.is_file():
            raise ValueError(f"E6 输入路径无效：{relative}")
        if _sha256(path) != expected:
            raise ValueError(f"E6 输入哈希不符：{relative}")
    source_inputs = _read_json(root / "source-input-sha256.json")
    source_project_hashes = {
        relative.removeprefix("project/"): expected
        for relative, expected in source_inputs.items() if relative.startswith("project/")
    }
    if source_project_hashes != hashes:
        raise ValueError("E5/E6 项目输入哈希集合不一致")
    return {
        "passed": True,
        "trace_id": result["trace_id"],
        "baseline_failure": "MISSING_MAKE",
        "candidate_build_exit_code": candidate["build_exit_code"],
        "verify_exit_code": exit_code,
        "verified_output": "hello E3",
        "candidate_sha256": result["candidate_sha256"],
        "build_dockerfile_sha256": result["build_dockerfile_sha256"],
        "build_adaptation": adaptation,
        "image_id": image_id,
        "scope": "Saved evidence consistency; does not independently rerun Docker builds",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="核对已保存的 E6 构建与运行证据")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
