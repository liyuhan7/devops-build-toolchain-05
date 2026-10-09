# DRAFT 项目输入与功能验证基线

本目录为 DRAFT 定义 fzy 的**构建成功条件**与**无终端交互的功能验证判据**。本阶段不实现 DRAFT，只交付可判断对错、可重复运行的输入、人工预期和实际运行记录。

- 人工预期来源：`cases.json`，标记 `TEAM_ORACLE`。
- 实际运行记录：`evidence/e3/draft/<run-id>/`，标记 `ACTUAL_RUN`。
- DRAFT 自动生成 Dockerfile 并迭代属于后续阶段，不在本目录断言。

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
| `docker.dockerfile_path` / `context_path` | 由后续容器任务提供，本目录不预设 |

功能用例本身不在 E2 契约字段内，作为 `validation` 之外的功能断言单独保留，供需要在容器内判定功能可用性的任务复用。

## 交接：容器失败与参考环境

后续容器任务必须复用本目录的同一套命令与用例，只改变容器环境：

- 失败候选应明确缺少 `make` 或 C 工具链，构建失败需保留非零退出码与错误日志，并区分工具缺失与网络或镜像拉取失败。
- 参考候选安装必要工具链后，用同一源码、同一构建命令和同一功能用例复跑，确认退出码 0、可执行文件生成、功能断言通过。
- 参考 Dockerfile 为人工准备，不属于 DRAFT 的自动生成结果。

## 未完成项

- `make acceptance` 因缺少 Ruby 与 Bundler 未运行，不作为成功条件。
- 容器构建失败与参考成功证据由后续任务交付。
- 配置标识 `fzy-upstream-linux-v1` 仅在 `cases.json` 中使用；是否登记进 `fixtures/e3/projects.json` 由该文件的负责人确认。
- `scripts/e3/check_baselines.py` 目前只检查 C0 材料，未包含本目录；扩展该共享脚本需与负责人确认范围。
