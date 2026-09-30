# E3 项目基线入口

本阶段使用 fzy 准备四工具的可重复测试基线。当前已准备 C0；MD/RD、C1/C2、DRAFT 故障和 MDFixer 修复由后续成员分别完成。

## 固定版本

- 上游：<https://github.com/jhawthorn/fzy>。
- Commit：`34b88869d022e861da4846c4463aea3ddfb3ff30`。
- 未改动源码快照：`fixtures/e3/fzy/`，包含原始 MIT 许可证及随源码分发的第三方许可证。
- C0 实验副本：`fixtures/e3/echecker/project/`，只改变 Makefile；差异见 `echecker/c0.patch`。
- 归档与源码摘要见 [projects.json](projects.json)。源码摘要按 POSIX 相对路径排序、LF 行尾规范化计算。
- libco 为后续集成候选，版本、论文对应关系和 Dockerfile 状态尚未核验，不属于本次实验运行。

## 原始项目与 C0

原始 fzy 可用 `make CC=gcc` 构建，`make CC=gcc check` 执行已有测试；`printf 'apple\nbanana\n' | ./fzy -e apple` 提供无终端交互的功能用例。

C0 限定 `src/options.o` 的项目依赖正确性。它显式依赖 `src/options.c`、`src/options.h`、`config.h`，该对象不生成或加载 `.d`。其他对象沿用上游自动依赖机制。因此不宣称整个 fzy 项目不存在 MD/RD。

## 从仓库根目录复跑

材料检查可在 Windows 或 Linux 执行：

```sh
python scripts/e3/check_baselines.py
```

Linux 已具备 gcc、libc 开发头文件、GNU Make、Python 3 和 Git 时：

```sh
python3 scripts/e3/run_c0.py --operator 你的姓名
```

Windows PowerShell 使用隔离 Linux 容器：

```powershell
docker build -t devops-e3-c0:ubuntu24.04 -f scripts/e3/Dockerfile.baseline scripts/e3
docker run --rm --network none --workdir /repo --mount "type=bind,src=$((Get-Location).Path),dst=/repo" -e E3_ENVIRONMENT_REFERENCE=devops-e3-c0:ubuntu24.04 devops-e3-c0:ubuntu24.04 python3 scripts/e3/run_c0.py --operator LiYuhan
```

脚本每次创建新的 `work/e3/<run-id>/` 副本和 `evidence/e3/c0/<run-id>/` 证据，输出 `EVIDENCE_DIR` 与 `STATUS`。它不修改受版本控制的源文件、不提交或推送 Git。

每个证据目录包含环境与命令日志、退出码和 `run.json` 中的断言。人工预期保存在 `echecker/expected.json`，来源 `TEAM_ORACLE`；运行记录来源 `ACTUAL_RUN`。本阶段未运行真实 BuildChecker 或 EChecker。

## C0 提交后

源码当前尚未由用户提交，因此 `echecker/commits.json` 的 C0 SHA 为 null。用户完成包含 C0 文件的提交后，将其完整 SHA 回填为 `commit_sha`，状态改为 `COMMITTED`，另作证据提交。不要把第二个证据提交的 SHA 冒充初始 C0，也不要为了回填 SHA 修改 C0 源码。

复跑已提交版本时，可增加 `--revision <当前实际检出的完整SHA>`，该参数是运行版本标签，脚本不验证工作区是否干净；操作者应核对 checkout 和 diff，源码摘要用于补充核验。PR 的合并 SHA 与 C0 SHA 分别记录。

C0/C1/C2 的真实历史必须保留，建议这几个 PR 使用普通 merge，并保留基线分支。后续 C1 在 C0 副本中新增头文件及可观察使用；C2 在同一个样本源码树内只改变编译参数。代码与 Makefile 的改造必须另存预期和实际记录。
