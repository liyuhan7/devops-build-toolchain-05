# EChecker 个人实验决策记录

- 姓名 / 学号：李宇瀚 / 241250029
- 日期 / 关联 Issue / PR：2026-11-17 / Issue 与 PR 待创建 / 源码 `4451f58e20b805647e52638882d402b077b7cddf`
- 对应源码 SHA / 证据路径：`4451f58` / `work/echecker/241250029-20261117-143410/`（镜像标签为补齐作者邮箱前的 `18fea72`，代码树相同）

## 背景与约束

受测项目是 `fixtures/echecker` 的双对象样例：main.o 实际读取 main.c 与 config.h，声明 main.c 与 unused.h；helper.o 只依赖 helper.c。Makefile 使用显式规则和 `CFLAGS = -O0`，头文件都在项目根目录。本轮扩展目标是验证第二个翻译单元的独立头文件依赖，以及头文件内容变化和缺失时复用结论是否仍然可信。

## 选择与替代方案

历史实际图来自本仓库 BuildChecker 的 `full_check`：在镜像内执行 clean 与构建，采集 strace、`make -p` 数据库和两图，再投影到对象目标。该结果与 GCC `-MM` 目标投影逐边核对，任一不一致即失败，不用人工抄写的依赖表。替代方案是只调用 `gcc -MM` 建立基线，但那样得到的是预处理声明而非真实构建读取，无法支撑 E8 的可回查要求。

缓存键由四部分组成：所有 `.c`/`.h` 的预处理指令行、Makefile 中制表符开头的配方行、编译选项、编译器版本。任一变化即保守刷新两个目标；只有 Makefile 声明行变化时配方与指令集合不变，因此复用实际图并仅重算声明图与发现。配置身份不含项目源码内容，所以普通表达式变化（C1 的 `+0`）不影响复用。

替代方案是按目标维护独立缓存键，只刷新受影响目标。该方案能在 C2 这类 main.c 变化时跳过多余的 helper.o 预处理，但需要为每个目标建立文件归属推断，超出课程显式规则的教学范围；当前样例只有两个目标，全量刷新的开销可以接受，且更不容易在归属判断出错时给出错误的复用结论。全量扫描始终作为对照基准保留，个人用例逐字段比较增量与全量结果。

## 代价与覆盖范围

保守刷新使任何头文件变化都会重跑两个目标的预处理，性能上不如按目标增量。覆盖范围限于两个固定翻译单元、根目录头文件、显式规则和三种 CFLAGS；通配符规则、`VPATH`、命令行覆盖变量、多层子目录头文件均会触发 `UNSUPPORTED_DECLARATION` 或 `UNSUPPORTED_FLAGS`，不会静默复用。删除被包含头文件时按键失效触发重新预处理，GCC 失败以 `COMMAND_FAILED` 上抛，不会输出可复用的历史图。

## 验证与实际证据

独立预期先于运行写出：helper.c 增加 `#include "config.h"` 后只新增一条 `MISSING helper.o config.h`；config.h 内部 include 加入再删除后 `added`、`resolved` 方向对称且回到基线；删除 config.h 后扫描失败。

实际命令为 `python3 scripts/echecker/lab.py test --image buildchecker-lab:241250029 --out work/echecker/241250029-20261117-143410/tests`，退出 0，服务 14 项（含个人 3 项）与编排 5 项全部通过。E8 的 `incremental.json` 为 `reused=[main.o, helper.o]`、`refreshed=[]`；E9 的 C1 复用两目标而 Make 仍重编译 main.o，C2 保守刷新并新增 `MISSING main.o extra.h`，C3 复用实际图并解决两条 MISSING。真实 trace、Make 数据库行号与构建日志见个人报告的 3.2、4 节及 `e8/`、`e9/` 证据目录。
