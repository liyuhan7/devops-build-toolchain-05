# DRAFT 构建与功能验证实际记录

本目录分别保留功能运行与容器运行记录。容器记录见 [20261012T082607Z-7f60c3b9](20261012T082607Z-7f60c3b9/run.json)，功能详情见该目录 `functional/`。整体环境、复现入口与验收范围见 [E3 汇总](../summary.md)。

来源：`ACTUAL_RUN`，运行由 CodeBuddy 辅助执行；operator 标签与 AI 辅助范围见 `run.json` 与 [AI_USAGE.md](../../../AI_USAGE.md)。

## 运行与输入

运行目录：[20261009T051451Z-4f7f3891](20261009T051451Z-4f7f3891/run.json)。配置 `fzy-upstream-linux-v1`，上游快照 `34b88869d022e861da4846c4463aea3ddfb3ff30`。

人工预期：[fixtures/e3/draft/cases.json](../../../fixtures/e3/draft/cases.json)（`TEAM_ORACLE`）。本记录来源 `ACTUAL_RUN`。该运行发生在提交前，`run.json` 的 `experiment_commit` 为 null，以源码快照与上游 SHA 定位当次输入。

环境：WSL2 Ubuntu 24.04.3 LTS，Linux 5.15.167.4-microsoft-standard-WSL2，x86_64，gcc 13.3.0，GNU Make 4.3，Git 2.43.0，Python 3.12.3。该记录不使用容器。

## 结果

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 使用 Linux 环境 | 通过 | run.json |
| `make CC=gcc` 构建 | 退出码 0，生成可执行 `fzy` | build.stdout.log、run.json |
| `make CC=gcc check` | 退出码 0，32 测试、102 断言，Pass: 32 / fail: 0 / skip: 0 | validation.stdout.log、run.json |
| 版本标记 | 退出码 0，输出包含 `1.1` | version.stdout.log |
| `match-apple` | 输出 `apple`，退出码 0 | functional-match-apple.stdout.log |
| `match-banana` | 输出 `banana`，退出码 0 | functional-match-banana.stdout.log |
| `no-match-empty` | 输出为空，退出码 0 | functional-no-match-empty.stdout.log |
| `multi-match-sorted` | 输出 `apple`、`application`，退出码 0 | functional-multi-match-sorted.stdout.log |
| `invalid-lines-usage` | 退出码 1，错误输出包含 `Invalid format for --lines: 1` | functional-invalid-lines-usage.stderr.log |
| 用例清单与人工预期一致 | 通过 | run.json |

共 21 项检查全部通过，12 条命令记录见 `commands.json`。

## 反向自检

为确认验证脚本能发现失败而不是恒为通过，另做一次自检：临时把 `cases/match-apple/expected_stdout` 改为 `wrong`，脚本判定 `STATUS=FAILED`，失败项为「用例 match-apple 标准输出符合人工预期」；随后恢复原文件并复跑，结果为 `STATUS=PASSED`。该自检只在临时目录生成证据，未提交到仓库。

复现方式（证据写入 `/tmp`，不影响仓库）：

```sh
cp fixtures/e3/draft/cases/match-apple/expected_stdout /tmp/backup
printf 'wrong\n' > fixtures/e3/draft/cases/match-apple/expected_stdout
bash scripts/e3/verify_fzy.sh --operator 你的姓名 --output /tmp/e3-negative/negative-run
cp /tmp/backup fixtures/e3/draft/cases/match-apple/expected_stdout
```

## 边界

- `make acceptance` 需要 Ruby 与 Bundler，本机未安装，未运行，也不作为成功条件。
- 本记录未使用 Docker，容器样本见 [20261012T082607Z-7f60c3b9](20261012T082607Z-7f60c3b9/run.json)。
- 本记录为作者采集的一次运行，不是独立复跑。

## 复跑记录

复跑：[20261009T061915Z-d1e0ac8e](20261009T061915Z-d1e0ac8e/run.json)，输入提交 `29dc66256ec12cdfd72f2fb06d7338c707319f59`。使用同一固定上游快照，在 WSL Linux 中构建并执行全部功能用例，21 项检查通过、12 条命令已记录；记录由 Codex 辅助执行。

E2 契约检查（29 JSON / 4 Schema）、18 项回归测试、C0 材料检查均通过。另在检查副本确认相对输出目录可用、已有证据目录和缺少参数值被拒绝，改错 match-apple 的预期 stdout 会准确判 FAILED，随后恢复原预期。
