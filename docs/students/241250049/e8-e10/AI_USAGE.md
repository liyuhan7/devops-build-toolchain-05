# E8-E10 AI 使用记录

工具/模型/日期：OpenAI Codex（模型标识未记录）；2026-11-17。

输入上下文与问题：依据仓库 `AGENTS.md`、README、E8/E9 B 组操作手册和课程模板，在服务器个人分支完成 E8/E9；遵守只在目标目录操作、不提交不推送、保留现有工作区修改、SSH 身份仅用于该仓库 Git 的约束。用户明确允许在仓库外构建 Docker 镜像。

模型建议：先检查分支与差异，按手册在 Docker 中运行 E8/E9，保存唯一 OUT，补做关键断言和回归测试，再记录实际结果与未完成事项。

采纳/拒绝及理由：采纳。由于新版 `classroom_helpers.sh` 未安装到服务器，使用仓库已有 `run_lab.py` 与 `labs/e8e10/lab.py` 运行相同课程入口，并按手册直接补做核验；没有复制外部材料或修改仓库外其他项目文件。

人工修改：个人代码贡献是 `labs/e8e10/test_profile.py` 中 `StudentE8B`、`StudentE9B` 两个测试类（由操作者此前加入，本轮保留）。本次记录的实验代码是仓库课程参考入口；文档由 Codex 根据真实命令、产物和测试结果整理，姓名与校区留待本人填写。Codex 未代替人工审核或确认课程教师验收。

实际验证命令/输入/结果：
- `python3 run_lab.py build`：生成 `course-e8e10:241250049`；镜像 ID `sha256:6b98c960197dae79a03b73df8e79ea30ad054a850b8809dfa46c54ac55d8cc67`。
- `python3 run_lab.py e8 --track B --out work/e8-B-docker-20261117`：退出码 0；E8 手册核验 apply-check、源文件/recipe 保持、过期报告拒绝均通过。
- `python3 run_lab.py e9 --track B --out work/e9-B-docker-20261117`：退出码 0；direct/macro/mixed 检查及 macro 副本应用通过。
- `python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v`：9 tests，全部通过；日志 `work/test_profile-20261117.log`。
- 未执行 E10；未提交、未推送、未创建 PR 或 Issue。