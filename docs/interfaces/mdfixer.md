# MDFixer 修复与重新验证接口

## 目标与边界

MDFixer 接收 EChecker 交付的单个、当前仍有效的 `introduced + MISSING` Finding，在隔离工作区内生成最小 Git Patch，并依次通过构建、测试和 EChecker 重新检测。接口只描述异步任务和 Artifact 交接，不直接修改远程仓库，不创建 commit，也不推送分支。

`MISSING` 是正常 Finding，不是系统错误。`REDUNDANT`、`resolved` 和 `unchanged` Finding 不进入本接口；请求来源不一致、无法安全生成补丁或验证失败时，MDFixer 使用失败 Job 的 `error` 返回原因。

## 端点

```text
POST /v1/jobs
GET  /v1/jobs/{job_id}
```

MDFixer 在自己的服务基础 URL 下使用 ADR-0001 统一规定的端点。`POST /v1/jobs` 接受 `contracts/mdfixer/repair.request.json` 所示请求，通过 `job_type: "MD_FIXER"` 选择任务类型。服务端接受请求后返回 HTTP 202 和服务端生成的 `job_id`；客户端通过公共 Job 查询端点轮询状态。最终成功 Job 见 `repair.response.json`，无法制定安全修复计划的结果见 `repair.rejected.json`。本接口不另设 `/v1/mdfixer/repairs`。

请求在创建任务前无法通过结构或来源校验时，服务端应返回 HTTP 4xx 和公共 Error；已经创建的任务在计划、应用或验证阶段失败时返回 `status: "FAILED"` 的 Job。

## 请求契约

| 字段 | 约束 |
|---|---|
| `trace_id` | 必须与 EChecker Job 相同 |
| `repository.commit` | 必须是 40 位当前 Commit，且等于 Finding 和所有输入 Artifact 的 `source_commit` |
| `configuration.configuration_id` | 必须等于 Finding 的 `configuration_id` 和所有输入 Artifact 的 `configuration_digest` |
| `finding` | 只能有一个 `category: "MISSING"` 的当前 Finding |
| `finding_delta` | 生产接口只接受 `introduced` |
| `declaration` | 指定允许修改的声明文件、格式和目标；路径必须在仓库工作目录内 |
| `repair_policy` | 限制修复策略、可修改路径、最大文件数以及是否允许改源文件 |
| `validation` | 明确 build、test、recheck 命令和总超时 |
| `input_artifacts` | 至少包含 `INCREMENTAL_CHECK_REPORT` 和 `DECLARED_DEPENDENCY_GRAPH` |

MDFixer 必须按 `artifact.kind` 查找输入，不依赖数组顺序。`INCREMENTAL_CHECK_REPORT` 必须由请求所引用的 EChecker Job 产生，并证明该 Finding 位于 `introduced` 集合；仅凭客户端传入的 `finding_delta` 不足以授权修复。

在排队前至少检查：

1. `job_type` 是 `MD_FIXER`，契约版本受支持；
2. Finding 为 `MISSING`，且在 EChecker 报告的 `introduced` 集合中；
3. commit、configuration、trace 和 Artifact 生产者来源一致；
4. Finding 的声明位置与 `declaration.path` 一致；
5. 声明路径属于 `repair_policy.allowed_paths`，且没有目录穿越；
6. build、test、recheck 三条命令均存在，超时为正数。

## 修复策略

样例策略 `ADD_MISSING_DEPENDENCY` 只允许修改依赖声明，将 Finding 中的依赖添加到指定目标。实现必须从请求 commit 创建干净的隔离工作区，先生成计划，再应用补丁。补丁必须满足：

- 只修改白名单内的声明文件，且修改文件数不超过 `maximum_changed_files`；
- 不修改源文件、测试文件、工具配置或请求之外的目标；
- 不包含二进制内容、仓库外路径、绝对路径或子模块变更；
- 能由 `git apply --check` 应用于请求 commit；
- 不隐藏工作区中的额外修改，也不替用户创建 commit。

声明存在歧义、依赖无法表示或必须越过策略边界时，应以 `REPAIR_REJECTED` 结束，并在 `error.details.reason_code` 中返回稳定的可机读原因。拒绝结果不得产生 `GIT_PATCH`。

## 未提交工作区的重检方式

MDFixer 不为候选修复创建 Commit，因此不能把 Patch 应用后的状态冒充为一个新的 `repository.commit`。重检按以下流程执行：

1. 从 `repository.commit` 创建干净、隔离的临时工作区；
2. 对 `GIT_PATCH` 校验 SHA-256，并执行 `git apply --check`；
3. 将 Patch 应用到临时工作区，但不执行 `git commit`；
4. 对应用 Patch 后的文件树生成确定性的 `workspace_digest`；
5. 在该目录中调用 EChecker 检查引擎的 `workspace-check` 模式；
6. 将 `base_commit`、`patch_sha256` 和 `workspace_digest` 一起写入修复清单和重检报告。

`workspace-check` 是 MDFixer 内部调用 EChecker 检查引擎的工作区模式，不是 EChecker 对外的增量 Job 接口，也不改变 EChecker 原有的 commit-based 契约。它直接检查当前文件系统中的 Patch Overlay；公共 Artifact 的 `source_commit` 仍记录基准 Commit，而精确的候选状态由以下三元组标识：

```text
(base_commit, patch_sha256, workspace_digest)
```

消费者不得只根据 `source_commit` 认定重检对象与原 Commit 相同。`workspace_digest` 应由排序后的仓库相对路径、文件类型和文件内容摘要确定性计算，忽略 `.git` 目录、构建输出和命令产生的临时文件。相同的基准 Commit 和 Patch 必须生成相同的 digest。

请求中的 `recheck_command` 只声明调用方式，因为请求创建时 Patch 尚未生成。MDFixer 生成 Patch 后必须把实际的 `base_commit`、`patch_sha256` 和 configuration 参数加入最终执行命令；解析后的完整命令记录在 `REPAIR_MANIFEST.gates.recheck.command` 中。

## 成功响应与 Artifact

成功响应遵守公共 Job Schema：`status` 为 `SUCCEEDED`、`error` 为 `null`、`findings` 为空。MDFixer 的专属数据放在 Artifact 中，避免扩展公共 Job 根对象。

| Artifact kind | 内容要求 |
|---|---|
| `GIT_PATCH` | 基于请求 commit 的统一 diff；只包含策略允许的修改 |
| `REPAIR_MANIFEST` | Finding ID、策略、修改路径、输入 commit/configuration，以及 build/test/recheck 三道 gate 的命令、退出码和状态 |
| `BUILD_LOG` | 应用补丁后的构建命令、标准输出、标准错误和退出码 |
| `TEST_LOG` | 测试命令、标准输出、标准错误和退出码 |
| `RECHECK_REPORT` | EChecker 重检结果；包含原 Finding 的处置结果和 `remaining_missing` 计数 |

所有输出 Artifact 的 `produced_by_job_id` 必须等于 MDFixer Job ID，`source_commit` 和 `configuration_digest` 仍指向输入快照。Patch 是相对该 commit 的候选修改，不得把一个尚未创建的新 Commit SHA 写入 Artifact。

`REPAIR_MANIFEST` 的具体载荷见 `contracts/mdfixer/repair.manifest.json`，至少包含：

- `source_commit`、`configuration_id`、`finding_id` 和修复策略；
- Patch Artifact ID 与 SHA-256；
- `workspace_snapshot` 三元组及 `commit_created: false`；
- 修改文件列表；
- patch apply、build、test、recheck 四个 gate 的状态、命令和退出码；
- build/test 日志 Artifact 和 recheck 报告 Artifact 的引用。

`RECHECK_REPORT` 的具体载荷见 `contracts/mdfixer/recheck.report.json`，至少包含：

- EChecker 的执行模式和退出码；
- 与修复清单完全一致的 `workspace_snapshot`；
- 重检使用的 configuration；
- 原 Finding ID、category 和 `RESOLVED` 结果；
- `remaining_findings` 和整数 `remaining_missing`。

消费方必须同时核对两个载荷中的 `trace_id`、MDFixer Job ID、configuration 和工作区三元组，不能只依赖 Job 外层的 Artifact 元数据。

只有同时满足以下条件，Job 才能成功：

```text
git apply --check == PASS
  -> build exit_code == 0
  -> test exit_code == 0
  -> recheck exit_code == 0
  -> original finding == resolved
  -> remaining_missing == 0
```

任一 gate 失败时 Job 必须为 `FAILED`，并保留已产生的日志 Artifact 以便追溯；不得交付可供合入的成功修复清单。

## 拒绝和失败

`repair.rejected.json` 展示计划阶段的安全拒绝。公共 `error.code` 表示失败类型，`phase` 表示阶段，`details.reason_code` 提供稳定的业务原因。建议错误码如下：

| 场景 | `error.code` | `phase` |
|---|---|---|
| Finding 不是 `MISSING` 或不是 `introduced` | `FINDING_NOT_REPAIRABLE` | `VALIDATE_INPUT` |
| commit、configuration 或 Artifact 来源不一致 | `PROVENANCE_MISMATCH` | `VALIDATE_INPUT` |
| 无法在策略边界内生成安全补丁 | `REPAIR_REJECTED` | `PLAN` |
| Patch 无法应用 | `PATCH_APPLY_FAILED` | `APPLY` |
| 构建或测试失败 | `VALIDATION_FAILED` | `BUILD` 或 `TEST` |
| 重检失败或仍有 `MISSING` | `REVALIDATION_FAILED` | `RECHECK` |

重试只适用于明确的临时执行故障。输入、来源、策略或确定性验证失败均应设置 `retryable: false`。

## 样例与本地验证

```text
contracts/mdfixer/repair.request.json
contracts/mdfixer/repair.response.json
contracts/mdfixer/repair.rejected.json
contracts/mdfixer/repair.manifest.json
contracts/mdfixer/recheck.report.json
```

样例 URI、commit、SHA-256、命令输出和时间均为接口说明用的虚构值，不表示真实构建或 Artifact 下载结果。运行：

```powershell
python scripts/validate.py
```

当前生产方 PR 验证 JSON 可解析、公共 Schema 引用完整，并可使用公共 Job Schema 检查成功与拒绝响应。MDFixer 的三类消费方负例和跨文件语义校验由后续配对验证 PR 提交。
