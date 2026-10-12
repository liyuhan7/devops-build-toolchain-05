# EChecker C0/C1/C2 基线

## 输入和配置

上游与源码摘要见 `../projects.json`。当前实验源码位于 `project/`，已经演进到 C2；配置 ID 为 `fzy-c2-options-version-1.2-e3-linux-v1`，构建入口 `make CC=gcc`、已有测试入口 `make CC=gcc check`。C2 只把 VERSION 从 `1.1` 改为 `1.2-e3`；仅选定对象的 recipe 从 CFLAGS 中过滤 `-MD -MMD -MP`。

限定对象目标为 `src/options.o`，项目文件范围为源码、`src/options.h`、`config.h`。`config.h` 由 `src/config.def.h` 复制生成。系统头文件不在人工 Finding 集合中。

## C0 的正确性判据

1. `gcc -MM src/options.c` 得到的项目文件集合，经路径规范化后等于人工图。
2. `make -pn src/options.o` 的显式前置依赖等于该集合。
3. 构建、上游测试和三条无交互功能断言通过。
4. 仅更新 `src/options.h` 时间戳，普通 make 重新编译 `src/options.o`，功能仍正确。
5. 选定对象没有 `src/options.d`，其依赖不由自动文件补全。

运行入口为仓库根目录的 `python3 scripts/e3/run_c0.py --operator 姓名`。环境和容器命令见 [公共说明](../README.md)。每次运行使用新副本，保持人工答案与实际观察分离。

## C1 新增 include

C1 提交为 `563f9c5b797aff1174f726f029e67cd352400a24`。它新增 `src/e3_c1_marker.h`，由 `src/options.c` 直接包含并用于 `--version` 输出；`Makefile` 的 `src/options.o` 规则仍只声明 C0 的三个项目输入。因此人工预期为一条 `introduced MISSING`：

```text
src/options.o -> src/e3_c1_marker.h
```

`c1.patch` 可以从 C0 重建 C1，`c1-expected.json` 保存 `TEAM_ORACLE`，实际行为由以下命令在 Linux 独立副本中验证：

```sh
python3 scripts/e3/run_c1.py --operator 管泽昊
```

脚本初次构建后只把头文件标记从 `one` 改为 `two`。普通 make 应保持对象文件和旧版本输出，clean 构建才得到 `two`；构建、上游测试和无交互功能断言均须通过。每次运行写入新的 `evidence/e3/echecker/<run-id>/`，并标记为 `ACTUAL_RUN`。

管泽昊的 Linux 成功复跑为 `evidence/e3/echecker/20261011T025224Z-40c9382e/`。两次前置失败记录 `20261011T024942Z-26215586/` 和 `20261011T025143Z-87b105b8/` 也予以保留，分别证明复跑脚本曾检出 CRLF 补丁兼容问题和缺少生成态 `config.h`；它们不能代替成功记录。

## C2 仅改变编译命令

C2 保持 C1 的全部 `.c/.h` 内容和依赖声明，只通过 `c2.patch` 把 Makefile 的 VERSION 从 `1.1` 改为 `1.2-e3`。因此 C1 的 `MISSING` Finding 在 C2 中属于 `unchanged`，命令变化本身不产生新的 MD。

复跑脚本先在 C1 构建对象，再把同一副本推进到 C2，并在不清理 C1 对象的前提下运行普通 make；另在同源码副本执行 C2 clean build：

```sh
python3 scripts/e3/run_c2.py --operator 黄骢驰
```

创建只包含 C2 配置变化的真实提交后，最终复跑增加 `--revision <完整C2-SHA>`；提交前不传该参数时，证据状态为 `PASSED_PRECOMMIT`。

普通 make 预期保留旧对象及版本 `1.1`，clean build 预期得到 `1.2-e3`。两者均保留 `E3_C1_MARKER=one`，功能和上游测试必须通过。该差异说明 GNU Make 不会仅因 recipe 展开值变化自动失效目标，后续工具需要把编译命令作为配置输入重新分析。

## 三种版本

`commits.json` 记录上游 SHA 和实验版本映射。C0 提交为 `0769e815259ab2cae12a21be43256c05906215e0`，C1 提交为 `563f9c5b797aff1174f726f029e67cd352400a24`，C2 提交为 `d9e9c80ea27510a71db1a6425585604c83ce0306`。
