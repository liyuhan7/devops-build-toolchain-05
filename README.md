# devops-build-toolchain-05

2026 DevOps 课程教学实验 05 组项目仓库。仓库定义构建工具链的公共数据契约与四段接口，提供固定 fzy 版本的可复现测试基线，并接入 A 组 BuildChecker 教学检测器及 E5—E7 本地实验入口。

## 工具链

四个工具按顺序交接构建、检测与修复职责：

```text
DRAFT          生成可构建、可验证的构建环境
  |
  v
BuildChecker   全量检测，产出 MISSING / REDUNDANT 依赖 Finding
  |
  v
EChecker       比较基线、变更与当前配置，计算依赖图增量
  |
  v
MDFixer        对已验证的 MISSING Finding 生成修复并重新检查
```

四个工具通过异步 Job、Artifact、Finding 和 Error 结构交接。契约位于 [`contracts/`](contracts/)，接口说明位于 [`docs/interfaces/`](docs/interfaces/)。

## 仓库结构

| 路径 | 内容 |
|---|---|
| [`contracts/`](contracts/) | 公共 Schema，各工具的请求、响应与失败样例，以及 [`negative/`](contracts/negative/) 负例 |
| [`docs/interfaces/`](docs/interfaces/) | DRAFT、BuildChecker、EChecker、MDFixer 接口说明 |
| [`docs/validation/`](docs/validation/) | 相邻工具之间的交接验证说明 |
| [`docs/adr/`](docs/adr/) | 接口与基线范围的设计决策 |
| [`fixtures/e3/`](fixtures/e3/) | 测试基线：固定上游版本、故障与变更样本、人工预期 |
| [`evidence/`](evidence/) | 端到端串联记录与实际运行证据 |
| [`scripts/`](scripts/) | 契约校验、基线复跑与证据整理脚本 |
| [`tests/`](tests/) | 契约语义与基线推导的回归测试 |
| [`services/buildchecker/`](services/buildchecker/) | A 组教学依赖检测器、环境冒烟和服务测试 |
| [`scripts/buildchecker/`](scripts/buildchecker/) | A 组原始采集、检测、修复复检和完整场景验证 |
| `work/` | 脚本生成的运行副本，不纳入版本控制 |

## 契约与数据模型

[`contracts/common/`](contracts/common/) 定义跨工具复用的四个结构：

- [`job.schema.json`](contracts/common/job.schema.json)：异步 Job 的状态流转与终态字段；
- [`artifact.schema.json`](contracts/common/artifact.schema.json)：交接产物载荷；
- [`finding.schema.json`](contracts/common/finding.schema.json)：依赖问题 Finding；
- [`error.schema.json`](contracts/common/error.schema.json)：失败结果。

各工具目录保存请求、成功与失败样例，[`contracts/negative/`](contracts/negative/) 保存应当被拒绝的负例。公共 Schema 禁止在根对象扩展字段，工具专属结果通过 Artifact 交接。

## 测试基线

[`fixtures/e3/`](fixtures/e3/) 固定上游 [jhawthorn/fzy](https://github.com/jhawthorn/fzy) 提交 `34b88869d022e861da4846c4463aea3ddfb3ff30`，并准备以下样本：

| 样本 | 关注点 |
|---|---|
| C0 | 选定目标 `src/options.o` 的项目依赖声明完整，且不由自动 `.d` 文件补全 |
| C1 | 新增头文件被读取但未声明，产生一条 introduced MISSING |
| C2 | 源码保持 C1 不变，只修改编译参数，C1 的 Finding 保持 unchanged |
| MD/RD | 同一目标的漏声明与冗余声明，含普通增量与 clean 构建的行为对照 |
| DRAFT | 构建与无终端交互功能验证用例，含可定位的容器构建失败与参考成功环境 |
| MDFixer | 固定 MISSING 报告、参考补丁，以及修复前后的增量验证 |

样本的版本映射、Patch 和人工预期位于 `fixtures/e3/<tool>/`，实际运行记录位于 `evidence/e3/<tool>/<run-id>/`。

材料按来源标签区分：`TEAM_ORACLE` 为人工编写的预期答案，`ACTUAL_RUN` 为脚本产生的实际记录，`TOOL_OUTPUT` 保留给工具真实运行后的输出。

## 环境要求

- 契约校验与回归测试：Python 3.12（CI 固定版本），先执行 `python -m pip install --require-hashes -r requirements-contracts.lock` 安装锁定的 Schema 校验依赖；基线材料检查仍使用标准库；
- 行为复跑：Linux 或 WSL，需要 gcc、GNU Make 与 Git；也可使用固定基础镜像的 Docker 容器。

## 本地校验

```sh
python scripts/validate.py                  # JSON 契约、Schema 元数据与本地 $ref
python -m unittest discover -s tests -v     # 契约语义与基线推导回归测试
python scripts/e3/check_baselines.py        # 基线材料、版本映射与文档链接
```

Linux 环境执行 C0 构建与行为验证：

```sh
python3 scripts/e3/run_c0.py --operator <姓名>
```

其余样本的复跑入口见 [基线项目说明](fixtures/e3/README.md) 与各工具目录的 README。

## A 组 BuildChecker 实验

操作命令、预期结果和交付要求见 [A 组论文复现实验](docs/guides/A组论文复现实验.md)，服务实现与支持范围见 [BuildChecker 说明](services/buildchecker/README.md)。运行副本和个人证据保存在 `work/buildchecker/`，报告使用 [A 组报告模板](docs/templates/buildchecker-report.md)。

## 持续集成

各工作流验证范围如下。远程运行、分支保护和成员审核需另有实际记录。

| 工作流 | 触发 | 内容 |
|---|---|---|
| [`contract-validation.yml`](.github/workflows/contract-validation.yml) | Pull Request、推送到 `main` | 契约校验与回归测试 |
| [`e3-baseline.yml`](.github/workflows/e3-baseline.yml) | Pull Request、推送到 `main` | 基线材料检查，在固定镜像中运行 C0 行为验证并上传证据 |
| [`buildchecker-lab.yml`](.github/workflows/buildchecker-lab.yml) | Pull Request、推送到 `main`、手动 | A 组镜像、服务测试、8 场景门禁、错误预期拦截及实验产物上传 |

## 协作约定

任务从 Issue 开始，经任务分支、Commit、Pull Request、Review 到合并，使用 `Backlog / Ready / In progress / In review / Done` 跟踪状态；提交信息遵循 Conventional Commits。具体要求见 [CONTRIBUTING.md](CONTRIBUTING.md)，Issue 与 PR 模板位于 [`.github/`](.github/)。

## 文档索引

| 文档 | 说明 |
|---|---|
| [`docs/interfaces/`](docs/interfaces/) | 四段接口契约 |
| [`docs/validation/`](docs/validation/) | 跨工具交接验证 |
| [`docs/adr/`](docs/adr/) | 设计决策记录 |
| [`fixtures/e3/README.md`](fixtures/e3/README.md) | 基线项目、固定版本与复跑方式 |
| [`evidence/e2/validation-summary.md`](evidence/e2/validation-summary.md) | 契约检查与回归测试结果 |
| [`evidence/e3/summary.md`](evidence/e3/summary.md) | 基线运行结果与证据索引 |
| [`docs/backlog/`](docs/backlog/)、[`docs/guides/`](docs/guides/) | 阶段计划、任务分工与交接说明 |
| [`evidence/e3/open-items.md`](evidence/e3/open-items.md) | 基线未覆盖内容与失败记录 |
| [`AI_USAGE.md`](AI_USAGE.md) | AI 参与与人工决策记录 |
