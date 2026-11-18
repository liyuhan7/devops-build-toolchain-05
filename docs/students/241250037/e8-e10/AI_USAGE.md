# AI 使用记录

工具/模型/日期：Codex coding agent（本会话未显示具体模型 ID）/ 2026-11-18。

输入上下文与问题：用户要求阅读本机 E8/E9 实验手册，在服务器个人仓库完成实验，并明确不提交、不推送。提供了服务器登录信息。执行前阅读 E8 B、E9 B、公共准备、提交与排错手册及报告模板；根据 `feat/MDfixer-lab` 起点确定使用 MDfixer B 组路线。

模型建议：构建学号对应实验镜像；运行 E8 B、E9 B 官方入口；检查报告 commit、Patch 计划、补丁可应用性及源文件保持；完成手册中的个人扩展测试；将实际结果记录到 OUT 和个人文档。

采纳/拒绝及理由：采纳 B 组路线、官方 `run_lab.py` 阶段入口和容器内验证。服务器缺少手册所用的 `classroom_helpers.sh` 解压目录，因此使用仓库中的官方阶段入口，并补充等价的容器内断言和验证日志。未执行 E10、提交、推送、PR 或 Actions。

人工修改：本轮由 Codex 编写两项新增测试及本目录三份文档。没有记录到学生本人对这些代码或文档进行手工改写；提交前应由学生审阅并按本人实际理解修订。

实际验证命令/输入/结果：构建 `course-e8e10:241250037` 成功；运行 `python3 run_lab.py e8 --track B --out work/e8-B-manual.20261118-154335` 和 `python3 run_lab.py e9 --track B --out work/e9-B-manual.20261118-154344` 成功。E8 核验精确 MISSING/REDUNDANT、报告身份、旧报告拒绝和源文件保持；E9 核验 direct/macro/mixed 三种计划、三份 `git apply --check` 和 macro 副本应用。`python3 -m unittest discover -s labs/e8e10 -p 'test_*.py'` 共 11 项通过；`git diff --check` 通过。实验 JSON、Patch、验证记录和日志保存在对应 `work/` OUT 中。

参考实现和自己的贡献边界：`labs/e8e10/lab.py` 与原有测试来自仓库现有 E8/E9 教学实现。本轮新增的两个测试由 Codex 撰写，尚未提交；报告与 ADR 也是本轮依据实际命令和证据生成。没有把 AI 生成内容标记为学生本人手写成果。
