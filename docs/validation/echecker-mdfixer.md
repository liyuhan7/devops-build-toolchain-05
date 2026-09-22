# EChecker 到 MDFixer 交接验证

## 验证范围

本验证对应 E2-04 的消费方 PR。它检查 EChecker 的成功/失败样例是否遵守公共 Job、Artifact 和 Finding 约定，并检查三类前置非法输入是否在进入增量比较前被拒绝。

样例中的 URI、commit、SHA-256 和时间均为接口说明用的虚构值，不代表真实构建或真实 Artifact 下载结果。

## 正常交接

```text
BuildChecker 成功基线
  -> EChecker 读取 baseline 图、声明图和历史报告
  -> EChecker 检查 base_commit、当前 commit、配置和 Artifact 来源
  -> EChecker 生成当前图、当前 Finding 和 introduced/resolved/unchanged 变化报告
  -> MDFixer 读取增量报告和当前 Finding
```

EChecker 与 MDFixer 必须遵守以下筛选规则：

| EChecker 结果 | MDFixer 行为 |
|---|---|
| `introduced` + `MISSING` | 可以进入修复候选；必须继续核验当前 commit、configuration、Job 和证据 Artifact 一致 |
| `introduced` + `REDUNDANT` | 不自动修复 |
| `resolved` | 不进入修复队列；它只表示基线问题在当前版本已消失 |
| `unchanged` + `MISSING` | 本接口不自动发送给 MDFixer，交由独立修复策略决定 |
| `FAILED` Job | 不允许产生修复请求 |
| commit/configuration 不一致 | 在 EChecker 前置校验阶段拒绝 |

`MISSING` 和 `REDUNDANT` 是 Finding category，不是系统错误。普通 Finding 应保留在成功 Job 的 `findings` 中；解析失败、Artifact 校验失败、构建失败等执行问题才进入 `job.error` 并使 Job 变为 `FAILED`。

## 来源一致性

EChecker 请求中的：

- `repository.base_commit` 必须等于 `baseline.source_commit`；
- 三份基线 Artifact 的 `source_commit` 必须等于 `base_commit`；
- 三份基线 Artifact 的 `produced_by_job_id` 必须等于 `baseline.job_id`；
- 当前容器 Artifact 的 `source_commit` 必须等于 `repository.commit`；
- 所有输入 Artifact 的 `configuration_digest` 必须等于请求的 `configuration.configuration_id`；
- baseline、请求和上游 Job 必须使用同一个 `trace_id`；
- `base_commit` 与当前 `commit` 必须不同。

成功响应中的当前 Finding 和输出 Artifact 必须使用当前 `repository.commit`，配置必须与请求一致，输出 Artifact 的 `produced_by_job_id` 必须是 EChecker 的 Job ID。成功样例同时展示 `MISSING` 和 `REDUNDANT`，证明两类 Finding 仍属于正常检测结果，不会被放入 `job.error`。

## 非法输入

### 缺少 baseline

文件：`contracts/negative/incremental-missing-baseline.json`

请求没有 `baseline`，也没有输入 Artifact。服务端在创建 Job 前拒绝请求，预期错误码为：

```text
INVALID_REQUEST
```

不能在缺少 baseline 身份和基线 Artifact 的情况下进行增量比较。

### baseline commit 不一致

文件：`contracts/negative/incremental-commit-mismatch.json`

请求的 `repository.base_commit` 与 `baseline.source_commit` 不一致。服务端拒绝请求，预期错误码为：

```text
BASELINE_COMMIT_MISMATCH
```

不能把来自另一个源代码版本的依赖图或 Finding 作为当前请求的 baseline。

### configuration 不一致

文件：`contracts/negative/incremental-configuration-mismatch.json`

请求使用 `make-debug-linux-v1`，但 baseline 使用 `make-release-linux-v2`。服务端拒绝请求，预期错误码为：

```text
CONFIGURATION_MISMATCH
```

服务端不能只比较一个配置 ID；实际接口还要求比较完整配置、目标范围和每个 Artifact 的配置来源。

## 本地验证

执行：

```powershell
python -m unittest tests.test_validate_echecker -v
python scripts/validate.py
python -m py_compile scripts\validate.py tests\test_validate_echecker.py
```

`tests/test_validate_echecker.py` 调用 `validate_echecker_semantics()`，确保 EChecker 成功/失败样例和三个负例同时满足校验器的约束。`scripts/validate.py` 还会继续运行已有的公共 Schema、BuildChecker 和 DRAFT 检查。

本 PR 不执行真实构建、不下载虚构 URI，也不声称完成 Draft 2020-12 的完整 Schema 实例验证；它验证的是仓库中可复现的 JSON 解析、公共引用和 EChecker 跨文件交接语义。
