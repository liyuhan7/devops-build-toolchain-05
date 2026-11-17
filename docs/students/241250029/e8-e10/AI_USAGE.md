# E8—E9 个人 AI 使用记录

- 姓名 / 学号：李宇瀚 / 241250029
- 工具 / 模型 / 日期：GitHub Copilot / DeepSeek-V4.1-Flash (Go) / 2026-11-17
- 关联 Issue / PR / 源码 SHA：Issue 与 PR 待创建 / `4451f58e20b805647e52638882d402b077b7cddf`（镜像标签为补齐邮箱前的 `18fea72`，代码树相同）

## 输入上下文与问题

本次请求是完成 A 组 E8—E9 个人部分。提供的上下文包括 `AGENTS.md`、`docs/guides/A组EChecker实验.md`、`services/echecker/echecker/core.py`、`services/echecker/tests/test_core.py`、`scripts/echecker/scenarios.py`、`scripts/echecker/lab.py` 和样例目录。需要解决的具体问题是：在不改动公共增量算法的前提下，补充公共回归未覆盖的独立用例，并按指南完成环境自检、镜像构建、E8/E9 运行和个人文档。

## 模型建议

1. 阅读代码后归纳出复用判定：缓存键由预处理指令、配方行、编译选项和编译器版本组成；声明变化只重算发现。
2. 建议新增三项目标级用例：helper.o 独立头文件依赖、头文件内部 include 增删可逆、被包含头文件删除时的失败边界。
3. 建议先提交个人测试再构建镜像，使镜像标签中的源码 SHA 与 dirty 状态对应交付提交，避免把旧镜像结果归给新代码。
4. 建议个人文档只填写真实证据，GitHub Issue、PR、Actions 与合并记录在未创建时写待补充，不预填编号。

## 采纳、拒绝及理由

采纳：三项用例均实现并运行通过；镜像在个人提交后重建，`source_commit` 与 `image_source_commit` 同为 `18fea72`、`dirty=false`；该提交随后仅补齐作者邮箱，代码树不变，交付提交为 `4451f58`；文档中的编号与链接保持待补充。

拒绝：模型曾建议用硬编码列表之外的排序函数统一断言顺序，实际直接按 `compare_graphs` 的既有顺序书写期望值，减少不必要的辅助逻辑；未采纳按目标拆分缓存键的实现改动，原因是它超出课程教学范围且会影响他人正在使用的公共算法，本轮只以测试验证现有保守刷新行为。

## 本人决策、修改与人工核对

课程参考实现为 `services/echecker/echecker/core.py` 与 `scripts/echecker/scenarios.py`，由公共导入提供；AI 生成的是个人测试文件与三份文档初稿；本人确认了用例的独立预期、执行了全部命令并逐项核对输出。公共算法、样例和既有测试未改动。Issue/PR 创建、提交推送、Review 与合并均由本人执行，AI 未代发任何 GitHub 消息。

## 实际验证

| 命令 / 输入版本 | 独立预期 | 实际结果 / 退出码 | 证据路径 |
|---|---|---|---|
| `python3 scripts/echecker/lab.py doctor --out work/echecker/241250029-20261117-143410/doctor` | 必需环境满足，problems 为空 | 退出 0，仅内存/磁盘建议提示 | `.../doctor/doctor/stdout.log`、`.../doctor/env.json` |
| `python3 scripts/echecker/lab.py build --image buildchecker-lab:241250029 --out work/echecker/241250029-build-20261117-143355` | 镜像含当前提交，BuildChecker 服务测试通过 | 退出 0，48 passed，标签 dirty=false | `.../build-20261117-143355/build/`、`image/`、`unit-tests/` |
| `python3 scripts/echecker/lab.py test --image buildchecker-lab:241250029 --out .../tests` | 服务与编排测试通过，含个人 3 项 | 退出 0；14 passed、编排 5 项 OK | `.../tests/runner/stdout.log` |
| `python3 scripts/echecker/lab.py e8 ... --out .../e8` | MD config.h、RD unused.h；两目标复用 | 退出 0；gate passed=true；reused 两个、refreshed 空 | `.../e8/evidence/result/` |
| `python3 scripts/echecker/lab.py e9 ... --out .../e9` | C1 复用、C2 新增 extra.h、C3 解决两条 MD | 退出 0；gate passed=true；C0—C3 SHA 与报告一致 | `.../e9/evidence/result/` |
| `git -C .../e9/evidence/result/project bundle verify .../sample-history.bundle` | 完整历史可校验 | `The bundle records a complete history.` | `.../e9/evidence/result/sample-history.bundle` |

未调用模型的部分：环境自检、镜像构建、E8/E9 执行与 bundle 校验均为本地实际运行，不是模型生成的说明。AI 生成的报告文字不作为人工 Review 记录。
