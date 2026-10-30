# E4 B 组环境验证与证据汇总

核对日期：2026-10-21。依据 [E4 操作与交付说明](../../docs/guides/E4操作与交付说明.md)、E4 课件第 18 至 20 页和 B 组命令手册核对。以下为服务器现存记录的审计结果；`work/` 被 Git 忽略，原始日志保留在各成员自己的克隆中。

## 固定版本与环境

- 仓库：`liyuhan7/devops-build-toolchain-05`，分支 `chore/e4-environment`。
- 四份 B 组完整运行的 `source-sha.txt` 均为 `48661309a5c23beecdb555f6919e1ff367eeebfd`，运行前 `worktree-status.txt` 均为空；核对时四份克隆的 `git status --short` 也为空。
- 汇总前远端分支已前进到 `51885acc4edb4a88e0ac75aa7fb9515ef8a5c58b`，该提交修改了 A、B 组 Dockerfile 的 Debian apt 源。下述四人运行均发生在 `4866130`，不能作为 `51885ac` 或后续汇总提交的构建通过证据。
- 服务器：`ecs-28cc`，Ubuntu 24.04.4 LTS，Linux `6.8.0-136-generic`，`x86_64`；Docker Server 29.1.3、Compose 2.40.3、Buildx 0.30.1、Git 2.43.0、Make 4.3、Python 3.12.3。B 组容器内 Docker CLI 为 28.5.1，Python 为 3.13.14。
- `env.json` 中四人的 `problems` 均为空。服务器为 2 CPU、约 5.4 GiB 可见内存、约 67 至 70 GiB 可用磁盘；这三项低于建议值，属于警告，不影响本次验证通过。Docker 镜像加速地址记录为 `https://dockerproxy.net/`。
- B 组 Dockerfile 固定 Python 基础镜像摘要 `sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74`，Docker CLI 镜像摘要 `sha256:9190b0613792e658a7783cf14b2d5ace5941bb68ede7276922ea36ee457d76ad`。构建日志含两者的 `resolve` 记录；依赖从 `requirements-dev.lock` 按哈希安装。四份 `toolchain.lock` 的 SHA-256 均为 `c07179f405a436f96a9aeb860f9b6f73b3e55e695ed10b57db193ff39d6820a1`。

## 四人完整运行

下表路径均为服务器绝对路径。每个成功目录均有 `env.json`、`build.log`、`image.json`、`toolchain.lock`、`test.log`、`smoke.json`、`project-smoke/summary.json`、`project-smoke/evidence/`、`secret-scan.txt`、`source-sha.txt` 和 `worktree-status.txt`。

| 成员 | 完整成功目录 | 镜像 ID | 核验结论 |
| --- | --- | --- | --- |
| 李新昊 `241250002` | `/root/241250002/draft/work/e4/B/20261021-103854-2434b23d/` | `sha256:3de0f97c3cac1022d82f120b664d7b0baaf40bf203357415a413fdea2f3d1662` | 通过 |
| 刘洋 `241250037` | `/root/241250037/draft/work/e4/B/20261021-104504-787e8d23/` | `sha256:eacdd9246e92fa4c4c754ba81666d139c54090207b878742dd7dcada953e2df1` | 通过 |
| 刘君杰 `241250049` | `/root/241250049/draft/work/e4/B/20261020-093109-b5f68501/` | `sha256:85b31b325597091f08c65cb59b34ec708fe2654e5df669a80e673c2d703c15fd` | 通过 |
| 陆泓 `241250105` | `/root/241250105/draft/work/e4/B/20261018-185548-7791ff21/` | `sha256:5ab940a2dd9404f980e7012c77d8fb418f5ab5844bf14390d52659370a156cd8` | 通过 |

四份 `test.log` 都记录 51 项 unittest 通过及 B 组 pytest `4 passed`；`smoke.json` 都是 `passed: true`，样例构建退出码为 1，关键错误行包含 `make: not found`。这里的非零退出码是 B 组教学样例的预期失败。四份 `project-smoke/summary.json` 都是 `passed: true`、`pending_cases: []`，`draft-functional`、`mdfixer`、`draft-container` 三项均为 `PASSED`，原始证据在各自的 `project-smoke/evidence/` 中。完整运行中的四份 `secret-scan.txt` 均未发现问题。

## 假密钥扫描

每人另有两份独立的 B 组扫描目录。第一份日志在暂存 `leak-demo.txt` 后报告 2 处 `FOUND`，第二份在撤销暂存并删除该文件后报告“未发现问题”。这些仅含扫描记录的目录不作为完整运行证据。

| 成员 | 负例扫描目录 | 清理后扫描目录 |
| --- | --- | --- |
| 李新昊 `241250002` | `/root/241250002/draft/work/e4/B/20261021-104138-e91d7435/` | `/root/241250002/draft/work/e4/B/20261021-104204-003d0a78/` |
| 刘洋 `241250037` | `/root/241250037/draft/work/e4/B/20261021-104754-d23a1597/` | `/root/241250037/draft/work/e4/B/20261021-104821-40d83f22/` |
| 刘君杰 `241250049` | `/root/241250049/draft/work/e4/B/20261020-094011-a3e2dbe0/` | `/root/241250049/draft/work/e4/B/20261020-094112-84fb7f63/` |
| 陆泓 `241250105` | `/root/241250105/draft/work/e4/B/20261018-191611-4fe5072c/` | `/root/241250105/draft/work/e4/B/20261018-191612-ea772655/` |

核对时四份克隆均无 `leak-demo.txt`、没有 Git 跟踪的 `.env`，工作区为空；四份 `.env` 权限均为 `600`。陆泓的现场命令记录保存了负例退出码 2、清理后退出码 0；其余三人的扫描日志保存了检测结论，但未单独保存命令退出码，须由本人在 `delivery.md` 中补记实际记录或明确注明未保存，不可把推断值当作实测值。

## 交叉对照

李新昊与刘洋、刘君杰与陆泓可组成两组同组对照。四份成功目录的源码 SHA、`toolchain.lock` 内容及 SHA-256、51 项 unittest 与 4 项 pytest 结论、B 组冒烟结论、三项原项目验证结论一致。镜像 ID、运行时间和日志行数不同；本次没有发现结论或工具版本冲突，也没有单独分析镜像 ID 差异的成因。同一台 ECS 共用 Docker 引擎和缓存，因此此结论是同服务器、独立克隆的可重复性验证。

陆泓另在 `/root/241250105/draft/work/e4/A/20261021-111723-6458b8cc/` 留有 A 组完整运行，`smoke.json` 和原项目四项案例通过。它是跨组辅助验证，不计入四人的 B 组同组对照。

## 收尾状态

- 已核实四位成员的 B 组完整运行、固定源码 SHA、项目证据、假密钥命中与清理，以及同组结果一致性。
- 逐人可核实的工作见 [contributions.md](B-contributions.md)。个人 `delivery.md` 尚未在成功目录中发现；姓名以组长提供的信息填写，但问题处理、互助、AI 参与和个人确认仍须本人据实填写并签认。
- 三位成员的负例扫描命令退出码未单独留档；扫描日志可证明命中与清理结果，不能反推出已保存了具体退出码。
- 本汇总只确认 `4866130` 的 B 组结果。更新 apt 源后的分支版本仍需重新验证；PR、Reviewer 审核、自动检查和合并状态尚未核实，不标记为已完成。正式交付前由成员补全 `delivery.md`，组长复查引用路径与待办，再按仓库流程提交 PR。
