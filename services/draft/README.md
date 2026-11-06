# DRAFT 教学服务

服务镜像保留 E4 环境，提供 `version`、`smoke` 和 `auto-build` 命令。`auto-build` 接受人工保存的候选 Dockerfile，在隔离的课程固定样例中先确认基线 `MISSING_MAKE`，再构建候选，并以候选镜像 ID 在断网容器中核对程序输出。E7 五场景门禁通过宿主机驱动脚本调用该服务命令。

E5/E6 的权威采集、溯源和证据核验入口位于仓库根目录 `scripts/draft/e5.py`、`scripts/draft/record_candidates.py`、`scripts/draft/e6.py` 和 `scripts/draft/verify_e6.py`。E7 门禁入口为 `scripts/draft/lab.py e7`，场景判据位于 `scripts/draft/gate.py`。操作、证据目录及报告要求见 [B 组 DRAFT 指南](../../docs/guides/B组DRAFT论文复现实验.md)。

运行时通过 `/var/run/docker.sock` 使用宿主机 Docker，因此服务容器的 CPU、内存限制不约束宿主机执行的构建。只应在课程受信任环境运行；该教学重放不实现 E2 通用 DRAFT Job、模型调用或 OCI Artifact 交接，也不等同于论文规模实验。

## E5 论文复现

E5 使用仓库根目录的 `scripts/draft/e5.py` 在课程 Linux 服务器上复现固定 Dockerfile 缺少 `make` 的真实构建失败，并由实际日志生成错误驱动与上下文驱动提示。模型回复与候选通过 `scripts/draft/record_candidates.py` 保存和校验；该阶段不构建候选，验证状态保持 `PENDING_E6`。操作、证据和报告要求见 [B 组 DRAFT E5 指南](../../docs/guides/B组DRAFT论文复现实验.md)。

E6 使用 `scripts/draft/e6.py` 读取 E5 选中候选和来源记录，校验输入摘要后分别构建失败基线与候选镜像。候选镜像通过不可变本地镜像 ID 在断网容器中运行，必须退出 0 并输出 `hello E3`；`scripts/draft/verify_e6.py` 独立核对保存的日志、退出码、镜像身份和输入哈希。该教学流程只验证课程固定样例，不等同于 E2 通用 DRAFT API 或 OCI 交接。
