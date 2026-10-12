# E3 运行结果与证据索引

本目录保存测试基线的实际运行记录，来源标签 `ACTUAL_RUN`。人工预期与判断依据位于 [fixtures/e3/](../../fixtures/e3/README.md)，两者分开保存。记录由复跑脚本与容器产生，不代表四个工具的实际输出。

## 结果

| 样本 | 结论 | 运行记录 | 预期与依据 |
|---|---|---|---|
| C0 | 构建、上游测试、功能与头文件重编译对照通过 | [5526eb2f](c0/20260930T050826Z-5526eb2f/run.json)、[cd642e81](c0/20260930T082248Z-cd642e81/run.json) | [expected.json](../../fixtures/e3/echecker/expected.json)、[oracle.md](../../fixtures/e3/echecker/oracle.md) |
| C1 | 一条 introduced MISSING，13 项检查通过 | [40c9382e](echecker/20261011T025224Z-40c9382e/run.json) | [c1-expected.json](../../fixtures/e3/echecker/c1-expected.json) |
| C2 | 17 项检查通过；保留 C1 对象的普通构建输出 `1.1`，clean 构建输出 `1.2-e3` | [28ba342e](echecker/20261012T082148Z-28ba342e/run.json)、[ef2359f1](echecker/20261012T093057Z-ef2359f1/run.json) | [c2-expected.json](../../fixtures/e3/echecker/c2-expected.json) |
| MD/RD | 12 项检查通过；MD 漏重建，RD 额外编译而输出不变 | [54e87e27](buildchecker/20261012T034849Z-54e87e27/run.json)、[446359ec](buildchecker/20261012T083915Z-446359ec/run.json) | [expected.json](../../fixtures/e3/buildchecker/expected.json)、[oracle.md](../../fixtures/e3/buildchecker/oracle.md) |
| DRAFT | 预期工具缺失的构建失败正确；参考环境构建与 21 项功能检查通过 | [7f60c3b9](draft/20261012T082607Z-7f60c3b9/run.json)、[functional](draft/20261012T082607Z-7f60c3b9/functional/run.json) | [cases.json](../../fixtures/e3/draft/cases.json) |
| MDFixer | 24 项检查通过；增量结果依次为 `two`、`three` | [65be5eb1](mdfixer/20261009T113517Z-65be5eb1/run.json) | [fixed-md.json](../../fixtures/e3/mdfixer/fixed-md.json)、[repair.md](../../fixtures/e3/mdfixer/repair.md) |

各样本目录列出该样本的全部运行记录，含失败记录与提交前记录。

## 独立复跑

| 样本 | 复跑环境 | 结果 | 记录 |
|---|---|---|---|
| C0 | WSL2 Ubuntu 22.04 | 18 条命令退出码均为 0，11 项行为检查通过 | [cd642e81](c0/20260930T082248Z-cd642e81/run.json) |
| C1 | 非作者环境 | 13 项检查通过 | [40c9382e](echecker/20261011T025224Z-40c9382e/run.json) |
| C2 | 从合并提交导出 LF 副本，固定输入与镜像，容器网络关闭 | 17 项检查通过 | [ef2359f1](echecker/20261012T093057Z-ef2359f1/run.json) |
| MD/RD | WSL2，GCC 11.4.0 | 命令退出码均为 0，与预期的一条 MISSING、一条 REDUNDANT 一致 | [复跑记录](buildchecker/20261012T034849Z-54e87e27/review-draft.md) |

## 环境、命令与日志

C2 独立复跑使用固定 C2 输入与已有 Linux amd64 镜像，容器网络关闭；镜像 ID、入口与源码摘要见该记录 `run.json.execution`，工具版本与完整命令见 `commands.json` 与 `commands.log`。

```sh
python3 scripts/e3/run_c2.py --operator <姓名> --revision d9e9c80ea27510a71db1a6425585604c83ce0306
```

Windows 采集 DRAFT 容器样本：

```powershell
python scripts/e3/run_draft_container.py --operator <姓名>
```

证据共 28 个文件、4 份合并日志。`commands.json` 保留命令、时间、退出码与输出字节索引，`packed-evidence.json` 保留日志摘要与辅助文本。C2 的完整 Make 数据库只提交目标依赖规则，索引标记 `EXCERPT`，并记录全文摘要、长度与节选位置；其他输出完整保留，空输出长度为 0。

```powershell
python scripts/e3/pack_evidence.py --directory evidence/e3/echecker/20261012T093057Z-ef2359f1 --read c2-clean-version
```

未标注提交的运行以源码摘要定位输入。运行路径是证据身份的一部分，索引分类不改变原始记录。
