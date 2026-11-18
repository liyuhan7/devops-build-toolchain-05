# 决策记录

背景与约束：本次完成 MDfixer B 组 E8/E9。输入是当前样例提交对应的固定报告；实验范围是报告身份检查、声明风格识别、候选 Patch 生成和副本应用。教学解析器只覆盖简单显式规则和变量赋值。E10 的构建、测试、回滚及动态重检未执行。

选择与替代方案：保留 `work/` 中的原始样例项目，把 Patch 作为候选产物。E8 先核对报告 commit 与项目 HEAD，再只对 MISSING 生成 direct 补丁；旧报告必须以 `STALE_REPORT` 拒绝。E9 根据目标依赖声明选择修改位置：direct 改目标依赖行，macro 改 `DEPS` 定义，mixed 保留 `$(HEADERS)` 并改目标行。每种补丁先运行 `git apply --check`；实际应用只在独立副本中进行。未选择直接改写所有输入文件或把候选写回原始样例，因为这样会混淆补丁生成和补丁验证，并破坏原始证据。

A：不适用，本次未执行 A 组历史缓存路线。

B：共享变量若被其他目标引用，修改变量定义可能扩大影响范围；当前实现未对跨目标引用作完整影响分析。E8/E9 仅证明本样例中的候选位置和应用行为，不证明复杂 Make 语法或所有共享变量情形安全。失败保护通过旧报告拒绝、未知目标拒绝、`git apply --check` 和源字节保持测试核对；正式接受条件留待 E10 验证。

代价与覆盖范围：原始输入保持可追溯，但 E8/E9 本身不建立构建正确性结论。变量展开仅适用于教学子集；隐式规则、复杂表达式及跨目标副作用需要额外建模。E10 未执行，因此当前候选不能视为已通过质量门。

验证命令与实际证据：

- `python3 run_lab.py e8 --track B --out work/e8-B-manual.20261118-154335`，随后验证固定报告 commit、精确 MD/RD、direct 计划、Patch `--check`、旧报告拒绝和原文件不变。证据：`work/e8-B-manual.20261118-154335/verification.json`、`expected-failure.json`、`steps/manual-verification.log`。
- `python3 run_lab.py e9 --track B --out work/e9-B-manual.20261118-154344`，随后验证三种风格计划与 Patch `--check`，并在 `apply-demo` 副本应用 macro Patch。证据：`work/e9-B-manual.20261118-154344/verification.json`、`apply-demo/`。
- `docker run ... python3 -m unittest discover -s labs/e8e10 -p 'test_*.py'`：11 项通过，退出码 0；日志位于两个 OUT 的 `steps/tests.log`。
- `git diff --check`：通过。
