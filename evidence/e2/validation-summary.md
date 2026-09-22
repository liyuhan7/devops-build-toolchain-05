# E2 验证汇总

## 验证范围

本阶段验证公共 Schema、本地 `$ref`、四组接口样例、消费方负例和四段跨文件交接。验证对象是离线契约，不执行真实 Git checkout、构建、镜像拉取、依赖分析或自动修复。

## 契约检查

执行：

```powershell
python scripts/validate.py
```

2026-09-22 本地结果：

```text
Validated 29 JSON file(s), including 4 schema(s).
PASS: DRAFT success response satisfies the BuildChecker handoff rules.
PASS: draft-missing-commit.json is correctly rejected.
PASS: draft-missing-image.json is correctly rejected.
PASS: MDFixer provenance, repair gates, and three negative cases satisfy the contract.
PASS: DRAFT, BuildChecker, EChecker, and MDFixer form one traceable handoff chain.
```

## 回归测试

执行：

```powershell
python -m unittest discover -s tests -v
```

2026-09-22 本地结果：

```text
Ran 18 tests in 0.019s
OK
```

测试覆盖 EChecker 成功/失败样例和三类非法输入，以及 MDFixer 来源、输入筛选、Artifact 完整性、四道验证门禁、Patch 工作区身份和剩余 MISSING 检查。

## 跨段验收

| 检查项 | 结果 |
|---|---|
| 四组成功样例共享 `trace_id=e2-example-001` | 通过 |
| DRAFT 镜像与 BuildChecker 输入逐字段一致 | 通过 |
| BuildChecker 三份基线 Artifact 与 EChecker 输入逐字段一致 | 通过 |
| EChecker 报告和声明图与 MDFixer 输入逐字段一致 | 通过 |
| MDFixer Finding 来自 EChecker 当前 Finding | 通过 |
| 基线 Commit、当前 Commit 和配置在消费边界一致 | 通过 |
| `MISSING`/`REDUNDANT` 与执行 Error 分离 | 通过 |

