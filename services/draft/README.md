# DRAFT 的 E4 环境

服务镜像包含原项目、编译工具、锁定的 pytest 和固定版本的 Docker 客户端；通过 docker.sock 使用宿主机引擎，socket 组号由 Makefile 注入。操作和交付要求见 [E4 指南](../../docs/guides/E4操作与交付说明.md)。

CLI 骨架提供 `version`、`smoke`；4 个骨架单测与原项目回归分别运行。教学冒烟确认缺少 make 的预期构建失败；项目复跑覆盖原始 fzy 功能、MDFixer 参考修复及 DRAFT 失败/参考容器，结果保存在个人 `work/e4/B/<运行编号>/`。

docker.sock 可控制宿主机 Docker，只构建课程指定项目。容器 CPU、内存限制不约束宿主机执行的构建。这里没有实现完整 DRAFT 或 MDFixer 方法。
