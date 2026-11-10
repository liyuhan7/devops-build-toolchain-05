# BuildChecker

面向 A 组 E5—E7 的 GNU Make / strace 教学依赖检测器。保留 E4 的 `version`、`smoke`，提供 `full-check` 生成实际图、声明图、进程信息和 MD/RD 报告。

## 运行与目录

实验命令、预期退出码和报告要求见 [A 组实验指南](../../docs/guides/A组论文复现实验.md)。E4 环境和基线复跑见 [E4 指南](../../docs/guides/E4操作与交付说明.md)。

镜像保持整个仓库的 `/repo` 布局和 `PYTHONPATH=/repo/services/buildchecker`。Dockerfile、Compose 和根 Makefile 继续承担原有环境与基线验证。基础镜像按原 digest 固定，默认从官方地址获取；APT 与 PyPI 使用阿里云 HTTPS 镜像，`lab.py build --base-image` 可覆盖基础镜像地址。实验入口仅选 A 组，不根据其他服务目录推断轨道。

## 实现与来源

| 文件 | 职责 |
|---|---|
| `buildchecker/fullcheck.py` | 进程归属、文件观察、Make 声明解析、逐目标集合差和真实构建跟踪 |
| `buildchecker/cli.py` | 版本、环境冒烟、全量检测及退出码 |
| `buildchecker/contract_output.py` | DRAFT 交接前置检查、公共结果转换、实际产物及证据校验 |
| `tests/test_fullcheck.py` | 课程参考实现的检测边界测试 |
| `tests/test_fullcheck_boundaries.py` | 声明完整、失败打开、元数据句柄及重复读取的完整报告回归 |
| `tests/test_fullcheck_cli.py` | 检测状态、请求参数与退出码回归 |
| `tests/test_collection_failures.py` | 共享超时预算和采集失败阶段回归 |
| `tests/test_contract_output.py` | 公共输出、上游交接和产物内容校验 |
| `../../scripts/buildchecker/` | 本仓库的实验编排、证据校验和完整场景验证 |

检测算法、参考测试、修复证据校验和门禁判定来自课程包 `DevOps_E4_E7_GitHub/07_实验包/E5E7/A-buildchecker/`。本仓库适配 CLI、目录和镜像，补充共享超时预算、阶段错误及公共输出。个人报告应分别注明参考代码和本人贡献。

### E6 成员测试与小组回归

根据已核对的 A05 E6 成员交付记录，将测试意图适配为 `test_fullcheck_boundaries.py` 的四个参数场景。原交付目录已由组长清理，本文件保存适配后的用例，不作为成员原始文件的逐字副本。相同行为合并到已有基线，不重复复制旧版检测器或整份测试文件。

| 参数场景 | E6 来源 | 当前回归判据 |
|---|---|---|
| `matching-declarations` | 孙鲲华 241250109：声明与实际一致时无发现；复用本仓库已有同类基线 | 目标正确、findings 为空、实际依赖边精确匹配 |
| `failed-open` | 李宇瀚 241250029：失败打开不得形成依赖 | 不把 missing.h 计入实际图，完整报告无误报 |
| `metadata-handles` | 管泽昊 241830149：O_DIRECTORY/O_PATH 句柄不形成读取依赖 | include 与 metadata.h 不进入实际图 |
| `duplicate-reads` | 黄骢驰 241840198：重复读取去重且不误报 | 两条实际依赖边，findings 为空 |

四个场景随服务镜像构建和 E7 门禁中的 `unit-tests` 统一执行。它们属于 E6 来源的小组回归；E7 的个人新增判定测试与来源记录按 [A 组实验指南的 E7 章节](../../docs/guides/A组论文复现实验.md#6-e7-组员本地验证与交付)执行。

## 范围与契约

- 支持单 Make 进程、每个构建作业一个最终输出；不支持的进程、目录描述符、软链接等输入按错误返回。
- 成功的只读打开作为实际依赖观察，不证明发生字节读取。系统路径在项目边界外过滤，RD 只针对当前构建配置。
- 两张图、进程、原始 trace、Make 数据库、输入哈希及 `findings.json` 保存在每次独立输出目录。
- `findings.json` 保留教学 CLI 报告格式。`scripts/buildchecker/contract.py run` 校验上游后运行检测，生成公共 Job、两张公共图、完整报告与合并日志；`verify` 校验真实本地产物。公共成功 Job 即使有发现仍为 `SUCCEEDED`，失败时只发布诊断日志。公共 Schema 和 [接口契约](../../docs/interfaces/buildchecker.md) 保持原样。
- clean/build 共用 `--timeout` 总执行预算；原始报告记录真实时间、环境、阶段及公共错误码，保留课程门禁使用的原状态和错误码。
- 公共产物使用本机可读的 `file:` URI；移动或跨机器交接时需要发布到接收方可读的位置。当前没有异步 REST、远程存储或实际 B→A 联调的完成声明。
- 原有 fzy 基线位于 `fixtures/e3/`，继续用其既有入口验证；教学小样例的通过不代表已完成 fzy 全量检测或论文项目规模评估。
