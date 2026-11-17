# EChecker 个人实验决策记录

- 姓名 / 学号：孙鲲华 / 241250109
- 日期 / 关联 Issue / PR：2026-11-17 / Issue 未提供 / PR 见个人报告第 6 节
- 对应源码 SHA / 证据路径：`f20fcb2ce6b371c93e0822efab7e39359084a215`；`/root/241250109/a-branch-pr-37/work/echecker/241250109-20261117-151138`

## 背景与约束

受测项目为课程固定双对象样例（main.c、helper.c），根目录头文件、显式 Make 规则与简单变量；需要在不重复全量 strace 的前提下判断依赖图能否复用，并保留可回查的真实证据。历史实际图由本仓库 BuildChecker `full_check` 实采，GCC `-MM` 投影只作独立核对，不用来替代真实基线。

## 选择与替代方案

1. **缓存键**：采用「各 `.c/.h` 的预处理指令 + Makefile 配方 + CFLAGS + GCC 版本」作为配置身份。替代方案是按文件内容哈希；未采用，因为注释与空白变化不应导致失效，而指令变化必须失效，按预处理指令更贴合依赖语义。
2. **失效策略**：键变化时保守刷新两个目标，而不是只刷新声明或内容变化的受影响目标。替代方案是受影响目标刷新；本轮未采用，原因是教学样例只有两个目标，保守策略更容易保证正确性，且与课程参考实现一致。
3. **声明变化**：只改 Makefile 声明时复用历史实际图，仅重算 MD/RD，避免无谓的再次编译跟踪。

## 代价与覆盖范围

保守刷新在 helper.c 未变时也会重新执行 `gcc -MM`，代价是少量重复调用；换来的是不会漏掉跨目标共享头文件引起的失效。当前不支持复杂 Make 规则、非根目录头文件、增量系统调用归并、CFLAGS 白名单外的编译命令；这些输入会明确失败（`UNSUPPORTED_*`），不输出通过结论。

## 验证与实际证据

- 独立预期：main.o 实际 config.h/main.c，声明 main.c/unused.h，MD config.h、RD unused.h；helper.o 两边均为 helper.c。
- 实际结果：参考运行 `gate.json` 为 `passed=true`，`incremental` 的 `reused` 为两目标、`refreshed` 为空；trace `t.28:579` 与 `make-db.txt:1044` 可回查。
- 个人扩展：`config.h` 加入 `#include "extra.h"` 后新增 `MISSING(extra.h)` 并刷新两目标，删除后 `resolved` 恰为该条；与全量扫描的 `actual/declared/findings` 一致。
- 扩展运行重建镜像后 `pytest 13 passed`、`unittest 5 tests OK`，E8/E9 `gate.json` 均为 `passed=true`。
