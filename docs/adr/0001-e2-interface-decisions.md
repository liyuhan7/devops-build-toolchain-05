# ADR-0001：E2 公共异步任务与交接约定

- 状态：Accepted
- 日期：2026-09-22
- 关联 Issue：#1

## 背景

DRAFT、BuildChecker、EChecker 和 MDFixer 由不同成员并行设计。若各工具分别定义任务状态、错误和文件传递方式，后续串联时会产生字段重命名、状态误解和大文件重复传输等问题。

## 决策

### 1. 统一异步 Job

四类工具都使用 `contracts/common/job.schema.json` 作为任务外层结构。各服务在自己的基础 URL 下提供：

```text
POST /v1/jobs
GET  /v1/jobs/{job_id}
```

`POST` 接受服务专属请求，返回 HTTP `202 Accepted` 和服务端生成的 `job_id`。客户端通过 `GET` 查询任务状态和产物引用。

公共状态为：

```text
QUEUED -> RUNNING -> SUCCEEDED
                  -> FAILED
                  -> CANCELLED
```

终态必须包含 `finished_at`。只有 `FAILED` 使用非空 `job.error`；其他状态的 `job.error` 为 `null`。

### 2. 大文件通过 Artifact URI 交接

构建日志、依赖图、补丁和报告等大文件不直接嵌入 Job。生产方输出 Artifact 元数据，消费方通过 `uri` 读取内容。

Artifact 必须记录：

- 内容类型和 SHA-256；
- 生产它的 `job_id`；
- 对应的源代码 Commit；
- 生成时使用的配置摘要。

这样可以判断下游读取的结果是否来自同一代码版本和配置。

### 3. Finding 与 Error 分离

`MISSING` 和 `REDUNDANT` 是依赖分析结果，写入 `job.findings`。发现这些问题并不表示工具执行失败，Job 仍可以是 `SUCCEEDED`。

解析失败、运行环境不可用或内部异常等执行问题写入 `job.error`，并将 Job 状态设为 `FAILED`。MDFixer 只接受经过上游验证的 `MISSING` Finding，不把 `REDUNDANT` 自动转换为修复请求。

### 4. 契约版本

`contract_version` 使用 `主版本.次版本.修订号`。删除字段、修改字段含义或收紧既有合法取值属于不兼容修改，必须提升主版本；兼容新增字段提升次版本；说明和示例修正提升修订号。

## 备选方案

- 将全部日志和图直接放入响应：会放大响应并妨碍独立存储，因此不采用。
- 将 `MISSING`、`REDUNDANT` 写入 `job.error`：会混淆“检测到问题”和“工具执行失败”，因此不采用。
- 四个工具分别定义状态：会增加串联转换成本，因此不采用。

## 影响

- 后续四段接口只需要定义服务专属请求、Artifact `kind` 和结果字段。
- 生产方修改公共字段前必须通知全部消费方并更新本 ADR 或新增 ADR。
- 当前自动检查只验证 JSON 可解析、Schema 元数据和本地引用存在；具体样例是否满足 Schema 将在对应接口 Issue 中补充。
