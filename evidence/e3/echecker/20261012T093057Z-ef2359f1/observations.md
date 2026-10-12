# C2 实际观察

人工预期：`fixtures/e3/echecker/c2-expected.json`（`TEAM_ORACLE`）。

本记录来源：`ACTUAL_RUN`。

| 检查 | 实际结果 |
|---|---|
| 使用 Linux 环境 | 通过 |
| 重建的 C1 与固定摘要一致 | 通过 |
| C1 加 C2 Patch 与签入的 C2 项目一致 | 通过 |
| C1 功能断言通过 | 通过 |
| C1 版本输出正确 | 通过 |
| C2 的 .c/.h 与 C1 完全一致 | 通过 |
| C2 Makefile 使用新 VERSION | 通过 |
| C1/C2 编译命令发生变化 | 通过 |
| VERSION 编译宏按预期变化 | 通过 |
| C2 编译器实际依赖与 C1 一致 | 通过 |
| C2 Make 声明与 C1 一致 | 通过 |
| C1 的 MISSING 在 C2 保持 unchanged | 通过 |
| 保留 C1 对象时普通 make 未重编译目标 | 通过 |
| 普通 make 保留 C1 版本输出 | 通过 |
| C2 clean build 使用新 VERSION 编译宏 | 通过 |
| C2 clean build 输出新版本 | 通过 |
| C2 clean build 后功能断言通过 | 通过 |

运行状态：PASSED。

失败原因：无。
