# E8—E9 个人 AI 使用记录

- 成员：管泽昊 / 241830149。
- 工具与日期：Codex；2026-11-17；具体运行模型标识未单独记录，不猜测型号。
- 关联：Related to [Issue #47](https://github.com/liyuhan7/devops-build-toolchain-05/issues/47)；个人 [PR #52](https://github.com/liyuhan7/devops-build-toolchain-05/pull/52)，分支 `codex/e8-e9-241830149`。
- 准备源码：`484dccd01c5a8d5cb4d63ab6187d80278a941900`；个人测试运行时未提交，实验后固定为 `5f1c1352391426b6472131841c23d554d5ddf2b5`，文件快照与哈希见报告。

## 输入上下文与任务

成员要求完成 E8/E9，指定前置准备位于 feat/EChecker-lab，镜像直连官方；随后明确授权创建和切换个人分支。Codex 阅读仓库规范、实验指南、接口、教学实现、既有测试与上轮身份材料，沿用管泽昊 / 241830149。实验完成后，成员追加“请推送”授权，Codex 提交本次测试和三份文档并推送个人分支；再按成员“创建PR”的追加授权，创建面向 feat/EChecker-lab 的 PR #52。未代成员执行人工批准或合并。

## AI 建议与实际采纳

采用两轮镜像与独立证据目录，将原始参考实验和加入个人测试后的实验分开。基础镜像固定官方 digest，Debian/PyPI 显式使用官方地址；保留编译与 Python 锁定依赖。

Codex 提出并编写两项条件编译测试：未定义 MODE 时不把条件 include 当成实际依赖；仅启用/撤销编译宏时，应刷新图并正确引入/消除 MISSING。既有 `-O1` 测试不改变实际边集，因此此处验证不同风险。没有将其他成员原有测试重新署名。

保留公共算法和保守刷新策略，未扩展 Schema、CI 或公共 API。另用归档内的个人扩展脚本执行真实 BuildChecker 基线和全量对照；仅在内存中去掉 flags 身份比较，验证个人测试能发现错误复用。

## 实际修改与核对边界

Codex 完成个人测试、三份个人文档、实验执行、原始 trace/Make 数据库/进程归属核对、文件哈希与证据包检查。用户已决定实验范围、官方源约束和分支授权；个人扩展细节由 Codex 选择，等待成员审阅，不写成已获人工认可。

首次 E8 的 UID 与 Git ownership 失败、编排脚本目录层级错误、变异结果归并器的子场景身份问题均如实保留并修正复跑，没有修改公共断言来制造通过。首次完整回归另有一项 DRAFT 候选哈希失败，核对后确认仅为 Windows CRLF，与 Git 原件不同；恢复 LF 原字节后在最终新镜像复跑，103 项全部通过。个人测试的 SHA-256 保持不变。

Codex 按代码审查技能安排独立只读子代理审查个人测试，未发现阻塞问题。审查提示变异日志第二个子场景的失败不是独立的撤销方向检错证明，已在报告中明确。未调用第三方模型 API；AI 辅助及独立审查均在 Codex 内完成，不作为成员人工批准。

## 实际验证

| 输入 / 命令 | 独立预期 | 实际结果与证据 |
|---|---|---|
| 官方源 build；原始 / 个人版本 | 共用 A 组环境，BuildChecker 回归通过 | 各 48 项通过；`baseline/build`、`personal-final/build` |
| lab.py test；个人版本 | 保留原回归并通过两项个人用例 | EChecker 16 项、编排 5 项通过；`personal-final/test` |
| lab.py e8 / e9；两轮 | 真实两图可溯源；C0—C3 精确差分 | 成功目录阶段退出 0、gate=true；完整路径见报告 |
| 条件宏扩展 | 仅配置变化引入/撤销 extra.h，增量与全量一致 | 6 项断言组通过；`personal-final/extension` |
| 内存变异与正常复跑 | 省略配置身份时个人用例拒绝错误复用 | `personal-final/mutation` detected=true；`personal-tests-final` 正常两项通过 |
| 契约、仓库回归与扫描 | 保留共享材料完整性和原回归 | 30 份 JSON / 5 份 Schema、103 项仓库回归通过，镜像扫描 1004 份文件未发现问题；见 `personal-final/summary.json`、`additional-checks.json` 及原始日志 |

个人 PR #52 已创建；人工逐项核对、指定 Reviewer 审核、Actions 最终结论和合并记录尚未取得，不将 AI 检查当成人工 Review。成员审阅后，按后续真实协作记录回填远程验收状态。
