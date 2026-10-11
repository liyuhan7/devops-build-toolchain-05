# C0 人工答案与依据

来源：`TEAM_ORACLE`。本说明是人工核对的预期，不是检测工具的输出。

| 目标 | 必需项目输入 | 依据 |
|---|---|---|
| src/options.o | src/options.c | recipe 编译的源文件 |
| src/options.o | src/options.h | options.c 包含该文件并使用 options_t |
| src/options.o | config.h | options.c 包含 ../config.h，并使用 DEFAULT_* 宏 |
| config.h | src/config.def.h | Makefile 通过 cp 生成 config.h |

在 `src/options.o` 的三条项目文件关系中，实际输入与声明输入一致，预期无 MISSING/REDUNDANT。config.h 的生成关系单独列出，不将它误当作 options.o 的直接编译读取。

人工核验采用源码 include、宏使用、Makefile 的规则和 recipe。实际编译器 `-MM` 输出提供运行对照；它不等同于 Linux 系统调用跟踪，也不是 BuildChecker 的实现。

适用范围排除系统头文件、其他对象文件、工具链内部文件及 Make 自身读文件。更新头文件时间戳的行为测试证明显式依赖能触发重编译；它不证明该头文件所有语义修改都正确。

## C1 新增缺失依赖

来源仍为 `TEAM_ORACLE`。C1 在 `src/options.c` 中直接包含 `e3_c1_marker.h`，并把 `E3_C1_MARKER` 编译进 `--version` 输出，因此编译 `src/options.o` 的项目输入变为：

```text
src/options.c
src/e3_c1_marker.h
src/options.h
config.h
```

`Makefile` 的显式规则保持 C0 状态，只声明 `src/options.c`、`src/options.h` 和 `config.h`。所以 C0 到 C1 的稳定 Finding 身份为：

```json
["MISSING", "src/options.o", "make", "src/e3_c1_marker.h", "build"]
```

它在 C1 中属于 `introduced`，没有 `resolved` 或 `unchanged` Finding。首次源码变化会使 Git 工作树中的对象重新构建，不能据此判断依赖是否完整；只有保留初次构建的 `src/options.o`，随后单独修改新增头文件，普通 make 仍保留旧版本输出，而 clean 构建读到新值，才构成漏重建的行为证据。

本结论不声称真实 EChecker 已运行。`c1-expected.json` 是人工预期，`evidence/e3/echecker/<run-id>/` 是实际构建记录，两者均不得标记为 `TOOL_OUTPUT`。
