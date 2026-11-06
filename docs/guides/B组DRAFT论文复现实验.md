# B 组 DRAFT E5-E6 论文复现实验

本指南覆盖 E5 失败复现、提示与候选留档，以及 E6 候选真实构建与程序验证。E5/E6 使用课程固定的小样例和人工取得的模型回复，不调用模型 API，也不代表已经实现 E2 公共契约中的通用 DRAFT 服务。

## 1. 前置与边界

- 在 Ubuntu 课程服务器、本人的 `feat/draft-lab` 克隆中执行。
- 宿主机需能使用 Docker；基础镜像必须固定完整摘要。
- 每次运行使用新的 `work/draft/e5/` 目录，失败记录不覆盖。
- `work/` 保持 Git 忽略，正式报告按组别放入 `docs/reports/B05/`，不以成员学号命名。
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

## 4. E6 构建与程序验证

E6 从 E5 `candidates/provenance.json` 读取已选候选，核对候选 SHA-256 和 E5 项目输入哈希。不要修改 E5 原始运行副本；每次使用新的 E6 输出目录。

```sh
python3 scripts/draft/e6.py \
  --run-dir work/draft/e5/本次E5目录 \
  --out work/draft/e6/本次E6目录 \
  --build-timeout 600 \
  --verify-timeout 60
python3 scripts/draft/verify_e6.py --run-dir work/draft/e6/本次E6目录
```

如果已确认服务器容器访问 `deb.debian.org` 不可用、但实验包所用固定基础镜像可正常使用，可显式指定受支持的 Debian HTTPS 镜像，例如增加 `--debian-mirror mirrors.aliyun.com`。该选项只在 E6 构建副本的 `apt-get update` 前加入源地址替换命令；E5 候选原文件和 SHA-256 保持不变。运行证据会同时保存 `iter-02/source-candidate.Dockerfile`、实际构建的 `iter-02/Dockerfile`、适配原因及两份 SHA-256，核验器检查派生内容只能是该项适配。该选项不能用于替代候选修复，也不能把构建失败改报成功。

第一轮使用 E5 保存的固定 `Dockerfile.broken` 重建基线，必须再次得到 `MISSING_MAKE`；网络、镜像拉取和超时错误均不能代替目标故障。第二轮使用来源记录中选定的完整候选 Dockerfile。候选构建成功后，脚本通过 `docker image inspect` 获取镜像 ID，并以该 ID 在断网容器中运行默认程序；必须退出 0 且标准输出精确为 `hello E3`。

E6 证据包括两份实际 Dockerfile、分轮构建命令/日志/退出码、镜像 ID、运行命令/输出/退出码、E5 来源记录快照、输入哈希、`result.json` 及核验结果。任何一轮不符合预期时状态为 `FAILED`，保留日志后另用新目录重跑。不要覆盖失败证据。

## 5. 测试与报告

本地脚本回归：

```sh
python3 -m unittest discover -s tests/draft_lab -v
```

创建本人报告时保留已有文件：

```sh
mkdir -p docs/reports/B05
cp -n docs/templates/draft-e5-report.md docs/reports/B05/e5.md
```

报告目录按组别命名；运行人姓名和学号只写入报告及运行元数据，不用于目录名或镜像标签。

## 6. E7 五场景门禁

E7 使用 E6 已验证且带来源记录的候选回放，不重新生成模型答案。默认候选位于 `fixtures/ci-candidates/`，启动前会比对候选 SHA-256 与 `provenance.json`。也可以传入自己的候选，但应在报告中补齐其来源记录。

```sh
python3 scripts/draft/lab.py e7 \
  --replay \
  --image draft-lab:B05 \
  --out work/draft/e7/B05-本次运行 \
  --build-timeout 600
cat work/draft/e7/B05-本次运行/gate/gate-result.json
```

门禁运行服务单测，并分别验证正常候选、错误输出、无效 CMD、候选构建失败和运行超时。预期五场景 `passed=true`；超时场景还检查运行容器已清理。CI 使用同一门禁，并额外注入错误 oracle，确认门禁会返回失败。

E5 报告应写明固定输入、目标故障行号、两份提示和原始回复、候选哈希与选择依据，以及课程小样例相对论文原型的范围限制。E6 结果填写单独的 [E6 报告模板](../templates/draft-e6-report.md)，记录 E5 运行目录、Docker 两轮结果和同一镜像 ID 验证。E7 场景与自主测试填写 [B 组 DRAFT 报告模板](../templates/draft-report.md)。未执行的阶段不得填写为通过。
