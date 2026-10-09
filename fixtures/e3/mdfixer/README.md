# MDFixer 固定 MISSING 输入

本案例基于固定 fzy C0 实验版本，目标是复现 `src/options.o` 漏声明项目头文件导致的增量漏重建。报告来源为 `TEAM_ORACLE`，不是 MDFixer 或 EChecker 的实际输出。

## 固定身份

| 字段 | 值 |
|---|---|
| 上游项目 | `jhawthorn/fzy` |
| 上游 Commit | `34b88869d022e861da4846c4463aea3ddfb3ff30` |
| 基准 C0 Commit | `0769e815259ab2cae12a21be43256c05906215e0` |
| configuration | `fzy-c0-options-linux-v1` |
| 目标 | `src/options.o` |
| 声明文件 | `Makefile` |
| 故障 Patch | `fault.patch` |
| 固定报告 | `fixed-md.json` |
| Target 参考 Patch | `reference.patch` |

`fault.patch` 应从基准 C0 Commit 对应的 `fixtures/e3/echecker/project/` 应用。Patch 不创建 Commit；运行时的样本身份由 `(base_commit, patch_sha256, workspace_digest)` 确定。两份 Patch 固定为 LF 行尾。

## 故障内容

Patch 新增 `src/e3_mdfixer_marker.h`，并让 `src/options.c` 在 `--version` 输出中读取 `MDFIXER_MARKER`。同时，Patch 将 `src/options.o` 的显式依赖保持为 `src/options.c src/options.h config.h`，故意不加入新头文件。

## 复现命令

在 Linux/WSL 的仓库根目录执行；脚本自动创建独立副本和新的证据目录：

```sh
bash scripts/e3/verify_repair.sh --operator 陆泓
```

首次构建的输出应包含 `MDFIXER_MARKER=one`。只修改头文件后，普通 `make` 应保留旧的 `one`，因为 `src/options.o` 未声明该头文件。应用参考 Patch 后，普通 `make` 应重编译并输出 `two`；再次只修改头文件后，普通 `make` 应重编译并输出 `three`。脚本记录命令、退出码、stdout/stderr 和检查结果到新的 `evidence/e3/mdfixer/<run-id>/`。补丁位置和人工依据见 [修复说明](repair.md)。

旧运行记录 `evidence/e3/mdfixer/20261009T02/` 对应的故障 Patch 未随当时提交入库，记录中的摘要 `1f9c120a...` 只作为历史观察保留。本次重建的 `fault.patch` 摘要已写入 `fixed-md.json`；不能把旧运行记录当成本次重建补丁的复跑证据。

## 交接边界

固定 MISSING 报告来源为 `TEAM_ORACLE`；复跑脚本产生的记录来源为 `ACTUAL_RUN`。本次 WSL2 复跑证据见 `evidence/e3/mdfixer/20261009T113517Z-65be5eb1/`，24 项检查全部通过。本案例只做人工依赖复核，不声称 MDFixer 或 EChecker 已实际输出修复或重检报告。
