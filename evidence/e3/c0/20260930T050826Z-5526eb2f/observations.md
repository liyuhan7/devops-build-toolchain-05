# C0 实际观察

来源 ACTUAL_RUN，人工预期见 fixtures/e3/echecker/expected.json（TEAM_ORACLE）。

Ubuntu 24.04 x86_64 运行完成。原始 fzy 与 C0 构建退出码均为 0，各通过 32 项上游测试、102 条断言。

三个查询的实际输出分别为 apple、banana 和空输出，退出码均为 0。编译器得到 src/options.c、src/options.h、config.h 三个项目输入，与显式 Make 声明及人工图一致。

src/options.d 未生成。仅更新 src/options.h 时间戳后，普通 make 重新编译 src/options.o，之后 apple 查询仍正确。11 项脚本断言全部通过，详细命令、输入和日志见 commands.json，断言见 run.json。

运行失败：无。未完成：用户提交 C0 和回填 SHA、组内独立复跑、远端 Actions。此次运行时源码尚未提交，experiment_commit 为 null，源码摘要用于定位实际输入。
