# AI 使用记录

本文件记录实际参与。记录应区分 AI 建议、成员决策与人工验证，不能把未经核对的生成内容作为已完成证据。

## 记录格式

| 日期 | 成员 | Issue/PR | 工具 | AI 参与内容 | 成员决策与修改 | 验证证据 |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | 姓名 | `#编号` | 工具名称 | 生成、分析或检查了什么 | 接受、拒绝或修改了什么 | 命令、Review 或结果 |

## 使用记录

| 日期 | 成员 | Issue/PR | 工具 | AI 参与内容 | 成员决策与修改 | 验证证据 |
|---|---|---|---|---|---|---|
| 2026-09-22 | 李新昊 | `#6` | Codex | 根据公共 Job/Artifact/Error Schema 和 E2 Backlog 起草 DRAFT 请求、成功与失败样例及接口说明 | 采用环境清单 Artifact 承载 DRAFT 专属结果，避免向禁止扩展字段的公共 Job 根对象添加字段；要求镜像以不可变 digest 交接，并要求构建和验证均成功 | `python scripts/validate.py` 通过：已解析 7 份 JSON；待由李宇瀚在 PR 中复核 |
| 2026-09-22 | 李宇瀚 | `#1` | Codex | 根据 E2 课件、论文术语和组内约定生成首批协作模板、贡献规范、Backlog 与操作示例 | 确定采用三阶段、六个 Issue；Issue 不在正文中重复填写分工；首个提交不包含接口实现 | Markdown 结构、Git 差异和暂存范围检查；后续由 PR Reviewer 复核 |
| 2026-09-22 | 李宇瀚 | `#1` | Codex | 生成 Job、Artifact、Finding、Error 公共 Schema、ADR、标准库校验脚本和 GitHub Actions | 采用异步 Job 与 Artifact URI；明确 Finding 不等于执行错误；校验脚本不引入第三方依赖 | `python scripts/validate.py` 通过，解析并检查 4 份 Schema；本机未安装 `jsonschema`，未执行额外语义检查 |
| 2026-09-22 | 李宇瀚 | `#1` | GitHub Copilot、Codex | Copilot Review 指出 Finding 追踪信息、Job `trace_id`、终态时间和本地 JSON Pointer 校验缺口；Codex 核对文档后完成修复 | 接受四条意见；统一 Finding 字段，要求共享 `trace_id`，收紧终态时间，并补充 Pointer 校验 | `python scripts/validate.py` 通过；临时回归测试共 5 项通过，按组内决定未保留测试文件 |
| 2026-09-22 | 孙鲲华 | `#3` | Codex | 阅读 E2 文档与已合并公共 Schema，生成 BuildChecker 请求/成功/失败样例及接口说明，执行校验并准备生产方 PR | 用户要求完成本人任务；沿用公共字段，采用 Make 文件依赖图与不可变配置标识；不代替刘洋提交消费方验证或编造 Review，配对审核待完成 | `python3 scripts/validate.py`：7 JSON / 4 Schema 通过；外部生产方检查使用 jsonschema Draft 2020-12 验证两份 Job，核验来源、Finding 筛选及两类错配变异均通过；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 刘洋 | `#3` / PR #4、消费方 PR | Codex | 阅读 BuildChecker 生产方契约，生成 commit/configuration 错配负例、消费方交接规则，并扩展标准库校验脚本 | 人工确认 Finding 与 Error 分离；只允许成功 Job 的 `MISSING` 进入 MDFixer；负例必须被来源一致性检查拒绝 | `python3 scripts/validate.py`、`git diff --check`；待 PR #4 合并后由 GitHub Actions 再验证生产方样例 |
| 2026-09-22 | 李宇瀚 | `#6` / 消费方 PR | Codex | 根据生产方 PR Review 补正 Commit 与环境清单交接信息，生成 DRAFT 缺 Commit/镜像负例、消费方验证文档并扩展校验脚本 | 采用最小单缺失字段负例；要求 BuildChecker 仅消费构建和验证均成功、来源一致且镜像不可变的 DRAFT 结果 | `python scripts/validate.py`；由李新昊在消费方 PR 中反向 Review，最终以 GitHub Actions 结果为准 |
| 2026-09-22 | 管泽昊 | `#8` / PR #9 | Codex | 依据 E2 Backlog、公共 Schema 和 BuildChecker 样例起草 EChecker 请求/成功/失败契约与接口说明，并按配对 Review 修正身份键、拒绝码和校验范围描述 | 生产方样例采用同一 `trace_id`、基线与当前 commit 分离、无碰撞 Finding 身份键和三类 delta；刘君杰第二轮 Review 已批准，未代替消费方提交验证 | `python scripts/validate.py`：17 JSON / 4 Schema 与 DRAFT 交接检查通过；jsonschema Draft 2020-12 验证两份 Job，另核对基线 Artifact、commit/配置来源及 introduced/resolved/unchanged 集合；未执行真实构建，样例 URI 为虚构 |
