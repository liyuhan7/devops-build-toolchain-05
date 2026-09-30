# C0 实际验证记录

日期：2026-09-30。任务负责人李宇瀚；运行由 Codex 辅助执行，日志的 operator 标签使用负责人姓名，不代表已经完成成员独立复跑。

## 实验环境与输入

运行目录：[20260930T050826Z-5526eb2f](20260930T050826Z-5526eb2f/run.json)。配置 `fzy-c0-options-linux-v1`，源码摘要 `a1620cbc7deeca5a6d1fa1c28f50b600761411b26ebb4e3678c9f26199c58d84`。

C0 提交：`0769e815259ab2cae12a21be43256c05906215e0`。该运行发生在提交前，运行记录中的 experiment_commit 为 null，以源码摘要定位当次输入。

关联任务：[#17](https://github.com/liyuhan7/devops-build-toolchain-05/issues/17)。

环境：Ubuntu 24.04，Linux x86_64，GCC 13.3.0，GNU Make 4.3，Python 3.12.3，Git 2.43.0。基础镜像摘要记录在 Dockerfile；本次构建镜像 ID：`sha256:0c9f2dbab150b926f6ebb44d60abf0601f1fe90e7b12c96db456233011110746`。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 原始 fzy 构建 | 退出码 0，生成可执行文件 | commands.json |
| 原始 fzy 测试 | 32 测试、102 断言，全部通过 | observations.md |
| C0 构建 | 退出码 0，生成可执行文件 | commands.json、run.json |
| C0 上游测试 | 32 测试、102 断言，全部通过 | observations.md |
| 三个无交互功能案例 | apple、banana、无匹配，输出及退出码符合人工预期 | run.json |
| 依赖对照 | gcc -MM 项目依赖与 Make 显式依赖、人工图一致 | run.json |
| 自动依赖控制 | src/options.d 不存在，选定对象的编译参数无 -MD | run.json |
| 仅更新头文件时间戳 | 普通 make 重新编译 src/options.o，之后功能仍正确 | run.json、observations.md |

由于其他对象也读取 options.h，头文件时间戳更新还可能触发它们重编译。这不是 RD 结论，本案例只断言选定对象必须重编译。

## 待完成

- 推送任务分支，创建关联 #17 的 PR，并记录 PR 链接。
- 黄骢驰按 README 独立复跑并 Review。
- GitHub Actions 通过：当前仅完成本地执行，不声称远端检查已经运行。

C1/C2 和四工具的真实输出由后续任务交付。
