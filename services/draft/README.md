# DRAFT 的 E4 环境

服务镜像包含原项目、编译工具、锁定的 pytest 和固定版本的 Docker 客户端；通过 docker.sock 使用宿主机引擎，socket 组号由 Makefile 注入。操作和交付要求见 [E4 指南](../../docs/guides/E4操作与交付说明.md)。

CLI 骨架提供 `version`、`smoke`；4 个骨架单测与原项目回归分别运行。教学冒烟确认缺少 make 的预期构建失败；项目复跑覆盖原始 fzy 功能、MDFixer 参考修复及 DRAFT 失败/参考容器，结果保存在个人 `work/e4/B/<运行编号>/`。

docker.sock 可控制宿主机 Docker，只构建课程指定项目。容器 CPU、内存限制不约束宿主机执行的构建。这里没有实现完整 DRAFT 或 MDFixer 方法。

## E5 论文复现

E5 使用仓库根目录的 `scripts/draft/e5.py` 在课程 Linux 服务器上复现固定 Dockerfile 缺少 `make` 的真实构建失败，并由实际日志生成错误驱动与上下文驱动提示。模型回复与候选通过 `scripts/draft/record_candidates.py` 保存和校验；该阶段不构建候选，验证状态保持 `PENDING_E6`。操作、证据和报告要求见 [B 组 DRAFT E5 指南](../../docs/guides/B组DRAFT论文复现实验.md)。

E6 使用 `scripts/draft/e6.py` 读取 E5 选中候选和来源记录，校验输入摘要后分别构建失败基线与候选镜像。候选镜像通过不可变本地镜像 ID 在断网容器中运行，必须退出 0 并输出 `hello E3`；`scripts/draft/verify_e6.py` 独立核对保存的日志、退出码、镜像身份和输入哈希。该教学流程只验证课程固定样例，不等同于 E2 通用 DRAFT API 或 OCI 交接。
