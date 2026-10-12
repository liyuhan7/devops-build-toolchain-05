#!/usr/bin/env bash
# 构建 DRAFT 失败与参考环境，并导出完整功能证据。
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/run_draft_container.py" "$@"
