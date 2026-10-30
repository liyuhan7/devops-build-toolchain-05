# 统一契约检查

## 执行

```sh
python -m pip install --require-hashes -r requirements-contracts.lock
python scripts/validate.py
python -m unittest discover -s tests -p 'test_validate_*.py' -v
```

两组服务镜像已从 `requirements-dev.lock` 引入同一依赖锁；在服务镜像内运行现有 `make test` 时无需另外安装。宿主机直接执行检查前须安装上面的依赖。

## 检查内容

- 按本地 `$id` registry 执行 Draft 2020-12 实例校验，启用日期时间和 URI 格式检查；服务请求、Job 及内嵌 Artifact/Finding/Error 均参与检查。
- 检查服务类型、完整小写 SHA、仓库相对路径、请求必填字段和配置标识；比较基线与当前完整构建配置，不能复用同名 ID 掩盖环境或命令变化。
- 检查每类必需产物恰好一份，kind 和 ID 不重复；输入与输出的来源字段一致，EChecker 原样保留输入元数据，允许调整数组顺序。
- MDFixer 请求必须显式携带 EChecker 的增量报告、实际图、声明图和构建日志，仅 `introduced + MISSING` 可消费。
- evidence 必须使用 `artifact:<ID>#/JSON/Pointer` 或 `artifact:<ID>#L起始-L结束`；检查 ID 归属、定位语法、媒体类型和日志范围顺序。
- DRAFT 交接、BuildChecker Finding 和 EChecker 基线负例调用各自的实际消费检查；MDFixer 沿用修复门禁检查。负例恢复指定变异后必须与合法正例相同。

## 载荷定位与验证边界

`scripts/contract_checks.py` 的 `evidence_errors` 接收按 Artifact ID 索引的已读取载荷。传入 JSON 对象或日志文本后，它会检查 Pointer 是否存在、数组下标和日志行号是否越界；`require_payloads=True` 会拒绝缺少载荷的输入。调用方应先完成下载、内容摘要及媒体类型核验，再把解析结果交给该函数。

当前契约 URI 和摘要是虚构示例，统一离线入口只核验 evidence 语法与元数据引用，不宣称已读取那些 URI，也不宣称验证了真实日志行数、图内容或文件摘要。载荷定位分支由本地测试数据验证，不能作为工具真实运行证据。

`tests/test_validate_contracts.py` 在临时副本中复现：缺终态时间、未知字段、错服务、短 SHA、重复/缺失产物、输入元数据变化、配置复用、缺修复证据、非法定位以及混入额外错误的负例。既有 EChecker/MDFixer 回归继续保留。
