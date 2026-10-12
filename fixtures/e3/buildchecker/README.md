# fzy BuildChecker MD/RD 基线

本样本基于固定 fzy 的 C0 基准提交 `0769e815259ab2cae12a21be43256c05906215e0`，上游提交 `34b88869d022e861da4846c4463aea3ddfb3ff30`，配置 `fzy-c0-options-linux-v1`。故障注入只作用于 `src/options.o`，Patch 为 `md-rd.patch`。

## 重建与运行

在 Linux/WSL，从仓库根目录执行：

```sh
bash scripts/e3/reproduce_a.sh --operator 你的姓名
```

入口调用 `scripts/e3/reproduce_a.py`，要求 Linux、gcc、GNU Make、Git 和 Python 3。每次创建唯一 `work/e3/buildchecker/<run-id>`，从固定上游快照与 `echecker/c0.patch` 重建 C0，核对上游与 C0 源码摘要，再检查并应用 `md-rd.patch`。C1/C2 实验目录不作为本样本输入。

运行包含 clean build、32 项项目测试、精确标准输出断言、MD 普通增量与 clean 对照、RD 普通增量。真实命令、工作目录、时间、退出码、stdout/stderr 和输入摘要保存到 `evidence/e3/buildchecker/<run-id>/`；状态为 `PASSED` 时退出码为 0，失败时为非零。`--output <新目录>` 可指定证据路径，已有目录会被拒绝。脚本不修改受版本控制的样本。

## 预期

人工答案见 `expected.json` 与 `oracle.md`，来源为 `TEAM_ORACLE`。初始版本输出 `E3_MD_MARKER=one`；MD 只改 `src/e3_md_marker.h`，普通 make 保持旧输出且 `src/options.o` mtime 不变，clean make 输出新值；RD 只改 `src/e3_rd_unused.h`，普通 make 重建 `src/options.o` 但输出不变。脚本结果是 `ACTUAL_RUN`，不声称真实 BuildChecker 或 EChecker 已运行。

Linux 文件跟踪为可选附录，判据以 Make 时间戳、版本输出与功能日志为准。运行记录见 [E3 汇总](../../../evidence/e3/summary.md)。

证据目录可用 `scripts/e3/pack_evidence.py` 合并日志。命令的 stdout/stderr 按字节索引读取，退出码与对象时间戳保存在 `commands.json`、`packed-evidence.json` 中。读取方法见 [E3 汇总](../../../evidence/e3/summary.md)。
