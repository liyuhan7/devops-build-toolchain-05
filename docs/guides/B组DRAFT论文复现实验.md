# B 组 DRAFT E5 论文复现实验

本指南只覆盖 E5：复现固定 Dockerfile 的真实构建失败，根据日志生成两份提示，保存两份模型原始回复与候选，并记录选择依据。候选构建、镜像运行和 `hello E3` 校验属于 E6，不在本阶段宣称通过。

## 1. 前置与边界

- 在 Ubuntu 课程服务器、本人的 `feat/draft-lab` 克隆中执行。
- 宿主机需能使用 Docker；基础镜像必须固定完整摘要。
- 每次运行使用新的 `work/draft/e5/` 目录，失败记录不覆盖。
- `work/` 保持 Git 忽略，正式报告进入 `docs/reports/<学号>/`。
- 关联 Issue、PR 和人工审核按实际情况填写。

先确认分支、工作区和工具：

```sh
git status --short --branch
git diff --name-only --diff-filter=U
docker version
python3 --version
```

## 2. 运行 E5

把姓名与学号替换为实际操作者：

```sh
python3 scripts/draft/e5.py \
  --student-id 你的学号 \
  --name 你的姓名 \
  --build-timeout 600
```

预期脚本自身退出 0，但 `invocation.json` 中 `build_exit_code` 非零，`classification=MISSING_MAKE`。`iter-01/build-combined.log` 必须包含 `make: not found`；网络超时、外层超时和基础镜像拉取失败不能算复现成功。

运行目录同时保存输入副本、SHA-256、源码提交、工作区状态、完整命令、标准输出、标准错误、退出码、错误定位和两份提示。

## 3. 取得并记录候选

分别将以下文件全文发送给同一模型，并原样保存回复：

```text
iter-01/prompt-error-driven.txt
iter-01/prompt-context-driven.txt
```

模型回复必须保留固定 `FROM` 摘要、`WORKDIR`、`COPY`、`RUN make` 和 `CMD`，并安装构建依赖。不要把 Markdown 围栏内的候选手工改写后冒充原始回复。

将两份原始回复保存在 `work/` 后执行：

```sh
python3 scripts/draft/record_candidates.py \
  --run-dir work/draft/e5/本次目录 \
  --error-response work/draft/model/error-response.txt \
  --context-response work/draft/model/context-response.txt \
  --provider 实际模型平台 \
  --model 实际模型版本 \
  --selected context-driven \
  --reason '根据两份原始回复填写可复核的选择理由'
```

该命令只提取并校验候选结构，生成 `candidates/provenance.json`；不会构建候选，状态保持 `PENDING_E6_REAL_BUILD_AND_PROGRAM_VERIFICATION`。

## 4. 测试与报告

本地脚本回归：

```sh
python3 -m unittest discover -s tests/draft_lab -v
```

创建本人报告时保留已有文件：

```sh
mkdir -p docs/reports/你的学号
cp -n docs/templates/draft-e5-report.md docs/reports/你的学号/e5.md
```

报告应写明固定输入、目标故障行号、两份提示和原始回复、候选哈希与选择依据，以及课程小样例相对论文原型的范围限制。E6 未执行时不得填写修复构建或程序验证通过。
