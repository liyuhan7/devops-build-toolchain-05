# devops-build-toolchain-05

2026 DevOps 课程教学实验 05 组项目协作仓库。

本仓库承载整个项目的需求、接口契约、协作记录和后续实现。当前工作阶段是 **E2：需求与接口契约**

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

## 成员配对

| A 组 | B 组 | 当前配对关注点 |
|---|---|---|
| 李宇瀚 | 李新昊 | DRAFT 与公共协作 |
| 孙鲲华 | 刘洋 | BuildChecker |
| 管泽昊 | 刘君杰 | EChecker |
| 黄骢驰 | 陆泓 | MDFixer |

