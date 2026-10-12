# E3-02 MD/RD 独立复跑审核记录（草稿）

状态：`DRAFT_PENDING_HUMAN_CONFIRMATION`

本文件由 Codex 根据实际 WSL2 复跑结果起草，供黄骢驰核对和修改。复跑命令已经真实执行，但当前操作者字段保留“Codex 辅助执行，待本人确认”，不能在黄骢驰核对前作为其本人独立复跑声明。

## 输入身份

| 项目 | 值 |
|---|---|
| 上游 fzy Commit | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| C0 基准 Commit | `0769e815259ab2cae12a21be43256c05906215e0` |
| PR #25 分支提交 | `6c4037b45db41f793228d909220f3296a180563beb8` |
| 配置 | `fzy-c0-options-linux-v1` |
| 目标 | `src/options.o` |
| 故障 Patch | `fixtures/e3/buildchecker/md-rd.patch` |
| 运行 ID | `20261012T034849Z-54e87e27` |
| 证据来源 | `ACTUAL_RUN` |

## 运行环境

- WSL2 Linux，`x86_64`，内核 `6.6.87.2-microsoft-standard-WSL2`。
- GCC `11.4.0`。
- GNU Make `4.3`。
- Git `2.34.1`。
- Python `3.10.12`。

运行时从提交内容导出临时 Linux 副本，避免 Windows 工作区的 CRLF 行尾影响 Bash 解析。临时副本不修改固定样本；生成的证据复制回本目录。

## 实际结果

1. Patch 检查和应用成功，初始 clean、build 和功能断言退出码均为 `0`；输入 `apple` 得到 `apple`。
2. MD：只修改实际被读取、但未在 `src/options.o` 前置依赖中声明的 `src/e3_md_marker.h`。普通 `make` 后，`src/options.o` 的 mtime 保持 `1791776929906821041`，版本仍包含 `E3_MD_MARKER=one`；clean build 后版本变为 `E3_MD_MARKER=two`。
3. RD：只修改被显式声明、但未被选定对象读取的 `src/e3_rd_unused.h`。普通 `make` 后，`src/options.o` 的 mtime 从 `1791776932784720969` 增加到 `1791776934345594608`，说明发生额外重编译；版本输出仍包含 `E3_MD_MARKER=two`。
4. 本次脚本记录的全部命令退出码均为 `0`，运行结果与 `TEAM_ORACLE` 中一条 `MISSING` 和一条 `REDUNDANT` 的预期一致。

## 结论边界

- 本次结论来自人工样本与构建行为对照，不代表真实 BuildChecker 已产生 Finding。
- 本次完成 Make 时间戳、版本输出和功能行为复核；未采集 `strace`，Linux 文件跟踪仍属于可选附录。
- PR #25 尚未合入 `main`。第二个 PR 应在 #25 合并后，以最新 `main` 为基础，只提交独立复跑证据和必要说明。

## 人工确认项

- [ ] 黄骢驰核对 `run.json` 中的操作者说明。
- [ ] 黄骢驰核对命令、退出码、mtime 和版本输出。
- [ ] 黄骢驰确认上述结论与本人审核意见一致。
- [ ] 确认后将状态改为 `CONFIRMED`，并按实际情况修改操作者说明。
- [ ] 在第二个 PR 中填写实际 PR 链接、Review 链接和最终验证结果。
