# MDFixer 修复验证观察

人工预期：fixtures/e3/mdfixer/fixed-md.json（TEAM_ORACLE）。本记录来源：ACTUAL_RUN。

| 检查 | 结果 |
|---|---|
| 环境命令 os | 通过 |
| 环境命令 gcc | 通过 |
| 环境命令 make | 通过 |
| 环境命令 git | 通过 |
| 故障 Patch 可应用 | 通过 |
| 故障 Patch 应用 | 通过 |
| 故障源码和头文件已写入 | 通过 |
| 故障样本首次构建 | 通过 |
| 初始版本包含 one | 通过 |
| 故障样本上游测试 | 通过 |
| 故障样本功能输出 | 通过 |
| 故障头文件晚于对象 | 通过 |
| 修复前漏重建并保留 one | 通过 |
| 参考 Patch 可应用 | 通过 |
| 参考 Patch 应用 | 通过 |
| 人工依赖复核 | 通过 |
| 补丁应用后构建并更新为 two | 通过 |
| 修复后上游测试 | 通过 |
| 修复后功能输出 | 通过 |
| 再次修改的头文件晚于对象 | 通过 |
| 不 clean 的增量重建得到 three | 通过 |
| 修复后 clean | 通过 |
| 修复后 clean build | 通过 |
| 修复后 clean build 保留 three | 通过 |

运行状态：PASSED。
失败原因：无。

本案例只做人工依赖复核，未运行真实 MDFixer/EChecker。
