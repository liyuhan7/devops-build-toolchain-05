# ACTUAL_RUN 观察

- 初始 clean build 成功，功能输入 `apple` 返回 `apple`。
- MD：只改真实被读取的 `src/e3_md_marker.h` 后，普通 make 保持 options.o mtime 和旧版本输出；clean build 得到新值。
- RD：只改未使用的显式依赖 `src/e3_rd_unused.h` 后，普通 make 更新 options.o mtime，版本输出不变。
- 结论：运行结果与 TEAM_ORACLE 的一条 MISSING 和一条 REDUNDANT 预期相符。
