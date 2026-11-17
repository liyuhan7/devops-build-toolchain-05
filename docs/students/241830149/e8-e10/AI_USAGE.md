# E8—E9 个人 AI 使用记录

- 成员：管泽昊 / 241830149；工具：Codex。具体模型标识未独立记录，不猜测型号。
- 关联：Related to [Issue #47](https://github.com/liyuhan7/devops-build-toolchain-05/issues/47)，原 [PR #52](https://github.com/liyuhan7/devops-build-toolchain-05/pull/52) 已合并。
- 本次服务器运行日期：2026-11-18；原始源码 `484dccd01c5a8d5cb4d63ab6187d80278a941900`，个人源码 `5568b2d33382a6ada903efd5b8daadeab468d028`。

## 任务、授权与执行纠正

用户要求完成 E8/E9、镜像使用官方来源，并先后授权分支操作、提交推送和创建 PR。Codex 最初未读取父目录已有的服务器环境说明，错误地以本地 WSL 执行结果交付。用户指出必须在服务器执行后，Codex 找到既有连接与个人目录，重新在 ecs-devops-05a 的 `/root/241830149/build-toolchain` 完成实验，没有要求用户重复提供可从既有材料取得的信息。

服务器官方基础镜像直连超时；Codex 核对官方 manifest/config 和服务器缓存公共层，恢复相同固定 digest 镜像，记录全层摘要验证。官方 Debian 下载过慢，用户明确允许项目默认软件包源，基础容器镜像仍保持官方。最终按标准 Dockerfile 独立重建两轮，不把本机镜像运行或其他成员结果当作本人服务器实验。

## AI 建议与个人贡献边界

Codex 编写的两项个人测试验证条件 include 的未激活情况及仅切换编译宏导致的边集变化；采用手写预期，并辅以全量对照。已有课程实现与其他成员测试全部保留，未改算法、公共 Schema、CI 或其他成员目录。

Codex 通过 SSH 辅助执行自检、构建、服务与编排回归、E8 真实 strace 基线、E9 真实连续提交、条件宏扩展、内存变异和证据整理。实际命令由 Agent 执行，不表述为成员手工逐条运行或已人工审阅。用户决定范围、服务器要求、官方基础镜像及默认软件包源许可；实现细节和文字由 Codex 辅助，仍待成员审阅。

## 真实验证

| 输入 / 检查 | 服务器实际结果 | 原始证据 |
|---|---|---|
| 原始 / 个人标准构建 | BuildChecker 各 48 项通过 | 两轮 build/unit-tests |
| EChecker / 编排 | 14→16 项、各 5 项通过 | 两轮 test/runner |
| E8/E9 | 两轮阶段退出 0，gate=true | 两轮 e8、e9 |
| 个人测试 / 条件宏扩展 | 2 项、6 项断言组通过；增量/全量一致 | personal-default-packages/personal-tests-final、extension |
| 内存变异 | 忽略 flags 身份时检出错误复用，检查器退出 0 | personal-default-packages/mutation |
| 全仓、契约、材料 | 103 项、30 JSON/5 Schema、E3 材料通过 | regression、contract-validation、baseline-materials |
| 版本与备份 | 文件哈希一致，5 份 bundle 可恢复；服务器原始包下载后 SHA-256 一致 | source-integrity、history-verification、服务器包及摘要 |

原始 WSL 的独立 AI 测试审查指出变异第二个子场景不是独立的撤销方向证明，当前报告保留该边界；未将 AI 检查记为人工批准。官方网络失败、主动停止的慢速构建、缓存环境试跑与最终标准轮次全部保留，如实说明，不删除失败来制造通过。

本次以服务器证据修正已合并报告，不将此前 WSL 材料改名充数。未向第三方模型 API 发送代码或凭据；人工审核、后续 PR、最新 Actions 和最终合并以真实协作记录为准，E10 未开展。
