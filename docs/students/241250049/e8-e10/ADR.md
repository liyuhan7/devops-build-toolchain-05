# E8-E10 决策记录

背景与约束：B 组 E8/E9 使用固定 MD 报告和受限 Make 样例，候选补丁不得在生成阶段改写源项目。E8 需验证报告与项目提交身份；E9 比较 direct、macro、mixed 三种声明形式。运行证据存于仓库忽略的 `work/`，不能据此宣称 E10 已验收。

选择与替代方案：保留课程入口 `labs/e8e10/lab.py` 的参考策略，并为个人贡献添加回归测试；E8 生成候选后仅用 `git apply --check` 验证上下文，不落盘。另以故意篡改 commit 的报告验证 `STALE_REPORT` 拒绝。E9 分别检查补丁目标，再将 macro 补丁应用到独立副本，以保护输入项目。

B 组共享变量处理：纯 macro 形式把新增依赖写入变量定义，保留目标对变量的引用；mixed 形式保留 `$(HEADERS)` 并只改目标行。验证没有证明任意共享变量均无跨目标影响，需对使用点和影响范围增加分析后才能扩展支持。

失败怎样保证原目录不变：E8 只执行 apply-check，且检查源 Git 工作树干净和 recipe 字节保持；E9 三个原始样例均只执行 apply-check，实际应用只发生在 `apply-demo` 副本。旧报告拒绝路径前后不修改 Makefile。该保护范围针对本次样例及断言，不替代 E10 沙箱构建和回滚验证。

代价与覆盖范围：不在 E8/E9 直接应用候选，牺牲了这两步对构建成功的证明；保留源输入以便追溯。E10 手册负责后续构建、测试、增量重检与拒绝回滚验证。

验证命令与实际证据：
- `python3 run_lab.py e8 --track B --out work/e8-B-docker-20261117`，证据：`work/e8-B-docker-20261117/`。
- `python3 run_lab.py e9 --track B --out work/e9-B-docker-20261117`，证据：`work/e9-B-docker-20261117/`。
- `python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v`，9 项通过；日志：`work/test_profile-20261117.log`。