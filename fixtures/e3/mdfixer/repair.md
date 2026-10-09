# MDFixer Target 参考修复

来源：`TEAM_ORACLE`。这是人工编写的参考答案，不是 MDFixer 工具输出。

固定报告 `fixed-md.json` 指向 C0 基准提交 `0769e815259ab2cae12a21be43256c05906215e0`，再叠加 `fault.patch`。`src/options.c` 直接包含 `src/e3_mdfixer_marker.h`，并把宏写入 `--version` 输出；`src/options.o` 的 Makefile 规则漏掉这项前置依赖。此案例只判断该对象的项目文件依赖。

`reference.patch` 仅修改 `Makefile` 的 `src/options.o` 规则，在现有 `src/options.c src/options.h config.h` 后加入 `src/e3_mdfixer_marker.h`。它保留对象专用 recipe 的自动依赖控制，不修改源码、其他目标或全局编译参数。

## 验收顺序

1. 在新副本应用故障 Patch，`make CC=gcc`、`make CC=gcc check` 和无交互功能用例通过；`./fzy --version` 包含 `MDFIXER_MARKER=one`。
2. 只改头文件为 `two`，普通 `make CC=gcc` 不重编译 `src/options.o`，版本仍为 `one`，确认修复前漏重建。
3. 在同一副本执行 `git apply --check` 并应用参考 Patch。普通 `make CC=gcc` 重编译该对象，版本变为 `two`；上游测试和功能用例仍通过。
4. 再只改头文件为 `three`，不执行 `clean`，普通 `make CC=gcc` 再次重编译该对象，版本变为 `three`。
5. 人工查看 Makefile 规则，确认缺失边已声明。此项称为人工依赖复核，不能写为工具重检通过。

从仓库根目录运行 `bash scripts/e3/verify_repair.sh --operator 陆泓`。脚本在 `work/e3/<run-id>/` 创建副本，在 `evidence/e3/mdfixer/<run-id>/` 保存 `run.json`、`commands.json`、日志与观察结果。每次使用新目录，不覆盖已有记录。

2026-10-09 WSL2 实际复跑：证据目录为 `evidence/e3/mdfixer/20261009T113517Z-65be5eb1/`，Linux x86_64、WSL2 内核 6.18.40.1。24 项检查全部通过。修复前普通 `make` 保留 `MDFIXER_MARKER=one` 且不重编译；应用参考 Patch 后更新为 `two`；再次不 clean 修改头文件后重新编译并更新为 `three`。上游 `make check`、无交互功能测试和修复后 clean build 均通过。本记录仍是人工依赖复核，不是 MDFixer/EChecker 工具输出；李新昊的独立复跑和 Review 仍待完成。

## 尚未覆盖

Macro、Hybrid、Implicit 声明风格，以及无效候选拒绝与恢复，属于课件附录扩展；当前固定输入只定义 Target 风格。真实 MDFixer 和 EChecker 的输出需在后续阶段另行验证。
