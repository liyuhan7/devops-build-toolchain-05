"""保存 E5 的两份模型原始回复、Dockerfile 候选和选择依据。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_candidate(response):
    blocks = re.findall(r"```dockerfile\s*\n(.*?)```", response, flags=re.IGNORECASE | re.DOTALL)
    if len(blocks) != 1:
        raise ValueError("每份原始回复必须且只能包含一个 dockerfile 围栏代码块")
    return blocks[0].strip() + "\n"


def validate_candidate(candidate, baseline):
    preserved = [
        baseline.splitlines()[0],
        "WORKDIR /work",
        "COPY main.c Makefile ./",
        "RUN make",
        'CMD ["./hello"]',
    ]
    missing = [instruction for instruction in preserved if instruction not in candidate]
    if missing:
        raise ValueError("候选没有保留固定输入：" + ", ".join(missing))
    install = re.search(r"apt-get\s+install(?P<packages>[\s\S]*?)(?:&&|\nRUN|$)", candidate)
    build = candidate.find("RUN make")
    if not install:
        raise ValueError("候选没有通过 apt-get install 安装构建工具链")
    packages = install.group("packages")
    has_toolchain = "build-essential" in packages or ("gcc" in packages and "make" in packages)
    if not has_toolchain:
        raise ValueError("候选必须安装 build-essential，或同时安装 gcc 与 make")
    if install.start() > build:
        raise ValueError("候选必须在 RUN make 之前安装构建工具链")


def write_new(path, content):
    if path.exists():
        raise ValueError(f"候选记录已存在，拒绝覆盖：{path}")
    path.write_text(content, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="记录 DRAFT E5 模型候选，不执行 E6 构建")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--error-response", required=True)
    parser.add_argument("--context-response", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--selected", choices=("error-driven", "context-driven"), required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).resolve()
    iteration = run_dir / "iter-01"
    baseline_path = iteration / "Dockerfile"
    if not (run_dir / "invocation.json").is_file() or not baseline_path.is_file():
        raise ValueError("--run-dir 不是完整的 E5 运行目录")
    baseline = baseline_path.read_text(encoding="utf-8")
    response_paths = {
        "error-driven": Path(args.error_response).resolve(),
        "context-driven": Path(args.context_response).resolve(),
    }
    candidates = {}
    for label, response_path in response_paths.items():
        response = response_path.read_text(encoding="utf-8")
        candidate = extract_candidate(response)
        validate_candidate(candidate, baseline)
        candidates[label] = (response, candidate, response_path)

    output = run_dir / "candidates"
    output.mkdir()
    records = {}
    for label, (response, candidate, source_path) in candidates.items():
        response_out = output / f"{label}-response.txt"
        dockerfile_out = output / f"{label}.Dockerfile"
        write_new(response_out, response)
        write_new(dockerfile_out, candidate)
        records[label] = {
            "prompt": f"iter-01/prompt-{label}.txt",
            "prompt_sha256": sha256(iteration / f"prompt-{label}.txt"),
            "response_file": str(response_out.relative_to(run_dir)),
            "response_sha256": sha256(response_out),
            "candidate_file": str(dockerfile_out.relative_to(run_dir)),
            "candidate_sha256": sha256(dockerfile_out),
            "local_input_name": source_path.name,
        }
    provenance = {
        "provider": args.provider,
        "model": args.model,
        "acquisition": "Manual transfer of the two saved E5 prompts; no API key stored",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "candidates": records,
        "selected": args.selected,
        "selection_reason": args.reason,
        "human_modification": "None",
        "validation_status": "PENDING_E6_REAL_BUILD_AND_PROGRAM_VERIFICATION",
    }
    write_new(
        output / "provenance.json",
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
    )
    invocation_path = run_dir / "invocation.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["candidate_generation"] = "RECORDED_TWO_MANUAL_MODEL_RESPONSES"
    invocation["selected_candidate"] = args.selected
    invocation["candidate_validation"] = "PENDING_E6"
    invocation_path.write_text(
        json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output / "provenance.json")
    print("候选已记录；本命令不构建候选，验证状态保持 PENDING_E6。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}")
