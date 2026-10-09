# MDFixer 固定输入复跑观察

运行目录：`work/e3/20261009T02`。环境：WSL2 Ubuntu，x86_64。

## 预期

故障 Patch 新增 `src/e3_mdfixer_marker.h` 并让 `src/options.c` 读取它，但 `src/options.o` 规则不声明该头文件。修改头文件后，普通 `make` 应漏重建并保留 `MDFIXER_MARKER=one`；`make veryclean` 后重新构建应得到 `MDFIXER_MARKER=two`。

## 实际

- `git apply --check --ignore-whitespace`：退出码 0。
- `git apply --ignore-whitespace`：退出码 0。仓库文件为 CRLF，省略该选项时 Git 不能匹配上下文。
- 初次 `make CC=gcc`：退出码 0；`./fzy --version` 输出包含 `MDFIXER_MARKER=one`。
- `make CC=gcc check`：退出码 0，32 个测试全部通过。
- 初次无交互功能测试：退出码 0，输出 `apple`。
- 修改头文件为 `MDFIXER_MARKER=two` 后执行普通 `make CC=gcc`：退出码 0，输出为 `make: Nothing to be done for 'all'.`；版本仍为 `MDFIXER_MARKER=one`。
- 执行 `make veryclean` 和 `make CC=gcc`：均退出码 0，构建日志重新包含 `src/options.o` 编译命令；版本变为 `MDFIXER_MARKER=two`。
- clean 后无交互功能测试：退出码 0，输出 `apple`。

## 结论

预期与实际一致。该运行证明固定输入确实能复现 `src/options.o` 对 `src/e3_mdfixer_marker.h` 的 MISSING 依赖及增量漏重建。参考修复 Patch 和修复后验证仍属于陆泓的后续 PR。
