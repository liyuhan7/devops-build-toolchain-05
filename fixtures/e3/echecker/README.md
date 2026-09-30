# EChecker C0 基线

## 输入和配置

上游与源码摘要见 `../projects.json`。当前实验源码位于 `project/`，配置 ID 为 `fzy-c0-options-linux-v1`，构建入口 `make CC=gcc`、已有测试入口 `make CC=gcc check`。保留上游 VERSION=1.1、CPPFLAGS 和 CFLAGS；仅选定对象的 recipe 从 CFLAGS 中过滤 `-MD -MMD -MP`。

限定对象目标为 `src/options.o`，项目文件范围为源码、`src/options.h`、`config.h`。`config.h` 由 `src/config.def.h` 复制生成。系统头文件不在人工 Finding 集合中。

## C0 的正确性判据

1. `gcc -MM src/options.c` 得到的项目文件集合，经路径规范化后等于人工图。
2. `make -pn src/options.o` 的显式前置依赖等于该集合。
3. 构建、上游测试和三条无交互功能断言通过。
4. 仅更新 `src/options.h` 时间戳，普通 make 重新编译 `src/options.o`，功能仍正确。
5. 选定对象没有 `src/options.d`，其依赖不由自动文件补全。

运行入口为仓库根目录的 `python3 scripts/e3/run_c0.py --operator 姓名`。环境和容器命令见 [公共说明](../README.md)。每次运行使用新副本，保持人工答案与实际观察分离。

## 三种版本

`commits.json` 记录上游 SHA 和实验版本映射。C0 提交为 `0769e815259ab2cae12a21be43256c05906215e0`；C1、C2 由后续任务制作。

后续 C1 新增头文件时，应选择能影响无交互输出的使用位置，并遗漏对应目标依赖。C2 可以改变 VERSION 编译宏，在保留 C1 对象文件时比较普通构建和 clean 构建的版本输出；需记录真实编译命令和配置变化。
