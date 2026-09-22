# DRAFT 到 BuildChecker 交接验证

本文件记录 E2-02 的消费方验证。验证范围是 DRAFT 成功结果能否作为 BuildChecker 的确定输入；不部署真实 API，也不执行真实镜像构建。

## 1. 消费流程

1. 通过 `GET /v1/jobs/{job_id}` 获取 DRAFT 终态 Job。
2. 仅接受 `status=SUCCEEDED` 且 `error=null` 的结果。
3. 按 Artifact 的 `kind` 查找环境清单、容器镜像、构建日志和验证日志，不依赖数组位置。
4. 核对所有 Artifact 的 `produced_by_job_id`、`source_commit` 和 `configuration_digest`。
5. 从环境清单读取工作目录、Dockerfile 路径、构建上下文和不可变镜像 URI。
6. 确认构建与验证的退出码均为 `0`，且 `final_validation_passed=true`，再启动 BuildChecker。

BuildChecker 至少需要以下交接字段：

- `trace_id` 和 DRAFT `job_id`；
- 完整的 `source_commit`；
- `working_directory`、`dockerfile_path` 和 `context_path`；
- 不可变的 `configuration_digest`；
- 包含 `@sha256:` digest 的 `image_uri`；
- 构建和验证退出码，以及最终验证结论。

任一字段缺失、来源不一致，或构建与验证未同时成功时，BuildChecker 必须拒绝交接。

## 2. 正向验证

`contracts/draft/draft.response.json` 必须满足：

- Job 为 `SUCCEEDED`，终态时间非空且 `error=null`；
- 包含 `DRAFT_ENVIRONMENT_MANIFEST`、`CONTAINER_IMAGE`、`BUILD_LOG` 和 `VALIDATION_LOG`；
- 所有 Artifact 来自当前 Job，并指向请求中的同一 Commit 和配置；
- 容器镜像使用不可变 OCI digest，不能只使用可变 tag；
- DRAFT 同时完成构建和验证，不能只构建镜像就交给 BuildChecker。

## 3. 负向验证

| 文件 | 故意缺少的输入 | 预期行为 |
|---|---|---|
| `contracts/negative/draft-missing-commit.json` | `source_commit` | 拒绝；无法确定被检查的源码版本，也无法追溯结果。 |
| `contracts/negative/draft-missing-image.json` | `image_uri` | 拒绝；无法确定 BuildChecker 应使用的构建环境。 |

两个负例均设置 `expected_rejection=true`。除目标缺失字段外，其余交接字段保持完整，用于证明消费方执行的是字段级门禁，而不是只检查 JSON 是否可解析。

## 4. 自动验证

从仓库根目录执行：

```bash
python scripts/validate.py
```

脚本除执行已有 JSON、Schema 和 BuildChecker 检查外，还会验证：

- DRAFT 请求未使用 Git 空树哈希，且使用完整 40 位 Commit SHA；
- 成功响应与请求的 `trace_id`、Commit、配置及生产 Job 一致；
- 四类必要 Artifact 完整，容器镜像 URI 包含不可变 digest；
- 两个负例分别只缺 `source_commit` 或 `image_uri`，并声明预期拒绝。

当前样例使用虚构 URI、SHA 和 Commit，验证的是接口语义，不代表真实构建结果。
