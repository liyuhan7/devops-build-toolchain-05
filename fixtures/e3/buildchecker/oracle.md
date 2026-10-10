# BuildChecker MD/RD 人工依据（TEAM_ORACLE）

案例固定在 E3-01 的 C0 提交 `0769e815259ab2cae12a21be43256c05906215e0`、配置 `fzy-c0-options-linux-v1` 和限定目标 `src/options.o`。Patch 同时注入两个独立的受控边：

- `src/e3_md_marker.h` 是 `src/options.c` 的真实项目头文件，`--version` 读取宏 `E3_MD_MARKER`，但 C0 的显式 `src/options.o` 规则没有列出它。因此只改头文件后普通 `make` 不重编译，旧对象继续输出 `E3_MD_MARKER=one`，这是 `MISSING`。
- `src/e3_rd_unused.h` 被显式列在 `src/options.o` 规则中，但不被任何编译单元包含或读取。只改它后普通 `make` 会额外重编译 `src/options.o`，行为输出保持不变，这是 `REDUNDANT`。

判断范围排除系统头文件、其他对象目标、Make 自身读取和编译器内部文件。`make clean` 后的结果只证明干净构建正确；MD 判定必须来自保留旧对象的普通增量构建。原始 C0 与 Patch 分开保存，实际运行记录标记为 `ACTUAL_RUN`，不能把人工答案写成工具输出。
