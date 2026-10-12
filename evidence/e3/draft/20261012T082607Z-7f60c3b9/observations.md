# DRAFT 容器实际观察

来源：ACTUAL_RUN。

预期：失败候选报告构建工具缺失；参考候选在同一固定源码上完成构建、测试和功能验证。

| 检查 | 实际结果 |
|---|---|
| 固定上游源码摘要一致 | 通过 |
| broken 使用同一固定基础镜像 | 通过 |
| reference 使用同一固定基础镜像 | 通过 |
| Docker 使用 Linux 容器引擎 | 通过 |
| base-inspect 镜像 ID 有效 | 通过 |
| 基础镜像 RepoDigest 与固定摘要一致 | 通过 |
| 基础镜像为 Linux | 通过 |
| 失败候选在项目构建步骤报告工具缺失 | 通过 |
| 本次构建产生有效镜像 ID | 通过 |
| reference-inspect 镜像 ID 有效 | 通过 |
| 容器功能检查通过且详细证据已导出 | 通过 |
| 功能命令的 stdout/stderr 文件齐全 | 通过 |

状态：PASSED。失败原因：无。

完整命令、退出码与镜像身份见 commands.json、run.json；功能详情见 functional/。
