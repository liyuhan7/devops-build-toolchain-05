#!/usr/bin/env bash
# 在独立副本中构建原始 fzy，并按人工预期执行无终端交互的功能验证。
# 只读取 fixtures/e3/draft 与源码快照，把产物写入 work/e3/，证据写入指定输出目录。
set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

SOURCE="$ROOT/fixtures/e3/fzy"
OPERATOR=""
REVISION=""
OUTPUT=""

usage() {
  cat <<'TXT'
用法：scripts/e3/verify_fzy.sh --operator 姓名 [--source 源码目录] [--output 证据目录] [--revision 完整SHA]

  --operator  必填，本次运行的操作者姓名
  --source    默认为 fixtures/e3/fzy
  --output    默认为 evidence/e3/draft/<run-id>
  --revision  可选，已提交版本的 40 位小写 Git SHA；尚未提交时留空
TXT
}

while [ $# -gt 0 ]; do
  case "$1" in
    --operator|--source|--output|--revision)
      if [ $# -lt 2 ] || [[ "$2" == --* ]]; then
        printf '参数 %s 缺少取值\n' "$1" >&2
        exit 2
      fi
      case "$1" in
        --operator) OPERATOR="$2" ;;
        --source) SOURCE="$2" ;;
        --output) OUTPUT="$2" ;;
        --revision) REVISION="$2" ;;
      esac
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) printf '未知参数：%s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

if [ -z "$OPERATOR" ]; then
  printf '缺少 --operator\n' >&2
  usage
  exit 2
fi
if [ -n "$REVISION" ] && ! printf '%s' "$REVISION" | grep -Eq '^[0-9a-f]{40}$'; then
  printf 'revision 必须是 40 位小写 Git SHA\n' >&2
  exit 2
fi
if [ ! -d "$SOURCE" ]; then
  printf '源码目录不存在：%s\n' "$SOURCE" >&2
  exit 2
fi

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$(LC_ALL=C tr -dc '0-9a-f' < /dev/urandom | head -c 8)
OUT=${OUTPUT:-$ROOT/evidence/e3/draft/$RUN_ID}
WORK=$ROOT/work/e3/$RUN_ID/fzy
CASES=$ROOT/fixtures/e3/draft/cases
CASES_JSON=$ROOT/fixtures/e3/draft/cases.json
# 每次运行使用新目录，防止覆盖既有证据；转换为绝对路径以支持相对 --output。
if [ -e "$OUT" ]; then
  printf '证据目录已存在，请指定新目录：%s\n' "$OUT" >&2
  exit 2
fi
mkdir -p "$OUT" || exit 2
OUT=$(cd "$OUT" && pwd) || exit 2

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# 操作者及路径中的常用控制字符也需要转义。
json_escape() {
  local value=$1
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '%s' "$value"
}

COMMANDS=""
CHECKS=""
CHECK_LINES=""
FAILURE=""

write_commands() {
  if [ -z "$COMMANDS" ]; then
    printf '[]\n' > "$OUT/commands.json"
  else
    printf '[\n%s\n]\n' "$COMMANDS" > "$OUT/commands.json"
  fi
}

add_command() { # 标签 工作目录 开始 结束 退出码 标准输入文件 命令...
  local label=$1 cwd=$2 started=$3 finished=$4 rc=$5 stdin=$6
  shift 6
  local args="" first=1 item
  for item in "$@"; do
    if [ $first -eq 1 ]; then first=0; else args="$args, "; fi
    args="$args\"$(json_escape "$item")\""
  done
  local stdin_json=null
  [ -n "$stdin" ] && stdin_json="\"$(json_escape "$stdin")\""
  local entry
  entry="    {\"label\": \"$(json_escape "$label")\", \"argv\": [$args], \"cwd\": \"$(json_escape "$cwd")\","
  entry="$entry \"stdin\": $stdin_json, \"started_at\": \"$started\", \"finished_at\": \"$finished\","
  entry="$entry \"exit_code\": $rc, \"stdout\": \"$label.stdout.log\", \"stderr\": \"$label.stderr.log\"}"
  if [ -z "$COMMANDS" ]; then COMMANDS="$entry"; else COMMANDS="$COMMANDS,
$entry"; fi
  write_commands
}

add_check() { # 检查项 是否通过
  local entry="    {\"check\": \"$(json_escape "$1")\", \"passed\": $2}"
  if [ -z "$CHECKS" ]; then CHECKS="$entry"; else CHECKS="$CHECKS,
$entry"; fi
  CHECK_LINES="$CHECK_LINES$1|$2
"
}

# 执行一条命令并保留标准输出、标准错误与退出码；不因非零退出码中断脚本。
execute() { # 标签 工作目录 标准输入文件（可为空） 命令...
  local label=$1 cwd=$2 stdin=$3
  shift 3
  local started finished rc
  started=$(now)
  (
    cd "$cwd" || exit 127
    if [ -n "$stdin" ]; then
      exec "$@" < "$stdin"
    else
      exec "$@" < /dev/null
    fi
  ) > "$OUT/$label.stdout.log" 2> "$OUT/$label.stderr.log"
  rc=$?
  finished=$(now)
  add_command "$label" "$cwd" "$started" "$finished" "$rc" "$stdin" "$@"
  return $rc
}

require() { # 条件退出码 检查项
  if [ "$1" -eq 0 ]; then
    add_check "$2" true
    return 0
  fi
  add_check "$2" false
  [ -z "$FAILURE" ] && FAILURE="$2"
  return 1
}

write_run() { # 状态
  local status=$1
  local failure_json=null
  [ -n "$FAILURE" ] && failure_json="\"$(json_escape "$FAILURE")\""
  local revision_json=null
  [ -n "$REVISION" ] && revision_json="\"$REVISION\""
  local env_json=null
  [ -n "${E3_ENVIRONMENT_REFERENCE:-}" ] && env_json="\"$(json_escape "${E3_ENVIRONMENT_REFERENCE}")\""
  cat > "$OUT/run.json" <<JSON
{
  "case_id": "fzy-draft-build-and-function",
  "provenance": "ACTUAL_RUN",
  "run_id": "$RUN_ID",
  "operator": "$(json_escape "$OPERATOR")",
  "started_at": "$STARTED_AT",
  "finished_at": "$(now)",
  "platform": "$(json_escape "$(uname -s) $(uname -r)")",
  "architecture": "$(uname -m)",
  "upstream_commit": "34b88869d022e861da4846c4463aea3ddfb3ff30",
  "experiment_commit": $revision_json,
  "configuration_id": "fzy-upstream-linux-v1",
  "oracle_path": "fixtures/e3/draft/cases.json",
  "environment_reference": $env_json,
  "status": "$status",
  "failure": $failure_json,
  "checks": [
$CHECKS
  ]
}
JSON
}

STARTED_AT=$(now)
STATUS="RUNNING"
write_run "$STATUS"

# 非 Linux 环境不作为本基线的运行结论，直接判失败并保留原因。
if [ "$(uname -s)" != "Linux" ]; then
  add_check "使用 Linux 环境" false
  FAILURE="使用 Linux 环境"
  STATUS="FAILED"
else
  add_check "使用 Linux 环境" true
  for name in os gcc make git; do
    case $name in
      os) set -- cat /etc/os-release ;;
      gcc) set -- gcc --version ;;
      make) set -- make --version ;;
      git) set -- git --version ;;
    esac
    execute "environment-$name" "$ROOT" "" "$@"
  done

  mkdir -p "$WORK"
  cp -r "$SOURCE/." "$WORK/"

  execute "build" "$WORK" "" make CC=gcc
  require $? "make CC=gcc 构建成功"
  if [ -x "$WORK/fzy" ]; then
    require 0 "生成可执行的 fzy"
  else
    require 1 "生成可执行的 fzy"
  fi

  execute "validation" "$WORK" "" make CC=gcc check
  require $? "make CC=gcc check 通过"
  if [ -f "$OUT/validation.stdout.log" ]; then
    for token in "32 tests" "102 assertions" "Pass: 32, fail: 0, skip: 0."; do
      grep -Fq "$token" "$OUT/validation.stdout.log"
      require $? "测试输出包含 $token"
    done
  fi

  execute "version" "$WORK" "" ./fzy --version
  require $? "版本查询成功"
  grep -Fq "1.1" "$OUT/version.stdout.log"
  require $? "版本标记符合配置"

  # 每个用例目录包含 argv、stdin、expected_stdout、expected_exit_code；
  # expected_stderr_contains 仅在需要断言错误输出时出现。
  for case_dir in "$CASES"/*; do
    [ -d "$case_dir" ] || continue
    case_id=$(basename "$case_dir")
    mapfile -t argv < "$case_dir/argv"
    execute "functional-$case_id" "$WORK" "$case_dir/stdin" ./fzy "${argv[@]}"
    actual=$?
    expected=$(tr -d ' \n' < "$case_dir/expected_exit_code")
    [ "$actual" = "$expected" ]
    require $? "用例 $case_id 退出码为 $expected"
    cmp -s "$case_dir/expected_stdout" "$OUT/functional-$case_id.stdout.log"
    require $? "用例 $case_id 标准输出符合人工预期"
    if [ -f "$case_dir/expected_stderr_contains" ]; then
      grep -Fqf "$case_dir/expected_stderr_contains" "$OUT/functional-$case_id.stderr.log"
      require $? "用例 $case_id 错误输出包含预期信息"
    fi
  done

  # 人工预期与用例文件的一致性自检需要解析 JSON，仅在具备 Python 3 时执行。
  if command -v python3 > /dev/null 2>&1; then
    python3 - "$CASES_JSON" "$CASES" <<'PY'
import json
import sys
from pathlib import Path

cases_json = Path(sys.argv[1])
cases_dir = Path(sys.argv[2])
data = json.loads(cases_json.read_text(encoding="utf-8"))
listed = {item["case_id"]: item for item in data["functional_cases"]}
present = {path.name for path in cases_dir.iterdir() if path.is_dir()}
assert listed.keys() == present, f"人工预期与用例目录不一致：{listed.keys() ^ present}"
for case_id, item in listed.items():
    directory = cases_dir / case_id
    assert directory.joinpath("argv").read_text(encoding="utf-8").splitlines() == item["argv"], f"{case_id} 参数不一致"
    assert int(directory.joinpath("expected_exit_code").read_text(encoding="utf-8").strip()) == item["expected_exit_code"], f"{case_id} 退出码不一致"
    for key in ("stdin", "expected_stdout"):
        assert (cases_dir.parent / item[key]).is_file(), f"{case_id} 缺少文件 {item[key]}"
print("用例清单与人工预期一致")
PY
    require $? "用例清单与人工预期一致"
  else
    printf '未安装 Python 3，跳过用例清单与人工预期的一致性自检。\n' > "$OUT/consistency.skipped.txt"
  fi

  if [ -z "$FAILURE" ]; then STATUS="PASSED"; else STATUS="FAILED"; fi
fi

write_run "$STATUS"
write_commands

{
  printf '# DRAFT 功能验证实际观察\n\n'
  printf '人工预期：fixtures/e3/draft/cases.json（TEAM_ORACLE）。本记录来源：ACTUAL_RUN。\n\n'
  printf '| 检查 | 实际结果 |\n|---|---|\n'
  printf '%s' "$CHECK_LINES" | while IFS='|' read -r label passed; do
    [ -z "$label" ] && continue
    if [ "$passed" = true ]; then verdict=通过; else verdict=失败; fi
    printf '| %s | %s |\n' "$label" "$verdict"
  done
  printf '\n运行状态：%s。\n\n失败原因：%s。\n' "$STATUS" "${FAILURE:-无}"
  printf '\nGit 提交标签：%s。\n' "${REVISION:-尚未提交，需操作者完成提交后另作带 SHA 的运行记录}"
} > "$OUT/observations.md"

printf 'EVIDENCE_DIR=%s\n' "$OUT"
printf 'STATUS=%s\n' "$STATUS"
[ "$STATUS" = "PASSED" ]
