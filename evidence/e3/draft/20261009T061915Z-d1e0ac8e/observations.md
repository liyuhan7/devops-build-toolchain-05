# DRAFT 功能验证实际观察

人工预期：fixtures/e3/draft/cases.json（TEAM_ORACLE）。本记录来源：ACTUAL_RUN。

| 检查 | 实际结果 |
|---|---|
| 使用 Linux 环境 | 通过 |
| make CC=gcc 构建成功 | 通过 |
| 生成可执行的 fzy | 通过 |
| make CC=gcc check 通过 | 通过 |
| 测试输出包含 32 tests | 通过 |
| 测试输出包含 102 assertions | 通过 |
| 测试输出包含 Pass: 32, fail: 0, skip: 0. | 通过 |
| 版本查询成功 | 通过 |
| 版本标记符合配置 | 通过 |
| 用例 invalid-lines-usage 退出码为 1 | 通过 |
| 用例 invalid-lines-usage 标准输出符合人工预期 | 通过 |
| 用例 invalid-lines-usage 错误输出包含预期信息 | 通过 |
| 用例 match-apple 退出码为 0 | 通过 |
| 用例 match-apple 标准输出符合人工预期 | 通过 |
| 用例 match-banana 退出码为 0 | 通过 |
| 用例 match-banana 标准输出符合人工预期 | 通过 |
| 用例 multi-match-sorted 退出码为 0 | 通过 |
| 用例 multi-match-sorted 标准输出符合人工预期 | 通过 |
| 用例 no-match-empty 退出码为 0 | 通过 |
| 用例 no-match-empty 标准输出符合人工预期 | 通过 |
| 用例清单与人工预期一致 | 通过 |

运行状态：PASSED。

失败原因：无。

Git 提交标签：29dc66256ec12cdfd72f2fb06d7338c707319f59。
