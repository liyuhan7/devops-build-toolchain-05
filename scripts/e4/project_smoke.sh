#!/usr/bin/env bash
# 复跑原项目本组基线，成功和失败证据均复制到本次个人目录。
set -euo pipefail
: "${STUDENT_ID:?请通过 make smoke 或 make all 执行}"
: "${E4_RUN_DIR:?缺少本次证据目录}"
: "${E4_TIMEOUT:?缺少运行超时}"
: "${COMPOSE:?缺少 Compose 命令}"
: "${GROUP:?缺少组别}"
: "${SERVICE:?缺少服务名}"
: "${E4_PROJECT_TIMEOUT:?缺少项目验证超时}"
test -d .git || { echo '请在本仓库的普通 Git 克隆目录运行。'; exit 1; }
read -r -a compose_cmd <<< "$COMPOSE"
container="e4-project-${GROUP}-${STUDENT_ID}-$(basename "$E4_RUN_DIR")"
set +e
timeout "$E4_TIMEOUT" "${compose_cmd[@]}" run --name "$container" --no-deps -T --interactive=false \
  -e GIT_OPTIONAL_LOCKS=0 -v "$PWD/.git:/repo/.git:ro" "$SERVICE" \
  python3 scripts/e4/project_smoke.py --group "$GROUP" --operator "$STUDENT_ID" \
  --repository-sha "$(git rev-parse HEAD)" 2>&1 | tee "$E4_RUN_DIR/project-smoke.log"
status=${PIPESTATUS[0]}
docker cp "$container:/repo/work/e4/project-smoke" "$E4_RUN_DIR/project-smoke"
copy_status=$?
docker rm "$container" >/dev/null
remove_status=$?
set -e
if [ "$copy_status" -ne 0 ] || [ "$remove_status" -ne 0 ]; then
  echo '证据复制或本次容器清理失败，请保留现有日志检查。'
  exit 1
fi
if [ "$status" -ne 0 ] || [ "$GROUP" != B ]; then
  exit "$status"
fi

# 子容器的 bind 路径属于 ECS 宿主机；DRAFT 原有入口在宿主机运行。
set +e
timeout "$E4_PROJECT_TIMEOUT" python3 scripts/e3/run_draft_container.py \
  --operator "$STUDENT_ID" --output "$E4_RUN_DIR/project-smoke/evidence/draft-container" \
  2>&1 | tee "$E4_RUN_DIR/draft-container.log"
status=${PIPESTATUS[0]}
set -e
python3 - "$E4_RUN_DIR/project-smoke" "$status" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
summary_file = root / 'summary.json'
summary = json.loads(summary_file.read_text(encoding='utf-8'))
run_file = root / 'evidence/draft-container/run.json'
run = json.loads(run_file.read_text(encoding='utf-8')) if run_file.is_file() else {}
passed = sys.argv[2] == '0' and run.get('status') == 'PASSED'
summary['cases'].append({'case': 'draft-container', 'exit_code': int(sys.argv[2]),
                         'status': run.get('status', 'FAILED'), 'passed': passed,
                         'evidence': 'evidence/draft-container'})
summary['pending_cases'] = []
summary['passed'] = all(item['passed'] for item in summary['cases'])
summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sys.exit(0 if summary['passed'] else 1)
PY
exit "$status"
