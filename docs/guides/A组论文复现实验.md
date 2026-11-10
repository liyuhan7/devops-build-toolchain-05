# A 组论文复现、核心检测与验证

E5、E6、E7 本地验证在本组 Ubuntu 服务器上执行。每位 A 组成员使用自己的仓库克隆、镜像标签和运行目录，按本手册收集本人证据。E4 的目录与环境约定见 [E4 操作与交付说明](E4操作与交付说明.md)，实现范围和代码来源见 [BuildChecker 说明](../../services/buildchecker/README.md)。E7 的组员任务与交付见第 6 节，远程 CI 与 PR 门禁见第 7 节。

## 1. 操作者、位置与前置条件

| 人员 | 工作内容 |
|---|---|
| 组长 | 确认服务器公共环境可用，提供包含实验入口的代码版本，首次跑通后收集成员结果 |
| A 组每人 | 独立执行 E5 采集与人工分析、E6 检测与修复复检，说明本人测试或实现贡献，填写报告并备份 |

执行位置：SSH 登录后的服务器终端、本人仓库根目录，例如 `~/<学号>/build-toolchain/`。已有本人克隆时继续使用；尚未克隆时按 E4 的个人目录约定获取组长指定版本。每人的克隆指向同一个小组远程仓库，不共用一份工作目录。

前置条件：宿主机 Docker、Docker Compose、Git、Make、Python3 可用；当前用户能访问 Docker。gcc、strace 和 Python 测试依赖在服务镜像内。本节只运行 A 组教学样例，不要求先取得 B 组 DRAFT 结果。

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
test -f scripts/buildchecker/lab.py
test -f fixtures/md-rd/Makefile
```

输入：本人仓库与组长指定的源码版本。输出：完整 SHA、当前分支，两个文件检查成功。正式复跑前确认源码与测试已固定；有未提交工作时先保留并核对，不覆盖其他人的目录。修改源码或测试后应重建镜像，再用新目录复跑受影响阶段。

## 2. 设置身份、检查环境并构建镜像

### 2.1 本人身份与本次目录

在本人的仓库中执行。Git 身份只设置为 `--local`，不修改服务器全局身份：

```bash
read -r -p '本人数字学号（6—16 位）: ' LAB_SID
read -r -p '本人 Git 提交邮箱: ' LAB_EMAIL
git config --local user.name "$LAB_SID"
git config --local user.email "$LAB_EMAIL"

LAB_IMAGE="buildchecker-lab:$LAB_SID"
LAB_RUN="work/buildchecker/server-$(date +%Y%m%d-%H%M%S)"
printf '镜像：%s\n本次证据：%s\n' "$LAB_IMAGE" "$LAB_RUN"
```

输入：本人学号、邮箱。输出：个人镜像名与本次证据目录。后续代码框在同一 Bash 会话顺序执行，沿用 `LAB_IMAGE`、`LAB_RUN`；重新登录后应恢复变量或开始新一轮。每次重跑更换目录名，旧记录保留。

### 2.2 环境自检

```bash
if python3 scripts/buildchecker/lab.py doctor --out "$LAB_RUN/doctor"; then
  LAB_DOCTOR_CODE=0
else
  LAB_DOCTOR_CODE=$?
fi
printf 'DOCTOR_EXIT_CODE=%s\n' "$LAB_DOCTOR_CODE"
```

输入：服务器环境和本地 Git 身份。预期退出 0，`$LAB_RUN/doctor/env.json` 中 `problems=[]`。必需项未满足时先定位问题，修正后使用新的阶段目录；`warnings` 为建议项。共享环境的工具安装、权限和服务配置由组长或管理员处理。

### 2.3 构建与服务测试

```bash
if python3 scripts/buildchecker/lab.py build \
  --image "$LAB_IMAGE" --out "$LAB_RUN/build" --build-timeout 1200; then
  LAB_BUILD_CODE=0
else
  LAB_BUILD_CODE=$?
fi
printf 'BUILD_EXIT_CODE=%s\n' "$LAB_BUILD_CODE"
```

输入：当前源码、`services/buildchecker/Dockerfile` 和锁定依赖。预期退出 0，服务测试全部通过，实际测试数量以该次日志为准。首次构建会下载镜像和依赖，建议组长先跑通，成员随后执行。下载源需调整时可用 `build --base-image` 指定本组可访问的固定镜像引用。

| 结果路径（相对 `$LAB_RUN`） | 内容与检查点 |
|---|---|
| `build/build/` | Docker 构建命令、完整输出、错误流和退出码 |
| `build/image/stdout.log` | 实际镜像 ID、架构和镜像来源标签 |
| `build/toolchain/stdout.log` | gcc、Make、strace、Python 及已安装依赖版本 |
| `build/unit-tests/` | 当前服务测试命令、日志及退出码 |
| 各阶段的 `source-commit.txt`、`worktree-status.txt`、`invocation.json` | 本次源码、工作区状态和调用信息 |

构建失败时查看 `build/build/stderr.log`；测试失败时查看 `build/unit-tests/`。构建与测试均通过后进入 E5。实验运行另记录实际镜像 ID，报告分别填写镜像中的源码版本和后续报告提交版本。

## 3. E5：从原始构建记录解释 MD/RD

位置：本人服务器仓库根目录。前置：第 2 节构建成功，镜像对应待验收源码版本。

### 3.1 查看输入样例

```bash
cat fixtures/md-rd/main.c
cat fixtures/md-rd/config.h
cat fixtures/md-rd/unused.h
cat fixtures/md-rd/Makefile
```

输入：仓库内 `md-rd` 样例。输出：main.c 包含 config.h，config.h 定义 `VALUE=1`，Makefile 对象规则为 `main.o: main.c unused.h`。

| 对象 | 本次作用 |
|---|---|
| main.c | 编译输入，使用 config.h 中的 VALUE |
| config.h | 实际参与编译的头文件 |
| unused.h | Makefile 声明、当前配置下未观察到读取的头文件 |
| main.o | 比较实际依赖和声明依赖的目标 |
| app | 链接后的程序，预期输出 `1` |

### 3.2 采集完整原始证据

```bash
if python3 scripts/buildchecker/lab.py e5 \
  --image "$LAB_IMAGE" --out "$LAB_RUN/e5"; then
  LAB_E5_CODE=0
else
  LAB_E5_CODE=$?
fi
printf 'E5_EXIT_CODE=%s\n' "$LAB_E5_CODE"
```

输入：服务镜像中的原始样例。预期退出 0。实际运行先复制到独立目录，仓库原始样例保持不变。

```text
$LAB_RUN/e5/
  source-commit.txt         本次仓库提交
  worktree-status.txt       本次工作区状态
  invocation.json          阶段、时间、镜像 ID 与来源标签
  image/                   实际镜像 inspect 记录
  runner/
    command.json           完整 Docker 调用
    container-id.txt       本次运行容器 ID
    stdout.log stderr.log  运行输出与错误
    exit-code.json         命令退出码
  evidence/
    main.c config.h unused.h Makefile  实际输入副本
    trace/t.<PID>          各进程原始系统调用记录
    make-db.txt            make -p app 的标准输出
    build-stderr.log       构建错误流
    program-output.txt     程序输出
    app main.o             运行生成的编译产物，不纳入提交
```

### 3.3 理解采集命令

`e5/runner/command.json` 保存容器中的实际调用。内部步骤如下：

| 内部命令 | 输入 | 输出或作用 |
|---|---|---|
| 复制 `/repo/fixtures/md-rd/.` 到 `/evidence/` | 镜像中的样例 | 创建本次独立构建副本 |
| `mkdir trace`、`make clean` | 本次副本 | 准备跟踪目录，清理旧编译产物 |
| `strace -ff -s 4096 -o trace/t -e trace=%file,%process make -p app` | Make 构建 | 分 PID 保存文件和进程调用；标准输出保存为 Make 数据库 |
| `./app` | 本次构建的程序 | 输出保存到 program-output.txt |

`-ff` 为每个进程分别写文件，`-s 4096` 保留较长字符串，`%file,%process` 选择文件和进程系统调用。构建标准输出重定向到 `make-db.txt`，标准错误重定向到 `build-stderr.log`。容器 `/evidence` 绑定服务器结果目录，容器退出后文件仍可读取。

### 3.4 定位程序输出、声明与成功打开记录

```bash
A5="$LAB_RUN/e5/evidence"
cat "$A5/program-output.txt"
grep -n '^main.o:' "$A5/make-db.txt"
grep -n 'config.h' "$A5"/trace/t.*
```

输入：同次采集的原始文件。预期程序输出 `1`；声明包含 `main.o: main.c unused.h`；trace 中存在成功只读打开 config.h 的记录。

核对形如 `openat(... "config.h", O_RDONLY...) = 非负文件描述符` 的记录。失败探测 `= -1 ENOENT`、`stat` 和 `access` 不能单独作为成功打开证据。本检测器以成功只读打开作为依赖观察，不证明发生了字节读取。

### 3.5 把 config.h 归到 main.o 的编译作业

```bash
grep -nE 'execve\(|clone\(|clone3\(|vfork\(' "$A5"/trace/t.* | sed -n '1,60p'
grep -nE 'main\.o|config\.h|main\.c' "$A5"/trace/t.* | sed -n '1,80p'
```

输入：各 PID 的完整 trace。输出：Make 派生编译驱动，编译驱动派生 cc1、as 等进程的线索；观察 main.c/config.h 的成功打开、main.o 的写出，以及链接时 main.o 到 app 的关系。具体进程名、PID 和行号以本次工具链输出为准。

在报告中引用真实 trace 文件、行号及父子进程关系，解释这些子进程为何属于同一次编译作业。可用 `less` 打开相应文件查看上下文。

### 3.6 写出人工结论并完成 E5 检查

| 目标 | 实际观察到的项目依赖 | Make 声明依赖 | 结论 |
|---|---|---|---|
| main.o | main.c、config.h | main.c、unused.h | MISSING：config.h；REDUNDANT：unused.h |
| app | main.o | main.o | 一致 |

MISSING 为实际集合减声明集合，REDUNDANT 为声明集合减实际集合。RD 仅描述当前配置和本次构建；项目边界之外的系统头文件在本实验中过滤。

E5 交付包括：输入版本、完整原始记录、两条错误的人工推导、对应 PID/文件/行号，以及与论文原型在跟踪机制、支持范围和实验规模上的差异。能从本人的原始记录解释两条结论后进入 E6；已知答案表本身不代替原始证据。

## 4. E6：自动依赖检测、修复与复检

位置：同一仓库根目录。输入：原始样例、已构建镜像和 E5 人工依赖结论。`--timeout` 默认为 120 秒，clean/build 共用这一总执行预算。

### 4.1 检测原始样例

修复前命令预期返回 1。以下代码显式捕获退出码，避免将这个预期结果当作脚本异常中断：

```bash
if python3 scripts/buildchecker/lab.py e6 \
  --image "$LAB_IMAGE" --out "$LAB_RUN/e6-before"; then
  LAB_BEFORE_CODE=0
else
  LAB_BEFORE_CODE=$?
fi
printf 'BEFORE_EXIT_CODE=%s\n' "$LAB_BEFORE_CODE"
python3 -m json.tool "$LAB_RUN/e6-before/evidence/findings.json"
```

预期：`status=SUCCEEDED`、clean/build 退出码均为 0，精确发现 `MISSING(main.o, config.h)` 和 `REDUNDANT(main.o, unused.h)`。入口启用 `--fail-on-findings`，因此 CLI 返回 1；这与检测任务成功完成分别表达不同结果。

| 路径（相对 `$LAB_RUN/e6-before/`） | 内容 |
|---|---|
| `fixture/` | 本次输入副本 |
| `evidence/project/` | 检测器实际 clean/build 的工作副本 |
| `evidence/findings.json` | 状态、发现、输入哈希、执行命令与耗时 |
| `evidence/actual-graph.json`、`declared-graph.json` | 实际图与声明图 |
| `evidence/processes.json` | 进程父子关系、执行程序和 job_pid |
| `evidence/trace/`、`make-db.txt` | 支撑图和 Finding 的原始记录 |
| `evidence/clean.log`、`clean-stderr.log`、`build-stderr.log` | clean/build 日志 |
| `runner/` 及来源记录 | 容器命令、退出码、源码版本与镜像身份 |

### 4.2 对照两图和 Finding 证据

```bash
A6_BEFORE="$LAB_RUN/e6-before/evidence"
python3 -m json.tool "$A6_BEFORE/actual-graph.json"
python3 -m json.tool "$A6_BEFORE/declared-graph.json"
python3 -m json.tool "$A6_BEFORE/processes.json"
```

实际图应有 main.o 到 main.c/config.h 的依赖边；声明图应有 main.o 到 main.c/unused.h 的依赖边。逐条 Finding 回查原始文件：

| 报告字段 | 含义 | 核对位置 |
|---|---|---|
| trace_id | 本次分析编号 | 同次报告和调用记录 |
| status、clean_exit_code、build_exit_code | 检测与构建是否完整成功 | clean/build 日志和退出码 |
| findings[].type、target、dependency | 错误类别与依赖边 | 同目标下两图的集合差 |
| findings[].evidence | trace 文件/行号/PID 或声明位置 | trace/、make-db.txt |
| input_sha256 | 构建前输入内容摘要 | 前后报告及输入副本 |

### 4.3 修复独立副本并复检

```bash
if python3 scripts/buildchecker/lab.py e6 \
  --image "$LAB_IMAGE" --fixed --out "$LAB_RUN/e6-after"; then
  LAB_AFTER_CODE=0
else
  LAB_AFTER_CODE=$?
fi
printf 'AFTER_EXIT_CODE=%s\n' "$LAB_AFTER_CODE"
python3 -m json.tool "$LAB_RUN/e6-after/evidence/findings.json"

if diff -u "$LAB_RUN/e6-before/fixture/Makefile" \
  "$LAB_RUN/e6-after/fixture/Makefile" > "$LAB_RUN/e6-makefile.diff"; then
  LAB_DIFF_CODE=0
else
  LAB_DIFF_CODE=$?
fi
cat "$LAB_RUN/e6-makefile.diff"
printf 'MAKEFILE_DIFF_EXIT_CODE=%s\n' "$LAB_DIFF_CODE"
```

输入：同一样例的另一份独立副本。`--fixed` 将规则从 `main.o: main.c unused.h` 改为 `main.o: main.c config.h`，同时补上漏声明并去掉当前冗余声明。

预期检测退出 0、`status=SUCCEEDED`、`findings=[]`；diff 显示这一行规则变化，diff 自身预期返回 1（表示有差异，返回大于 1 才表示执行错误）。仓库原始 `fixtures/md-rd/` 保留，修复副本不作为新的源码 commit 或 EChecker 正式基线。

### 4.4 校验并保存修复前后结果

```bash
if python3 scripts/buildchecker/verify_evidence.py \
  --before "$LAB_RUN/e6-before/evidence/findings.json" \
  --after "$LAB_RUN/e6-after/evidence/findings.json" \
  > "$LAB_RUN/e6-comparison.json"; then
  LAB_VERIFY_CODE=0
else
  LAB_VERIFY_CODE=$?
fi
cat "$LAB_RUN/e6-comparison.json"
printf 'VERIFY_EXIT_CODE=%s\n' "$LAB_VERIFY_CODE"
```

输入：两份已保存报告。预期退出 0，输出 `passed=true`、`before_findings=2`、`after_findings=0`、`changed_inputs=["Makefile"]`。该脚本校验保存的报告与输入摘要，不重新构建，也不独立重放原始 trace。

### 4.5 阅读实现并记录个人工作

```bash
grep -n '^def ' services/buildchecker/buildchecker/fullcheck.py
```

| 函数 | 阅读重点 |
|---|---|
| load_processes、execution_graph | 父子进程、成功读写及编译作业归属 |
| declaration_graph | Make 声明解析、伪目标展开、order-only 依赖 |
| analyze、compare_graphs | 同目标依赖比较与 MISSING/REDUNDANT 生成 |
| full_check | 输入副本、共享时限、失败阶段及证据保存 |

每人选择一段机制解释，并在 `services/buildchecker/tests/` 中补充自己的边界测试，写明输入、预期、实际结果及参考来源。已有教学测试与本人新增测试分别记录。

测试写好并重建镜像后，可在新一轮目录执行针对性验证；按提示输入实际测试文件的仓库相对路径：

```bash
read -r -p '本人测试文件路径: ' LAB_TEST_FILE
if docker run --rm --network none "$LAB_IMAGE" \
  pytest -c services/buildchecker/pytest.ini "$LAB_TEST_FILE" \
  > "$LAB_RUN/personal-test.log" 2>&1; then
  LAB_TEST_CODE=0
else
  LAB_TEST_CODE=$?
fi
cat "$LAB_RUN/personal-test.log"
printf 'PERSONAL_TEST_EXIT_CODE=%s\n' "$LAB_TEST_CODE"
```

报告保存该命令、测试日志及退出码。若在本轮实验后修改了代码或测试，应重新设置 `LAB_RUN`，从构建开始复跑受影响阶段，避免将不同版本结果拼为同一次成功记录。

## 5. E5/E6 交付物与验收

### 5.1 每人交付清单

| 交付项 | 文件或内容 | 验收条件 |
|---|---|---|
| 版本与环境 | 仓库 URL、完整源码 SHA、依赖锁文件、工作区状态、镜像 ID、来源标签、doctor/env.json、构建及工具链日志 | 能确定本人环境、实际代码和镜像版本 |
| E5 原始复现 | e5/ 的输入副本、完整 trace、make-db、构建错误流、程序输出、命令和退出码 | 退出 0、程序输出 1，证据文件可读取 |
| E5 人工说明 | MD/RD 对照表、成功打开与写出的 PID/文件/行号、进程归属、项目边界及论文差异 | 两条结论能从本人原始记录推导 |
| E6 自动检测 | e6-before/ 和 e6-after/ 的输入、两张图、进程、findings、原始 trace、数据库及日志 | 修复前精确两条发现，修复后无发现，clean/build 均成功 |
| 修复与校验 | e6-makefile.diff、e6-comparison.json | 规则变化明确；校验通过且仅 Makefile 输入变化 |
| 个人实现与测试 | 实际修改、测试文件、测试目的、运行日志及来源说明 | 能解释本人工作；参考代码、AI 参与和人工核对分别注明 |
| 正式报告与备份 | 本人报告、服务器证据绝对路径、下载归档 | 报告路径与原始文件对应，电脑端有一份可读备份 |

其中 E5、E6 的预期退出码如下。不能只凭一次非零退出码认定依赖错误已被检测：

| 步骤 | 预期退出码 | 结果判据 |
|---|---|---|
| doctor、build | 0 | 自检必需项满足，镜像构建和服务测试通过 |
| E5 | 0 | 完整原始证据，程序输出 1 |
| E6 修复前 | 1 | 报告 SUCCEEDED，精确两条发现 |
| E6 修复后 | 0 | 报告 SUCCEEDED，findings 为空 |
| Makefile diff | 1 | 一行依赖规则变化 |
| verify_evidence | 0 | passed=true，仅 Makefile 输入变化 |

### 5.2 编写正式报告

在本人仓库执行，`cp -n` 保留已经填写的文件：

```bash
LAB_REPORT="docs/reports/$LAB_SID/e5-e6.md"
mkdir -p "$(dirname "$LAB_REPORT")"
cp -n docs/templates/buildchecker-report.md "$LAB_REPORT"
printf '报告：%s\n服务器证据：%s/%s\n' "$LAB_REPORT" "$PWD" "$LAB_RUN"
```

填写模板中的来源、E5、E6 和证据索引；尚未进行的 E7、公共交接据实标记未执行。记录本人姓名/学号、实际操作、代码版本、镜像身份、每步命令和退出码、原始证据路径、问题及重跑结果。

正式报告和可复用测试进入仓库；`work/` 原始证据保持忽略，单独交付。提交和推送由成员执行，不提交凭据、本地配置、镜像缓存和编译产物。

### 5.3 备份本次证据

下面只打包本轮目录和本人报告，排除样例生成的 app、main.o 和 Python 缓存，不打包整个仓库：

```bash
LAB_ARCHIVE="${LAB_RUN}-e5-e6.tar.gz"
tar --exclude='app' --exclude='main.o' --exclude='__pycache__' \
  -czf "$LAB_ARCHIVE" "$LAB_RUN" "$LAB_REPORT"
tar -tzf "$LAB_ARCHIVE" | sed -n '1,60p'
sha256sum "$LAB_ARCHIVE" > "${LAB_ARCHIVE}.sha256"
printf '归档：%s/%s\n' "$PWD" "$LAB_ARCHIVE"
```

输出：本轮原始证据和报告归档及传输核对摘要。用 SFTP 下载归档和摘要文件，解压抽查报告、trace、两张图、前后 findings 和校验结果。失败运行原样保留并注明状态，不能充当成功证据。

### 5.4 交给组长与现场展示

组长按下表收齐成员材料；每人保留自己的报告和原始记录，不让多人共同填写一份个人报告。

| 姓名/学号 | 完整源码 SHA/镜像 ID | 报告路径 | 服务器证据绝对路径/备份位置 | 个人工作与测试 | E5/E6 结果及未完成项 |
|---|---|---|---|---|---|
| | | | | | |

现场应能从 trace 解释 config.h 如何归到 main.o，从 Make 数据库指出 unused.h 声明，对照两图说明两条发现，并展示修复差异与校验结果。以上材料满足后可登记 E5/E6 结果；E7 和真实公共交接按下列独立章节验收。

## 公共 Job、Finding 和 Artifact 交接

公共入口使用成功 DRAFT 结果生成现有契约的 Job。E5/E6 教学样例可独立运行，保留自己的教学报告和原始证据。

正式交接在 Linux Docker 宿主机执行，前置材料为：

- 符合现有契约的成功 DRAFT Job，trace、commit、配置与检测请求一致。
- 四类已下载载荷：`environment-manifest.json`、`image-manifest.json`、`build.log`、`validation.log`。入口核验摘要、大小、媒体类型，以及构建和最终程序验证的成功结论。
- manifest 对应的 OCI 镜像已在本机准备好。入口核对 RepoDigests 后按 image ID 运行；本地 image ID 与 OCI manifest digest 分别记录，镜像不自动拉取。
- 本地 Git 仓库包含请求的完整 commit，origin 对应请求 URL。入口导出该 commit 并核对采集输入哈希。

运行容器挂载检测器代码、固定源码副本、请求和本次证据目录。上游镜像需提供 Python3、GNU Make、strace 及编译工具，A 组检测器代码由入口注入。仅安装 `build-essential` 的环境还需核对 Python3 和 strace。

公共教学入口支持自包含工作目录、默认 Makefile 和 `build_command=["make", *targets]`；编译变量写入 `configuration.environment`，不推测 `-C`、`-f` 或外部目录的语义。准备好本人真实交接文件后执行：

```sh
python3 -m pip install --require-hashes -r requirements-contracts.lock
python3 scripts/buildchecker/contract.py run \
  --request work/handoff/buildchecker-request.json \
  --draft-job work/handoff/draft-job.json \
  --draft-files work/handoff/draft-files \
  --repository . \
  --out work/buildchecker/handoff-01
python3 scripts/buildchecker/contract.py verify \
  --request work/handoff/buildchecker-request.json \
  --job work/buildchecker/handoff-01/public/job.json
```

公共成功输出为实际图、声明图、完整报告和合并日志。Finding 引用两图及原始记录对应的日志行，位置指向 Makefile；只有已确定的位置才填写行号。路径使用仓库相对路径，依赖使用 `ecosystem=make/name/scope=build`，`configuration_digest` 等于 `configuration_id`。

`public/job.json` 在产物字节和证据位置校验通过后生成。正常发现为 `SUCCEEDED/error=null`；执行失败输出 `FAILED`、具体 Error 和诊断日志。`verify` 返回 0 表示产物校验通过，执行结果以 Job.status 为准。

本地输出使用同机 `file:` URI；跨机器交接需发布产物并更新 URI。入口提供本地契约适配，REST 和远程发布未实现，真实 B→A 联调需另有上游运行记录。

## 6. E7：组员本地验证与交付

本节对应老师 `DevOps_E7_Student_Cloud` 的 A 组本地验证与新增测试任务，使用本仓库已有入口。组长先提供可获取的源码版本，成员在自己的服务器克隆中完成下列流程。代码获取、分支、提交和后续合并由成员按小组约定操作，继续使用本组仓库。

### 6.1 人员、版本与本次目录

| 人员 | 本轮任务 | 完成后交给谁 |
|---|---|---|
| 组长 | 提供包含本节文件的代码版本，核对环境，先跑通一套本地结果，收齐成员材料 | 汇总小组索引，后续组织 CI 与 PR 实验 |
| A 组每名成员 | 运行小组回归与八场景，核对原始证据，补一项个人判定测试，重建并复跑，填写报告和验收表 | 组长 |

E6 来源的四类测试已集中适配到 `services/buildchecker/tests/test_fullcheck_boundaries.py`，来源与去重方式见 [服务说明](../../services/buildchecker/README.md#e6-成员测试与小组回归)。它们随服务测试执行；E7 个人新增测试另行记录。

执行位置：SSH 登录后的本人仓库根目录。前置：Docker、Compose、Git、Make、Python3 可用；当前用户能访问 Docker；组长已提供可获取的完整源码 SHA。本地验证可直接使用镜像中的锁定依赖。

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
test -f scripts/buildchecker/lab.py
test -f tests/buildchecker_lab/test_gate.py
test -f docs/templates/buildchecker-e7-report.md
test -f docs/templates/buildchecker-e7-acceptance.csv

read -r -p '本人数字学号（6—16 位）: ' LAB_SID
read -r -p '本人 Git 提交邮箱: ' LAB_EMAIL
git config --local user.name "$LAB_SID"
git config --local user.email "$LAB_EMAIL"

LAB_IMAGE="buildchecker-lab:$LAB_SID"
LAB_E7_RUN="work/buildchecker/e7-${LAB_SID}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LAB_E7_RUN"
git rev-parse HEAD > "$LAB_E7_RUN/source-commit.txt"
git status --porcelain=v1 > "$LAB_E7_RUN/worktree-status.txt"
git remote get-url origin > "$LAB_E7_RUN/repository-url.txt"
printf '镜像：%s\n证据：%s/%s\n' "$LAB_IMAGE" "$PWD" "$LAB_E7_RUN"
```

输入：本人身份、组长提供的代码版本。输出：本次证据根目录和版本记录。后续命令在同一 Bash 会话执行。若有未提交的个人测试，报告同时记录差异与工作区状态；实验源码版本、镜像来源和后续报告提交分别填写。

### 6.2 环境检查、构建与服务测试

首次构建需要下载基础镜像和依赖，组内首次构建按顺序执行。

```bash
if python3 scripts/buildchecker/lab.py doctor --out "$LAB_E7_RUN/doctor"; then
  LAB_E7_DOCTOR_CODE=0
else
  LAB_E7_DOCTOR_CODE=$?
fi
printf 'DOCTOR_EXIT_CODE=%s\n' "$LAB_E7_DOCTOR_CODE"
```

预期退出 0，`doctor/env.json` 的 `problems=[]`。必需项失败时由组长或管理员处理后，换新目录重试。

```bash
if python3 scripts/buildchecker/lab.py build \
  --image "$LAB_IMAGE" --out "$LAB_E7_RUN/build" --build-timeout 1200; then
  LAB_E7_BUILD_CODE=0
else
  LAB_E7_BUILD_CODE=$?
fi
printf 'BUILD_EXIT_CODE=%s\n' "$LAB_E7_BUILD_CODE"
```

预期退出 0，当前服务测试全部通过。`build/image/stdout.log` 保存镜像 ID 与来源标签，`build/toolchain/stdout.log` 保存工具链，`build/unit-tests/` 保存测试命令、日志和退出码。服务测试数量以本次日志为准，课程包的 15 项不作为本仓库固定数量。

构建失败查看 `build/build/stderr.log`；测试失败查看 `build/unit-tests/`。本节完成后再进入判定回归与门禁。

### 6.3 运行独立判定回归

使用刚构建的镜像运行，不要求宿主机另装 pytest 或 Schema 格式校验依赖。

```bash
if docker run --rm --network none "$LAB_IMAGE" \
  python3 -m unittest discover -s tests/buildchecker_lab -v \
  > "$LAB_E7_RUN/oracle-tests.log" 2>&1; then
  LAB_E7_ORACLE_CODE=0
else
  LAB_E7_ORACLE_CODE=$?
fi
cat "$LAB_E7_RUN/oracle-tests.log"
printf 'ORACLE_EXIT_CODE=%s\n' "$LAB_E7_ORACLE_CODE" \
  | tee "$LAB_E7_RUN/oracle-exit-code.txt"
```

输入：镜像中的 `tests/buildchecker_lab/`。预期退出 0，日志结尾 `OK`。小组初始回归包含 6 项门禁判定及其他编排、公共入口测试；个人补测试后数量相应增加，按实际日志填写。

### 6.4 运行完整八场景并核对结果

```bash
if python3 scripts/buildchecker/lab.py gate \
  --image "$LAB_IMAGE" --out "$LAB_E7_RUN/local-gate"; then
  LAB_E7_GATE_CODE=0
else
  LAB_E7_GATE_CODE=$?
fi
printf 'E7_GATE_EXIT_CODE=%s\n' "$LAB_E7_GATE_CODE" \
  | tee "$LAB_E7_RUN/gate-exit-code.txt"
cat "$LAB_E7_RUN/local-gate/gate/gate-result.json"
cat "$LAB_E7_RUN/local-gate/gate/results.csv"
```

输入：`fixtures/md-rd/` 的独立副本和本人的服务镜像。预期整体退出 0、`passed=true`，共 8 行且每行 `passed=true`。

| 场景 | 故障或输入 | 预期状态／工具退出码 | 需要解释的结果 |
|---|---|---|---|
| unit-tests | 当前服务全部测试 | 测试通过／0 | E6 来源回归也参与执行 |
| original-1 | 原始 md-rd | SUCCEEDED／1 | 精确 MISSING(main.o, config.h)、REDUNDANT(main.o, unused.h) |
| original-2 | 新的原始副本 | SUCCEEDED／1 | 错误集合与第一次一致 |
| original-3 | 新的原始副本 | SUCCEEDED／1 | 错误集合与前两次一致 |
| fixed | 补 config.h、去 unused.h | SUCCEEDED／0 | findings 为空 |
| build-failed | 删除 config.h | FAILED／1、CHECK_FAILED | build_exit_code 非零，不能当作修复成功 |
| unsupported | 同一作业写出两个最终文件 | FAILED／1、UNSUPPORTED | 构建本身成功，分析明确拒绝不支持的输入 |
| timeout | sleep 10 与 1 秒预算 | TIMED_OUT／1、TIMEOUT | 超时与普通构建失败区分 |

故障场景返回失败状态但符合预期时，该场景判定为 PASS。`original-*` 返回 1 表示发现依赖问题，报告仍为 SUCCEEDED。

```text
local-gate/
  source-commit.txt、worktree-status.txt、invocation.json
  image/                  实际镜像信息
  driver/                 门禁脚本命令、完整输出与退出码
  gate/
    gate-result.json、results.csv
    unit-tests/           服务测试命令、输出与退出码
    original-1/           原始检测，另有 original-2/、original-3/
    fixed/                修复后的检测
    build-failed/、unsupported/、timeout/
```

七个构建检测场景各自保存 `fixture/`、`evidence/`、`command.json`、`stdout.log`、`stderr.log` 和 `exit-code.json`。正常检测的 evidence 包含两张图、进程、trace、Make 数据库和 findings。故障目录按实际失败阶段保存诊断材料，不要求失败构建产出成功依赖图。

在报告中记录三个 original 的真实 trace_id；从一个 original 找到 config.h 的成功只读打开、main.o 的输出与 Make 声明位置，说明进程归属。对照 fixed 的图与报告解释修复效果。失败时保留原目录，修正后使用新的输出目录。

### 6.5 校验修复、扫描并保存日志

```bash
if python3 scripts/buildchecker/verify_evidence.py \
  --before "$LAB_E7_RUN/local-gate/gate/original-1/evidence/findings.json" \
  --after "$LAB_E7_RUN/local-gate/gate/fixed/evidence/findings.json" \
  > "$LAB_E7_RUN/repair-verification.json" \
  2> "$LAB_E7_RUN/repair-verification.stderr.log"; then
  LAB_E7_VERIFY_CODE=0
else
  LAB_E7_VERIFY_CODE=$?
fi
cat "$LAB_E7_RUN/repair-verification.json"
printf 'VERIFY_EXIT_CODE=%s\n' "$LAB_E7_VERIFY_CODE" \
  | tee "$LAB_E7_RUN/verify-exit-code.txt"
```

预期退出 0、`passed=true`、2 条变 0 条、`changed_inputs=["Makefile"]`。该脚本比较保存的报告及输入哈希；原始记录的文件和行号按第 6.4 节人工核对。

```bash
if diff -u \
  "$LAB_E7_RUN/local-gate/gate/original-1/fixture/Makefile" \
  "$LAB_E7_RUN/local-gate/gate/fixed/fixture/Makefile" \
  > "$LAB_E7_RUN/repair.diff"; then
  LAB_E7_DIFF_CODE=0
else
  LAB_E7_DIFF_CODE=$?
fi
cat "$LAB_E7_RUN/repair.diff"
printf 'DIFF_EXIT_CODE=%s\n' "$LAB_E7_DIFF_CODE"
```

diff 预期退出 1，表示依赖规则有差异；大于 1 表示执行错误。

```bash
if python3 scripts/secret_scan.py . --history --image "$LAB_IMAGE" \
  > "$LAB_E7_RUN/secret-scan.log" 2>&1; then
  LAB_E7_SCAN_CODE=0
else
  LAB_E7_SCAN_CODE=$?
fi
cat "$LAB_E7_RUN/secret-scan.log"
printf 'SCAN_EXIT_CODE=%s\n' "$LAB_E7_SCAN_CODE" \
  | tee "$LAB_E7_RUN/scan-exit-code.txt"
```

预期退出 0。扫描器在 Git 仓库中检查已跟踪源码，并检查历史和指定镜像；个人未跟踪测试先人工检查，正式纳入仓库后再随最新版本扫描。日志保存在本人 work/，不要将凭据放入报告。

### 6.6 每名成员补充一项 E7 判定测试

阅读 `scripts/buildchecker/gate.py` 的 `evaluate()` 与 `tests/buildchecker_lab/test_gate.py`。在本人克隆中创建 `tests/buildchecker_lab/test_gate_<学号>.py`，使用 `unittest.TestCase` 编写至少一项有明确输入、预期和断言的测试。组内建议选择不同方向：

| 成员 | 建议覆盖方向 | 预期 |
|---|---|---|
| 李宇瀚 241250029 | 正确的两条发现之外多出一条 | 抛出 ValueError，拒绝多报 |
| 孙鲲华 241250109 | 正确 Finding 的 evidence 为空 | 抛出 ValueError，拒绝无依据报告 |
| 管泽昊 241830149 | 同一条 Finding 重复出现 | 抛出 ValueError，不能用集合去重掩盖重复 |
| 黄骢驰 241840198 | 正常报告缺少 trace_id | 抛出 ValueError，拒绝不可追踪报告 |

本表是待执行分工，不代表成员已完成。可按实际情况协调其他有效测试，报告写明与现有覆盖的差别。测试只构造小报告并调用判定函数，不需要为此改检测器业务逻辑。E6 来源回归、E7 个人新增测试和后续 CI 故意失败演示分别记录。

个人测试完成后重新设置一个新的 `LAB_E7_RUN`，例如：

```bash
LAB_E7_RUN="work/buildchecker/e7-${LAB_SID}-personal-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LAB_E7_RUN"
git rev-parse HEAD > "$LAB_E7_RUN/source-commit.txt"
git status --porcelain=v1 > "$LAB_E7_RUN/worktree-status.txt"
git remote get-url origin > "$LAB_E7_RUN/repository-url.txt"
```

在该目录从第 6.2 节重建镜像开始，重新执行服务测试、独立判定回归、完整门禁、修复校验和扫描。门禁仍为 8 场景；只在 `tests/buildchecker_lab/` 添加用例时，服务测试数不变，独立判定回归数增加。报告同时列出修改前后目录和真实测试数量。

### 6.7 编写报告、验收表并打包

```bash
LAB_E7_REPORT="docs/reports/$LAB_SID/e7.md"
LAB_E7_ACCEPTANCE="docs/reports/$LAB_SID/e7-acceptance.csv"
LAB_E7_TEST="tests/buildchecker_lab/test_gate_${LAB_SID}.py"
mkdir -p "$(dirname "$LAB_E7_REPORT")"
cp -n docs/templates/buildchecker-e7-report.md "$LAB_E7_REPORT"
cp -n docs/templates/buildchecker-e7-acceptance.csv "$LAB_E7_ACCEPTANCE"
printf '报告：%s\n验收表：%s\n个人测试：%s\n' \
  "$LAB_E7_REPORT" "$LAB_E7_ACCEPTANCE" "$LAB_E7_TEST"
```

输入：本轮个人结果与 [E7 报告模板](../templates/buildchecker-e7-report.md)、[课程验收 CSV](../templates/buildchecker-e7-acceptance.csv)。输出：填写后的个人报告和验收表。CSV 的 A 项与本轮本地共同项填写真实结果和证据路径，B 项标为不适用；CI、保护、拒绝、恢复及合并项标为待开展。只有实际通过的项目填写 PASS。

| 每人本轮交付 | 内容 | 验收条件 |
|---|---|---|
| 版本与环境 | 仓库 URL、完整 SHA、工作区状态、镜像 ID/来源、doctor、工具链、构建日志 | 能取回代码，说明镜像实际来源；未提交测试另附差异 |
| 独立判定与服务回归 | oracle-tests.log、退出码、build/unit-tests/，修改前后测试数 | 测试通过，个人用例确实被发现和执行 |
| 八场景 | gate-result.json、results.csv、整体退出码、七次构建检测的完整输入和原始记录 | 8 项全部符合各自预期，三个 original 错误集合一致 |
| 人工核对与修复 | trace/Make 行号、进程归属、repair.diff、repair-verification.json | 两条错误有原始依据，修复后为空，仅 Makefile 变化 |
| 个人新增测试 | 测试文件、输入、预期、断言、来源与实际结果 | 本人新增至少一项有效 E7 测试，重建后复跑 |
| 扫描 | secret-scan.log 与退出码 | 已跟踪源码、历史和本次镜像扫描通过 |
| 正式报告与备份 | 报告、验收 CSV、服务器绝对路径及电脑端备份位置 | 路径可读取，状态与证据一致 |

完成个人测试并填写文档后打包最终一轮证据、报告、验收表和个人测试。修改前的运行目录若需解释测试数量变化，另行备份并在报告中注明。

```bash
LAB_E7_ARCHIVE="${LAB_E7_RUN}-local.tar.gz"
tar --exclude='app' --exclude='main.o' --exclude='__pycache__' \
  -czf "$LAB_E7_ARCHIVE" \
  "$LAB_E7_RUN" "$LAB_E7_REPORT" "$LAB_E7_ACCEPTANCE" "$LAB_E7_TEST"
tar -tzf "$LAB_E7_ARCHIVE" | sed -n '1,60p'
sha256sum "$LAB_E7_ARCHIVE" > "${LAB_E7_ARCHIVE}.sha256"
printf '归档：%s/%s\n' "$PWD" "$LAB_E7_ARCHIVE"
```

通过 SFTP 下载归档和摘要，解压抽查报告、CSV、测试文件、各场景 findings 与 trace。正式报告和测试按团队约定入库，work/ 原始证据单独交付。只打包本轮文件，排除凭据、本地配置与编译产物。

### 6.8 组长收件与本轮完成标准

组长收齐四名成员的报告、验收表、个人测试和证据包，用下面的表记录；共同环境记录写明执行人，每人原始门禁结果分别保留。

| 姓名／学号 | 源码 SHA／镜像 ID | 报告／CSV／测试路径 | 服务器证据与电脑备份 | 服务／判定测试数及八场景结果 | 缺项 |
|---|---|---|---|---|---|
| 李宇瀚／241250029 | | | | | |
| 孙鲲华／241250109 | | | | | |
| 管泽昊／241830149 | | | | | |
| 黄骢驰／241840198 | | | | | |

抽查一条 MD 与 RD 的原始依据、修复后的零发现、个人测试输入和断言、归档可读性。材料满足第 6.7 节后登记“E7 本地验证完成”，远程部分按下一节继续。小样例结果、fzy 全量检测、论文项目提高实验及真实公共交接分别记录。

## 7. E7 后续：CI 与 PR 合并门禁

本轮先完成第 6 节，以下由组长后续组织并补入同一份 E7 报告：

| 后续工作 | 需要保留的材料 |
|---|---|
| 完善并运行远程 CI | 正常运行链接、运行 ID、head SHA、实际检出 SHA、检查结果和下载的 artifact |
| 对齐主分支保护 | 实际必需检查名及 App ID、strict、管理员约束、保护配置快照；保留小组原有审核与其他检查要求 |
| 故意失败 PR | 错误版本返回码预期导致的失败日志、失败提交和 artifact |
| 实际拒绝合并 | 普通合并拒绝日志与退出码、OPEN/BLOCKED 快照 |
| 同一 PR 修复恢复 | 正确预期、最新通过检查、审核及 MERGED/mergeCommit/mergedAt 记录 |

现有 `.github/workflows/buildchecker-lab.yml` 检查名为 `buildchecker-lab`，课程 E7 配置要求 `e7-a-quality-gate`；后续统一实际检查名，并接入源码、Git 历史和镜像扫描。当前工作流中的错误预期自测会捕获预期失败，不能替代真实失败 PR 被禁止合并的记录。CI、保护与 PR 验收有实际记录后再填写完成状态。
