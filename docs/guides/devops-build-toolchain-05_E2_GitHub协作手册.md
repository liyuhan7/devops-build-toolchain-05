# devops-build-toolchain-05：E2 GitHub 协作手册

> 仓库：`devops-build-toolchain-05`  
> 当前阶段：E2 需求与接口契约  
> 仓库负责人：李宇瀚  
> 本仓库承载整个完整项目，E2 只是当前 Milestone，不是仓库的全部生命周期。

## 1. E2 要留下什么证据

E2 不只交付接口文件，还要让教师从 GitHub 看到完整过程：

```text
课程要求
  -> Backlog / Issue
  -> 负责人和验收条件
  -> 任务分支
  -> Commit
  -> Pull Request
  -> 跨组 Review
  -> 修改 Commit
  -> GitHub Actions
  -> Merge
  -> E2 Release
```

E2 使用以下标识与后续阶段隔离：

```text
Milestone: E2 需求与接口契约
Issue 前缀: [E2]
Label: stage:E2
Backlog: docs/backlog/E2.md
Evidence: evidence/e2/
Release tag: e2-contract-v1.0.0
```

E2 完成后继续使用同一仓库开展后续阶段，不删除或改写 E2 的 Issue、PR、Commit 和 Release。

## 2. GitHub 基础概念

| 名称 | 含义 | E2 中的用途 |
|---|---|---|
| Issue | 一项待办或待讨论问题 | 写清负责人、交付物和验收条件 |
| Branch | 独立于 `main` 的工作分支 | 每项 Issue 在独立分支修改 |
| Commit | 一次有明确含义的修改记录 | 证明谁修改了什么 |
| Pull Request / PR | 请求把分支合入 `main` | 展示修改、讨论、Review 和验证 |
| Review | 其他成员审核 PR | Comment、Approve 或 Request changes |
| GitHub Actions | 自动检查 | 校验 JSON、Schema 和跨字段语义 |
| Merge | 把 PR 合入 `main` | 只有 Review 和检查通过后执行 |
| Milestone | 一个阶段的 Issue 集合 | 区分 E2 与后续阶段 |
| Project | 任务看板 | 展示 Backlog、进行中、评审和完成状态 |
| Tag / Release | 一个不可混淆的交付节点 | 标记最终 E2 版本和完整 Commit SHA |

记住：

- Issue 描述“准备做什么”。
- Commit 记录“实际修改了什么”。
- PR 解释“为什么这样改、怎样验证”。
- Review 证明另一组成员能够理解并使用交付物。

## 3. 每名成员的本地操作

### 3.1 首次配置

每个人使用自己的 GitHub 账号和真实 Git 身份：

```powershell
git config --global user.name "自己的姓名"
git config --global user.email "GitHub验证过的邮箱"
```

克隆仓库：

```powershell
git clone https://github.com/<李宇瀚GitHub用户名>/devops-build-toolchain-05.git
cd devops-build-toolchain-05
git remote -v
git status
```

不得多人共用同一个 GitHub 账号或 Git 身份。

### 3.2 开始一项 Issue

先同步 `main`：

```powershell
git switch main
git pull --ff-only origin main
```

再创建与 Issue 对应的分支：

```powershell
git switch -c feat/draft-contract
```

规则：

- 不直接在 `main` 修改。
- 一个分支只处理一个主要 Issue。
- 分支名必须能说明内容。
- 不共用任务分支。

### 3.3 提交和推送

修改后先检查：

```powershell
git status
git diff
```

只暂存本 Issue 相关文件：

```powershell
git add contracts/draft/draft.request.json
git add contracts/draft/draft.response.json
```

提交并推送：

```powershell
git commit -m "feat: define DRAFT contract"
git push -u origin feat/draft-contract
```

不要无检查地使用 `git add .`，以免提交日志、本地配置或其他人的文件。

## 4. Issue 怎么提

GitHub 网页进入：

```text
Repository -> Issues -> New issue -> E2 Task
```

标题格式：

```text
[E2][DRAFT] 定义环境生成契约
[E2][BuildChecker] 验证全量检测报告交接
[E2][EChecker] 增加 baseline 非法输入
[E2][MDFixer] 验证修复后的重新检测
```

Issue 模板：

```md
## 目标

一句话说明要完成的接口或交接。

## 交付产物

- [ ] 产物 1
- [ ] 产物 2

## 验收条件

- [ ] 交付文件完整
- [ ] 配对成员 Review 通过
- [ ] GitHub Actions 通过

## 依赖

无，或填写 `Blocked by #Issue编号`。
```

创建时设置：

- Assignee：一名主要负责人。
- Milestone：`E2 需求与接口契约`。
- Project：完整项目的 GitHub Project。
- Label：`stage:E2`、所属组、工具领域和工作类型。

Issue 是工作开始前的约定。不能先完成文件，再补建 Issue。

## 5. PR 怎么提

推送分支后点击 `Compare & pull request`，或进入：

```text
Pull requests -> New pull request
base: main
compare: 自己的任务分支
```

PR 标题示例：

```text
feat: define DRAFT contract
test: validate DRAFT to BuildChecker handoff
docs: record asynchronous job decision
ci: validate E2 contracts
```

PR 模板：

```md
## 修改内容

本次修改了什么。

## 交付产物

- [ ] 产物 1
- [ ] 产物 2

## 验证

- 执行命令：
- 实际结果：

## 接口交接

- 输入：
- 输出：
- 下游读取方式：

## 检查清单

- [ ] 已关联 Issue
- [ ] 已更新 AI_USAGE.md
- [ ] 已完成本地验证

## 关联 Issue

<!-- 中间 PR 使用 Related to；完成 Issue 的最后一个 PR 使用 Closes -->
Related to #Issue编号
```

中间 PR 使用 `Related to #12`，保持 Issue 打开；完成该 Issue 的最后一个 PR 攭成 `Closes #12`，合入默认分支后自动关闭 Issue。

## 6. Review 和修改流程

### 6.1 Reviewer 操作

Reviewer 打开 PR：

1. 阅读 `Conversation` 中的背景、交付物和验证结果。
2. 打开 `Files changed`。
3. 逐文件检查，并用 `Viewed` 标记。
4. 在具体代码行旁点击 `+` 留言。
5. 点击 `Review changes`。
6. 选择：
   - `Comment`：非阻塞问题或建议。
   - `Approve`：允许合并。
   - `Request changes`：必须修改后才能合并。

Review 至少回答：

- 下游能否仅凭契约构造请求？
- commit、配置和 Artifact 是否可追溯？
- 正常 Finding 与系统错误是否区分？
- 无效输入是否有确定行为？
- 作者是否真的执行了验证？

不能只写“没问题”或“同意”。

### 6.2 作者处理 Request changes

不要关闭原 PR，不要新建第二个 PR。继续修改原分支：

```powershell
git switch <原任务分支>
git pull

# 修改并验证

git add <相关文件>
git commit -m "fix: address review comments"
git push
```

然后在 Review 对话中回复：

```text
已在 commit <短SHA> 中修复：说明修改内容和验证结果。
```

重新请求 Reviewer。Reviewer 确认后 Approve。

### 6.3 合并

同时满足以下条件后使用 `Squash and merge`：

- PR 关联 Issue。
- 指定的跨组 Reviewer 已批准。
- Review 对话全部解决。
- GitHub Actions 全部通过。
- PR 写明交付物、验证结果和未完成项。
- `AI_USAGE.md` 已记录本次工作。

合并后删除远程分支。本地同步：

```powershell
git switch main
git pull --ff-only origin main
git branch -d <已合并的本地分支>
```

## 7. 完整示例：从 Issue 到合并

下面以 BuildChecker 为例。假设 GitHub 创建后给这个 Issue 的实际编号是 `#3`；你们操作时要替换为真实编号。

### 7.1 创建 Issue

进入：

```text
Issues -> New issue -> E2 Task
```

标题：

```text
[E2][BuildChecker] 设计全量检测与报告接口
```

正文：

```md
## 目标

定义 BuildChecker 全量检测的请求、响应和报告交接方式。

## 交付产物

- [ ] BuildChecker 请求、响应和失败样例
- [ ] 下游交接验证和非法样例
- [ ] 接口说明和校验脚本

## 验收条件

- [ ] 契约 PR 已合并
- [ ] 验证 PR 已合并
- [ ] GitHub Actions 通过

## 依赖

Blocked by #公共约定Issue编号
```

在 GitHub 右侧设置：

- Assignee：孙鲲华。
- Milestone：`E2 需求与接口契约`。
- Labels：`stage:E2`、`area:BuildChecker`。
- Project Status：先设为 `Ready`。

### 7.2 生产方开始开发

孙鲲华开始工作时，把 Project Status 改成 `In Progress`，然后执行：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/buildchecker-contract
```

本轮修改：

```text
contracts/buildchecker/full-check.request.json
contracts/buildchecker/full-check.response.json
contracts/buildchecker/full-check.failed.json
docs/interfaces/buildchecker.md
```

检查并提交：

```powershell
git status
git diff
git add contracts/buildchecker
git add docs/interfaces/buildchecker.md
git diff --cached --check
git commit -m "feat: define BuildChecker full-check contract"
git push -u origin feat/buildchecker-contract
```

### 7.3 创建生产方 PR

进入：

```text
Pull requests -> New pull request
base: main
compare: feat/buildchecker-contract
```

PR 标题：

```text
feat: define BuildChecker full-check contract
```

PR 描述中的关联方式：

```md
## 关联 Issue

Related to #3
```

这里使用 `Related to`，因为后面还有消费验证 PR，Issue 暂时不能关闭。

创建 PR 后：

- 添加 Reviewer：刘洋。
- 把 Project Status 改成 `In Review`。
- 等待 GitHub Actions。

### 7.4 Reviewer 提出修改

刘洋打开 PR 的 `Files changed`，检查下游能否获得 Finding 的 commit、configuration、target、dependency、位置和证据。

假设发现响应缺少 `configuration_id`，刘洋在对应行留言：

```text
下游无法判断报告是否来自相同构建配置，请在响应和 Finding 报告中补充 configuration_id，并增加一个配置不匹配样例。
```

然后选择：

```text
Review changes -> Request changes
```

Project Status 改成 `Changes Requested`。

### 7.5 作者修改原 PR

孙鲲华继续在原分支修改，不创建新分支或新 PR：

```powershell
git switch feat/buildchecker-contract

# 修改响应和接口说明

git add contracts/buildchecker/full-check.response.json
git add docs/interfaces/buildchecker.md
git commit -m "fix: include configuration in full-check result"
git push
```

然后在 Review 评论下回复：

```text
已补充 configuration_id，并在接口说明中增加一致性要求，请重新检查。
```

Project Status 改回 `In Review`。

### 7.6 Review 通过并合并第一个 PR

刘洋再次检查后选择 `Approve`。确认 GitHub Actions 通过，然后使用：

```text
Squash and merge
```

删除远程分支 `feat/buildchecker-contract`。

此时 Issue `#3` 仍保持打开，因为 PR 使用的是 `Related to #3`。

### 7.7 消费方提交验证 PR

刘洋从最新 `main` 建立第二个分支：

```powershell
git switch main
git pull --ff-only origin main
git switch -c test/buildchecker-report-handoff
```

本轮修改：

```text
contracts/negative/finding-commit-mismatch.json
contracts/negative/finding-configuration-mismatch.json
docs/validation/buildchecker-consumers.md
scripts/validate.py
```

提交：

```powershell
git add contracts/negative
git add docs/validation/buildchecker-consumers.md
git add scripts/validate.py
git diff --cached --check
git commit -m "test: validate BuildChecker report handoff"
git push -u origin test/buildchecker-report-handoff
```

创建第二个 PR：

```text
Title: test: validate BuildChecker report handoff
Reviewer: 孙鲲华
```

PR 描述使用：

```md
## 关联 Issue

Closes #3
```

这表示第二个 PR 是 Issue `#3` 的最终验收。

### 7.8 反向 Review 和最终关闭

孙鲲华检查：

- 负例是否符合 BuildChecker 契约。
- 校验脚本是否误解接口含义。
- 正常 Finding 是否仍能通过。
- commit/configuration 错配是否被拒绝。

Review 和 Actions 都通过后使用 `Squash and merge`。

合并结果：

- GitHub 自动关闭 Issue `#3`。
- Project 卡片移动到 `Done`。
- 删除远程验证分支。
- 两人分别拥有一个作者 PR 和一个 Review 记录。

最后双方同步本地仓库：

```powershell
git switch main
git pull --ff-only origin main
git branch -d feat/buildchecker-contract
git branch -d test/buildchecker-report-handoff
```

其他三个配对 Issue 按完全相同的流程执行，只替换分支名、交付文件和 Reviewer。

## 8. 四对成员与四段流程

| 配对 | A05成员 | B05成员 | 负责流程 | 契约主导方 | 消费验证方 |
|---|---|---|---|---|---|
| 配对1 | 李宇瀚 | 李新昊 | DRAFT -> BuildChecker | 李新昊 | 李宇瀚 |
| 配对2 | 孙鲲华 | 刘洋 | BuildChecker 全量检测与报告交接 | 孙鲲华 | 刘洋 |
| 配对3 | 管泽昊 | 刘君杰 | EChecker 增量检测与报告交接 | 管泽昊 | 刘君杰 |
| 配对4 | 黄骢驰 | 陆泓 | MDFixer 修复与重新验证 | 陆泓 | 黄骢驰 |

论文所属组负责生产契约，另一组从下游消费者角度验收。每一对至少完成两个独立 PR：

1. 生产方提交契约 PR，消费方 Review。
2. 消费方提交验收 PR，生产方反向 Review。

因此每个人都应当既有作者贡献，也有 Review 贡献。

## 9. E2 执行阶段

| 阶段 | 工作 | 执行者 | 产物 |
|---|---|---|---|
| 1. E2 准备 | 协作模板、Backlog、公共 Job/Artifact/Finding/Error、初始校验 | 李宇瀚提交，陆泓 Review | E2-01，一个 PR |
| 2. 四对接口设计 | 每对完成生产契约和消费验证 | 四对并行 | E2-02 至 E2-05，每个 Issue 两个 PR |
| 3. 串联与收尾 | 检查四段样例衔接，汇总贡献、验证和未完成项 | 李宇瀚组织，全员确认 | E2-06，一个 PR 和 E2 Release |

依赖顺序：

```text
E2 准备
  -> 四对接口设计与相互验证
  -> 串联检查和 E2 Release
```

E2-01 合并后，四对可以并行工作。每对只维护一个 Issue，但用两个 PR 分别记录生产方设计和消费方验证。

## 10. 每轮改什么

### 第一轮：E2 准备

E2-01 一次性添加：

```text
.github/ISSUE_TEMPLATE/e2-task.md
.github/pull_request_template.md
.github/workflows/contract-validation.yml
.gitignore
CONTRIBUTING.md
docs/backlog/E2.md
AI_USAGE.md
docs/adr/0001-e2-interface-decisions.md
contracts/common/job.schema.json
contracts/common/artifact.schema.json
contracts/common/finding.schema.json
contracts/common/error.schema.json
scripts/validate.py
```

这一轮只统一公共字段和协作规则，不提交四个服务的最终请求、响应。

### 第二轮：四对接口设计

每对在一个 Issue 内完成两个 PR：

1. 生产方提交请求、响应、失败样例和接口说明，消费方 Review。
2. 消费方提交负例、交接验证和校验脚本修改，生产方反向 Review。

四个 Issue：

```text
E2-02：DRAFT -> BuildChecker
E2-03：BuildChecker -> 下游
E2-04：EChecker -> MDFixer
E2-05：MDFixer -> 重新验证
```

Review 中发现的小问题直接在原 PR 修复，不必再拆 Issue。

### 第三轮：串联与 E2 收尾

E2-06 用一个最终 PR 汇总：

- 四段流程完成情况。
- 每名成员的 Issue、PR、Review 和 Commit SHA。
- Actions 运行结果。
- ADR。
- AI 使用记录。
- 已完成项。
- 未完成项、原因和下一步。

同时使用一个 `trace_id` 检查 DRAFT、BuildChecker、EChecker、MDFixer 的样例能否连续交接。这里只验证接口设计，不要求部署真实 API。

最终创建：

```text
Tag: e2-contract-v1.0.0
Release: E2 Requirements and Interface Contracts
```

## 11. GitHub Actions

E2-01 在同一个 PR 中添加初始校验脚本和工作流：

```text
.github/workflows/contract-validation.yml
```

最小工作流：

```yaml
name: Contract Validation

on:
  pull_request:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  contract-validation:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Validate contracts
        run: python scripts/validate.py
```

工作流至少成功运行一次后，再将 GitHub 上实际出现的检查名称加入 `main` 的 Required status checks。

## 12. 强制约定

1. 不直接向 `main` Push。
2. 一项主要 Issue 对应一个任务分支。
3. 不共用 GitHub 账号和 Git 身份。
4. 不替其他成员 Commit。
5. PR 作者不能批准自己的 PR。
6. 每个 PR 至少一名指定跨组成员 Review。
7. Review 不能只写“同意”。
8. `Request changes` 后必须产生修复 Commit。
9. 不使用 `git push --force`。
10. 不提交密码、Token、私钥或本地配置。
11. 不在没有验证记录时声称完成。
12. 不补造 Issue、PR、Review 或时间记录。

## 13. E2 最终贡献表

| 学号姓名 | 负责流程 | 主 Issue | 作者 PR | Review PR | Commit SHA | 验证结果 |
|---|---|---|---|---|---|---|
| 241250029 李宇瀚 | DRAFT 消费、公共 Job、阶段管理 |  |  |  |  |  |
| 241250109 孙鲲华 | BuildChecker 生产 |  |  |  |  |  |
| 241830149 管泽昊 | EChecker 生产 |  |  |  |  |  |
| 241840198 黄骢驰 | MDFixer 重检 |  |  |  |  |  |
| 241250002 李新昊 | DRAFT 生产 |  |  |  |  |  |
| 241250037 刘洋 | BuildChecker 消费 |  |  |  |  |  |
| 241250049 刘君杰 | EChecker 消费、公共 Artifact |  |  |  |  |  |
| 241250105 陆泓 | MDFixer 生产、CI |  |  |  |  |  |

## 14. 官方参考

- [创建 Issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue)
- [关联 PR 与 Issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- [Review Pull Request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request)
- [Ruleset 可用规则](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub Actions Python 工作流](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
