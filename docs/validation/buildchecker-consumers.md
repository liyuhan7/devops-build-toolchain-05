# BuildChecker 报告交接验证

本文件是 E2-03 的消费方验证记录。BuildChecker 生产方契约见
`contracts/buildchecker/full-check.*.json` 和 `docs/interfaces/buildchecker.md`。
本验证不部署真实 API，也不执行真实构建；它验证 EChecker、MDFixer 消费报告前必须执行的边界检查。

## 1. 消费流程

1. 通过 `GET /v1/jobs/{job_id}` 获取 BuildChecker 终态 Job。
2. 仅接受 `status=SUCCEEDED` 的报告作为完整 baseline；`FAILED`、`CANCELLED` 或缺少终态时间的 Job 拒绝交接。
3. 按 Artifact `kind` 读取实际图、声明图、报告和日志，不依赖数组位置。
4. 校验每个 Artifact 的 URI、SHA-256、`source_commit`、`configuration_digest` 和生产 `job_id`。
5. 校验每个 Finding 的 `source_commit` 等于请求的仓库 commit，`configuration_id` 等于请求的不可变配置标识。
6. 将同一 `trace_id`、commit、配置、实际图和报告交给 EChecker 作为 baseline。
7. 只筛选 `category=MISSING` 且来自成功 Job 的 Finding 交给 MDFixer；`REDUNDANT` 不自动生成修复请求。

正常检测发现不是系统错误。成功报告可以同时包含 `MISSING` 和 `REDUNDANT`，但必须保持
`job.status=SUCCEEDED`、`job.error=null`。只有构建、清理、追踪、解析、产物完整性等执行问题才进入 `job.error`。

## 2. 错配负例

| 文件 | 变异 | 消费方行为 |
|---|---|---|
| `finding-commit-mismatch.json` | Finding 的 `source_commit` 与请求 commit 不同 | 拒绝，不能交给 EChecker 或 MDFixer |
| `finding-configuration-mismatch.json` | Finding 的 `configuration_id` 与请求配置不同 | 拒绝，不能交给 EChecker 或 MDFixer |

两个文件保留完整的最小请求和 Finding，`expected_rejection=true` 表示它们是反例而不是合法输出。
它们证明消费者不能只检查 JSON 可解析性，必须核对来源和配置一致性。

## 3. MDFixer 门禁

MDFixer 的输入必须满足全部条件：

- BuildChecker Job 成功完成，且 `error` 为 `null`；
- Finding 的 commit、配置、目标和位置证据都通过校验；
- Finding 的 `category` 等于 `MISSING`；
- Finding 来自本次报告的 `findings`，不是手工拼接或另一份 Artifact；
- 目标声明位置和证据仍可从同一版本的报告中解析。

`REDUNDANT` 只表示当前配置和本次完整构建中未观察到声明依赖，不能自动删除依赖，也不能转换成修复输入。

## 4. 自动验证

从仓库根目录执行：

```bash
python3 scripts/validate.py
```

脚本除检查 JSON、Schema 元数据和本地 `$ref` 外，还会检查：

- 两个错配负例确实发生预期的 commit/configuration 不一致；
- 成功样例必须是 `SUCCEEDED` 且 `error=null`；
- 失败样例必须是 `FAILED` 且包含公共 Error；
- 成功响应中的 Finding 和输出 Artifact 与请求 commit/configuration 一致；
- 输出 Artifact 的生产 job 必须等于响应 `job_id`；
- Finding 只能使用 `MISSING` 或 `REDUNDANT`。

当前样例使用虚构的 URI、SHA 和 commit，验证的是接口语义，不代表真实构建结果。
