#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OPERATOR=unknown
while (($#)); do case "$1" in --operator) OPERATOR=$2; shift 2;; *) echo "unknown argument: $1" >&2; exit 2;; esac; done
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%s' "$RANDOM" | shasum -a 256 | cut -c1-8)
WORK="$ROOT/work/e3/buildchecker/$RUN_ID"; EVID="$ROOT/evidence/e3/buildchecker/$RUN_ID"
mkdir -p "$WORK" "$EVID"
cp -a "$ROOT/fixtures/e3/echecker/project/." "$WORK/"
cp "$ROOT/fixtures/e3/buildchecker/md-rd.patch" "$EVID/md-rd.patch"
printf '{"case_id":"fzy-c0-options-md-rd","provenance":"ACTUAL_RUN","operator":%s,"run_id":%s,"base_commit":"0769e815259ab2cae12a21be43256c05906215e0","configuration_id":"fzy-c0-options-linux-v1","target":"src/options.o","patch":"fixtures/e3/buildchecker/md-rd.patch"}\n' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$OPERATOR")" "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$RUN_ID")" > "$EVID/run.json"
run(){ name=$1; shift; printf '+ %q ' "$@" >> "$EVID/commands.log"; printf '\n' >> "$EVID/commands.log"; set +e; (cd "$WORK" && "$@" >"$EVID/$name.stdout.log" 2>"$EVID/$name.stderr.log"); code=$?; set -e; echo "$code" > "$EVID/$name.exit"; return "$code"; }
run patch git apply "$EVID/md-rd.patch"
run initial-clean make clean
run initial-build make CC=gcc
set +e
printf 'apple\nbanana\n' | (cd "$WORK" && ./fzy -e apple > "$EVID/initial-functional.stdout.log" 2>"$EVID/initial-functional.stderr.log")
func_code=$?
set -e
echo "$func_code" > "$EVID/initial-functional.exit"
test "$func_code" -eq 0
python3 -c 'import os,sys; print(os.stat(sys.argv[1]).st_mtime_ns)' "$WORK/src/options.o" > "$EVID/initial-options.mtime"
sleep 1
run md-header-change perl -pi -e 's/E3_MD_MARKER=one/E3_MD_MARKER=two/' "$WORK/src/e3_md_marker.h"
run md-ordinary-make make CC=gcc
python3 -c 'import os,sys; print(os.stat(sys.argv[1]).st_mtime_ns)' "$WORK/src/options.o" > "$EVID/md-ordinary-options.mtime"
(cd "$WORK" && ./fzy --version > "$EVID/md-ordinary-version.stdout.log" 2>"$EVID/md-ordinary-version.stderr.log") || true
run md-clean make clean
run md-clean-build make CC=gcc
(cd "$WORK" && ./fzy --version > "$EVID/md-clean-version.stdout.log" 2>"$EVID/md-clean-version.stderr.log") || true
run rd-clean make clean
run rd-build make CC=gcc
python3 -c 'import os,sys; print(os.stat(sys.argv[1]).st_mtime_ns)' "$WORK/src/options.o" > "$EVID/rd-before-options.mtime"
sleep 1
run rd-header-change perl -pi -e 's/Deliberately/Deliberately touched/' "$WORK/src/e3_rd_unused.h"
run rd-ordinary-make make CC=gcc
python3 -c 'import os,sys; print(os.stat(sys.argv[1]).st_mtime_ns)' "$WORK/src/options.o" > "$EVID/rd-after-options.mtime"
(cd "$WORK" && ./fzy --version > "$EVID/rd-version.stdout.log" 2>"$EVID/rd-version.stderr.log") || true
python3 - "$EVID" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]); a=int((p/'initial-options.mtime').read_text()); b=int((p/'md-ordinary-options.mtime').read_text()); c=int((p/'rd-before-options.mtime').read_text()); d=int((p/'rd-after-options.mtime').read_text());
assert a==b, (a,b); assert d>c, (c,d)
assert 'E3_MD_MARKER=one' in (p/'md-ordinary-version.stdout.log').read_text(); assert 'E3_MD_MARKER=two' in (p/'md-clean-version.stdout.log').read_text(); assert (p/'rd-version.stdout.log').read_text()==(p/'md-clean-version.stdout.log').read_text()
(p/'observations.md').write_text('''# ACTUAL_RUN 观察\n\n- 初始 clean build 成功，功能输入 `apple` 返回 `apple`。\n- MD：只改真实被读取的 `src/e3_md_marker.h` 后，普通 make 保持 options.o mtime 和旧版本输出；clean build 得到新值。\n- RD：只改未使用的显式依赖 `src/e3_rd_unused.h` 后，普通 make 更新 options.o mtime，版本输出不变。\n- 结论：运行结果与 TEAM_ORACLE 的一条 MISSING 和一条 REDUNDANT 预期相符。\n''')
PY
printf 'STATUS=PASS\nEVIDENCE_DIR=%s\n' "$EVID"
