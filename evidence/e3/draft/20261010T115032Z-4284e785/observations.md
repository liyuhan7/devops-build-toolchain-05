# DRAFT 容器基线运行观察

来源：ACTUAL_RUN。操作者：刘洋。运行目录：/Users/liuyang/Desktop/DevOps/2/devops-build-toolchain-05/evidence/e3/draft/20261010T115032Z-4284e785。

## 预期

失败候选应在项目构建步骤因缺少 make 或 C 编译器返回非零；参考候选应使用同一 fzy 快照完成构建、测试和功能用例。

## 实际

- 失败构建退出码：1；状态：FAILED。
- 参考构建退出码：1；状态：FAILED。
- 参考容器功能验证退出码：125。
- 镜像摘要见 `reference-inspect.stdout.log` 和 `base-inspect.stdout.log`。
- 完整命令和日志见 `commands.json` 及对应 stdout/stderr 文件。
