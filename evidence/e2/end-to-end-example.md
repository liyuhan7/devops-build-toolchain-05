# E2 端到端接口串联示例

本示例把四组已评审的成功契约串成一条可追溯链。它验证 JSON 契约、Artifact 身份和消费门禁，不代表真实 API 已部署，也不代表样例 URI 可以下载。

## 统一身份

| 项目 | 值 |
|---|---|
| `trace_id` | `e2-example-001` |
| 基线 Commit | `0123456789abcdef0123456789abcdef01234567` |
| 当前 Commit | `fedcba9876543210fedcba9876543210fedcba98` |
| 配置标识 | `make-debug-linux-v1` |

两个 Commit 和所有 URI、摘要、时间均为接口说明用的虚构值。

## 串联过程

### 1. DRAFT 生成基线环境

`contracts/draft/draft.request.json` 请求在基线 Commit 上执行构建和验证。成功 Job `draft-001` 同时完成两项检查，并通过 `contracts/draft/draft.response.json` 交付：

- `DRAFT_ENVIRONMENT_MANIFEST`；
- `CONTAINER_IMAGE`：`draft-image`；
- `BUILD_LOG`；
- `VALIDATION_LOG`。

镜像使用包含 `@sha256:` 的不可变 OCI URI。BuildChecker 必须拒绝缺少 Commit 或镜像的交接。

### 2. BuildChecker 建立全量基线

`contracts/buildchecker/full-check.request.json` 原样消费 DRAFT 的 `draft-image`。成功 Job `bc-001` 生成实际依赖图、声明依赖图、完整报告和构建日志，并报告：

- `bc-finding-001`：`MISSING`；
- `bc-finding-002`：`REDUNDANT`。

两类 Finding 都属于成功检测结果，`job.error` 保持 `null`。

### 3. EChecker 检查当前版本

`contracts/echecker/incremental-check.request.json` 将 `bc-001` 作为基线，比较基线 Commit 与当前 Commit。请求原样消费 BuildChecker 的三份基线 Artifact，并引用同一 trace 下当前 Commit 的 DRAFT 镜像 `draft-current-image`。

成功 Job `ec-001` 生成当前实际图、声明图、增量报告和日志。增量报告把 `ec-finding-001` 标记为 `introduced + MISSING`，因此它可以成为 MDFixer 候选；`REDUNDANT`、`resolved` 和本接口不自动处理的 `unchanged` Finding 不进入自动修复。

### 4. MDFixer 修复并重新验证

`contracts/mdfixer/repair.request.json` 原样消费 EChecker 的 `ec-report` 和 `ec-declared-graph`，并携带 `ec-finding-001`。成功 Job `mdf-001` 交付 Git Patch、修复清单、构建日志、测试日志和重检报告。

成功门禁为：

```text
git apply --check
  -> build exit_code == 0
  -> test exit_code == 0
  -> recheck exit_code == 0
  -> original finding == RESOLVED
  -> remaining_missing == 0
```

MDFixer 不创建 Commit，也不推送代码。未提交工作区由 `(base_commit, patch_sha256, workspace_digest)` 唯一标识。

## Artifact 交接表

| 生产方 | 消费方 | Artifact |
|---|---|---|
| DRAFT `draft-001` | BuildChecker | `draft-image` |
| BuildChecker `bc-001` | EChecker | `bc-actual-graph`、`bc-declared-graph`、`bc-report` |
| EChecker `ec-001` | MDFixer | `ec-declared-graph`、`ec-report` |
| MDFixer `mdf-001` | 重建与重检结果 | `mdf-patch`、`mdf-manifest`、`mdf-build-log`、`mdf-test-log`、`mdf-recheck-report` |

`scripts/validate.py` 会逐对象比较这些交接 Artifact，而不是只比较文件名或 Artifact kind。
