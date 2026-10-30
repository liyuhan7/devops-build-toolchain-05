# A 组论文复现、核心检测与验证

在仓库根目录执行以下命令。每人使用自己的克隆和 Git 本地学号；代码或测试变化后重新构建镜像，每次运行使用新的输出目录。

## 环境和镜像

在本组 Ubuntu 服务器、仓库根目录运行。宿主机需要现有 Git、Python、Make 和 Docker，gcc、strace 在服务镜像内。入口复用 `scripts/doctor.py` 的 A 组环境检查，不修改宿主服务或配置。Windows Docker Desktop 的 Linux 引擎也能执行 build、e5、e6、gate；doctor 检查课程 Linux 服务器环境。

```sh
python3 scripts/buildchecker/lab.py doctor --out work/buildchecker/doctor-01
python3 scripts/buildchecker/lab.py build --out work/buildchecker/build-01 --build-timeout 1200
```

默认镜像为 `buildchecker-lab:学号`，学号读取本仓库 `git config --local user.name` 的 6—16 位数字；`--image` 可指定其他镜像。构建保存日志、镜像详情、工具链和服务测试。基础镜像来源可用 `build --base-image` 覆盖，服务范围见 [BuildChecker 说明](../../services/buildchecker/README.md)。

每次运行保存 `source-commit.txt`、`worktree-status.txt`、`invocation.json` 和实际镜像 ID。报告分别记录镜像中的源码版本与报告提交版本；正式复跑使用成员确认的固定代码版本。

## E5：原始构建与人工结论

```sh
python3 scripts/buildchecker/lab.py e5 --out work/buildchecker/e5-01
echo "E5_EXIT_CODE=$?"
cat work/buildchecker/e5-01/evidence/program-output.txt
grep -n '^main.o:' work/buildchecker/e5-01/evidence/make-db.txt
grep -n 'config.h' work/buildchecker/e5-01/evidence/trace/t.*
```

预期退出 0，程序输出 `1`。镜像内 `/repo/fixtures/md-rd` 复制到本次 evidence 后，执行 clean、strace 跟踪和 `make -p app`。原始样例不修改。

| 目标 | 实际依赖 | 声明依赖 | 人工结论 |
|---|---|---|---|
| main.o | main.c、config.h | main.c、unused.h | MD：config.h；RD：unused.h |
| app | main.o | main.o | 一致 |

报告需引用本次 config.h 成功打开的 trace 行，通过 cc 与 cc1/as 的父子关系解释读取和 main.o 写出如何归到同一编译任务，填写实际 PID、文件与行号，并说明与论文跟踪实现的差异。

## E6：自动检测、修复副本与复检

分别执行并记录退出码，修复前命令返回 1 后仍需继续下一条：

```sh
python3 scripts/buildchecker/lab.py e6 --out work/buildchecker/e6-before
echo "BEFORE_EXIT_CODE=$?"
python3 scripts/buildchecker/lab.py e6 --fixed --out work/buildchecker/e6-after
echo "AFTER_EXIT_CODE=$?"
python3 scripts/buildchecker/verify_evidence.py \
  --before work/buildchecker/e6-before/evidence/findings.json \
  --after work/buildchecker/e6-after/evidence/findings.json
```

修复前 `status=SUCCEEDED`，clean/build 均为 0，精确两条发现；由于启用 `--fail-on-findings`，CLI 返回 1。修复后 findings 为空、CLI 返回 0；校验 `passed=true`、`changed_inputs=["Makefile"]`。

阅读 `actual-graph.json`、`declared-graph.json`、`processes.json`，由每条发现回查 `trace/` 和 `make-db.txt`。`input_sha256` 保存输入内容；校验脚本只比较保存的报告，不代替重新构建或独立重放原始跟踪。

`--timeout` 是 clean/build 共用的总执行预算，默认 120 秒。修复只改本次副本的 Makefile，输入哈希用于核对实际差异；该副本不冒充一个新的源码 commit 或 EChecker 正式基线。

## 公共 Job、Finding 和 Artifact 交接

公共入口使用成功 DRAFT 结果生成现有契约的 Job。E5/E6 教学样例可独立运行，保留自己的教学报告和原始证据。

正式交接在 Linux Docker 宿主机执行，前置材料为：

- 符合现有契约的成功 DRAFT Job，trace、commit、配置与检测请求一致。
- 四类已下载载荷：`environment-manifest.json`、`image-manifest.json`、`build.log`、`validation.log`。入口核验摘要、大小、媒体类型，以及构建和最终程序验证的成功结论。
- manifest 对应的 OCI 镜像已在本机准备好。入口核对 RepoDigests 后按 image ID 运行；本地 image ID 与 OCI manifest digest 分别记录，镜像不自动拉取。
- 本地 Git 仓库包含请求的完整 commit，origin 对应请求 URL。入口导出该 commit 并核对采集输入哈希。

运行容器挂载检测器代码、固定源码副本、请求和本次证据目录。上游镜像需提供 Python3、GNU Make、strace 及编译工具，A 组检测器代码由入口注入。仅安装 `build-essential` 的环境还需核对 Python3 和 strace。

公共教学入口支持自包含工作目录、默认 Makefile 和 `build_command=["make", *targets]`；编译变量写入 `configuration.environment`，不推测 `-C`、`-f` 或外部目录的语义。准备好本人真实交接文件后执行：

```sh
python3 -m pip install --require-hashes -r requirements-contracts.lock
python3 scripts/buildchecker/contract.py run \
  --request work/handoff/buildchecker-request.json \
  --draft-job work/handoff/draft-job.json \
  --draft-files work/handoff/draft-files \
  --repository . \
  --out work/buildchecker/handoff-01
python3 scripts/buildchecker/contract.py verify \
  --request work/handoff/buildchecker-request.json \
  --job work/buildchecker/handoff-01/public/job.json
```

公共成功输出为实际图、声明图、完整报告和合并日志。Finding 引用两图及原始记录对应的日志行，位置指向 Makefile；只有已确定的位置才填写行号。路径使用仓库相对路径，依赖使用 `ecosystem=make/name/scope=build`，`configuration_digest` 等于 `configuration_id`。

`public/job.json` 在产物字节和证据位置校验通过后生成。正常发现为 `SUCCEEDED/error=null`；执行失败输出 `FAILED`、具体 Error 和诊断日志。`verify` 返回 0 表示产物校验通过，执行结果以 Job.status 为准。

本地输出使用同机 `file:` URI；跨机器交接需发布产物并更新 URI。入口提供本地契约适配，REST 和远程发布未实现，真实 B→A 联调需另有上游运行记录。

## E7：重复和故障验证

先运行不需要 Docker 的门禁判定与入口回归，再执行真实完整场景。宿主回归需安装根 README 中的锁定 Schema 依赖，也可在已构建镜像内执行相同的 unittest 命令：

```sh
python3 -m unittest discover -s tests/buildchecker_lab -v
python3 scripts/buildchecker/lab.py gate --out work/buildchecker/e7-01
echo "E7_GATE_EXIT_CODE=$?"
cat work/buildchecker/e7-01/gate/gate-result.json
cat work/buildchecker/e7-01/gate/results.csv
```

| 场景 | 预期 |
|---|---|
| unit-tests | 当前 A 组全部服务测试通过 |
| original-1/2/3 | 三次 SUCCEEDED/1，精确相同的两条依赖错误，有证据锚点 |
| fixed | SUCCEEDED/0，无发现 |
| build-failed | 删除头文件后编译失败，FAILED/1、CHECK_FAILED |
| unsupported | 作业写出多个最终输出，FAILED/1、UNSUPPORTED，构建本身成功 |
| timeout | 构建预算 1 秒，TIMED_OUT/1、TIMEOUT |

完整门禁共 8 行，只有全部场景符合各自预期才整体退出 0。各子目录保存完整命令、标准输出、错误输出和退出码。单个故障报告 FAILED 与场景通过不矛盾。

每位成员提交至少一项本人测试或有明确理由的实现改动，说明输入、预期和实际结果，并注明参考来源。修改后重建镜像，用新目录复跑受影响实验及完整门禁。

## 报告与交付

使用 [A 组报告模板](../templates/buildchecker-report.md)。正式报告按团队约定放入仓库，个人原始证据在 `work/buildchecker/` 单独备份，排除凭据、本地配置和编译产物。报告引用本人的实际运行结果。

`.github/workflows/buildchecker-lab.yml` 构建镜像、运行测试及八场景门禁，验证错误预期的拒绝结果，并上传 `work/buildchecker/ci-*` 证据。检查名为 `buildchecker-lab`，使用课程保护配置前需与实际检查名对齐；当前工作流未接入源码、Git 历史和镜像扫描。远程 CI、分支保护、失败 PR 拦截与修复合并需保存实际运行记录。

每人交付报告、E5 原始证据、E6 修复前后报告与图、E7 门禁结果、个人贡献及复现命令。公共交接按实际执行情况记录。小样例的验收范围与 fzy 全量检测、3—5 个论文项目提高任务分别记录。
