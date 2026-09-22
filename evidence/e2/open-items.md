# E2 未完成项与边界

## 本阶段明确不实现

- 不部署 DRAFT、BuildChecker、EChecker 或 MDFixer 的真实 API。
- 不下载样例 Artifact URI，也不把虚构 SHA 当作真实运行证据。
- 不执行真实容器构建、依赖追踪或 Patch 应用。
- 不由 MDFixer 创建 Commit、推送分支或自动合并修复。

以上是 E2“需求与接口契约”阶段的设计边界，不是接口契约缺陷。后续实现阶段应使用真实仓库、Commit、构建日志和 Artifact 摘要补充运行证据。
