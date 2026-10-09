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
| 故障 Patch | `target/fault.patch` |
| 固定报告 | `fixed-md.json` |

`target/fault.patch` 应从基准 C0 Commit 应用。Patch 不创建 Commit；运行时的样本身份由 `(base_commit, patch_sha256, workspace_digest)` 确定。

## 故障内容

Patch 新增 `src/e3_mdfixer_marker.h`，并让 `src/options.c` 在 `--version` 输出中读取 `MDFIXER_MARKER`。同时，Patch 将 `src/options.o` 的显式依赖保持为 `src/options.c src/options.h config.h`，故意不加入新头文件。

## 复现命令

在 Linux/WSL 的新工作副本中执行：

```sh
git checkout 0769e815259ab2cae12a21be43256c05906215e0
git apply --check --ignore-whitespace fixtures/e3/mdfixer/target/fault.patch
git apply --ignore-whitespace fixtures/e3/mdfixer/target/fault.patch
make CC=gcc
./fzy --version
printf 'MDFIXER_MARKER=two\n' > src/e3_mdfixer_marker.h
touch src/e3_mdfixer_marker.h
make CC=gcc
./fzy --version
make veryclean
make CC=gcc
./fzy --version
```

首次构建的输出应包含 `MDFIXER_MARKER=one`。只修改头文件后，普通 `make` 应保留旧的 `one`，因为 `src/options.o` 未声明该头文件；clean 构建应输出新的 `MDFIXER_MARKER=two`。构建前后应保存命令、退出码、stdout/stderr 和观察结果到新的 `evidence/e3/mdfixer/<run-id>/`。

## 交接边界

本目录只提供固定故障输入和人工 MISSING 报告。参考修复 Patch、修复后的构建/功能/增量验证由陆泓的 E3-05 第二个 PR 完成。
