#!/usr/bin/env bash
# 构建 DRAFT 失败/参考镜像并保存可复核的容器运行证据。
set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OPERATOR=""
OUTPUT=""

usage() { printf '用法：scripts/e3/run_draft_container.sh --operator 姓名 [--output 证据目录]\n'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --operator|--output)
      if [ $# -lt 2 ] || [[ "$2" == --* ]]; then printf '参数 %s 缺少取值\n' "$1" >&2; exit 2; fi
      [ "$1" = "--operator" ] && OPERATOR=$2
      [ "$1" = "--output" ] && OUTPUT=$2
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) printf '未知参数：%s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

[ -n "$OPERATOR" ] || { printf '缺少 --operator\n' >&2; exit 2; }
command -v docker >/dev/null 2>&1 || { printf '未找到 docker\n' >&2; exit 2; }

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$(LC_ALL=C tr -dc '0-9a-f' < /dev/urandom | head -c 8)
OUT=${OUTPUT:-$ROOT/evidence/e3/draft/$RUN_ID}
[ ! -e "$OUT" ] || { printf '证据目录已存在：%s\n' "$OUT" >&2; exit 2; }
mkdir -p "$OUT" || exit 2
OUT=$(cd "$OUT" && pwd) || exit 2
RECORDS="$OUT/commands.records.jsonl"
: > "$RECORDS"

run_capture() {
  local label=$1 cwd=$2
  shift 2
  local started finished rc
  started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  (
    cd "$cwd" || exit 127
    "$@"
  ) >"$OUT/$label.stdout.log" 2>"$OUT/$label.stderr.log"
  rc=$?
  finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s\n' "$rc" >"$OUT/$label.exit"
  python3 - "$RECORDS" "$label" "$cwd" "$started" "$finished" "$rc" "$OUT/$label.stdout.log" "$OUT/$label.stderr.log" "$@" <<'PY'
import json
import sys
from pathlib import Path

records, label, cwd, started, finished, rc, stdout, stderr, *argv = sys.argv[1:]
entry = {
    "label": label,
    "argv": argv,
    "cwd": cwd,
    "environment": {},
    "started_at": started,
    "finished_at": finished,
    "exit_code": int(rc),
    "stdout": Path(stdout).name,
    "stderr": Path(stderr).name,
}
with open(records, "a", encoding="utf-8") as stream:
    stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY
  return "$rc"
}

set -e
BROKEN_TAG=devops-e3-draft-broken:ubuntu24.04
REFERENCE_TAG=devops-e3-draft-reference:ubuntu24.04
run_capture broken-build "$ROOT" docker build --progress=plain -f fixtures/e3/draft/Dockerfile.broken -t "$BROKEN_TAG" . || true
run_capture reference-build "$ROOT" docker build --progress=plain -f fixtures/e3/draft/Dockerfile.reference -t "$REFERENCE_TAG" . || true
run_capture reference-inspect "$ROOT" docker image inspect "$REFERENCE_TAG" || true
run_capture base-inspect "$ROOT" docker image inspect ubuntu:24.04 || true
run_capture container-validation "$ROOT" docker run --rm --network none --workdir /repo "$REFERENCE_TAG" bash scripts/e3/verify_fzy.sh --operator "$OPERATOR" || true

python3 - "$RECORDS" "$OUT/commands.json" <<'PY'
import json
import sys
from pathlib import Path

records = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]
Path(sys.argv[2]).write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

broken_rc=$(cat "$OUT/broken-build.exit")
reference_rc=$(cat "$OUT/reference-build.exit")
validation_rc=$(cat "$OUT/container-validation.exit")
if [ "$broken_rc" -ne 0 ] && grep -Eiq 'make: (not found|未找到)|make: command not found|gcc: (not found|未找到)|gcc: command not found' "$OUT/broken-build.stderr.log"; then broken_status=PASSED; else broken_status=FAILED; fi
if [ "$reference_rc" -eq 0 ] && [ "$validation_rc" -eq 0 ]; then reference_status=PASSED; else reference_status=FAILED; fi

final_status=FAILED
[ "$broken_status" = PASSED ] && [ "$reference_status" = PASSED ] && final_status=PASSED
python3 - "$OUT/reference-inspect.stdout.log" "$OUT/base-inspect.stdout.log" "$OUT/run.json" "$RUN_ID" "$OPERATOR" "$broken_status" "$broken_rc" "$reference_status" "$reference_rc" "$validation_rc" "$final_status" <<'PY'
import json
import sys
from pathlib import Path

reference_log, base_log, output, run_id, operator, broken_status, broken_rc, reference_status, reference_rc, validation_rc, final_status = sys.argv[1:]

def identity(path):
    try:
        item = json.loads(Path(path).read_text(encoding="utf-8"))[0]
        return {"id": item.get("Id"), "repo_digests": item.get("RepoDigests", [])}
    except (FileNotFoundError, IndexError, json.JSONDecodeError):
        return {"id": None, "repo_digests": []}

data = {
    "case_id": "fzy-draft-container",
    "provenance": "ACTUAL_RUN",
    "run_id": run_id,
    "operator": operator,
    "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
    "configuration_id": "fzy-upstream-linux-v1",
    "base_image": "ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3",
    "images": {"reference": identity(reference_log), "base": identity(base_log)},
    "broken_build": {"status": broken_status, "exit_code": int(broken_rc)},
    "reference_build": {"status": reference_status, "exit_code": int(reference_rc)},
    "container_validation": {"exit_code": int(validation_rc)},
    "status": final_status,
}
Path(output).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cat >"$OUT/observations.md" <<EOF
# DRAFT 容器基线运行观察

来源：ACTUAL_RUN。操作者：$OPERATOR。运行目录：$OUT。

## 预期

失败候选应在项目构建步骤因缺少 make 或 C 编译器返回非零；参考候选应使用同一 fzy 快照完成构建、测试和功能用例。

## 实际

- 失败构建退出码：$broken_rc；状态：$broken_status。
- 参考构建退出码：$reference_rc；状态：$reference_status。
- 参考容器功能验证退出码：$validation_rc。
- 镜像摘要见 \`reference-inspect.stdout.log\` 和 \`base-inspect.stdout.log\`。
- 完整命令和日志见 \`commands.json\` 及对应 stdout/stderr 文件。
- 如果基础镜像检查失败，必须将该次运行标记为失败，不能把镜像拉取或网络错误解释为预期的工具缺失。
EOF
