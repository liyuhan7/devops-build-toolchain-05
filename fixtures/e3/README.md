# fzy 测试基线

本目录固定测试项目与样本，为构建工具链提供可判断对错、可重复运行的输入。

来源标签：`TEAM_ORACLE` 为人工编写的预期答案，`ACTUAL_RUN` 为脚本产生的实际记录，`TOOL_OUTPUT` 保留给工具真实运行后的输出。

## 固定项目与版本

| 项 | 值 |
|---|---|
| 上游项目 | [jhawthorn/fzy](https://github.com/jhawthorn/fzy) |
| 上游 Commit | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| 上游快照 | `fzy/`，未改动源码，含原始 MIT 许可证与随源码分发的第三方许可证 |
| 实验源码 | `echecker/project/`，依次演进 C0 → C1 → C2 |
| 版本映射 | [echecker/commits.json](echecker/commits.json) |
| 归档与源码摘要 | [projects.json](projects.json)，摘要按 POSIX 相对路径排序、LF 行尾规范化计算 |

C0 由上游快照叠加 `echecker/c0.patch` 重建，改造只作用于 Makefile。各样本统一使用配置 `fzy-c0-options-linux-v1`、构建命令 `make CC=gcc`、测试命令 `make CC=gcc check`，功能断言使用无终端交互的 `./fzy -e <查询词>`。

## 判断范围

人工答案限定在选定目标 `src/options.o` 的项目文件依赖：`src/options.c`、`src/options.h`，以及由 `src/config.def.h` 生成的 `config.h`。系统头文件、其他对象目标、Make 自身读取与编译器内部文件不在范围内。

该对象不生成或加载 `src/options.d`，使受控的漏声明不会被自动依赖补回；其他对象沿用上游的自动依赖规则。该改造以 Patch 形式保存，不声称上游存在同类缺陷。

## 样本

| 样本 | 目录 | 关注点 |
|---|---|---|
| C0 | [echecker/](echecker/) | 声明完整：目标的项目依赖与编译读取一致，预期无 Finding |
| C1 | [echecker/](echecker/) | 新增 `src/e3_c1_marker.h` 被读取但未声明，预期一条 introduced MISSING |
| C2 | [echecker/](echecker/) | 源码保持 C1，只把 VERSION 从 `1.1` 改为 `1.2-e3`，原 Finding 保持 unchanged |
| MD/RD | [buildchecker/](buildchecker/) | 同一目标的漏声明与冗余声明各一条，含普通增量与 clean 构建的行为对照 |
| DRAFT | [draft/](draft/) | 上游快照的构建与功能判据，含容器工具缺失失败与参考成功环境 |
| MDFixer | [mdfixer/](mdfixer/) | 固定 MISSING 报告、参考补丁与修复前后的增量验证 |

每个样本包含样本输入（Patch 或源码）、人工预期与判断依据三类文件，具体命名见各目录 README。

## 复跑入口

| 入口 | 环境 | 说明 |
|---|---|---|
| `python scripts/e3/check_baselines.py` | Windows 或 Linux | 材料、版本映射、源码边界与人工答案一致性 |
| `python3 scripts/e3/run_c0.py --operator <姓名>` | Linux | C0 构建、测试、功能与依赖对照 |
| `python3 scripts/e3/run_c1.py --operator <姓名>` | Linux | C1 新增头文件的漏重建验证 |
| `python3 scripts/e3/run_c2.py --operator <姓名>` | Linux | C2 仅编译命令变化的增量与 clean 对照 |
| `bash scripts/e3/reproduce_a.sh --operator <姓名>` | Linux | MD/RD 样本，从上游快照与补丁重建 C0 |
| `bash scripts/e3/verify_fzy.sh --operator <姓名>` | Linux | DRAFT 构建与功能用例 |
| `bash scripts/e3/verify_repair.sh --operator <姓名>` | Linux | MDFixer 修复前后的增量验证 |
| `python scripts/e3/run_draft_container.py --operator <姓名>` | Windows + Docker | DRAFT 失败候选与参考成功容器 |

脚本在 `work/e3/<run-id>/` 创建运行副本，证据写入 `evidence/e3/<tool>/<run-id>/`，输出 `EVIDENCE_DIR` 与 `STATUS`，不修改受版本控制的源文件。`--revision <完整SHA>` 标注已提交版本；未传入时记录为提交前状态。

参考环境为 Ubuntu 24.04 x86_64（gcc 13.3.0、GNU Make 4.3、Git 2.43.0、Python 3.12.3）。容器方式使用固定基础镜像摘要，见 [Dockerfile.baseline](../../scripts/e3/Dockerfile.baseline)。

## 证据与读取

运行目录包含 `run.json`（输入、配置、环境、状态与检查结果）、`commands.json`（命令、时间、退出码与输出字节索引）、`observations.md`（观察摘要）以及逐命令的 `*.stdout.log`、`*.stderr.log`。读取顺序为 `run.json` → `commands.json` → 对应输出。

提交证据可用 `python scripts/e3/pack_evidence.py --directory <运行目录>` 整理为合并日志。失败记录与成功记录分别读取，失败记录不构成成功证据。

## 范围外

- libco 作为后续集成候选记录在 [projects.json](projects.json)，本基线不覆盖其版本核验。
- `make acceptance` 需要 Ruby 与 Bundler，不作为成功条件。
- 依赖缺陷的自动检测、修复与重检属工具实现范围，本基线只提供人工预期与实际运行记录。
