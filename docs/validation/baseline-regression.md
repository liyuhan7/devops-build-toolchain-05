# 基线脚本回归验证

在 Linux 中执行：

```sh
python3 -m unittest discover -s tests -v
```

契约校验依赖按根目录锁文件安装。现有 CI 的测试发现入口会自动执行这些测试；Windows 会跳过需要 Linux 编译工具的部分，跳过不代表验证通过。

| 测试文件 | 验证内容 |
|---|---|
| `tests/test_behavior_runners.py` | 实际运行两个版本复跑入口；注入构建失败、超时、错误输出、缺产物和损坏依赖输出，要求非零退出并保存明确失败原因；参考补丁通过，不能应用、构建失败、测试失败、缺失边未修复的候选均被拒绝 |
| `tests/test_behavior_functional.py` | 构建与功能均正确才成功；构建成功但功能错误、缺二进制、stdout/stderr 不符及超时均失败；用例预期的非零退出码仍可通过外层检查 |
| `tests/test_baseline_states.py` | 健康、仅漏声明、仅冗余声明、混合缺陷；同一编译配置下的 introduced、unchanged、resolved、无变化；两个目标共享头文件时保留两条目标边 |
| `tests/test_bounded_command.py` | 正常退出、非零退出、命令不存在、超时输出保留，以及 POSIX 子进程组终止 |

测试复制固定源码与补丁到临时目录。真实编译和 Make 行为与命令输出故障注入分开断言；拒绝候选后必须恢复源码摘要，并重新构建、执行上游测试和功能用例。恢复失败会单独记录，不能把候选失败改写成成功。

两个独立入口支持 `--command-timeout <正整数秒>`，默认每条命令 600 秒：

```sh
bash scripts/e3/verify_fzy.sh --operator 姓名 --command-timeout 600
python3 scripts/e3/verify_repair.py --operator 姓名 --command-timeout 600
```

超时记录退出码 124、`timed_out` 和部分 stdout/stderr。Bash 使用 GNU coreutils 的 `timeout`，TERM 后最多等待 2 秒再终止；修复入口在 Linux 上终止整个命令进程组。修复候选只允许修改 Makefile，失败后恢复的对象是本次运行的独立副本。

依赖与增量结果是针对固定样本的人工判据。依赖复核失败测试使用未补齐声明的候选，不等于已运行真实检测器。此处不验证真实 BuildChecker、EChecker、DRAFT 或 MDFixer 实现，也不改变编译参数变化样本的配置身份与接口预期。
