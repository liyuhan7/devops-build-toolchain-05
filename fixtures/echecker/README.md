# EChecker 双对象教学样例

由 `DevOps_E8_E10` 2026-10-31 版 A 组样例适配，供 `scripts/echecker/scenarios.py` 复制到本人的 `work/` 后使用。原始目录保持只读，受测副本建立自己的 Git 历史。

main.o 实际读取 main.c/config.h，声明 main.c/unused.h，因此初始预期为 MD config.h、RD unused.h。helper.o 只依赖 helper.c；程序初始输出 1。

E9 的 C1 增加普通表达式 `+0`，C2 新增 extra.h 包含，C3 补齐 config.h/extra.h 声明。编号属于本教学样例，与 `fixtures/e3/echecker` 的 fzy 版本映射分开使用。
