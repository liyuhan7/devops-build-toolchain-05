# MDFixer 修复与重新验证

本验证是 E2-05 的消费方交付，对应 Issue #13，生产方契约由 PR #12 合并。
黄同学提交验证 PR，由陆泓反向 Review；最终 PR 使用 `Closes #13`。

## 正常交接

从 `contracts/mdfixer/repair.request.json` 读取请求，对照 EChecker 成功 Job、报告中的
`delta.introduced` 和当前 Finding，核对 commit、configuration、trace、产物生产者及输入 Artifact。
只有 `introduced + MISSING` 可以进入修复；客户端自己声明 `introduced` 不足以通过。

`contracts/mdfixer/validation/upstream-report.excerpt.json` 是按 EChecker 接口文档第 4 节
整理的**消费方测试用报告摘录**，不是新定义的生产方接口或下载到的真实报告。
它保留筛选所需的来源、当前 Finding 和 delta；Finding 与上游响应逐项比对。
本验证不证明真实服务生成的 delta 正确，也不代替 EChecker 的增量算法测试。

成功修复同时核对生产方的 `repair.response.json`、`repair.manifest.json` 和
`recheck.report.json`：

- Job 必须成功、error 为 null、findings 为空并有终态时间。
- 五类产物（Patch、清单、构建日志、测试日志、重检报告）必须齐全，ID 不重复，来源一致。
- 清单和重检报告的 `(base_commit, patch_sha256, workspace_digest)` 必须一致；
  `commit_created` 必须为 false，Patch 摘要必须对应输出 Artifact。
- 修改路径必须处于策略白名单内，文件数不得超过限制。
- patch apply、build、test、recheck 四个 gate 必须为 PASSED 且退出码为整数 0。
- build/test 命令与请求一致，日志引用正确；重检采用生产方样例的 workspace-check 调用，
  带上基准 commit、Patch 摘要和配置，并引用同一重检报告。
- 原 Finding 必须 RESOLVED；`remaining_missing` 必须为整数 0，剩余列表不能隐藏 MISSING。
- 计划拒绝样例必须为 FAILED、REPAIR_REJECTED、PLAN 且不可重试，不能提供 GIT_PATCH。

## 三个单字段负例

| 文件 | 从正例变更的字段 | 消费方拒绝码 |
|---|---|---|
| `repair-redundant-finding.json` | 请求 `finding.category` 改为 REDUNDANT | FINDING_NOT_REPAIRABLE |
| `repair-commit-mismatch.json` | 请求 `finding.source_commit` 改为另一个合法 40 位 SHA | PROVENANCE_MISMATCH |
| `repair-validation-failed.json` | 清单 `gates.test.exit_code` 改为 1 | VALIDATION_FAILED |

前两个文件包含完整请求；第三个包含完整修复清单，并与生产方成功响应、重检报告组合。
第三个特意保留 Job 的 SUCCEEDED 和 gate 的 PASSED，证明消费者不会忽略非零退出码。
这是故意不一致的拒绝输入，不是合法的失败 Job 响应。

负例经过与正例相同的检查函数，必须得到指定拒绝码。脚本还会恢复唯一变更字段，
确认其余内容与生产方正例完全相同；缺字段或混入其他错误不能冒充有效负例。

## 执行方式

```text
python scripts/validate.py
python -m unittest discover -s tests -v
git diff --check
```

MDFixer 校验直接集成在 `scripts/validate.py`，沿用现有 test 分支的标准库方式。
`tests/test_validate_mdfixer.py` 使用独立变异覆盖失败上游、伪造 introduced、来源错配、
缺产物、缺终态时间、每个 gate 失败、Patch/工作区错配及剩余问题未清零。
CI 同时运行契约校验和回归测试。

## 验证边界

这是 E2 的离线契约语义验证，不是完整 JSON Schema 验证器，也不实现修复服务。
不会执行样例命令、创建 Commit、下载 Artifact 或运行真实构建与 EChecker。
URI、SHA 和 workspace digest 均为生产方虚构示例；这里只验证它们之间的关联，
不声称重新计算或验证真实文件内容的摘要，也不验证真实 Patch 的可应用性和安全性。
