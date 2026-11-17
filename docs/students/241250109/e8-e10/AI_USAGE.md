# E8—E9 个人 AI 使用记录

- 姓名 / 学号：孙鲲华 / 241250109
- 工具 / 模型 / 日期：Codex（DeepSeek 驱动的编码代理）/ 2026-11-17
- 关联 Issue / PR / 源码 SHA：Issue 未提供；PR 见个人报告第 6 节；`f20fcb2ce6b371c93e0822efab7e39359084a215`

## 输入上下文与问题

阅读 `docs/guides/A组EChecker实验.md`、`services/echecker/echecker/core.py`、`scripts/echecker/scenarios.py` 与课程 `DevOps_E8_E10` A 组手册，确定 E8/E9 的执行步骤、通过条件和个人扩展方向。

## 模型建议

- 建议按指南顺序在服务器执行 `doctor → build → test → e8 → e9`，并使用新目录记录证据。
- 建议个人测试选择「头文件间接包含」的缓存失效与「删除包含」的发现消解两个方向，补充公共回归未覆盖的 resolved 路径。
- 建议报告、ADR 与 AI 记录按模板填写，未知的 Issue/PR 字段标为待回填，不编造编号。

## 采纳、拒绝及理由

采纳：执行顺序、测试方向、文档结构。拒绝：不把 AI 生成的说明当作人工 Review，不代替组长合并 PR，不修改检测器业务逻辑。

## 本人决策、修改与人工核对

本人决定在 `feat/EChecker-lab` 基础上建立 `student/241250109/e8-e10` 分支，保留参考运行与扩展运行两套 OUT；本人核对服务器上的 trace 行号、Make 声明、E9 四个 JSON 与 gate 结果后确认。

## 实际验证

| 命令 / 输入版本 | 独立预期 | 实际结果 / 退出码 | 证据路径 |
|---|---|---|---|
| `lab.py test`（参考） | 服务 11 项、编排 5 项通过 | pytest 11 passed；unittest 5 OK；退出 0 | `work/echecker/241250109-20261117-151138/tests/` |
| `lab.py e8`（参考） | 两目标复用、发现两条 | 退出 0，`passed=true` | 同上 `/e8/evidence/result/` |
| `lab.py e9`（参考） | C0—C3 断言通过 | 退出 0，`passed=true` | 同上 `/e9/evidence/result/` |
| `lab.py test`（扩展） | 新增 2 项通过 | pytest 13 passed；unittest 5 OK；退出 0 | `work/echecker/241250109-ext-20261117-151226/tests/` |
| `lab.py e8`、`lab.py e9`（扩展） | 新 OUT 仍通过 | 均退出 0，`passed=true` | 同上 `/e8/`、`/e9/` |
