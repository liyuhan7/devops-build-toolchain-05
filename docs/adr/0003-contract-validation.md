# ADR-0003：配置身份与离线契约检查

- 状态：Accepted
- 日期：2026-10-17
- 范围：本次六项契约修正；未建立新 Issue/PR，提交 SHA 待成员提交后记录

## 决策

1. `configuration_id` 是工具链和构建配置的不可变身份。本版 `configuration_digest` 沿用同一 ID，不再以两种来源形式混用。包含项目源码的服务镜像另以不可变 URI 和 Artifact SHA-256 标识；仅源码和打包镜像变化不强制更换配置 ID。编译器、运行库、目标、构建命令、环境或时限变化时须换配置 ID，并重建基线。DRAFT 生产方负责核实工具链身份；离线虚构样例只能检查声明的一致性。
2. 当前修复路线固定为 BuildChecker 基线 → EChecker 当前结果 → MDFixer。MDFixer 只消费 `introduced + MISSING`，请求显式携带增量报告、实际图、声明图和构建日志，各一份，覆盖全部 evidence 引用。不增加上游隐式补取规则。
3. 服务请求由 `request.schema.json` 的对应定义校验，Job、Artifact、Finding、Error 由公共 Schema 校验。四种请求保留原有形状；所有源码 SHA 必须为小写完整 40 位。使用本地 `$id` registry，不通过网络下载 Schema。
4. 在建立 kind 索引前检查产物类型、基数和 ID 唯一性；EChecker 响应中的输入 Artifact 元数据必须与请求一致，数组顺序不影响身份。
5. 检查 evidence 语法、媒体类型和引用归属。提供可读取载荷时进一步校验 JSON Pointer 和日志行号；未读取真实载荷不能宣布定位或内容摘要核验通过。
6. 负例必须由合法正例的指定变异产生，调用与正例相同的消费检查函数，并返回明确拒绝码。恢复变异后须与正例一致；结构错误不能冒充来源错配。

## 依赖与边界

采用标准 `jsonschema` Draft 2020-12 实例校验，依赖及日期/URI 格式检查器锁定在 `requirements-contracts.lock`。CI 先安装锁文件；两组服务镜像通过开发依赖锁文件安装相同版本。

本次仍是离线契约验证，不部署 API、不运行样例命令、不下载虚构 Artifact，不验证真实工具的检测或修复效果。原协议的完整 SHA、终态和字段要求落实为机器检查，旧的不完整负例改为完整的单变异材料。
