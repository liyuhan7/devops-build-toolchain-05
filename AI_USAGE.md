# AI 使用记录

本文件记录实际参与。记录应区分 AI 建议、成员决策与人工验证，不能把未经核对的生成内容作为已完成证据。

## 记录格式

| 日期 | 成员 | Issue/PR | 工具 | AI 参与内容 | 成员决策与修改 | 验证证据 |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | 姓名 | `#编号` | 工具名称 | 生成、分析或检查了什么 | 接受、拒绝或修改了什么 | 命令、Review 或结果 |

## 使用记录

| 日期 | 成员 | Issue/PR | 工具 | AI 参与内容 | 成员决策与修改 | 验证证据 |
|---|---|---|---|---|---|---|
| 2026-09-22 | 李宇瀚 | `#1` | Codex | 根据 E2 课件、论文术语和组内约定生成首批协作模板、贡献规范、Backlog 与操作示例 | 确定采用三阶段、六个 Issue；Issue 不在正文中重复填写分工；首个提交不包含接口实现 | Markdown 结构、Git 差异和暂存范围检查；后续由 PR Reviewer 复核 |
| 2026-09-22 | 李宇瀚 | `#1` | Codex | 生成 Job、Artifact、Finding、Error 公共 Schema、ADR、标准库校验脚本和 GitHub Actions | 采用异步 Job 与 Artifact URI；明确 Finding 不等于执行错误；校验脚本不引入第三方依赖 | `python scripts/validate.py` 通过，解析并检查 4 份 Schema；本机未安装 `jsonschema`，未执行额外语义检查 |
| 2026-09-22 | 李宇瀚 | `#1` | GitHub Copilot、Codex | Copilot Review 指出 Finding 追踪信息、Job `trace_id`、终态时间和本地 JSON Pointer 校验缺口；Codex 核对文档后完成修复 | 接受四条意见；统一 Finding 字段，要求共享 `trace_id`，收紧终态时间，并补充 Pointer 校验 | `python scripts/validate.py` 通过；临时回归测试共 5 项通过，按组内决定未保留测试文件 |
| 2026-09-22 | 孙鲲华 | `#3` | Codex | 阅读 E2 文档与已合并公共 Schema，生成 BuildChecker 请求/成功/失败样例及接口说明，执行校验并准备生产方 PR | 用户要求完成本人任务；沿用公共字段，采用 Make 文件依赖图与不可变配置标识；不代替刘洋提交消费方验证或编造 Review，配对审核待完成 | `python3 scripts/validate.py`：7 JSON / 4 Schema 通过；外部生产方检查使用 jsonschema Draft 2020-12 验证两份 Job，核验来源、Finding 筛选及两类错配变异均通过；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 刘洋 | `#3` / PR #4、消费方 PR | Codex | 阅读 BuildChecker 生产方契约，生成 commit/configuration 错配负例、消费方交接规则，并扩展标准库校验脚本 | 人工确认 Finding 与 Error 分离；只允许成功 Job 的 `MISSING` 进入 MDFixer；负例必须被来源一致性检查拒绝 | `python3 scripts/validate.py`、`git diff --check`；待 PR #4 合并后由 GitHub Actions 再验证生产方样例 |
| 2026-09-22 | 管泽昊 | `#8` | Codex | 依据 E2 Backlog、公共 Schema 和 BuildChecker 样例起草 EChecker 请求/成功/失败契约与接口说明，并执行本地校验 | 生产方样例采用同一 `trace_id`、基线与当前 commit 分离、稳定 Finding 身份键和三类 delta；本人决策及配对 Review 尚待确认，未代替刘君杰提交消费方验证 | `python scripts/validate.py`：10 JSON / 4 Schema 通过；jsonschema Draft 2020-12 验证两份 Job，另核对基线 Artifact、commit/配置来源及 introduced/resolved/unchanged 集合；未执行真实构建，样例 URI 为虚构 |
