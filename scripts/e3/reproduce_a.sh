#!/usr/bin/env bash
# 从固定 C0 重建 MD/RD 样本并保存行为证据。
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/reproduce_a.py" "$@"
