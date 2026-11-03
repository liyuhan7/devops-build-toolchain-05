"""根据 DRAFT 真实构建失败生成 E5 教学提示。"""
import json
from pathlib import Path


KEYWORDS = (
    "error",
    "failed",
    "missing",
    "no such file or directory",
    "not found",
)


def classify_missing_make(log, exit_code):
    """确认构建真正到达缺少 make 的目标故障。"""
    lines = log.splitlines()
    root_cause = [
        {"line": number, "text": line}
        for number, line in enumerate(lines, 1)
        if "make: not found" in line
    ]
    matches = [
        {
            "line": number,
            "text": line,
            "keywords": [keyword for keyword in KEYWORDS if keyword in line.lower()],
        }
        for number, line in enumerate(lines, 1)
        if any(keyword in line.lower() for keyword in KEYWORDS)
    ]
    passed = exit_code not in (0, 124) and bool(root_cause)
    return {
        "passed": passed,
        "classification": "MISSING_MAKE" if passed else "INFRASTRUCTURE_OR_UNEXPECTED_FAILURE",
        "build_exit_code": exit_code,
        "root_cause_lines": root_cause,
        "keyword_matches": matches,
        "provenance": "DERIVED_FROM_ACTUAL_BUILD_LOG",
    }


def render_prompts(dockerfile, log, readme):
    """生成错误驱动与上下文驱动的两份提示。"""
    instruction = (
        "Repair the failed Dockerfile using the actual build evidence.\n"
        "Preserve the exact pinned FROM image and digest, WORKDIR, project files, "
        "build command, and final program command. Install the necessary build dependencies.\n"
        "Do not bypass the build, suppress a failure, or replace the program with printed output.\n"
        "Return exactly one complete Dockerfile in a fenced dockerfile code block.\n"
        "The candidate will be built and its program output verified in E6.\n"
    )
    evidence = (
        "\nFailed Dockerfile:\n```dockerfile\n"
        + dockerfile.rstrip()
        + "\n```\n\nLast up to 50 lines of the actual build log:\n```text\n"
        + "\n".join(log.splitlines()[-50:])
        + "\n```\n"
    )
    return {
        "prompt-error-driven.txt": instruction + evidence,
        "prompt-context-driven.txt": (
            instruction
            + "\nProject README context:\n```text\n"
            + readme.rstrip()
            + "\n```\n"
            + evidence
        ),
    }


def write_prompt_evidence(iteration, dockerfile, log, readme, exit_code):
    """写入分类结果和两份提示，不覆盖不同的既有证据。"""
    iteration = Path(iteration)
    classification = classify_missing_make(log, exit_code)
    if not classification["passed"]:
        raise ValueError("构建未复现 make: not found；请保留日志并排查环境故障")
    outputs = {
        "error-localization.json": json.dumps(
            classification, ensure_ascii=False, indent=2
        )
        + "\n",
        **render_prompts(dockerfile, log, readme),
    }
    for name, content in outputs.items():
        path = iteration / name
        if path.exists() and path.read_text(encoding="utf-8") != content:
            raise ValueError(f"已有不同证据，拒绝覆盖：{path}")
    for name, content in outputs.items():
        path = iteration / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    return classification
