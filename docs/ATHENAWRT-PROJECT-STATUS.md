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
