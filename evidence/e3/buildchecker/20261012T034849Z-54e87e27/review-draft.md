# MD/RD 独立复跑记录

来源：`ACTUAL_RUN`。本记录由非作者在独立环境执行，结果与 `TEAM_ORACLE` 预期对照。

## 输入身份

| 项目 | 值 |
|---|---|
| 上游 fzy Commit | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| C0 基准 Commit | `0769e815259ab2cae12a21be43256c05906215e0` |
| 配置 | `fzy-c0-options-linux-v1` |
| 目标 | `src/options.o` |
| 故障 Patch | `fixtures/e3/buildchecker/md-rd.patch` |
| 运行 ID | `20261012T034849Z-54e87e27` |

## 运行环境

- WSL2 Linux，`x86_64`，内核 `6.6.87.2-microsoft-standard-WSL2`。
- GCC `11.4.0`。
- GNU Make `4.3`。
- Git `2.34.1`。
- Python `3.10.12`。

运行时从提交内容导出临时 Linux 副本，避免 Windows 工作区的 CRLF 行尾影响 Bash 解析；临时副本不修改固定样本，生成的证据复制回本目录。

## 实际结果

1. Patch 检查和应用成功，初始 clean、build 与功能断言退出码均为 `0`；输入 `apple` 得到 `apple`。
2. MD：只修改被读取但未在 `src/options.o` 前置依赖中声明的 `src/e3_md_marker.h`。普通 `make` 后 `src/options.o` 的 mtime 保持 `1791776929906821041`，版本仍包含 `E3_MD_MARKER=one`；clean build 后版本变为 `E3_MD_MARKER=two`。
3. RD：只修改被显式声明但未被选定对象读取的 `src/e3_rd_unused.h`。普通 `make` 后 `src/options.o` 的 mtime 从 `1791776932784720969` 增加到 `1791776934345594608`，说明发生额外重编译；版本输出仍包含 `E3_MD_MARKER=two`。
4. 本次脚本记录的全部命令退出码均为 `0`，结果与 `TEAM_ORACLE` 中一条 `MISSING`、一条 `REDUNDANT` 的预期一致。

## 边界

- 结论来自人工样本与构建行为对照，不代表真实 BuildChecker 已产生 Finding。
- 已复核 Make 时间戳、版本输出与功能行为；未采集 `strace`，Linux 文件跟踪属可选附录。
- 同一运行目录的 `run.json` 与命令日志为原始记录，本文件只作结论摘要。
