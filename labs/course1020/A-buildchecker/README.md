# A 轨道 BuildChecker 教学实验

本目录包含学生包的独立教学实现，不替代仓库根目录的服务契约或正式工具链。实现范围为单 Make 进程、每个 recipe 一个最终输出，依赖基于成功读取式 open 观察。

在 Linux Docker 主机中进入本目录，按顺序执行：

```sh
python3 scripts/lab_cloud.py build --out work/build-01 --build-timeout 1200
python3 scripts/lab_cloud.py e5 --out work/e5-01
python3 scripts/lab_cloud.py e6 --out work/e6-before
# 上一步预期退出 1，报告包含精确的 MD/RD。
python3 scripts/lab_cloud.py e6 --fixed --out work/e6-after
python3 scripts/verify_e6_evidence.py --before work/e6-before/evidence/findings.json --after work/e6-after/evidence/findings.json
python3 -m unittest discover -s tests/e7 -v
python3 scripts/lab_cloud.py gate --out work/e7-01
```

每次使用新的 work/ 输出目录。默认镜像为 course1020-buildchecker:local；可显式传入 --image。构建会安装锁定依赖，真实场景在禁网容器中运行。

原始样例应得到 MISSING(main.o, config.h) 和 REDUNDANT(main.o, unused.h)，修复后 findings=[]。

[个人实验报告](docs/实验报告_241830149.md)、[验收记录](docs/验收记录_241830149.csv)、[精选原始证据](evidence/241830149/)保留实际运行结论。根目录 .github/workflows/e7-a-quality-gate.yml 运行 CI 并上传原始证据；CI、分支保护和最终合并状态以报告中的实际记录为准。
