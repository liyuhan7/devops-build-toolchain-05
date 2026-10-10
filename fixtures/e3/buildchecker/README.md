# fzy BuildChecker MD/RD 基线

本案例来自 E3-01 固定 fzy C0，基准提交 `0769e815259ab2cae12a21be43256c05906215e0`，上游提交 `34b88869d022e861da4846c4463aea3ddfb3ff30`，配置 `fzy-c0-options-linux-v1`。故障注入只作用于 `src/options.o`，Patch 为 `md-rd.patch`。

## 重建与运行

在 Linux/WSL，从仓库根目录执行：

```sh
bash scripts/e3/reproduce_a.sh --operator 孙鲲华
```

脚本每次创建唯一 `work/e3/buildchecker/<run-id>`，复制 `fixtures/e3/echecker/project`，应用 Patch，执行 clean build、无交互 `--version`/`-e` 功能断言、MD 普通增量和 clean 对照、RD 普通增量，并将真实命令、环境、退出码和 stdout/stderr 保存到 `evidence/e3/buildchecker/<run-id>/`。它不会修改受版本控制的样本。

## 预期

人工答案见 `expected.json` 与 `oracle.md`，来源为 `TEAM_ORACLE`。初始版本输出 `E3_MD_MARKER=one`；MD 只改 `src/e3_md_marker.h`，普通 make 保持旧输出且 `src/options.o` mtime 不变，clean make 输出新值；RD 只改 `src/e3_rd_unused.h`，普通 make 重建 `src/options.o` 但输出不变。脚本结果是 `ACTUAL_RUN`，不声称真实 BuildChecker 或 EChecker 已运行。

Linux 文件跟踪属于后续独立复跑 PR 的附录；本 PR 保留可重复的 Make 时间戳和功能日志。
