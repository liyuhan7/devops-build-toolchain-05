# ADR-0002：E3 测试项目和 C0 范围

日期：2026-09-30。状态：已实施并提交，[PR #18](https://github.com/liyuhan7/devops-build-toolchain-05/pull/18) 已创建，GitHub Actions 已通过（负责人确认），待组内独立复跑、Review 与合并。

## 背景

课件要求固定项目和环境，准备 MD/RD、C0/C1/C2、DRAFT 构建与功能条件、固定 MD 和参考修复，并保存真实命令与成功或失败记录。

## 决策

采用 jhawthorn/fzy，固定上游 SHA `34b88869d022e861da4846c4463aea3ddfb3ff30`。保留上游完整快照、许可证和第三方文件，C0 使用独立实验副本。libco 用于后续集成选型，其版本及论文对应关系待核验。

C0 仅承诺 `src/options.o` 的项目文件依赖正确。显式列出源码、options.h、config.h；仅该对象的编译禁用自动依赖生成，Makefile 不加载 options.d。其他对象沿用上游逻辑。这样后续 include 故障能由人工判断，而不会被自动依赖补齐。

构建使用 gcc、GNU Make，无交互验证使用 `fzy -e`，已有测试使用 `make check`。不要求系统安装 fzy，也不需要 sudo make install。Ruby acceptance 不属于本次 C0 验收。

公共环境采用固定基础镜像摘要的 Ubuntu 24.04；运行时记录 GCC、Make、Python、Git 版本和镜像 ID。apt 软件包没有逐一锁版本，因此未来重建镜像不保证工具版本完全相同；需要严格性能比较时复用同一镜像 ID 或发布固定环境镜像。

基础镜像摘要、源码 SHA 和归档摘要分别记录。

## 证据和限制

人工预期为 TEAM_ORACLE，实际运行记录为 ACTUAL_RUN。C0 提交为 `0769e815259ab2cae12a21be43256c05906215e0`。提交前的运行记录通过源码摘要定位输入；CI 执行检出的版本，与初始 C0 提交分别记录。

本次验证涵盖 C0 的构建、功能和选定对象依赖关系。四工具的真实输出由后续阶段验证。

## 交接

MD/RD 在独立副本注入；C1 在 C0 历史之后新增 include；C2 保持 C1 样本源码，只改编译命令。版本之间保留真实历史和配置，预期集合只涵盖声明的范围。
