# 决策记录

## 背景与约束

本次执行 Group-B 的 E8/E9 MDfixer 路线。主仓库当前 `main` 尚未包含课程 E8-E10 实验入口，因此在个人分支导入课程提供的实验包，以便按手册运行。实验输入限定为两个 C 翻译单元、项目内头文件及简单显式 Make 规则。

## 选择与替代方案

E8 使用样例当前提交生成固定 MD 报告，并要求报告 commit 与项目 HEAD 一致后才生成候选。候选只补充 MISSING，不自动删除 RD。旧报告以 `STALE_REPORT` 拒绝。

E9 按声明形式选择修改位置：direct 修改目标依赖行；macro 修改变量定义并保留目标引用；mixed 保留变量引用并在目标行添加缺失依赖。补丁先在独立副本验证。

## 代价与覆盖范围

当前实现仅处理手册约定的显式 Make 规则和有限变量展开。共享变量被多个目标复用时，修改变量定义可能影响其他目标；复杂隐式规则及目标间声明图分析不在本次范围。E9 补丁应用检查不替代 E10 的构建、程序测试和动态重检。

## 验证命令与实际证据

- 镜像：`python3 run_lab.py build`，结果保存在 `work/environment-build-241250105.log`。
- 单测：`docker run ... python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v`，8 项通过。
- E8：`python3 run_lab.py e8 --track B --out work/e8-B-241250105-680951d6c21cec48d9648579e8180e8a0de41194`，入口通过；补充证据 `work/e8-B-241250105-680951d6c21cec48d9648579e8180e8a0de41194/verification.json`。
- E9：`python3 run_lab.py e9 --track B --out work/e9-B-241250105-680951d6c21cec48d9648579e8180e8a0de41194`，入口通过；三份 Patch 检查及 macro 副本应用记录于该 OUT 的 `verification.json`。
