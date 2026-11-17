# A 组 EChecker：E8—E9 成员实验与交付指南

本指南依据 `DevOps_E8_E10` 2026-10-31 版 A 组手册、课件和提交要求，将其增量检测机制接入本仓库现有 BuildChecker、A 组环境及运行证据体系。每名成员在本人克隆中独立执行，保存自己的代码贡献、原始结果和报告。

## 1. 任务与代码位置

| 阶段 | 要做什么 | 验收结果 |
|---|---|---|
| E8 复现 | 人工分析依赖，调用现有 BuildChecker 取得历史图，用 GCC 对象投影交叉核对，验证未变化输入复用 | main.o 缺 config.h、冗余 unused.h；两个对象图复用；来源可回查 |
| E9 MVP | 阅读并验证变化判断、配置身份和图更新，建立 C0—C3 提交，增加个人用例 | 普通变化复用、include 触发刷新、声明修复消除 MD，真实提交与报告对应 |

本次范围为 A 组 E8、E9。整个 EChecker Issue 继续跟踪 E10 验证和后续公共服务交接。每次参考路线完成后，增加一个自己的独立测试或实现改动。

| 路径 | 本次职责与复用关系 |
|---|---|
| `services/echecker/echecker/core.py` | 课程增量算法；MD/RD 比较复用现有 BuildChecker 的 compare_graphs，真实基线调用其 full_check |
| `services/echecker/tests/` | EChecker 图复用、失效、配置变化及基线交接回归；在此增加个人测试 |
| `scripts/echecker/lab.py` | 复用 scripts/buildchecker 的身份、镜像构建、容器和运行日志 |
| `scripts/echecker/scenarios.py` | 复制样例，在 work 内建立内部历史并执行 E8/E9 独立断言 |
| `tests/echecker_lab/` | 现有镜像与 EChecker 编排的集成边界测试 |
| `fixtures/echecker/` | 课程双对象样例，运行时复制，原目录保持只读 |
| `services/buildchecker/Dockerfile`、根依赖锁文件 | A 组共用环境；EChecker 使用同一镜像和依赖 |

本教学样例只处理两个固定翻译单元、根目录项目头文件、显式规则及简单变量。fzy 的 E3 基线、公共 Schema 与接口说明继续保留，样例通过不代表已完成 fzy 扫描或公共异步服务。

## 2. 组长交接与个人准备

### 2.1 取得组长固定版本

公共接入分支为 `EChecker-lab`。组长完成 Review、原有检查和 EChecker 检查后合并，公布真实导入 PR 和 main SHA。导入尚未合并时，成员先等待，或明确使用组长指定的分支固定版本；不能假定 main 已含入口。

以下命令在 SSH 登录后的 Linux 服务器、本人外层仓库根目录、Bash 中执行。沿用 E4—E7 本人的克隆、目录及 GitHub 认证，不共用他人的工作区。

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git status --short
git config --local user.name
git config --local user.email
```

确认 user.name 是本人 6—16 位数字学号，origin 是本组仓库。已有改动先核对保留，冲突解决后再继续。确认导入已合并且工作区干净，由本人同步并建立或更新个人分支：

```bash
git switch main
git pull --ff-only origin main
SID=$(git config --local user.name)
BRANCH="student/$SID/e8-e10"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
  git merge --no-edit main
else
  git switch -c "$BRANCH" main
fi
git rev-parse HEAD
ls scripts/echecker/lab.py services/echecker/echecker/core.py
```

人员和实际 Issue 编号由组内确认；不编造关联。公共实现与他人测试重叠时先协调范围，再编辑。

### 2.2 自检并构建共用 A 组镜像

服务器需要 Git、Python3、Docker、Compose；GCC、GNU Make、strace、Python 测试依赖沿用现有 A 组镜像。首次构建会下载，组长安排串行；不修改服务器全局配置。

```bash
LAB_IMAGE="buildchecker-lab:$SID"
LAB_RUN="work/echecker/$SID-$(date +%Y%m%d-%H%M%S)"
python3 scripts/echecker/lab.py doctor --out "$LAB_RUN/doctor"
```

通过条件：doctor 退出 0，必需环境满足；读取其 env.json 和 doctor 日志。然后构建含当前仓库代码的镜像：

```bash
python3 scripts/echecker/lab.py build --image "$LAB_IMAGE" --out "$LAB_RUN/build"
BUILD_CODE=$?
printf 'BUILD_EXIT_CODE=%s\n' "$BUILD_CODE"
```

`build` 直接委托现有 `scripts/buildchecker/lab.py`，沿用同一 Dockerfile、基础镜像参数、根锁文件和 BuildChecker 服务测试。通过条件：退出 0；`build/image/`、`build/toolchain/`、`build/unit-tests/` 完整，BuildChecker 测试通过。

镜像保留 `/repo` 布局。修改 EChecker 源码、样例或测试后需要重新构建，再用新 LAB_RUN 复跑；报告分别记录外层 HEAD、工作区差异及镜像标签中的源码 SHA/dirty 状态，不能把旧镜像结果归给新代码。

### 2.3 执行 EChecker 与编排回归

```bash
python3 scripts/echecker/lab.py test --image "$LAB_IMAGE" --out "$LAB_RUN/tests"
TEST_CODE=$?
printf 'TEST_EXIT_CODE=%s\n' "$TEST_CODE"
```

通过条件：服务测试和编排测试均通过，退出 0。真实数量按 `tests/runner/stdout.log` 填写。该步骤使用已构建镜像并禁网运行。任何阶段非零时先读取 runner 的 command.json、stdout.log、stderr.log、exit-code.json，处理后用新目录重做，保留失败证据。

## 3. E8：真实基线与未变化输入复用

### 3.1 运行前独立写出预期

```bash
cat fixtures/echecker/Makefile
cat fixtures/echecker/main.c fixtures/echecker/config.h fixtures/echecker/helper.c
```

报告先填写：main.o 实际需要 main.c/config.h，声明 main.c/unused.h，预期 MD config.h、RD unused.h；helper.o 实际与声明均只有 helper.c。头文件存在使首次编译成功，Make 声明缺失影响后续触发关系。

### 3.2 执行采集与复用

```bash
python3 scripts/echecker/lab.py e8 --image "$LAB_IMAGE" --out "$LAB_RUN/e8"
E8_CODE=$?
printf 'E8_EXIT_CODE=%s\n' "$E8_CODE"
E8_OUT="$LAB_RUN/e8/evidence/result"
```

入口在同一 A 组镜像中按以下依赖顺序执行；可对照 `scripts/echecker/scenarios.py` 阅读每一步：

1. 复制 fixtures/echecker 到本次 project，建立内部 C0 提交。
2. 用 GCC -MM 取得对象目标投影，独立核对边集。
3. 调用本仓库 BuildChecker full_check，保存完整 clean build、strace、Make 数据库、两图、进程及发现。
4. 核对实际图、声明图、发现与 GCC 投影一致，将真实图和 trace_id 写入 baseline。
5. 将 baseline 传给 scan，断言两个目标复用、刷新为空且发现不变。
6. 保存结论、内部提交列表、完整历史 bundle 和 gate.json。

通过条件：阶段退出 0，gate.json 的 passed=true；构建、跟踪、投影不一致时明确失败，不发布通过结论。

### 3.3 逐项检查输出

```bash
cat "$E8_OUT/gate.json" "$E8_OUT/结论.txt"
python3 -m json.tool "$E8_OUT/baseline.json"
python3 -m json.tool "$E8_OUT/incremental.json"
cat "$E8_OUT/buildchecker/findings.json"
grep -n '^main.o:' "$E8_OUT/buildchecker/make-db.txt" | head -n 8
grep -n 'config.h' "$E8_OUT/buildchecker/trace/"* | head -n 12
cat "$E8_OUT/buildchecker/processes.json"
```

报告引用本人真实 trace 文件、PID、行号和 Make 声明位置，说明 config.h 的成功只读打开如何归属 main.o 编译作业。失败打开、stat/access 不能单独作依赖依据。填写 baseline_source、baseline_trace_id，以及 reused/refreshed 和图/发现比较结果。

## 4. E9：C0—C3 连续提交与图更新

### 4.1 执行独立 E9 样例

```bash
python3 scripts/echecker/lab.py e9 --image "$LAB_IMAGE" --out "$LAB_RUN/e9"
E9_CODE=$?
printf 'E9_EXIT_CODE=%s\n' "$E9_CODE"
E9_OUT="$LAB_RUN/e9/evidence/result"
```

E9 另建样例和历史，不继续修改 E8 已结束的项目。入口逐步改动、提交、实际构建，再生成报告；每步自带独立断言。

| 内部版本 | 输入变化 | 依赖扫描预期 | 实际构建证据 |
|---|---|---|---|
| C0 | 初始样例 | MD config.h、RD unused.h | C0-build.log；程序输出 1 |
| C1 | 普通表达式增加 +0 | 两对象复用；findings 不变，added/resolved 为空 | C1-build.log 应有 main.o 重编译及 app 链接 |
| C2 | main.c 新增 include extra.h | 保守刷新两个对象，新增 MD extra.h；原 MD/RD 保留 | C2-build.log；构建成功仍可能有 MD |
| C3 | 补齐 config.h/extra.h 声明 | 实际图复用，声明图更新，两条 MD 消除，RD unused.h 保留 | C3.json、Makefile 与内部提交 |

### 4.2 读取报告并回查真实版本

```bash
cat "$E9_OUT/gate.json" "$E9_OUT/sample-history.txt"
cat "$E9_OUT/C0-build.log" "$E9_OUT/C1-build.log" "$E9_OUT/C2-build.log"
python3 - "$E9_OUT" <<'PY'
from pathlib import Path
import json, sys
out = Path(sys.argv[1])
for name in ['baseline', 'C1', 'C2', 'C3']:
    r = json.loads((out / (name + '.json')).read_text())
    print(name, r['commit'], r['reused'], r['refreshed'], r['added'], r['resolved'])
PY
git -C "$E9_OUT/project" bundle verify "$PWD/$E9_OUT/sample-history.bundle"
```

通过条件：退出 0，报告 commit 对应 sample-history，C1 扫描复用与实际重编译分别可见，C2/C3 发现变化准确。完整历史 bundle 已由实验入口导出，可在独立目录克隆后按报告 commit 复查输入，不切换原始证据项目来覆盖状态。

## 5. 个人扩展与代码贡献

每次实验完成参考路线后至少增加一个有独立预期的测试或实现改动，并解释本人工作。参考范围：

- E8：在 config.h 中加入间接头文件包含，先写新增依赖，再核对全量图与历史图失效。
- E9：增加头文件内部 include/删除变化；或将保守刷新改为受影响目标刷新，并与全量结果对照。

测试放在 `services/echecker/tests/test_student_<本人学号>.py`。保留公共回归，不把公共测试重新署名为个人贡献。可从以下结构开始，成员补充自己的变化和断言：

```python
import tempfile
from pathlib import Path
from services.echecker.echecker.core import scan
from scripts.echecker.scenarios import fixture, commit

def test_indirect_header_change():
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory) / 'sample'
        fixture(p)
        old = scan(p)
        (p / 'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
        commit(p, 'header includes extra')
        incremental = scan(p, old)
        full = scan(p)
        assert incremental['actual']['main.o'] == ['config.h', 'extra.h', 'main.c']
        assert incremental['added'] == [['MISSING', 'main.o', 'extra.h']]
        assert set(incremental['refreshed']) == {'main.o', 'helper.o'}
        for key in ['actual', 'declared', 'findings']:
            assert incremental[key] == full[key]
```

解释 core.scan 的 key：本地预处理指令及文件集合、配方、CFLAGS、GCC 版本。当前支持 CFLAGS 为 -O0、-O1、-O0 -DMODE=1；复杂编译命令和 Make 规则在当前教学范围外。

修改后重新设置 LAB_RUN，重建同一 A 组镜像，执行 test，并复跑受影响 E8/E9。原始、扩展运行目录都保留；在报告写明输入、独立预期、修改文件/函数、源码版本和测试结果。

## 6. 作业文档与必交清单

个人文档按实验包要求组织，沿用 e8-e10 目录名；本轮填写 E8、E9，E10 标记未开展：

```bash
REPORT_DIR="docs/students/$SID/e8-e10"
mkdir -p "$REPORT_DIR"
cp -n docs/templates/echecker-report.md "$REPORT_DIR/个人报告.md"
cp -n docs/templates/echecker-adr.md "$REPORT_DIR/ADR.md"
cp -n docs/templates/echecker-ai-usage.md "$REPORT_DIR/AI_USAGE.md"
```

| 作业交付项 | 本人材料与验收点 |
|---|---|
| 复现说明与论文对照 | 个人报告按 E8/E9 分节；说明论文机制、课程简化、参考来源和个人贡献 |
| E8 图与结论 | baseline.json、incremental.json、结论.txt；真实 BuildChecker 来源、精确两条发现和复用结果 |
| E8 原始证据 | buildchecker 完整目录：trace、make-db、processes、两图、findings 和 clean/build 日志；可回查本人 PID/行号 |
| E9 跨提交结果 | baseline、C1/C2/C3 JSON，C0/C1/C2-build.log，project、sample-history.txt、sample-history.bundle |
| 个人贡献与测试 | 每次实验的本人测试/实现差异、独立预期、修改前后日志、扩展运行目录 |
| 版本与环境 | 阶段根目录 source-commit.txt、worktree-status.txt、invocation.json、image/；构建目录 toolchain 和 unit-tests |
| 命令与结果 | 每个 runner 的 command.json、stdout.log、stderr.log、exit-code.json，以及实验 gate.json |
| 决策和 AI 记录 | ADR.md 说明缓存/配置策略和取舍；AI_USAGE.md 如实记录建议、本人决策、修改和实际核对 |
| GitHub 记录 | Issue、PR、真实交付 SHA、Actions URL/headSha/结论、run.json、artifact 和最终合并记录 |
| 备份 | 仅本人的原始/扩展证据、源码和文档归档，服务器和电脑各一份 |

外层源码 SHA 与内层样例 commit 分别填写；invocation 同时记录镜像 ID、镜像来源 SHA/dirty 和本次退出码。未提交源码与测试也应保留差异或通过正式提交固定，确保实际执行版本可复现。

模板见 [个人报告](../templates/echecker-report.md)、[ADR](../templates/echecker-adr.md)、[AI_USAGE](../templates/echecker-ai-usage.md)。真实失败保留原因和新目录复跑结果，未执行项如实标记；取得实际 Issue、PR 和合并 SHA 后回填。

## 7. 个人提交、PR 与 CI

Git/GitHub 操作由成员本人执行。检查实际差异，精确暂存本人测试、必要实现和三份文档；不要提交 work、凭据或编译产物。提交采用中文 Conventional Commits，例如 `test(echecker): 验证头文件变化时的缓存失效`。

创建或更新本人 PR，指定 Reviewer。整个 EChecker Issue 的中间 PR 用 Related to，全部验收完成的最后一个 PR 才用 Closes。公共导入完成不代表个人实验完成。

```bash
GH_REPO=liyuhan7/devops-build-toolchain-05
BRANCH=$(git branch --show-current)
SOURCE_SHA=$(git rev-parse HEAD)
gh run list --repo "$GH_REPO" --workflow echecker-lab.yml --branch "$BRANCH" \
  --commit "$SOURCE_SHA" --json databaseId,event,headSha,status,conclusion,url --limit 10
```

选择本次提交对应的运行，PR 验收优先看 pull_request 记录：

```bash
read -r -p '本次提交对应的 Actions 运行 ID: ' RUN_ID
gh run watch "$RUN_ID" --repo "$GH_REPO" --exit-status
CI_CODE=$?
printf 'CI_EXIT_CODE=%s\n' "$CI_CODE"
CI_OUT="work/echecker/ci-backup/$RUN_ID"
mkdir -p "$CI_OUT"
gh run view "$RUN_ID" --repo "$GH_REPO" --json headSha,conclusion,url > "$CI_OUT/run.json"
gh run download "$RUN_ID" --repo "$GH_REPO" --dir "$CI_OUT/artifacts"
cat "$CI_OUT/run.json"
```

验收 headSha 与交付版本对应、conclusion=success，下载 artifact；保留期 14 天。失败使用 `gh run view "$RUN_ID" --repo "$GH_REPO" --log-failed` 定位，修正后更新同一 PR。合并前需最新相关检查通过、指定 Reviewer 批准、讨论解决；合并由组长执行。

## 8. 归档下载与断线恢复

报告填好服务器绝对路径与真实版本后，仅选择本人材料。下列数组包含本轮环境、测试、E8/E9 和个人文档，按提示加入原始/扩展运行及 CI 备份：

```bash
SUBMIT_PATHS=(services/echecker scripts/echecker fixtures/echecker tests/echecker_lab "$REPORT_DIR" "$LAB_RUN")
while read -r -p '其他本人证据路径（扩展运行或CI备份；留空结束）: ' EXTRA_PATH; do
  [[ -n "$EXTRA_PATH" ]] || break
  SUBMIT_PATHS+=("$EXTRA_PATH")
done
SUBMIT_DIR="$HOME/devops-submissions/$SID"
mkdir -p "$SUBMIT_DIR"
ARCHIVE="$SUBMIT_DIR/A-E8-E9-$SID-$(date +%Y%m%d-%H%M%S).tar.gz"
tar --exclude='.git' --exclude='.env' --exclude='*.pem' --exclude='*.key' \
  --exclude='__pycache__' --exclude='*.o' --exclude='app' \
  -czf "$ARCHIVE" "${SUBMIT_PATHS[@]}"
tar -tzf "$ARCHIVE" | head -n 50
printf '归档=%s\n' "$ARCHIVE"
```

共用的 BuildChecker、Dockerfile 和根依赖由报告指定的仓库版本取得。用 SFTP 下载并解压抽查：三份文档、原始 trace、四份 E9 JSON、三份构建日志、历史 bundle、个人测试、命令/退出码和 CI artifact。

断线后回本人仓库，恢复 SID、LAB_IMAGE 和报告中实际 LAB_RUN；按上文重设 E8_OUT/E9_OUT 读取结果。当前入口按阶段完整执行，不原样重跑已有非空目录；失败目录保留，修正后换新目录。
