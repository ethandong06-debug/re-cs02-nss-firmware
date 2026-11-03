# AthenaWrt 项目状态（唯一交接入口）

> 新对话默认只读本文件，再核对本分支最新 HEAD 与最近一次 Actions。详细源码证据按需查阅第 7 节文档。
> 更新日期：2026-11-03

## 1. 项目与交付

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`
- 分支：`athenawrt/apk-fixed-signing`
- 本轮完整源码提交：`8877431224a971790deaa6822c0697a4b3aeccbe`
- 交付：独立 LuCI APK；不编译或刷写整机固件。
- 设备：JDCloud Athena RE-CS-02 / IPQ6018，ImmortalWrt SNAPSHOT r1-20261017。
- 设备当前安装：`luci-app-athena-1.2.60-r2`（Run #188）；本轮 r4 尚未安装。

## 2. 不可突破的设备与界面边界

- PPPoE、VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM 驱动与硬件加速现网状态保持不动。
- 不在在线设备执行固件刷写、恢复出厂、网络模式切换、重启网络、格式化磁盘、服务启停或包安装/卸载测试。
- **只修改 Athena 自有界面与专属后端。原生 LuCI 的页面、菜单、ACL、软件包管理器及其后端全部不改。**
- 只交付独立 APK；签名和 SHA256 必须通过验证后才进入设备验收。

## 3. 最新构建与验收状态

- 包版本：`1.2.60-r4`（Makefile `PKG_RELEASE:=4`）。
- 完整源码提交：`8877431224a971790deaa6822c0697a4b3aeccbe`。
- 最终构建：Run #198，ID `41567139400`；已通过静态语法/元数据检查、FileBrowser ARM64 CLI smoke test、ImmortalWrt/LuCI feeds 拉取及 package-only 配置准备；当时正在构建 host tools。尚未产生最终 APK Artifact/SHA256。
- 旧 Run #197（ID `41565253767`，r3 源码）已取消，没有生成可供安装的 APK。
- Run #198：https://github.com/ethandong06-debug/re-cs02-nss-firmware/actions/runs/41567139400
- 设备验收仍以 Run #188 的 r2 为基线。r4 未安装，不能视为真机验收通过。

## 4. 本轮完整 Athena 源码整改

### 后端安全（仅 Athena 文件）
1. Athena RPC ACL 收敛为 Athena 脚本执行白名单及恢复备份所需的单一路径写权限；删除未见调用依据的通用 UCI 权限与额外系统命令执行授权。
2. `athena-upgrade.sh` 在 verify 和 flash 两阶段校验上传路径、本机机型、tar 成员路径与必需成员、SHA256；flash 再校验并使用受保护暂存副本和并发锁。
3. `athena-services-legacy.sh` 只允许静态审核的 `ddns`、`ttyd`、`matrix` 服务启停；动态发现服务只读展示。ucode 与 shell 列表行为保持一致。
4. `athena-reset.sh` 使用 256-bit 一次性确认码、60 秒有效期；成功消费确认码后才执行 firstboot，失败返回非零。前端确认流程使用同一挑战码。
5. `athena-mode.sh` 的 NSS 关闭调用点改为保持/恢复 NSS/ECM，不再停止 qca-nss-ecm 或删除硬件加速配置。
6. Athena 包管理后端保护 OpenClash、NSS/ECM、内核、网络栈及关键 LuCI；安装/卸载/升级前预演 APK 事务，阻止依赖事务间接变更受保护组件。Athena 页面同步隐藏受保护组件操作入口。

### Athena 全站页面优化
1. 全站统一标准 Liquid Glass、balanced density、卡片间距、控件高度与视觉层级。
2. 桌面/平板采用多列布局；窄屏和手机单列布局，保留触控尺寸与原有导航。
3. “跟随系统”主题选择真实持久化为 auto，系统明暗模式变化时同步更新；保留手动浅色/深色覆盖。
4. 首页 CPU、内存、运行时长、接入设备、WAN/拓扑等不再预填静态示例值；读取中状态由真实 RPC 数据替换。
5. WiFi、访客网络、磁盘、资源占用、服务、LED/点阵屏和维护页面不再在数据加载前宣称示例状态；数据失败时保留明确的未读取/未知状态。
6. 首页实时网速继续使用 `athena-status.sh rate` 真实采样，每 2 秒请求，近 10 秒平滑显示；没有新增假流量或虚构硬件加速开关。
7. 增加键盘焦点可见性、减少动态效果偏好适配及桌面/触屏交互差异处理。

## 5. 原生界面与设备安全说明

- 与原生 LuCI 相关的源码文件本轮未修改；原生 package-manager ACL 和可用操作维持原样。
- 因原生包管理器不在修改范围，Athena 关键包保护只对 Athena 页面/后端生效；不宣称原生入口也被 Athena 保护。
- 不执行任何设备侧升级或危险操作；现网 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash、NSS/ECM 未被本轮操作触碰。

## 6. 统一验证清单

Run #198 必须全部通过后才能提供 APK：
1. 所有 Shell 脚本 `sh -n`。
2. Athena menu/ACL JSON 解析。
3. 24 个直接 RPC 脚本与 Makefile 安装清单、ACL 执行权限匹配。
4. 全部内嵌 JavaScript Node 语法检查。
5. FileBrowser ARM64 CLI 冒烟测试。
6. Athena package-only APK 构建。
7. APK 签名验证、运行时依赖模拟与 SHA256 记录。
8. 上传 Artifact 并核对提交 SHA、包版本与文件哈希。
9. 用户确认后才进行 r4 设备安装验收；不执行刷写固件、恢复出厂或网络模式切换。

## 7. 详细技术证据

仅在需要具体源码行级证据时读取：
1. `docs/ATHENAWRT-CURRENT-SOURCE-REVALIDATION.md`
2. `docs/ATHENAWRT-FRONTEND-BACKEND-CALLCHAIN-AUDIT.md`

**当前阶段：Athena 后端安全整改和全站页面优化已在 r4 源码批次提交；Run #198 构建中；设备仍运行 r2，未安装新 APK。**


## 8. 网络原生回滚与存储/NAS 后续决策

### 网络配置变更后的失联回退（采用原生 LuCI/UCI，不另造 watchdog）
- 用户已明确：ImmortalWrt 原生 LuCI 已有 UCI 定时回滚机制；Athena 应复用原生后端，不另建 Athena watchdog、pending 状态守护进程或第二套 token/回滚框架。
- 原生流程的核心是先通过当前 LuCI RPC 会话暂存配置，再调用原生 UCI rollback apply（LuCI 路由 `/admin/uci/apply_rollback`）；原生机制生成确认 token 并启动回滚期限。管理端重新连通后，通过原生确认入口（`/admin/uci/confirm`）确认；期限内未确认则由系统自动回滚。必须以设备当前安装的 LuCI 版本及接口实现复核后再接入。
- **关键接入条件：** 当前 Athena 的 `athena-mode.sh` 多个分支直接使用命令行 `uci commit`，随后重启网络；这种提交方式不能直接等同于当前 LuCI 会话中的 staged UCI changes。不得先执行 `uci commit` 再假设原生 rollback apply 能恢复旧配置。下一轮必须先梳理 Athena RPC/认证会话与原生 UCI session 的关系，让模式变更进入原生 UCI 事务，再由原生 apply-with-rollback 完成应用。
- 接入范围覆盖所有会改变管理链路的模式/接口/VLAN 变更：router、AP、single、bypass；不能只保护 single。现有 single-bg 的本机 IP/VLAN 检查和 athena-netcheck 冷启动检查可作为既有兼容性检查评估保留，但不得把它们宣传为管理端失联回退，也不得再复制一套独立 watchdog。
- Athena 只调整自身模式切换调用链与前端提示，不修改原生 LuCI 页面、菜单、ACL 或后端实现。前端在应用前明确提示网络短暂中断及原生自动回滚保护；重新连接后使用原生确认流程，不要求用户 SSH 操作或新增一套手动回滚步骤。
- 具体实现前，先在当前目标固件核对原生 LuCI 版本、`/admin/uci/apply_rollback`、`/admin/uci/confirm`、当前 RPC session 和 UCI staged changes 行为；完成离线/CI 调用链测试后再安排设备验收。不得在线盲测网络切换；设备测试须有可用带外救援路径。
- 所有事务必须只提交本次 Athena 网络模式修改涉及的 UCI 配置，不得顺带提交其他 LuCI 页面中用户尚未应用的配置；PPPoE、VLAN 2044、IPv6、防火墙既有策略、OpenClash 和 NSS/ECM 的保护边界保持不变。

### 存储中心与按需 NAS
- 当前 Athena 存储能力仍是磁盘管理 + FileBrowser 网页文件管理；没有 Athena 自有 SMB/ksmbd/NFS NAS 管理后端。FileBrowser 是 HTTP 网页文件访问，不等同 SMB 网络共享。
- 现有兼容边界：FileBrowser 根目录为 `/mnt/usb`，监听 LAN 管理地址的 8081 端口；磁盘后端仅允许经校验的真实 USB 分区挂载至 `/mnt/usb`，格式化也限制在真实 USB 分区。不得破坏这一兼容路径或放宽格式化白名单。
- 页面长期定位为“存储中心”，统一入口下分为三个独立能力区：①磁盘与卷管理；②网页文件管理（保留 FileBrowser）；③NAS 网络共享。NAS 未安装时展示安装入口；安装成功后重新读取实际安装/服务状态，并动态显示 NAS 管理模块，而不是仅凭前端点击就假设安装成功。
- NAS 首选 KSMBD + SMB（优先 SMB2/SMB3，按目标系统实际支持情况设置），暂不默认安装 NFS；只有明确存在 NFS 客户端需求时再评估。优先使用目标固件已配置并验证签名的软件源，让 APK 解析完整依赖，不手工猜测或硬编码内核模块版本。
- 一键安装后端（未来新增独立的 `athena-nas.sh`）先检查软件源可用性/签名、设备架构、运行内核 ABI、磁盘空间、依赖及服务端口；执行 APK 事务模拟，并确认不会安装/升级/删除/替换 OpenClash、NSS/ECM、内核、网络栈或其他关键组件。所有依赖通过同一受控 APK 事务解析；任何保护组件将被变更时直接拒绝安装并说明原因。
- 安装完成后自动完成服务初始化、LAN-only 访问边界、账户/认证及默认共享设置；默认禁用匿名/guest 访问，不开放 WAN。账户凭据应安全生成和存储，页面提供查看/重置凭据的受控入口。默认共享目录仅指向已真实挂载的数据卷（首选当前兼容路径 `/mnt/usb`），绝不共享系统根目录、overlay 或未挂载目录。
- 页面动态模块至少显示：安装状态、服务运行状态、共享状态、访问地址、账户/密码管理、启动/停止和卸载入口。安装进度/失败原因必须来自后端真实结果；完成后自动刷新 NAS 模块状态。
- **关闭/停止 NAS：** 停止服务并关闭开机自启，保留软件包、共享配置、账户配置和数据；之后可一键重新启用。
- **卸载 NAS：** 停止服务、移除 Athena NAS 集成及明确由 Athena 安装/拥有的 NAS 软件包；只有在依赖事务确认安全且不影响其他服务时才能卸载共享依赖。卸载不得删除 USB/硬盘数据、格式化分区或清理用户文件。对已有系统组件或用户预先安装的组件不得擅自卸载；必要时保留/导出共享配置并明确告知。
- 后端职责分离：`athena-disk.sh` 继续只负责块设备/卷操作；`athena-nas.sh` 负责 NAS 软件包事务、服务、共享、账户和权限。卸载卷前必须检查并停止 FileBrowser/NAS 等数据卷消费者；热拔出时停止依赖服务并报告离线状态。
- 卷身份后续逐步从易变化的 `/dev/sda1` 改为 UUID/LABEL；当前主数据卷继续兼容挂载到 `/mnt/usb`，其他卷使用独立稳定挂载点。所有共享路径必须 realpath 校验并限制在已登记且真实挂载的数据卷内，禁止路径穿越。
- NAS 是后续独立源码批次，不纳入当前 r4。安装按钮、APK 依赖清单、RPC ACL、后端脚本、页面动态渲染和卸载保护必须一起交付并统一 CI 验证；不得只做一个没有后端的前端按钮。未经用户明确同意，不在设备上自动安装或卸载 NAS 软件包。
