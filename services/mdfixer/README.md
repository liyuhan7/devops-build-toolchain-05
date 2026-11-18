# MDFixer 教学实现

本目录承载 B 组 E8-E10 的受限 C/Make 修复逻辑。teaching.py 接收当前提交的 MISSING 报告，生成只增加依赖声明的 Git Patch；验证入口在隔离副本里运行补丁应用、构建、程序检查和依赖重检，失败时保留原始输入。

阶段编排、固定样例与证据输出由项目根目录 scripts/e8e10/lab.py 负责。镜像由本目录 Dockerfile 构建；A 组 BuildChecker 仅作为修复后重检的上游依赖。运行命令见 docs/guides/E8-E10集成运行说明.md。

这是课程教学 profile，不实现 docs/interfaces/mdfixer.md 中的异步 Job、Artifact 与生产级来源校验。后续接口实现应单独设计和验证，不把实验 JSON 当作生产契约结果。
