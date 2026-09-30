# devops-build-toolchain-05

2026 DevOps 课程教学实验 05 组项目协作仓库。

本仓库承载整个项目的需求、接口契约、协作记录和后续实现。当前工作阶段是 **E3：并行测试基线**，E2 契约与协作证据继续保留。

## E3 协作入口

- [E3 分工与执行计划](docs/backlog/E3.md)：按课件任务安排 A、B 组内部协作。
- [E3 任务与组内交接](docs/guides/E3任务与组内交接说明.md)：项目选型、环境准备、成员执行步骤和交付标准。
- [测试项目与复跑说明](fixtures/e3/README.md)：固定 fzy 上游版本、Linux 环境与执行命令。
- [C0 基线](fixtures/e3/echecker/README.md)：选定对象的正确声明、人工预期与后续版本交接。
- [设计决策](docs/adr/0002-e3-baseline-decisions.md)：自动依赖控制、环境和验证范围。
- [C0 验证记录](evidence/e3/c0/README.md)：实际运行、独立复跑结果和后续操作。

材料检查：`python scripts/e3/check_baselines.py`。Linux 实际构建与行为验证：`python3 scripts/e3/run_c0.py --operator 姓名`。容器方式见项目复跑说明。

E3-01：Issue [#17](https://github.com/liyuhan7/devops-build-toolchain-05/issues/17)，PR [#18](https://github.com/liyuhan7/devops-build-toolchain-05/pull/18)。GitHub Actions 已通过（负责人确认）；针对提交 `5c2bc894659a4e32652262f45907352b993ad1e7` 的独立 Linux 复跑已完成并通过，C0 已满足合并前验证条件。最终 Review、合并状态及对应提交见 [PR #18](https://github.com/liyuhan7/devops-build-toolchain-05/pull/18) 和 [Checks](https://github.com/liyuhan7/devops-build-toolchain-05/pull/18/checks)。

## E2 工具链

四个工具按以下方向交接：

```text
DRAFT
  -> BuildChecker：生成构建与依赖分析所需输入
  -> EChecker：比较基线、变更和当前配置
  -> MDFixer：针对已验证的 MISSING finding 生成修复
  -> 重建、测试、重新检查
```

公共异步 Job、Artifact、Finding 和 Error 结构位于 [`contracts/common/`](contracts/common/)。设计决策记录在 [`docs/adr/`](docs/adr/)。

## E2 协作入口

- [E2 Backlog](docs/backlog/E2.md)：阶段、Issue、PR 关联方式和验收条件；
- [GitHub 协作指南](docs/guides/devops-build-toolchain-05_E2_GitHub协作手册.md)：Issue、分支、Commit、PR、Review 和合并示例；
- [贡献规范](CONTRIBUTING.md)：分支、Commit、PR 和 Review 约定；
- [AI 使用记录](AI_USAGE.md)：记录 AI 建议、成员决策和人工验证；
- [Issue 模板](.github/ISSUE_TEMPLATE/e2-task.md) 和 [PR 模板](.github/pull_request_template.md)：创建任务和 PR 时自动使用。

## E2 阶段证据

- [端到端接口串联](evidence/e2/end-to-end-example.md)：DRAFT、BuildChecker、EChecker 和 MDFixer 的统一 trace 与 Artifact 交接；
- [验证汇总](evidence/e2/validation-summary.md)：契约检查、回归测试和跨段验收结果；
- [贡献记录](evidence/e2/contributions.md)：八名成员的 Issue、Commit SHA 回填表；
- [未完成项与边界](evidence/e2/open-items.md)：合并前后操作和本阶段不实现的内容。

## 本地检查

公共 JSON 契约使用标准库脚本检查 JSON 可解析性、Schema 元数据和本地 `$ref`：

```bash
python scripts/validate.py
```

GitHub Actions 会在每个 Pull Request 和推送到 `main` 时运行契约检查与标准库回归测试。具体工作流见 [contract-validation.yml](.github/workflows/contract-validation.yml)。

## 基本协作流程

```text
Issue -> Project 看板 -> 任务分支 -> Commit -> Pull Request
      -> 配对成员 Review -> 修改 -> Actions 通过 -> 合并
```

## E2 历史成员配对

| A 组 | B 组 | 当前配对关注点 |
|---|---|---|
| 李宇瀚 | 李新昊 | DRAFT 与公共协作 |
| 孙鲲华 | 刘洋 | BuildChecker |
| 管泽昊 | 刘君杰 | EChecker |
| 黄骢驰 | 陆泓 | MDFixer |

