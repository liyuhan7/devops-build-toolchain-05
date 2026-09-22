# EChecker 增量检测接口（E2 / v1.0.0）

关联：E2-04 / [Issue #8](https://github.com/liyuhan7/devops-build-toolchain-05/issues/8)。本文与 `contracts/echecker/incremental-check.*.json` 一起定义生产方契约，复用 `contracts/common/` 的 Job、Artifact、Finding、Error 和 ADR-0001。样例沿用 BuildChecker 的 `bc-001` 作为基线；仓库地址、产物 URI、SHA-256、时间及当前 commit 均为说明接口的虚构值，不能作为真实构建证据。

## 1. 异步调用

在 EChecker 服务基础 URL 下，`POST /v1/jobs` 接收 `incremental-check.request.json`。合法请求返回 HTTP 202 和服务端生成的公共 Job：`job_type=E_CHECKER`、`status=QUEUED`、`input_artifacts` 原样保存、`findings=[]`、`output_artifacts=[]`、`error=null`。客户端不能指定 `job_id`，整个链路保持同一个 `trace_id`。

`GET /v1/jobs/{job_id}` 返回 HTTP 200 和公共 Job。`incremental-check.response.json` 展示成功终态，`incremental-check.failed.json` 展示另一任务的失败终态。未知任务返回 HTTP 404。状态流转、`finished_at` 和 `job.error` 遵循 ADR-0001；正常检测出依赖问题时 Job 仍为 `SUCCEEDED`。

## 2. 请求和基线验收

| 字段 | 约束与用途 |
|---|---|
| `repository.url` | 与基线报告相同的绝对 HTTPS 仓库地址，不包含凭据。 |
| `repository.base_commit` | 完整小写 40 位 SHA；必须等于基线 Job、三份基线 Artifact 及其内容中的 `source_commit`。 |
| `repository.commit` | 当前完整小写 40 位 SHA；必须是同一仓库中 `base_commit` 的后代，且不能相等。 |
| `configuration` | 与 BuildChecker 请求同构，包括工作目录、构建系统、目标、环境、clean/build 命令和时限；本版只支持 `make`。 |
| `baseline` | 基线 `job_id`、`trace_id`、`source_commit` 和 `configuration_id`；服务端核对它们与已成功的 BuildChecker Job。 |
| `changed_paths` | 从 Git 比较 `base_commit..commit` 得到的去重仓库相对路径；请求者提供提示，服务端必须自行重算并拒绝不一致结果。 |
| `input_artifacts` | 恰好一份基线实际图、一份基线声明图、一份基线完整报告，以及一份当前 DRAFT 容器镜像。 |

基线三份产物的 `produced_by_job_id` 必须等于 `baseline.job_id`，其 `source_commit` 必须等于 `base_commit`。当前镜像的 `source_commit` 必须等于 `repository.commit`，且上游 DRAFT Job 已成功完成构建和最终验证。四份产物的 `configuration_digest` 均必须等于 `configuration.configuration_id`。`baseline.trace_id`、请求 `trace_id` 和上游 Job 的追踪 ID 相同。

EChecker 读取每个 URI 后先验证 SHA-256 和媒体类型，再验证内容的 commit、配置、`produced_by_job_id`、目标集合与外层 Artifact 一致。基线 Job 必须为 `SUCCEEDED`，实际图、声明图、完整报告必须来自同一个 Job；不能使用失败、取消或部分完成的图。完整报告的 `findings` 作为历史 Finding 集合，必须与基线 Job 的 `findings` 相同。配置标识相同还不够：服务端也要逐字段比较完整配置，禁止复用标识掩盖配置变化。若配置变化，应先建立新基线，再进行增量比较。

## 3. 增量计算与更新后的图

1. 在隔离环境中检出当前 commit，核对 Git 祖先关系和实际变更路径，并验证当前 DRAFT 镜像。
2. 从基线实际图和声明图计算受变更影响的目标闭包。对受影响目标执行 clean 与构建追踪，并重新解析声明；未受影响边只有在可以证明其目标、源文件和配置均未变化时才能复用。
3. 生成**当前 commit 的完整目标范围**的实际图和声明图，并使用与 BuildChecker 相同的边定义比较。若无法证明复用安全，扩大重算范围；仍不能得到完整可信结果则 `FAILED`，不得把局部图标记为成功。
4. 用 `category + target + dependency.ecosystem + dependency.name + dependency.scope` 组成稳定 Finding 身份键。比较基线与当前键集合，得到 `introduced`、`resolved` 和 `unchanged`。`finding_id` 是报告内引用 ID，不作为跨 commit 身份键；位置、消息和证据可以变化而不改变同一问题的身份。

成功响应的 `output_artifacts` 各有一份：`ACTUAL_DEPENDENCY_GRAPH`、`DECLARED_DEPENDENCY_GRAPH`、`INCREMENTAL_CHECK_REPORT`、`BUILD_LOG`。图格式沿用 [BuildChecker 接口](buildchecker.md) 的 `targets` 和 `edges`，边方向为 `target` 依赖 `dependency`。输出 Artifact 的 `source_commit` 和内部图/报告的 `source_commit` 均为当前 commit，`configuration_digest` 为当前配置标识，`produced_by_job_id` 为 EChecker Job ID。下游按 `kind` 选取，不能按数组下标选取。

本样例中，基线实际图包含 `src/main.c`、`include/config.h` 两条边；基线声明图包含 `src/main.c`、`include/unused.h`。当前两类图的边分别为：

| 图 | 当前边（均以 `build/app` 为 target，依次对应 `/edges/0` 起） |
|---|---|
| 实际图 | `src/main.c`、`include/config.h`、`include/feature.h` |
| 声明图 | `src/main.c`、`include/config.h`、`include/unused.h` |

因此 `include/feature.h` 是新增 `MISSING`，`include/config.h` 的旧 `MISSING` 已解决，`include/unused.h` 的 `REDUNDANT` 未变化。`REDUNDANT` 仍只描述当前配置下的观察，不证明可以自动删除依赖。

## 4. 当前 Finding 和增量报告

公共 Job 的 `findings` 只放**当前** Finding，来源 commit 和配置与当前输出一致。成功样例包含 `ec-finding-001`（新增 `MISSING`）及 `ec-finding-002`（持续存在的 `REDUNDANT`）。旧 Finding `bc-finding-001` 已解决，不能留在当前 Job 的 `findings` 中。

`INCREMENTAL_CHECK_REPORT` URI 指向的 JSON 内容必须包含：`contract_version`、`trace_id`、`source_commit`、`base_commit`、`configuration_id`、`produced_by_job_id`、完整 `configuration`、`baseline_job_id`、`actual_graph_artifact_id`、`declared_graph_artifact_id`、`findings`、`delta`、`summary`。其中 `findings` 与当前 Job 的数组完全相同；`delta` 记录基线与当前 ID 的对应关系：

```json
{
  "introduced": [{"current_finding_id": "ec-finding-001"}],
  "resolved": [{"baseline_finding_id": "bc-finding-001"}],
  "unchanged": [{"baseline_finding_id": "bc-finding-002", "current_finding_id": "ec-finding-002"}]
}
```

`summary` 至少包含 `introduced_count=1`、`resolved_count=1`、`unchanged_count=1`、`current_missing_count=1`、`current_redundant_count=1`。三个 delta 数组按稳定身份键互斥且覆盖基线与当前 Finding 的并集；引用的 ID 必须存在于相应基线或当前报告。`resolved` 只引用历史 Finding，不携带可修复的当前 Finding。当前 Finding 的 `location` 指向当前 commit 的构建声明位置，`evidence` 引用本次 Job 的图和日志；不得沿用旧 commit 的位置证据。

## 5. MDFixer 交接规则

MDFixer 先核验 EChecker Job 为 `SUCCEEDED`，下载并校验 `INCREMENTAL_CHECK_REPORT`、当前实际/声明图及其 Artifact 元数据。修复候选仅取 `delta.introduced` 所指向的、当前 Job `findings` 中 `category=MISSING` 的 Finding。候选的 `source_commit`、`configuration_id`、`trace_id` 所属 Job 和证据产物必须与当前报告一致。`resolved`、`REDUNDANT`、失败任务以及缺失或校验不通过的报告都不得进入自动修复；`unchanged` 的 MISSING 留给单独的修复策略判断，本接口不自动发送。

## 6. 非法请求和执行失败

解析和前置校验失败时不创建 Job，返回 `{ "error": <公共 Error> }`。主要情况包括：缺少基线产物或字段为 HTTP 400 `INVALID_REQUEST`；不支持的契约版本或构建系统为 HTTP 422；基线 Job 非成功、commit 不是祖先、基线/当前 commit 错配为 HTTP 422 `BASELINE_COMMIT_MISMATCH` 或 `COMMIT_MISMATCH`；配置、目标或完整配置内容不一致为 HTTP 422 `CONFIGURATION_MISMATCH`；变更路径不一致为 HTTP 422 `CHANGED_PATHS_MISMATCH`。未知基线 Job 返回 HTTP 404 `BASELINE_JOB_NOT_FOUND`。

已接受任务后才发现 URI 不可读、摘要不符、Git checkout 失败、追踪/解析失败或构建失败，`GET` 保持 HTTP 200，Job 为 `FAILED`，`error.phase` 指明 `INPUT`、`CHECKOUT`、`BUILD`、`TRACE`、`PARSE` 或 `PUBLISH`，`findings=[]`，不能输出可供 MDFixer 使用的增量报告。失败样例展示 `BASELINE_ARTIFACT_INTEGRITY_ERROR`；其他执行码包括 `ARTIFACT_UNAVAILABLE`、`CHECKOUT_FAILED`、`BUILD_FAILED`、`BUILD_TIMEOUT`、`TRACE_FAILED`、`DECLARED_GRAPH_PARSE_FAILED` 和 `INTERNAL_ERROR`。确定性输入或内容错误 `retryable=false`，只有确认的临时故障才为 true。

## 7. 本轮验证边界

`python scripts/validate.py` 只验证 JSON 解析、Schema 基本元数据和本地 `$ref`；不能证明样例满足公共 Schema 或上述跨字段语义。生产方应另行用 Draft 2020-12 验证两份 Job，并核对基线/当前来源、delta 集合及 MDFixer 筛选。刘君杰的消费方 PR 负责持久化缺基线、commit 错配和配置错配的负例，扩展校验脚本并反向验证交接。本生产方 PR 使用 `Related to #8`，消费方最终 PR 才使用 `Closes #8`。
