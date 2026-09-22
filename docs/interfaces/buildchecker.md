# BuildChecker 全量检测接口（E2 / v1.0.0）

关联：E2-03 / [Issue #3](https://github.com/liyuhan7/devops-build-toolchain-05/issues/3)。

本文与三个 `contracts/buildchecker/full-check.*.json` 一起定义生产方契约。复用
`contracts/common/` 的 Job、Artifact、Finding、Error 及 ADR-0001，不部署真实 API。
样例中的仓库、镜像 Artifact URI、SHA、摘要和时间均为虚构契约数据，不代表真实构建记录；
URI 所指文件未上传，摘要不可用于真实下载验证。实际运行必须替换为可读取产物及真实摘要。

## 1. 调用与异步状态

在 BuildChecker 服务基础 URL 下调用 `POST /v1/jobs`，请求见 `full-check.request.json`。
服务端接受合法请求后生成 job_id，返回 HTTP 202 和完整公共 Job：status 为 QUEUED、
findings/output_artifacts 为空、error 为 null；原样保留 trace_id、contract_version 和 input_artifacts，
设置 created_at、updated_at，不要求 finished_at。客户端不能指定 job_id。

使用 `GET /v1/jobs/{job_id}` 查询完整 Job。`full-check.response.json` 是 GET 成功终态，
`full-check.failed.json` 是另一次请求的 GET 失败终态，不是 POST 的同步响应。
GET 成功返回 HTTP 200（包括 status=FAILED）；未知 job_id 返回 HTTP 404。
状态转换为 QUEUED → RUNNING → SUCCEEDED / FAILED / CANCELLED，终态必须有 finished_at。
仅 FAILED 的 error 非空；取消产生的残缺产物不能作为基线或修复输入。

## 2. 请求字段与前置条件

| 字段 | 类型 / 约束 | 含义 |
|---|---|---|
| contract_version | string，当前为 1.0.0 | 契约版本 |
| trace_id | 非空 string，最长 128 字符 | 完整链路共享的追踪 ID |
| job_type | 常量 BUILD_CHECKER | 全量检测任务 |
| repository.url | 绝对 HTTPS URL | 待检仓库，不携带凭据 |
| repository.commit | 40 位十六进制 SHA | 固定源码版本，拒绝分支名及短 SHA |
| configuration.configuration_id | 非空 string | 不可变构建配置标识 |
| configuration.working_directory | 仓库内相对路径 | `.` 表示根目录；不得包含 `..` 或越界软链接 |
| configuration.build_system | 当前支持 make | 本版使用 Make 目标与文件依赖语义 |
| configuration.targets | 非空且去重的 string 数组 | 分析的明确构建目标 |
| configuration.environment | string → string 对象 | 显式构建变量；本样例 CC/CFLAGS |
| configuration.clean_command | 非空 string 数组 | 无 shell 插值的清理命令 argv |
| configuration.build_command | 非空 string 数组 | 无 shell 插值的构建命令 argv |
| configuration.timeout_seconds | 正整数 | clean 和 build 共用的总执行时限，单位秒 |
| input_artifacts | Artifact 数组 | 恰好一份 kind=CONTAINER_IMAGE 的 DRAFT 镜像引用 |

上述字段均必填，本版拒绝未知请求字段和未知 configuration/repository 字段。
镜像必须来自构建与验证均成功的 DRAFT Job；仅存在镜像元数据不能证明其成功，
调用方必须通过 DRAFT Job 查询或可信交接记录验证状态与最终验证结果。
消费镜像的 manifest 并验证 Artifact.sha256，再按 manifest 的不可变 digest 拉取镜像；不使用浮动 tag。
镜像和其他输入产物都必须通过公共 Artifact Schema。

configuration_id 是覆盖工作目录、构建系统、目标、环境、clean/build 命令、时限和镜像内容摘要的
不可变配置标识；任意一项变化都分配新标识，不通过重用同名标识表示不同配置。
本版约定 `Artifact.configuration_digest == configuration.configuration_id`，使用公共 Schema 允许的
不可变标识形式。下游不把 `configuration_digest` 与 Finding 的 `configuration_id` 当作不同配置。
所有输入 Artifact.source_commit、输出 Artifact.source_commit 和 Finding.source_commit
都必须等于 repository.commit（统一小写完整 SHA），其配置字段必须等于上述标识。

## 3. clean build 与执行顺序

1. 在隔离的构建容器内检出精确 commit，确认工作目录和目标合法，核验镜像来源和摘要。
2. 执行 clean_command，必须成功清理目标及中间产物；禁止将缓存命中、增量构建或旧追踪记录作为全量结果。
3. 在同一配置执行 build_command，对目标及其构建子进程追踪文件读取、写入和生成关系。
4. 从相同源码/配置解析 Make 声明图，比较同一组目标的依赖边。
5. 持久化完整图、报告与日志，计算真实 SHA-256 后发布 SUCCEEDED Job。

必须在单次配置的完整目标范围成功完成追踪和声明解析。clean 失败、build 非零退出、超时、
追踪缺失或声明图解析失败都进入 FAILED，不能把不完整图当成功基线；失败日志仍可发布。
构建命令来自待检项目，仅在受限环境执行，不允许继承宿主凭据。

## 4. 输出产物与内容格式

成功时 output_artifacts 必须各有一份：

| kind | media_type | 用途 |
|---|---|---|
| ACTUAL_DEPENDENCY_GRAPH | application/json | 运行追踪所得实际依赖图；EChecker baseline |
| DECLARED_DEPENDENCY_GRAPH | application/json | 构建声明依赖图 |
| FULL_CHECK_REPORT | application/json | 运行配置、clean/build 结果和 Finding 报告 |
| BUILD_LOG | text/plain | 命令、退出状态及追踪定位证据 |

每份输出的 produced_by_job_id 必须等于当前 Job.job_id，artifact_id 在 Job 内唯一。
输入的 produced_by_job_id 保持 DRAFT 原任务 ID，不能改为 BuildChecker ID。
下游按 kind 选择产物，不能依赖数组下标。读取 URI 内容后先核验 SHA-256、媒体类型、
source_commit 与配置，再解析；下载失败、摘要不符或产物缺失必须拒绝交接。

两类图的 JSON 格式一致，以下为实际图的内容示例（为简洁仅列最小边集合）：

```json
{
  "contract_version": "1.0.0",
  "trace_id": "e2-example-001",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "configuration_id": "make-debug-linux-v1",
  "produced_by_job_id": "bc-001",
  "graph_type": "ACTUAL",
  "targets": ["build/app"],
  "edges": [
    {"target": "build/app", "dependency": "include/config.h"},
    {"target": "build/app", "dependency": "src/main.c"}
  ]
}
```

声明图将 graph_type 改为 DECLARED，edges 为：

```json
[
  {"target": "build/app", "dependency": "src/main.c"},
  {"target": "build/app", "dependency": "include/unused.h"}
]
```

图字段全部必填；targets/edges 去重；节点为仓库相对 POSIX 路径（目标亦可为 Make 逻辑目标）。
边方向固定为 target 依赖 dependency，构建产物亦可作为依赖节点，传递关系由多条边表示。
实现需先规范化路径、展开声明和追踪关系到同一目标粒度再比较。
本契约下 MISSING 是实际图存在而声明图不存在的边，REDUNDANT 是声明图存在而本次实际图未观察到的边。
REDUNDANT 仅是当前配置、目标与本次运行范围的观察结果，不证明所有平台都可删除该依赖。

FULL_CHECK_REPORT 内容必须有以下字段：

- contract_version、trace_id、source_commit、configuration_id、produced_by_job_id：与请求及 Job 一致。
- configuration：完整复制请求配置，避免消费者仅看到无法解释的配置名称。
- clean / build：各包含 command（请求 argv）、exit_code（成功时 0）和 log_artifact_id。
- actual_graph_artifact_id / declared_graph_artifact_id：指向同一 Job 对应 kind 的图。
- findings：与 Job.findings 完全相同的公共 Finding 数组；无问题时为 `[]`。
- summary：missing_count、redundant_count，分别等于对应 category 的 Finding 数量。

这些字段是报告文件的内容，不向 `additionalProperties: false` 的公共 Job 随意添加字段。
图/报告内部来源字段必须与外部 Artifact 元数据一致；不能只检查外层。

## 5. Finding 与位置证据

每个 Finding 都遵守公共 finding.schema.json。category 仅为 MISSING 或 REDUNDANT，
target、dependency.name 与图中的边对应；location 指向仓库构建声明位置，line/column 从 1 开始。
MISSING 的 location 指向需要补充依赖的目标声明行，不伪造尚不存在的依赖行。
evidence 至少一条非空字符串。本接口约定 `artifact:<artifact_id>#<定位>`：
JSON 使用 RFC 6901 JSON Pointer（例如 `/edges/0`），日志使用 `L10-L30` 的闭区间行号。
消费者先按 artifact_id 找到当前 Job 的产物再解析定位；不存在的 ID、Pointer 或日志行范围拒绝交接。
不存在某条边的证据定位到被比较的完整 edges 数组，不能指向不存在的数组项。

检测到 Finding（即使 severity=ERROR）仍可为 SUCCEEDED 且 error=null。
MDFixer 只能选择 SUCCEEDED 报告中 category=MISSING 的 Finding，并再次确认 commit、配置、
目标声明位置和来源；不得将 REDUNDANT 或 FAILED 的部分结果发送修复。
EChecker 接收本次实际图、完整报告及配置作为同一 baseline，baseline commit 必须等于本次源码 commit。

## 6. 无效输入与执行失败

请求解析/前置校验失败时不创建 Job，返回 `{ "error": <公共 Error> }`：

| HTTP / code | 触发条件 |
|---|---|
| 400 / INVALID_REQUEST | 非法 JSON、缺字段、类型错误、未知字段、短 SHA、越界路径、空命令或非正时限 |
| 422 / UNSUPPORTED_CONTRACT_VERSION | 契约版本不支持 |
| 422 / UNSUPPORTED_BUILD_SYSTEM | 本版不能解析的构建系统 |
| 422 / COMMIT_MISMATCH | 输入镜像或其他来源的 commit 与请求不一致 |
| 422 / CONFIGURATION_MISMATCH | 配置标识不一致 |
| 422 / INVALID_DRAFT_RESULT | 上游没有通过构建与最终验证，或无法确认其成功 |
| 404 / JOB_NOT_FOUND | GET 的 job_id 不存在 |

已接受任务后才发现执行问题，GET 保持 HTTP 200，Job.status=FAILED，error.code 为：
ARTIFACT_UNAVAILABLE、ARTIFACT_INTEGRITY_ERROR、CHECKOUT_FAILED、CLEAN_FAILED、BUILD_FAILED、
BUILD_TIMEOUT、TRACE_FAILED、DECLARED_GRAPH_PARSE_FAILED 或 INTERNAL_ERROR。
error.phase 指明 INPUT/CHECKOUT/CLEAN/BUILD/TRACE/PARSE/PUBLISH，details 可给出 exit_code、
command 和 log_artifact_id（若有日志）。确定性输入/构建错误 retryable=false，只有已确认的临时故障才为 true。
失败样例示范 BUILD_FAILED，findings 为空，仅输出诊断日志；不得声称已生成可用全量报告。

## 7. 验证与配对交接

运行仓库入口 `python3 scripts/validate.py` 检查所有 JSON 及 Schema 引用。
该基础入口尚不检查实例是否满足 Schema，也不执行真实 build；生产方还需用 Draft 2020-12
验证成功/失败 Job 及其内嵌 Artifact/Finding，并核对本节语义。

刘洋的消费方 PR 负责持久化负例及扩展 `scripts/validate.py`。孙鲲华反向 Review 要求：

1. 正常成功样例（含 MISSING、REDUNDANT）通过，且 error=null；执行失败样例满足公共 Schema。
2. finding-commit-mismatch.json 仅修改 Finding 的 commit 后被明确拒绝。
3. finding-configuration-mismatch.json 仅修改 Finding 的配置后被明确拒绝。
4. MDFixer 只选择 MISSING，拒绝 REDUNDANT 和失败 Job；不得靠把正常 Finding 当 error 让测试通过。
5. 检查输入/输出 Artifact、报告内容和图内容的来源一致性及位置证据；基础 JSON 解析成功不能代替上述验证。

生产方 PR 使用 `Related to #3`，消费方最终 PR 使用 `Closes #3`。双方 Review 与 CI 通过后再合并。
