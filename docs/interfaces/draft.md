# DRAFT 环境生成接口

## 目的与范围

DRAFT 根据固定的代码版本和构建配置生成可供 BuildChecker 使用的构建环境。本契约定义请求、异步 Job 查询结果和交接产物；E2 不要求部署真实 API 或实际构建镜像。

对应样例：

- [`contracts/draft/draft.request.json`](../../contracts/draft/draft.request.json)：创建任务的请求体；
- [`contracts/draft/draft.response.json`](../../contracts/draft/draft.response.json)：构建和验证均成功的结果；
- [`contracts/draft/draft.failed.json`](../../contracts/draft/draft.failed.json)：无法准备构建上下文的失败结果。

## HTTP 交互与状态

| 操作 | 接口 | 行为 |
|---|---|---|
| 创建任务 | `POST /v1/jobs` | 接受请求，立即返回 HTTP `202 Accepted` 与服务端生成的 `job_id`。 |
| 查询任务 | `GET /v1/jobs/{job_id}` | 返回公共 Job 结构，`job_type` 固定为 `DRAFT`。 |

状态为 `QUEUED -> RUNNING -> SUCCEEDED` 或 `QUEUED -> RUNNING -> FAILED`。终态必须包含 `finished_at`。调用方提供的 `trace_id` 必须贯穿同一次端到端运行。

## 请求字段

| 字段 | 约束与用途 |
|---|---|
| `repository_url` | 可访问的 Git 仓库 URL，用于获取源代码。 |
| `source_commit` | 完整 40 位 Git Commit SHA；不得使用分支名、标签或短 SHA。 |
| `working_directory` | 仓库内相对路径，供下游执行构建、读取配置。 |
| `docker` | 提供 Dockerfile、构建上下文和目标镜像仓库。 |
| `build` / `validation` | 分别提供可执行命令和超时限制。 |
| `iteration_limit` | 正整数，限制 DRAFT 的构建/验证尝试次数。 |
| `configuration` | 稳定的 `configuration_id` 与不可变 `configuration_digest`。 |

DRAFT 不得擅自切换到请求 Commit 之外的代码。

## 成功结果和 BuildChecker 交接

成功 Job 的 `status` 必须为 `SUCCEEDED`，`error` 必须为 `null`，`findings` 必须为空数组。公共 Job Schema 禁止在根对象扩展字段，因此 DRAFT 的专属结果通过 `output_artifacts` 交接：

| Artifact kind | 内容 | BuildChecker 的使用方式 |
|---|---|---|
| `DRAFT_ENVIRONMENT_MANIFEST` | 仓库 URL、完整 Commit、工作目录、Dockerfile 路径、构建上下文、不可变镜像 URI、配置 ID、构建/验证命令、迭代次数、两项退出码和成功结论 | 首先读取并核对交接条件。 |
| `CONTAINER_IMAGE` | OCI 镜像的不可变 digest | 拉取镜像作为构建和依赖分析环境，不能只使用可变 tag。 |
| `BUILD_LOG` | 实际构建日志 | 异常排查和交接追溯。 |
| `VALIDATION_LOG` | 最终验证日志 | 确认验证命令确实成功执行。 |

每个 Artifact 均须有 `uri`、`sha256`、`produced_by_job_id`、`source_commit` 和 `configuration_digest`。BuildChecker 消费前必须确认：

1. Artifact 的 `produced_by_job_id` 等于 DRAFT Job 的 `job_id`；
2. `source_commit` 和环境清单中的完整 Commit 一致；
3. `configuration_digest` 和环境清单一致；
4. Job 成功，且环境清单说明构建、验证均成功。

任一条件不满足都必须拒绝交接。

`DRAFT_ENVIRONMENT_MANIFEST` 的内容至少应为以下形状；它与 Job 分开保存，因此不会破坏公共 Job 的字段约束：

```json
{
  "repository_url": "https://github.com/example-org/checkout-service.git",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "working_directory": ".",
  "dockerfile_path": "Dockerfile",
  "context_path": ".",
  "image_uri": "oci://registry.example.edu/e2/checkout-service@sha256:5b703879df7f0cc99a5a91dc0759158fc4e2575805d5509cc21cb2030b8611dc",
  "configuration_id": "maven-jdk17-linux-amd64",
  "configuration_digest": "sha256:<配置摘要>",
  "build": { "command": "./mvnw --batch-mode -DskipTests package", "exit_code": 0 },
  "validation": { "command": "./mvnw --batch-mode test", "exit_code": 0 },
  "iteration_count": 1,
  "final_validation_passed": true
}
```

## 失败语义

`draft.failed.json` 表示一次独立的失败请求，不与 `draft.request.json` 和 `draft.response.json` 构成同一次任务。因此它使用独立的 `trace_id` 和 Commit，其请求的 `dockerfile_path` 为 `docker/Dockerfile`。

系统或执行异常必须使用 `status: "FAILED"` 和非空 `error`。`DOCKERFILE_NOT_FOUND` 表示请求 Commit 中没有指定 Dockerfile，是不可重试的输入/配置错误。失败 Job 可以保留 `BUILD_LOG` Artifact 追溯，但不得生成可消费的 `CONTAINER_IMAGE` 或环境清单。

构建失败、验证失败、Docker 运行时不可用都是 Job Error，而非 Finding；`MISSING` 和 `REDUNDANT` 不应出现在 DRAFT 的 `findings` 中。
