# EChecker

A 组 E8—E9 的增量依赖检测教学实现。代码由 `DevOps_E8_E10` 2026-10-31 版 A 轨道算法适配，按仓库既有 services、scripts、fixtures 和 tests 结构组织。成员步骤与作业交付见 [A 组 EChecker 指南](../../docs/guides/A组EChecker实验.md)。

## 与现有项目的结合

- `echecker/core.py` 保留课程预处理指令、配方和配置签名驱动的图复用；MD/RD 计算调用现有 `services/buildchecker/buildchecker/fullcheck.py` 的 compare_graphs。
- `build_baseline()` 调用同一文件的 full_check，消费真实两图、进程、trace 和 findings；与 GCC 投影独立核对后建立历史图，记录 baseline_trace_id。
- `scripts/echecker/lab.py` 复用现有 A 组的 student_image、fresh_output、container 和 run_logged；build/doctor 直接委托 BuildChecker 入口。
- 使用现有 `buildchecker-lab:<学号>` 镜像、`services/buildchecker/Dockerfile` 和根依赖锁文件。镜像保留完整 `/repo`；源码/测试修改后重建，实际运行绑定镜像 ID。
- 双对象受控输入位于 `fixtures/echecker/`，E8/E9 在 work 副本生成历史。原 E3 fzy 基线继续使用其原入口。

## 运行

在 Linux 外层仓库根目录执行：

```bash
python3 scripts/echecker/lab.py build --image buildchecker-lab:本人学号 --out work/echecker/新的构建目录
python3 scripts/echecker/lab.py test --image buildchecker-lab:本人学号 --out work/echecker/新的测试目录
python3 scripts/echecker/lab.py e8 --image buildchecker-lab:本人学号 --out work/echecker/新的E8目录
python3 scripts/echecker/lab.py e9 --image buildchecker-lab:本人学号 --out work/echecker/新的E9目录
```

实验报告位于阶段目录的 `evidence/result/`。阶段根目录记录源码、工作区状态、镜像、调用日志和退出码。每次使用新目录；完整操作和通过条件见成员指南。

也可对已准备的受限项目单独扫描，Linux 仓库根目录设置包路径后调用：

```bash
PYTHONPATH=services/echecker:. python3 -m echecker --project work/实际样例/project --baseline work/实际基线/baseline.json --out work/新的报告.json
```

## 支持范围与测试

当前限定 main.c/helper.c 两个翻译单元、根目录项目头文件、显式 Make 规则和简单变量。支持 CFLAGS 为 -O0、-O1、-O0 -DMODE=1。全局缓存键改变时保守刷新两个对象；声明变化复用实际图并重算发现。完整论文的命令推断、增量系统调用归并和公共异步服务另行实现。

报告使用 `echecker-teaching-1` 教学格式；公共 Job/Artifact/Finding 契约仍以 [接口说明](../../docs/interfaces/echecker.md) 为准。本轮未将教学 JSON 声明为公共服务响应。

```bash
python3 -m pytest -c services/echecker/pytest.ini services/echecker/tests
python3 -m unittest discover -s tests/echecker_lab -v
```

服务测试验证固定边集、普通变化复用、include/配置失效、声明修复、真实 BuildChecker 调用边界及输出保护；编排测试验证共用环境、不可变镜像 ID、日志和失败传播。真实 strace 端到端由 `echecker-quality-gate` 的 E8 阶段执行，E9 阶段验证真实 Make 与 C0—C3 历史。
