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
| 2026-09-22 | 李宇瀚 | `#6` / 消费方 PR | Codex | 根据生产方 PR Review 补正 Commit 与环境清单交接信息，生成 DRAFT 缺 Commit/镜像负例、消费方验证文档并扩展校验脚本 | 采用最小单缺失字段负例；要求 BuildChecker 仅消费构建和验证均成功、来源一致且镜像不可变的 DRAFT 结果 | `python scripts/validate.py`；由李新昊在消费方 PR 中反向 Review，最终以 GitHub Actions 结果为准 |
| 2026-09-22 | 管泽昊 | `#8` / PR #9 | Codex | 依据 E2 Backlog、公共 Schema 和 BuildChecker 样例起草 EChecker 请求/成功/失败契约与接口说明，并按配对 Review 修正身份键、拒绝码和校验范围描述 | 生产方样例采用同一 `trace_id`、基线与当前 commit 分离、无碰撞 Finding 身份键和三类 delta；刘君杰第二轮 Review 已批准，未代替消费方提交验证 | `python scripts/validate.py`：17 JSON / 4 Schema 与 DRAFT 交接检查通过；jsonschema Draft 2020-12 验证两份 Job，另核对基线 Artifact、commit/配置来源及 introduced/resolved/unchanged 集合；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 刘君杰 | `#8` / 消费方 PR | Codex | 基于已合并的 EChecker 生产契约，设计缺 baseline、baseline commit 错配和 configuration 错配负例，补充 EChecker 到 MDFixer 交接说明和跨文件语义校验 | 保持公共 Job、Artifact、Finding 和 Error 字段不变；要求只有来源一致的当前 Finding 可交接，并明确 `introduced + MISSING` 才能进入 MDFixer | `python -m unittest tests.test_validate_echecker -v`；`python scripts/validate.py`；`python -m py_compile scripts\\validate.py tests\\test_validate_echecker.py`；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 陆泓 | `#13` / PR #12 | Codex | 依据公共 Schema、BuildChecker Finding 和 EChecker 交接规则起草 MDFixer 契约，并根据黄骁驰的 Request changes 补充 Patch Overlay 重检语义、Artifact 载荷样例和统一 Job 端点 | 只接受来源一致的 `introduced + MISSING`；使用 `(base_commit, patch_sha256, workspace_digest)` 标识未提交工作区；采用 ADR-0001 的 `POST /v1/jobs`；MDFixer 不创建 Commit 或推送代码 | `python scripts/validate.py`、公共 Job Schema 实例校验、MDFixer 跨文件语义检查与 Git 差异检查；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 黄骢驰 | `#13` / 消费方 PR | Codex | 基于已合并的 MDFixer 生产契约，设计 REDUNDANT Finding、commit 错配和验证失败负例，补充重新验证说明、跨文件语义校验及回归测试 | 沿用公共字段和生产方契约，将校验集成到 `scripts/validate.py`；要求修复来源与工作区快照一致，构建、测试和重检均通过，且 `remaining_missing == 0` | `python scripts/validate.py`：29 JSON / 4 Schema 通过；`python -m unittest discover -s tests -v`：18 项通过；`git diff --check` 通过；待陆泓反向 Review；未执行真实构建，样例 URI 为虚构 |
| 2026-09-22 | 李宇瀚 | E2-06 / 收尾 PR | Codex | 审计四组已合并契约，统一 DRAFT 与 BuildChecker 的 trace、配置和镜像 Artifact，增加端到端交接校验并生成 E2 收尾证据 | 保留各组内部契约和失败场景，只修正跨段不一致；贡献表中的私有 PR 链接与合并 SHA 不编造，由仓库负责人回填 | `python scripts/validate.py`：29 JSON / 4 Schema 及四段串联通过；`python -m unittest discover -s tests -v`：18 项通过；未执行真实构建，最终以收尾 PR 的 GitHub Actions 为准 |
| 2026-09-30 | 李宇瀚 | [#17](https://github.com/liyuhan7/devops-build-toolchain-05/issues/17) / [PR #18](https://github.com/liyuhan7/devops-build-toolchain-05/pull/18) | Codex | 准备固定 fzy 源码、C0 显式依赖、人工答案、复跑脚本与说明，辅助执行构建和功能验证；编写组内交接说明并回填协作状态 | 采用 fzy 建立测试基线；限定 src/options.o 的项目依赖范围；C0 提交为 0769e815259ab2cae12a21be43256c05906215e0；负责人确认 PR 已创建、Actions 已通过 | 原始 fzy 和 C0 各通过 32 测试/102 断言；三项功能断言、依赖集合及头文件重编译通过；针对 `5c2bc894659a4e32652262f45907352b993ad1e7` 的 Codex 辅助独立 Linux 复跑已通过，证据见 evidence/e3/c0/README.md；最终 Review、合并状态和 merge SHA 以 PR #18 为准 |
| 2026-10-09 | 李新昊 | E3-04，Issue 编号待回填 | CodeBuddy | 阅读 E3 计划与已合并 C0 材料，起草 DRAFT 的 fzy 构建与功能验证判据、用例文件与 `scripts/e3/verify_fzy.sh`，并在 WSL Ubuntu 24.04 实际执行构建、测试和功能断言 | 采用原始上游快照而非 C0 实验副本；构建与测试命令沿用仓库约定 `make CC=gcc`；功能判据必须逐字节比对标准输出，因无匹配时退出码仍为 0；保留一个预期非零退出码的用例；未修改公共源码快照、`projects.json` 和 `check_baselines.py`；未推送分支或创建 PR | `bash scripts/e3/verify_fzy.sh --operator LiXinhao`：21 项检查通过，12 条命令记录，证据见 evidence/e3/draft/20261009T051451Z-4f7f3891；另做一次改错预期的反向自检，脚本判定 FAILED 并指出具体用例，恢复后 PASSED；`make acceptance` 因缺少 Ruby 未运行；最终以 Reviewer 复跑与 Actions 结果为准 |
| 2026-10-09 | 李新昊 | E3-04，Issue 尚未创建，PR 待回填 | Codex | 审阅既有用例与证据，修正相对证据路径、重复目录覆盖、缺少参数值及说明链接；辅助 GitHub CLI 登录与 PR 准备 | 用户授权推送并创建 PR；Reviewer 按 E3 分工选刘君杰（Liuyiiing）；不关联或关闭其他 Issue；本次仍只交付测试基线 | Linux 构建与 21 项检查通过；E2 18 项回归与 C0 材料检查通过；错误预期被判 FAILED，缺少参数和重复输出目录被拒绝；成员独立复跑及正式 Review 待完成 |
