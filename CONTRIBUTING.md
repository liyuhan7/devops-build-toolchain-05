# 贡献规范

本仓库用于完整项目协作。

## 1. 开始任务

1. 在 GitHub Project 的 Backlog 中选择一个 Issue。
2. 将卡片移到 `Ready`，确认目标、交付产物和验收条件。
3. 从最新 `main` 创建任务分支。

分支命名：

```text
docs/e2-<topic>
chore/e2-<topic>
feat/e2-<topic>
fix/e2-<topic>
```

示例：`docs/e2-buildchecker-contract`。

## 2. 提交修改

每个 Commit 只表达一个明确目的，推荐格式：

```text
docs(e2): add BuildChecker contract
chore(e2): add collaboration templates
fix(e2): align error response example
```

提交前检查：

- 文件位于约定目录，命名清楚；
- JSON 示例可解析，输入输出字段一致；
- 已运行 `python scripts/validate.py`；
- 文档说明失败场景、产物位置和下游读取方式；
- `AI_USAGE.md` 已如实更新；
- 没有提交密钥、个人配置或生成缓存。

## 3. 创建 Pull Request

1. 推送任务分支并创建 PR，目标分支选择 `main`。
2. 标题使用 `[E2] 简短动作说明`。
3. 根据模板填写修改、产物、验证和接口交接。
4. 如果同一 Issue 有多个 PR：中间 PR 写 `Related to #编号`；完成该 Issue 的最后一个 PR 写 `Closes #编号`。
5. 指定配对成员为 Reviewer。

不要在同一个 PR 中混入无关阶段、无关接口或大范围格式化。

## 4. Review 与合并

Reviewer 至少检查：

- 交付产物是否齐全；
- 生产方输出能否被消费方理解和读取；
- 正常与失败示例是否符合 Schema；
- 字段、状态、错误码、版本和路径是否前后一致。

作者收到 `Request changes` 后，在原分支继续修改、提交并推送，不要重新开 PR。满足以下条件后才能合并：

- 验收条件完成；
- 配对成员批准；
- GitHub Actions 通过；
- 对话均已解决。

默认使用 `Squash and merge`。禁止向 `main` 强制推送，禁止绕过 Review 直接合并。
