# DRAFT 项目输入与功能验证基线

本目录为 DRAFT 定义 fzy 的**构建成功条件**与**无终端交互的功能验证判据**。本阶段不实现 DRAFT，只交付可判断对错、可重复运行的输入、人工预期和实际运行记录。

- 人工预期来源：`cases.json`，标记 `TEAM_ORACLE`。
- 实际运行记录：`evidence/e3/draft/<run-id>/`，标记 `ACTUAL_RUN`。
- DRAFT 自动生成 Dockerfile 并迭代属工具实现范围，本目录不断言。

## 固定输入

| 项 | 值 |
|---|---|
| 上游仓库 | <https://github.com/jhawthorn/fzy> |
| 上游 Commit | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| 源码快照 | `fixtures/e3/fzy`（未改动，含原始 MIT 许可证及第三方许可证） |
| 工作目录 | `.`（快照根目录） |
| 构建系统 | Make |
| 构建命令 | `make CC=gcc` |
| 测试命令 | `make CC=gcc check` |
| 功能验证命令 | `./fzy -e <查询词>`，候选行从标准输入提供 |
| 环境要求 | Linux、gcc、libc 开发头文件、GNU Make、Git |

参考环境：Ubuntu 24.04.3 LTS x86_64，gcc 13.3.0，GNU Make 4.3，Git 2.43.0，Python 3.12.3。

`make acceptance` 需要 Ruby 与 Bundler，本环境未安装，因此不作为 DRAFT 的成功条件；需要终端交互的选择流程同样不纳入。

## 成功判据

| 层级 | 命令 | 判据 |
|---|---|---|
| 构建 | `make CC=gcc` | 退出码 0，生成可执行的 `fzy` |
| 测试 | `make CC=gcc check` | 退出码 0，输出包含 `32 tests`、`102 assertions`、`Pass: 32, fail: 0, skip: 0.` |
| 版本 | `./fzy --version` | 退出码 0，输出包含 `1.1`（`VERSION` 宏由 Makefile 传入） |
| 功能 | 逐个用例执行 | 退出码与标准输出逐字节符合 `cases/<id>/expected_stdout` |

测试输出中的 ticks 与耗时随机器变化，不纳入断言。

## 功能用例

用例文件位于 `cases/<id>/`：`argv`（每行一个参数）、`stdin`、`expected_stdout`、`expected_exit_code`，需要断言错误输出时另有 `expected_stderr_contains`。

| 用例 | 参数 | 预期输出 | 退出码 | 人工依据 |
|---|---|---|---|---|
| `match-apple` | `-e apple` | `apple` | 0 | `-e` 走 `show_matches` 路径，两行输入中只有 apple 命中 |
| `match-banana` | `-e banana` | `banana` | 0 | 共用输入、更换查询词，确认输出随查询词变化而非固定文本 |
| `no-match-empty` | `-e zzz` | 空 | 0 | 无匹配时不输出且退出码仍为 0 |
| `multi-match-sorted` | `-e app` | `apple`、`application` | 0 | 两个候选同时命中，按分数降序输出；banana 不命中 |
| `invalid-lines-usage` | `-l 1 -e app` | 空 | 1 | `--lines` 下限为 3，传入 1 时输出用法错误并非零退出 |

## 失败边界

- **无匹配属于正常行为**：退出码 0、标准输出为空。功能验证必须比对标准输出内容，不能只检查退出码，否则空结果会被误判为通过。
- **`invalid-lines-usage` 预期非零退出码**：脚本按预期比对，不把该用例的失败计为基线失败；它用于确认验证脚本能发现失败而不是恒为通过。
- **以下做法不构成功能验证**：只检查 `fzy` 文件是否存在；只运行 `--help` 或 `--version`；只统计 `make` 退出码而不运行功能用例。

## 复跑

从仓库根目录执行：

```sh
bash scripts/e3/verify_fzy.sh --operator 你的姓名
```

常用参数：`--revision <完整SHA>` 标注已提交版本，`--output <目录>` 指定证据目录，`--source <目录>` 指定源码快照。

`--output` 支持绝对或相对路径，目录必须尚不存在，以免覆盖已有运行证据。参数缺少取值时以退出码 2 拒绝执行。

脚本把源码复制到被忽略的 `work/e3/<run-id>/` 后构建，不修改受版本控制的源文件；证据写入 `evidence/e3/draft/<run-id>/`，包含 `run.json`、`commands.json`、`*.stdout.log`、`*.stderr.log` 和 `observations.md`，并输出 `EVIDENCE_DIR` 与 `STATUS`。脚本主体为纯 bash，便于在精简容器中运行；只有在具备 Python 3 时才会额外执行用例清单与人工预期的一致性自检。

已提交版本可用环境变量 `E3_ENVIRONMENT_REFERENCE` 记录容器镜像标识，该值会写入 `run.json`。

## 与 DRAFT 契约的映射

后续 DRAFT 读取本基线时按下表对应 `contracts/draft/draft.request.json`：

| 契约字段 | 本基线取值 |
|---|---|
| `repository_url` | <https://github.com/jhawthorn/fzy> |
| `source_commit` | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| `working_directory` | `.` |
| `build.command` | `make CC=gcc` |
| `validation.command` | `make CC=gcc check` |
| `configuration.configuration_id` | `fzy-upstream-linux-v1` |
| `docker.dockerfile_path` / `context_path` | 由本目录的容器样本提供 |

功能用例本身不在 E2 契约字段内，作为 `validation` 之外的功能断言单独保留，供需要在容器内判定功能可用性的任务复用。

## 容器失败与参考环境

容器样本复用本目录的同一套命令与用例，只改变容器环境：

- 失败候选应明确缺少 `make` 或 C 工具链，构建失败需保留非零退出码与错误日志，并区分工具缺失与网络或镜像拉取失败。
- 参考候选安装必要工具链后，用同一源码、同一构建命令和同一功能用例复跑，确认退出码 0、可执行文件生成、功能断言通过。
- 参考 Dockerfile 为人工准备，不属于 DRAFT 的自动生成结果。

## 容器样本

本节固定 DRAFT 的失败候选与参考成功环境。两个 Dockerfile 使用同一份
`fixtures/e3/fzy/` 原始快照、同一上游 Commit 和同一构建命令；差异只在构建环境是否提供 C 工具链。

| 文件 | 预期 | 构建阶段 | 验证方式 |
|---|---|---|---|
| `Dockerfile.broken` | 非零退出 | Ubuntu 24.04 中不安装 `make`，`RUN make CC=gcc` 应报告工具缺失 | 保存 Docker build 的退出码和 stderr，确认不是网络或镜像拉取错误 |
| `Dockerfile.reference` | 零退出 | 安装 `build-essential`、Git 和 Python，在同一源码上执行 `make CC=gcc`、`make CC=gcc check` | 容器启动后运行 `bash scripts/e3/verify_fzy.sh --operator 姓名` |

基础镜像固定为 `ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3`。
该摘要来自公共实验环境；每次实际运行仍需把 `docker image inspect` 的镜像 ID 和 RepoDigest 写入运行证据。

从仓库根目录执行失败候选。该命令预期返回非零，非零结果只有在日志明确显示缺少 `make` 或编译器时才算通过：

```sh
docker build -f fixtures/e3/draft/Dockerfile.broken -t devops-e3-draft-broken:ubuntu24.04 .
```

参考镜像应成功完成项目构建和测试：

```sh
docker build -f fixtures/e3/draft/Dockerfile.reference -t devops-e3-draft-reference:ubuntu24.04 .
docker image inspect devops-e3-draft-reference:ubuntu24.04 --format '{{.Id}} {{.RepoDigests}}'
docker image inspect ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3 --format '{{.Id}} {{.RepoDigests}}'
```

完整采集入口要求 Python 3.10 或以上、Git 和可用的 Docker Linux 引擎。Windows PowerShell 在仓库根目录执行：

```powershell
python scripts/e3/run_draft_container.py --operator 你的姓名
```

Linux 可执行 `bash scripts/e3/run_draft_container.sh --operator 你的姓名`。入口检查固定上游源码摘要，复制受控文件到唯一构建上下文并规范为 LF，核验两个 Dockerfile 的基础镜像摘要。基础镜像未缓存时先拉取，再核对实际 RepoDigest；身份不一致直接判定失败。

两个候选使用本次运行的独立标签。参考构建必须成功产生镜像 ID，容器按该 ID 运行，关闭网络，并将宿主机证据目录绑定到 `/evidence`。`verify_fzy.sh` 的结果、命令和每个功能用例日志保存到 `functional/`，容器删除后仍可读取。手动构建时同样要求源码、脚本与用例为 LF，并挂载功能证据目录。

真实运行记录保存到 `evidence/e3/draft/<run-id>/`，包含 `run.json`、`commands.json`、`observations.md`、构建上下文清单、两个 Dockerfile、镜像身份、退出码与日志。`--output <新目录>` 可指定证据路径；已有目录会被拒绝。只有基础镜像身份、工具缺失失败、参考构建、功能检查和详细证据全部满足条件时返回退出码 0，否则返回非零并保存失败原因。网络、镜像拉取与源码路径错误不能解释为预期工具缺失。

容器运行记录见 `evidence/e3/draft/`，成功记录与历史失败记录分别保存。

提交证据可用 `scripts/e3/pack_evidence.py` 整理为合并日志；`commands.json` 的输出字节索引与 SHA-256 保留精确内容，`functional/` 单独保留功能命令和检查结果。

## 限制

- `make acceptance` 因缺少 Ruby 与 Bundler 未运行，不作为成功条件。
- 容器运行记录位于 `evidence/e3/draft/<run-id>/`，其中 `20261010T115032Z-4284e785` 为网络与构建失败记录。
- 配置标识 `fzy-upstream-linux-v1` 只在 `cases.json` 中使用。
- `scripts/e3/check_baselines.py` 只检查 C0/C1/C2 材料；DRAFT 的容器验证由本目录入口单独执行。
