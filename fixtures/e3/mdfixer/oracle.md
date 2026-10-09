# MDFixer 固定输入人工依据

来源：`TEAM_ORACLE`。本文件描述预期，不是 MDFixer、EChecker 或 BuildChecker 的输出。

## 依赖关系

`src/options.c` 直接包含 `e3_mdfixer_marker.h`，并在版本分支中使用 `MDFIXER_MARKER`。因此编译 `src/options.o` 时，编译器实际读取：

```text
src/options.c
src/options.h
config.h
src/e3_mdfixer_marker.h
```

故障 Patch 中的 `Makefile` 规则只声明：

```make
src/options.o: src/options.c src/options.h config.h
```

所以预期存在一条：

```text
src/options.o -> src/e3_mdfixer_marker.h
```

类别为 `MISSING`，位置为 `Makefile` 中 `src/options.o` 规则，目标为 `src/options.o`。固定报告的 `source_commit` 指向 C0 基准 Commit；故障 Makefile 和新增头文件由 `target/fault.patch` 叠加产生。

## 可观察依据

头文件定义的 `MDFIXER_MARKER` 被编译进 `--version` 输出。初次构建后只更新该头文件：

1. 普通 `make` 不应重编译 `src/options.o`，输出继续显示旧标记；
2. clean 构建会重新编译 `src/options.o`，输出显示新标记。

这一区分证明故障影响增量构建行为，而不是仅凭源码 include 推断。系统头文件、其他对象目标、Make 自身读取和编译器内部文件不在本案例判断范围内。

## 与 MDFixer 接口的关系

该报告是 MDFixer 的固定输入，后续生产请求只能把它作为当前有效的 `introduced + MISSING` 候选，并继续核对 commit、configuration、trace 和 Artifact 来源。报告本身不代表真实 EChecker 已生成该 Finding。
