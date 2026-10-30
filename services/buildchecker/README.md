# BuildChecker 的 E4 环境

服务镜像包含原项目、gcc、GNU Make、strace 和锁定的 pytest；使用普通用户运行，禁用容器网络并保留 SYS_PTRACE。操作和交付要求见 [E4 指南](../../docs/guides/E4操作与交付说明.md)。

CLI 骨架提供 `version`、`smoke`；3 个骨架单测与原项目回归分别运行。项目复跑覆盖 fzy C0、C1、C2、MD/RD，结果保存在个人 `work/e4/A/<运行编号>/`。

这验证环境与已有基线，不代表完整 BuildChecker 或 EChecker 算法已实现。
