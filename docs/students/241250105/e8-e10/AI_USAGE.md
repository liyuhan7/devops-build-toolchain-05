# AI使用记录

工具/模型/日期：Codex（GPT-6）/ 2026-11-17。

输入上下文与问题：用户要求在学号 241250105 的个人分支中完成 E8、E9 实验并推送。参考材料为 `DevOps_E8_E10` 中的 Group-B E8、E9 操作手册、实验包和报告模板。

模型建议：按课程手册运行 Group-B 路线，保留固定报告、三种 Makefile 声明风格、候选 Patch、补丁应用检查和源文件不变证据；补充一条 macro 风格个人测试。

采纳/拒绝及理由：采纳手册定义的实验步骤和验收点。用户授权提交并推送个人分支；未代建 PR。实验包未在 `main`，因此仅导入到个人分支供本次实验使用。

人工修改：用户提供服务器地址、学号、个人项目目录，并指出所属项目目录为 Group-B；本轮个人测试、报告和验证由 Codex 执行。姓名和校区未知，报告中明确标注未提供。

实际验证命令/输入/结果：构建 `course-e8e10:241250105` 镜像成功；合并目标分支测试后容器内执行 `python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v`，9 项通过；分别运行 `python3 run_lab.py e8 --track B ...` 和 `python3 run_lab.py e9 --track B ...`，均成功。E8 旧报告被 `STALE_REPORT` 拒绝，候选补丁 apply-check 通过且源 Makefile 不变；E9 direct/macro/mixed 三份补丁 apply-check 通过，macro 补丁在副本应用成功。

参考实现和个人贡献边界：`labs/e8e10/lab.py` 来自课程实验包；个人贡献为 `labs/e8e10/test_profile.py` 中的 E9 B 组 macro Patch 独立测试，以及本目录中的实验记录。未调用外部模型服务。

## 2026-11-18 MDFixer 集成维护

操作者：学号 241250105 的个人仓库；本节记录组长维护实验基线，与此前个人 E8/E9 实验记录分开。

人工决策：用户明确 B 组负责 MDFixer，并纠正了最初以 A 组 BuildChecker 为主线的方案。BuildChecker 仅用于修复后的依赖重检。

AI 参与：Codex 将课程实验中的 MDFixer 补丁与隔离验证迁入 services/mdfixer/，将阶段编排和测试迁入 scripts/e8e10/、tests/e8e10/，改用 MDFixer 专用镜像与 B 轨道 CI；原实验包目录及空父目录从工作树移除。代码与文档由 AI 编辑，用户已明确要求提交并推送，人工审查状态未记录。

验证：服务镜像构建成功；容器入口的 11 项 E8-E10 测试通过，B 轨道 E8/E9/E10 运行成功；全仓 109 项测试在仓库提供的依赖路径下通过；E10 的接受与回滚证据分别确认成功修复和失败时输入保持不变。Issue 与 PR 编号未提供，不作推测。
