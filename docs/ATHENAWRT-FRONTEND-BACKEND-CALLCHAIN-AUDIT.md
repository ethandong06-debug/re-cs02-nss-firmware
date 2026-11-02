# AthenaWrt 全站前端—后端调用链审计（阶段 A）

> 审计日期：2026-11-02  
> 分支：`athenawrt/apk-fixed-signing`  
> 性质：只读源码静态审计；不代表真机行为验收。  
> 保护边界：不改变 PPPoE、现网 VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM；不执行网络模式切换、回滚测试、服务启停、格式化、刷写或恢复出厂。

## 1. 审计对象与版本锚点

- 当前分支 HEAD（本次开始审计时）：`6cc913ca4e4d2617ae3c2087fe528b74e742f8a5`。
- SPA：`luci-app-athena-src/frontend/luci-app-athena/htdocs/luci-static/resources/view/athena/index.html`，4,218 行、291,149 字符，Blob SHA `55ce39ddf0fa6df6e7f188beedb35e177527aea8`。
- LuCI 入口薄壳：同目录 `index.js`，负责跳转到 SPA。
- 菜单定义：`root/usr/share/luci/menu.d/luci-app-athena.json`。
- ACL：`root/usr/share/rpcd/acl.d/luci-app-athena.json`。
- 安装清单：前端 Makefile。
- 后端目录：`root/usr/libexec/`，另含 init.d、hotplug、uci-defaults 和 ucode 实现。

## 2. 数量核对与统计口径

| 项目 | 本次核对结果 |
|---|---:|
| 顶层管理页面 | 8 |
| SPA 中 `athenaRPC.exec` 调用表达式 | 82 |
| 其中字面量脚本目标调用 | 81 |
| 动态目标调用 | 1（`cfg.f`，由网络模式应用流程设置） |
| 去重后的直接后端脚本入口 | 24 |
| ACL 中对应的 `/usr/libexec/athena-*.sh` 执行授权 | 24 |
| Makefile 安装的 libexec 文件 | 36（含 Shell、ucode、legacy 与辅助脚本） |

**统计更正：**此前状态记录曾写 81 次调用、78 个字面量目标和 3 个动态目标。本次以当前分支完整 SPA 文本重新扫描所有 `athenaRPC.exec` 表达式，结果为 82 次、81 个字面量目标、1 个动态目标；差异来自此前扫描没有覆盖全部调用写法。后端入口仍为 24 个，不应把安装的 36 个 libexec 文件等同于 36 个前端 RPC 入口。

动态目标位于网络应用流程：`saveApply()` 将目标固定设为 `athena-mode.sh`，`doApply()` 再以 `cfg.f,cfg.a` 执行。单臂模式另有 `athena-mode.sh progress` 轮询和 `single-bg` 后台执行。

## 3. 菜单与页面入口

菜单文件只定义两个入口：

1. `admin/athena` → AthenaWrt SPA。
2. `admin/athena/advanced` → 原生 LuCI 的 `admin/status` 别名。

SPA 顶部提供 8 个主页面：

| 页面 | DOM ID | 主要职责 |
|---|---|---|
| 概览 | `pg-home` | 实时流量、CPU/内存、运行时长、在线设备、WAN 摘要、活跃应用、拓扑示意、快捷入口 |
| WiFi | `pg-wifi` | 三频开关与配置、访客网络、恢复默认 |
| 设备 | `pg-dev` | 设备列表、在线筛选、备注/改名/认识设备/拉黑、家长控制 |
| 网络 | `pg-net` | 模式切换、WAN 参数、单臂 VLAN 参数、网口状态、体检、Ping、测速 |
| 存储 | `pg-st` | 磁盘识别、USB 挂载/卸载/格式化、FileBrowser |
| 灯光 | `pg-light` | 点阵屏、夜间亮度、显示项目、三色灯/呼吸灯 |
| 维护 | `pg-keep` | 重启、定时重启、固件升级、恢复出厂、备份与恢复 |
| 高级 | `pg-adv` | CPU/内存与进程、服务、软件包、日志、密码、主题、UI 偏好 |

## 4. 按页面的前后端调用链

### 4.1 概览

- `athena-status.sh`：默认调用取得系统、WAN、无线、端口、设备和资源摘要；`rate` 子命令用于实时流量采样。
- `athena-client.sh list/known/notes`：补充拉黑列表、已知设备和备注。
- `athena-apps.sh list`：活跃应用分类；后端依据 DNS 查询等数据匹配 OAF 应用映射，不是 DPI/真实应用层流量识别。
- `athena-prefs.sh get/set kpi_order`：指标卡顺序持久化。
- 主要风险/准确性边界：
  - 拓扑卡在 HTML 中明确标注“示意”，但仍写死 VLAN 3066、`br-iptv`、LAN4 等示例信息；它不是设备实际物理拓扑采集结果。
  - 活跃应用只能作为 DNS 线索推测，不能表述为精准识别。
  - 首屏 HTML 含演示初值，登录后由 RPC 数据替换；应保证失败时明确显示“数据不可用”，不要让演示值伪装成实时状态。

### 4.2 WiFi

- `athena-wireless.sh get`：读取三频状态。
- `athena-wireless.sh enable|disable <band|all>`：总开关/单频开关。
- `athena-wireless.sh set <band> <ssid> <password> <channel> <bandwidth> <encryption>`：修改频段参数。
- `athena-wireless.sh guest get|enable <ssid> <password>|disable`：访客网络。
- `athena-wireless.sh reset-defaults`：恢复无线默认配置并生成随机密码。
- 风险/待验收：
  - 访客网络必须验证实际隔离、DHCP、防火墙和 IPv6 路径，不能仅凭 UI 文案认定隔离成功。
  - WiFi 重载失败时，前端应清楚区分“配置已保存”和“无线重载成功”；不得退化为整体 network restart。
  - 默认恢复会断开全部无线终端，属于高影响操作。

### 4.3 设备

- `athena-status.sh`：提供当前设备/IP/MAC/在线状态基础数据。
- `athena-client.sh list|known|notes|note|rename|know|unlearn|block|unblock`：设备备注、已知设备标记、改名、拉黑/解除拉黑。
- `athena-parent.sh list|set <mac> <days_csv> <start> <end>|clear <mac>`：家长控制规则。
- 风险/待验收：
  - 拉黑/家长控制涉及防火墙规则，需核对重启持久化、IPv6 绕过、规则唯一性，以及与 OpenClash、firewall reload 的交互。
  - 设备在线状态来自状态采样/租约与缓存逻辑，不能只依据拓扑示意图推断。
  - 页面 HTML 有演示设备和演示规则，需确认登录后是否始终被真实数据覆盖。

### 4.4 网络

- `athena-mode.sh progress`：读取单臂后台流程进度。
- `athena-mode.sh single-bg ...`：单臂后台配置；`router|single|ap|bypass` 是模式配置入口，另有 `single-status`。
- `athena-scan.sh`：一键体检。
- `athena-diag.sh check|ping <host> <count>|nodes|dns`：连通性诊断。
- `athena-speedtest.sh`：测速；另有测速节点/单位读取和设置。
- 网络表单由 JS 的 `modeFormHTML()` 动态生成；主路由/单臂支持 PPPoE、DHCP、静态 IP；单臂另含内网 VLAN、拨号 VLAN、IPTV VLAN 和 IPTV 透传口参数。
- 单臂前端 VLAN 校验：内网/拨号 VLAN 必须是 1–4094 纯数字；IPTV VLAN 可空，否则也必须是 1–4094；端口从 lan1–lan4 选择。
- 高风险边界：
  - 模式脚本会重写 network/wireless/DHCP/firewall 等 UCI 配置并重启相关服务；AP/旁路由路径涉及 NSS/ECM 关闭逻辑。绝不能在当前设备上试点。
  - 单臂模式的原生 LuCI/UCI 超时回滚接入仍只是设计原则；尚未核对 Athena 当前 LuCI 版本的实际 API/RPC/ACL，也没有证明它覆盖脚本的全部副作用。
  - `athena-netcheck` 是独立 init.d 冷启动自检：延迟后仅以 `br-lan` 管理 IP 作为健康条件，异常时可触发回主路由配置。它不是 LuCI 的 UCI apply-with-rollback，应作为 P0 单独审计。
  - 页面中的示意拓扑与端口状态不能替代真实网络配置读取。

### 4.5 存储

- `athena-disk.sh list|mount|umount|format`：磁盘识别、挂载、卸载、格式化。
- `athena-services.sh filebrowser-password`：在 USB 确认挂载且 FileBrowser 进程运行时读取初始随机密码。
- FileBrowser 服务由 init.d `filebrowser` 管理，USB hotplug 由 `99-athena-filebrowser` 联动。
- 风险/待验收：
  - 格式化属于不可逆操作；本次只审计代码，不调用。
  - 需真机验证 USB 拔除/重插、挂载竞争、服务退出、LAN 绑定与共享根目录限制。
  - 共享目录目标为 `/mnt/usb`，服务不应在 USB 未挂载时启动。

### 4.6 灯光

- `athena-matrix.sh get|set <key> <value>`：点阵屏开关、亮度、模式、显示项目和夜间计划。
- `athena-led.sh get|set breath <0|1>`：LED 状态/呼吸灯。
- 风险/待验收：
  - “打开完整管理”按钮当前应继续核对是否真正集成；若仅提示未集成，属于无效入口候选。
  - 预览图是 UI 模拟，不等于硬件当前显示状态。
  - 参数范围必须以后端校验为准，不能只依赖前端 slider/select。

### 4.7 维护

- `athena-reboot.sh status|now|enable <time> <dow>|disable`：立即/定时重启。
- `athena-upgrade.sh check|verify <file>|flash <file> <keep>`：固件检查、验证、刷写。
- `athena-reset.sh --confirm`：恢复出厂并重启。
- `athena-backup.sh create|list|restore|download|export|restore-upload|schedule get|set|disable`：备份与恢复。
- 高风险边界：
  - 本次不调用重启、flash、reset、restore。
  - 前端确认框不是安全边界；后端 RPC 必须独立验证调用参数和确认条件。
  - 固件刷写与恢复出厂应优先评估交给原生 LuCI 维护页面，Athena 仅保留确有必要的设备专属增强。
  - 备份文件路径、文件名、符号链接和归档内容校验需要后端保护。

### 4.8 高级

- `athena-resources.sh`：读取 CPU/内存/进程；`stop|restart <pid>` 执行进程操作。
- `athena-services.sh list|set <id> <0|1>`：服务列表与启停。
- `athena-packages.sh list installed|available|install|remove|update|upgrade`：APK 软件包管理（ucode 用于快速列出已安装包，其他动作回退到 Shell 实现）。
- `athena-log.sh list|export|clear`：日志读取、导出、清空。
- `athena-passwd.sh <current> <new> <sync_ssh>`：管理密码修改。
- `athena-prefs.sh get|set|del|list`：KPI 顺序、内核线程显示、UI 缩放、测速单位等偏好。
- `athena-theme.sh get|set|reset`：主题配置。
- `athena-ui.sh get|set|mark|sync|zoom`：默认界面和 UI 缩放。
- 原生 LuCI iframe/链接不走 Athena RPC，是原生管理界面入口。
- 风险/待验收：
  - 进程与服务操作必须以后端保护名单为准；OpenClash、Mihomo、NSS/ECM 不能被误停。
  - 软件包卸载/升级必须由后端保护关键包，不能只依赖前端隐藏按钮。
  - 日志清空、软件包变更、密码修改均是写操作，需核对权限和失败反馈。
  - SSH 开关当前只是提示“由系统安全策略管理，始终启用”，不是实际开关。

## 5. 24 个 RPC 入口清单（按后端职责）

| 脚本 | 已核对的主要动作/参数 | 主要页面 |
|---|---|---|
| `athena-status.sh` | 默认状态聚合；`rate` | 概览、设备、网络 |
| `athena-client.sh` | list、known、notes、note、rename、know、unlearn、block、unblock、restore | 概览、设备 |
| `athena-apps.sh` | list（活跃应用识别） | 概览 |
| `athena-wireless.sh` | get、enable/disable、set、reset-defaults、guest get/enable/disable | WiFi |
| `athena-mode.sh` | router、single、single-bg、progress、single-status、ap、bypass | 网络 |
| `athena-scan.sh` | 一键体检，无前端参数 | 网络 |
| `athena-diag.sh` | check、ping、nodes、dns | 网络 |
| `athena-speedtest.sh` | 测速、测速节点/单位 get/set | 网络、高级 |
| `athena-disk.sh` | list、mount、umount、format | 存储 |
| `athena-matrix.sh` | get、set（键值参数） | 灯光 |
| `athena-led.sh` | get、set breath | 灯光 |
| `athena-theme.sh` | get、set、reset | 全局主题 |
| `athena-ui.sh` | get、set、mark、sync、zoom get/set | 高级/全局 |
| `athena-reboot.sh` | status、now、enable、disable | 维护 |
| `athena-backup.sh` | create、list、restore、download、export、restore-upload、schedule | 维护 |
| `athena-parent.sh` | list、set、clear | 设备 |
| `athena-services.sh` | list、set、filebrowser-password | 高级、存储 |
| `athena-resources.sh` | 采样、stop/restart PID | 高级 |
| `athena-packages.sh` | list、install、remove、update、upgrade | 高级 |
| `athena-upgrade.sh` | check、verify、flash | 维护 |
| `athena-reset.sh` | `--confirm` | 维护 |
| `athena-log.sh` | list、export、clear | 高级 |
| `athena-passwd.sh` | 当前密码、新密码、是否同步 SSH | 高级 |
| `athena-prefs.sh` | get、set、del、list；键白名单 | 概览、高级 |

## 6. ACL 与实现结构发现

1. 菜单与 SPA 的主入口清晰，但单页内有较大段历史预览/模拟 UI 代码与后续真实 RPC 实现并存。不能仅凭“重复函数名”直接删除；需按 IIFE/作用域、运行顺序和真实调用关系继续判定。
2. Makefile 注释已描述 24 个前端 RPC 脚本入口，实际安装 36 个 libexec 文件，包含 legacy 回退、ucode 和 helper；文档和清单应始终区分这两种数量。
3. 状态、服务、资源、软件包等入口通过 Shell wrapper 优先调用 ucode，异常时回退 legacy Shell；这属于同一 RPC 入口下的实现后端，不应另算成新的前端 API。
4. 前端 `athenaRPC` 适配层实际使用的 ubus 对象/方法为：`session.login`、`system.info`（登录/会话心跳）、`file.exec`（命令固定为 `/usr/libexec/` + `file`）和 `file.write`（配置备份分块上传）。完整 SPA 未发现直接调用 `uci`、`athena.status`、`network.device`、`network.wireless`、`/etc/init.d/network`、`ping`、`nslookup` 或 `ubus` 可执行文件的代码。ACL 却额外授权这些 `file.exec` 路径，并对 `athena/network/wireless/dhcp/system/ddns/ttyd` 配置开放 UCI 读写权限。因为浏览器可直接构造 ubus 请求，这些授权不受前端封装限制，构成可绕过 UI 的直接 RPC 面。下一步必须确认是否有其他合法调用者；若无，应移除未使用的直接执行权限，并将 UCI 权限缩至真实必需配置/操作。
5. `athena-netcheck`、`athena-vlan-pre`、filebrowser init/hotplug、uci-defaults 不属于前端直接 RPC，但会影响开机和运行态，必须纳入系统行为审计。
6. HTML 的初始演示内容、静态拓扑、硬编码端口/设备/服务示例与真实 RPC 数据要区分；本次只确认数据刷新路径，不将占位文本认定为真实设备状态。

## 7. 当前缺口与下一轮核查顺序

### P0：先闭环安全边界
- [ ] ACL 的额外 `file.exec` 与 UCI 写权限逐条追踪调用者，提出最小权限方案。
- [ ] 网络模式脚本、`athena-netcheck`、`athena-vlan-pre` 的启动顺序、配置备份/恢复范围、失败路径完整核对。
- [ ] 核实 LuCI/UCI 原生超时回滚在当前 ImmortalWrt 固件中的真实接口、ACL 和配置覆盖范围；未核实前不接入、不宣称已具备安全回滚。
- [ ] 复核所有可能触及 OpenClash/NSS/ECM 的服务、进程、软件包和网络模式入口。

### P1：功能真实性和前后端一致性
- [ ] 为每个页面按钮补充“控件 → JS 函数 → RPC 命令/参数 → 后端分支 → UCI/文件/服务副作用”逐项表。
- [ ] 核查遗留预览代码、重复函数、无效按钮、静态演示内容和异常降级。
- [ ] FileBrowser 真机 USB/LAN/认证/目录隔离验收（单独安排，不在本静态审计中启动服务）。
- [ ] 访客网络、家长控制、设备拉黑、LED/点阵屏等设备专属功能做行为与持久化验收。

### P2：原生能力替代与交互整理
- [ ] 把通用软件包、服务、进程、日志、网络基础配置、密码、升级/备份能力与当前设备原生 LuCI 页面逐项对照。
- [ ] 输出保留/合并/替代/移除/重做的最终去留表，交用户确认后才实施。

## 8. 本次审计未执行的事项

本次只读取 GitHub 源码与文档。没有修改前端/后端源码，没有运行 GitHub Actions 构建，没有连接路由器，没有调用任何会更改设备配置或运行状态的 RPC，也没有执行网络切换、服务启停、格式化、升级、恢复出厂或回滚测试。


## 9. 网络模式与启动保护链专项审计（静态）

### 9.1 启动脚本顺序与职责

| 脚本 | START | 条件 | 作用 |
|---|---:|---|---|
| `athena-vlan-pre` | 40 | `athena.system.mode=single` 且父设备 wan 存在 | 在 netifd/network（START 50）前，按 UCI 中的 8021q device 段预创建 `wan.X` VLAN 子接口 |
| `athena-netcheck` | 98 | 单臂模式 | 开机后后台等待 45 秒，检查 `br-lan` 是否存在预期管理 IPv4；失败则记录异常配置并触发主路由回退 |
| `athena-boot` | 99 | 无模式限制 | 恢复呼吸灯状态，并从 UCI 恢复设备拉黑规则 |

### 9.2 当前存在的三条不同回退路径

1. **前端使用的 `single-bg` 路径：**
   - 先备份 `network/wireless/dhcp/firewall/athena` 五份 UCI 配置。
   - 配置并提交五份配置，后台重启 network。
   - 最多等待 15 秒检查管理地址、内网 VLAN、拨号 VLAN，以及启用时的 IPTV VLAN。
   - 检查失败时导入五份备份并重启 network、WiFi、firewall。
   - 前端通过 `progress` 轮询结果。
2. **直接调用 `single` 的同步路径：**
   - 主流程提交 network/wireless/dhcp/firewall/athena 并重启 network。
   - 另起 8 秒自检；失败时只恢复最近的 `network.*.uci`，设置 Athena 模式为 router 并重启 network。
   - 该路径与 `single-bg` 的五配置备份/15 秒检查并不等价；ACL 允许执行同一脚本，不能假设只有 UI 调用者。
3. **开机 `athena-netcheck` 路径：**
   - 等待 45 秒后只用 `br-lan` 是否存在管理 IP 判断健康。
   - 不检查 PPPoE、拨号 VLAN、内网回传 VLAN、IPTV VLAN、IPv6、DHCP 或防火墙状态。
   - 失败时先保存 `network.broken.<timestamp>.uci`，再调用 `athena-mode.sh router pppoe` 并重启 network。
   - 这不是 UCI apply-with-rollback，也不等价于 `single-bg` 的完整五配置恢复。

### 9.3 NSS/ECM 与网络副作用

- `config_single()` 通过 `nss_on()` 启动 qca-nss-ecm，并将软件 flow_offloading 设为 0；注释明确单臂模式保持 NSS/ECM 启用。
- `config_router()` 同样调用 `nss_on()`。
- `config_ap()` 和 `config_bypass()` 调用 `nss_off()`：关闭 firewall flow_offloading，并停止 qca-nss-ecm。
- 模式脚本会清理/重建 VLAN device、bridge、LAN/WAN interface、DHCP 及部分 firewall zone 引用；单臂还会改变 `wan6.device` 指向拨号 VLAN。
- 因此 AP/旁路由按钮不是普通网络偏好开关；对当前要求保留 NSS/ECM 的设备必须保持禁用/不可误触，不能在审计阶段执行。

### 9.4 原生 LuCI/UCI 回滚的真实接入限制

- LuCI UCI `apply(true)` 的回滚语义依赖 rpcd UCI 的 session/rollback 状态；`confirm()` 用于确认并取消待回滚任务。
- Athena 当前 `athena-mode.sh` 直接通过 CLI `uci set/delete/add_list` 修改配置，随后执行 `uci commit`，并在后台重启 network；它没有把这些变更放入当前 LuCI 登录会话的 UCI pending changes 中。
- 因此不能只在现有脚本外围调用一次 `apply(true)` 就宣称原生回滚覆盖所有副作用。若要真正复用原生机制，需要重构配置提交路径，使网络配置变更进入同一 rpcd UCI session 的 staged changes，再由原生 apply/confirm/rollback 管理；同时仍需验证无线、DHCP、防火墙、Athena 私有配置、硬件 VLAN 预创建与重启脚本是否都在回滚覆盖范围内。
- 在完成设备当前 LuCI 版本、RPC/ACL、会话权限与覆盖范围核对前，现有手工备份/回退逻辑不能删除，也不能假定原生回滚已接管。
- 本节只作静态审计，没有执行任何模式切换或回滚测试。


## 10. 主要交互控件映射（阶段 A 初表）

| 页面/控件 | 前端处理 | 后端/副作用 | 判定 |
|---|---|---|---|
| 概览：访客网络快捷开关 | `toggleGuest()` | `athena-wireless.sh guest enable/disable` | 真实写操作；必须验证隔离 |
| 概览：WiFi/设备/网络快捷入口 | `goto()` / `navGo()` | 页面切换后触发对应数据加载 | 纯导航 |
| WiFi：总开关/单频开关 | `toggleWifiAll()` / `toggleBand()` | `athena-wireless.sh enable/disable` | 真实写操作 |
| WiFi：编辑名称/密码/信道/频宽/加密 | `editBand()` / `saveBand()` | `athena-wireless.sh set` | 真实写操作 |
| WiFi：访客网络 | `openGuestModal()` / `toggleGuest()` | `athena-wireless.sh guest get/enable/disable` | 真实写操作；隔离效果待验收 |
| WiFi：恢复默认 | `resetWifi()` / `doResetWireless()` | `athena-wireless.sh reset-defaults` | 高影响写操作 |
| 设备：全部/在线/离线筛选 | `switchDevTab()` | 无 | 本地筛选 |
| 设备：备注/改名/认识设备 | `saveDevNote()` / `doRename()` / `knowDev()` | `athena-client.sh note/rename/know` | 真实写操作 |
| 设备：拉黑/解除拉黑 | `doBlock()` / `doUnblock()` | `athena-client.sh block/unblock` | 真实网络控制；核对 IPv4/IPv6 和重启持久化 |
| 设备：家长控制 | `saveParent()` / `cancelParent()` | `athena-parent.sh set/clear` | 真实定时规则；核对规则恢复与防火墙交互 |
| 网络：模式卡片/协议选择 | `pickMode()` / `setWanProto()` | 暂存前端状态，不立即写入 | 本地表单状态 |
| 网络：保存并应用 | `saveApply()` → `confirmApply()` → `doApply()` | `athena-mode.sh` router/single-bg/ap/bypass；单臂 progress 轮询 | P0 高风险；当前不执行 |
| 网络：一键体检/连通性/Ping | `runScan()` / `runDiag()` / `runPing()` | `athena-scan.sh`、`athena-diag.sh check/ping` | 只读诊断（Ping 有外发流量） |
| 网络：测速 | `runSpeed()` | `athena-speedtest.sh <node>` | 产生外网流量；测速源/数据口径需说明 |
| 存储：刷新/挂载/卸载/格式化 | `refreshDisks()` / `mountUsb()` / `umountUsb()` / `fmtDiskDo()` | `athena-disk.sh list/mount/umount/format` | 格式化不可逆；当前不执行 |
| 存储：打开文件共享 | `openFbModal()` | `athena-services.sh filebrowser-password`，随后访问 LAN:8081 | 服务运行/目录/监听需真机验收 |
| 灯光：点阵屏开关/亮度/模式/项目/夜间计划 | `toggleMatrix()`、`setMatrix*()`、`setNight*()` | `athena-matrix.sh set <key> <value>` | 真实硬件配置 |
| 灯光：呼吸灯 | `toggleBreath()` | `athena-led.sh set breath <0|1>` | 真实硬件配置 |
| 灯光：“打开完整管理” | `openMatrixFull()` | 仅 toast“独立的点阵屏完整管理页面尚未集成” | **无效入口候选，应移除或实现** |
| 维护：立即/定时重启 | `doReboot()` / `saveRebootSched()` | `athena-reboot.sh now/enable/disable` | 高影响系统操作 |
| 维护：固件升级 | `doUpgrade()` → multipart `cgi-upload` → `verify` → `flash` | `athena-upgrade.sh verify/flash` | 刷写级危险操作；当前不执行 |
| 维护：恢复出厂 | `doReset()` | `athena-reset.sh --confirm` | 不可逆；后端确认参数目前为固定字符串 |
| 维护：备份/恢复 | `backupNow()`、`restore-upload`、备份列表/下载/恢复 | `athena-backup.sh`；备份上传用 `file.write` | 覆盖全配置的高风险操作 |
| 高级：进程操作 | `procGrpAct()` / `doProcAction()` | `athena-resources.sh stop/restart <pid>` | 高风险；后端保护名单优先 |
| 高级：服务启停/重启 | `svcAct()` | `athena-services.sh set <id> <0|1>` | 高风险；OpenClash/NSS/ECM 必须后端拒绝 |
| 高级：软件包安装/卸载 | `installPkg()` / `doRemovePkg()` | `athena-packages.sh install/remove` | 高风险；关键包保护必须在后端 |
| 高级：检查软件源更新 | `checkUpdate()` | `athena-packages.sh update`（刷新索引） | **不是升级已安装软件包**；文案需避免误导 |
| 高级：日志查看/导出/清空 | `loadLog()` / `exportLog()` / `clearLog()` | `athena-log.sh list/export/clear` | 清空为写操作 |
| 高级：修改管理密码 | `savePassword()` | `athena-passwd.sh <current> <new> 1` | 真实账号操作 |
| 高级：网速单位/主题/默认界面/缩放/KPI 排序 | 对应设置函数 | `athena-speedtest.sh`、`athena-theme.sh`、`athena-ui.sh`、`athena-prefs.sh` | 偏好设置 |
| 高级：SSH 开关 | 最终生效的 `toggleSsh()` 只显示“SSH 始终启用”提示 | 无 RPC、无服务动作 | **假开关/无效入口，应移除** |

说明：
- SPA 中有历史预览脚本块，部分同名函数在后续真实实现中重新定义；本表以最终生效的真实 RPC 实现为准。删除旧代码前仍需做作用域/脚本边界检查。
- “检查软件源更新”执行的是 `apk update` 刷新索引，不是 `apk upgrade`；不要把按钮称为“升级已安装软件”。
- 固件升级使用独立 `cgi-upload` 上传通道；配置备份上传才使用 ubus `file.write`。


## 11. 高风险后端入口复核：新增 P0 候选

### 11.1 服务管理动态 init 名称缺少白名单

- `athena-services.sh set` 会把参数转交给 `athena-services-legacy.sh set`。
- 对动态服务，`set_svc()` 直接令 `init="$id"`，随后检查 `/etc/init.d/$init` 是否可执行，并用该路径执行 `enable/start` 或 `stop/disable`。
- 该分支没有先将 `id` 限定为 `^[A-Za-z0-9_.-]+$`，也没有拒绝 `..`、斜杠或路径分隔符；核心服务保护只按完整字符串比较，不能阻止目录穿越。
- 结果：调用者可尝试用路径片段逃出 `/etc/init.d` 并触发非预期可执行文件。这里不在真机测试；必须后端先做严格 init 名称白名单/字符校验，再拼接路径，并在执行前 realpath 确认仍位于 `/etc/init.d` 内。

### 11.2 固件刷写后端未重复执行完整兼容性验证

- 前端流程先上传 `/tmp/athena-fw-upload.bin`，调用 `athena-upgrade.sh verify` 检查 tar 结构、目标机型和 SHA-256，随后显示用户确认按钮。
- 但后端 `flash` 分支只检查文件存在，再执行 `sysupgrade -T`；脚本自身注释明确当前平台 `sysupgrade -T` 对任意数据可能返回成功，不能作为有效判据。
- `flash` 分支没有重新检查 `sysupgrade-<board>/CONTROL/kernel/root` 结构，也没有重新验证目标机型；因此直接 RPC 调用可绕过前端 `verify` 步骤。
- 必须在后端 `flash` 分支重新执行完整验证，并把可刷写文件路径限制到受控上传目录/文件；不得依赖前端先调用 verify。审计期间禁止调用。

### 11.3 其他“前端确认、后端未独立确认”的危险入口

- `athena-reset.sh --confirm` 使用固定字符串作为确认参数，不是一次性确认令牌；任何具备脚本执行权限的调用者都可直接传入该字符串。
- `athena-mode.sh` 的 router/single/ap/bypass 模式入口可直接由 RPC 调用，后端没有绑定前端弹窗的一次性授权；模式脚本会直接写 UCI、commit 并重启网络。
- `athena-backup.sh restore-upload` 通过固定临时文件恢复配置，后端没有一次性恢复确认令牌；具备对应 file.write/file.exec 权限的客户端可绕过页面确认流程。
- 上述操作不能把前端 modal 当作安全边界；应由后端实现短时、一次性、与具体操作/参数绑定的确认票据，或将危险操作移交原生 LuCI 的受保护流程。

### 11.4 已复核的保护措施

- 服务核心保护名单已包含 `openclash`、`qca-nss-ecm`、`qca-nss-drv`、`qca-nss` 等；但动态 init 名称校验仍须先修复。
- 软件包后端已验证包名字符集，并在 remove/upgrade 中阻止 OpenClash、NSS/ECM、内核、网络、防火墙、LuCI 与 Athena 关键包；对已安装的受保护包也阻止通过 install 入口变相升级。
- 备份恢复路径已限制文件名格式、拒绝路径穿越，并通过 realpath 检查目标位于备份目录内；恢复前检查 tar.gz 结构。
- USB 管理挂载点固定为 `/mnt/usb`，目标限定真实 USB 分区；格式化会拒绝已挂载/swap/系统分区及系统分区所在物理盘。
- 以上均为静态代码判断；本节没有调用任何危险入口。


## 12. 其他后端脚本静态审计（参数、持久化与副作用）

### 12.1 设备拉黑/备注/已知设备（`athena-client.sh`）

- MAC 输入统一校验六组十六进制字节；备注限制 128 字节并拒绝控制字符；名称限制 63 字节并拒绝控制字符。
- 拉黑会同时尝试向 `inet fw4 forward` 添加 nft 规则、向 iptables FORWARD 插入兼容规则，再写入 `athena.client.blocked` 并 commit；开机 restore 只恢复 nft 规则。
- 解除拉黑会在整个 nft ruleset 中搜索包含该 MAC 的规则并按 handle 删除，再删除 iptables 规则、更新 UCI。此搜索范围比 Athena 自己的规则更广，可能触及其他组件/用户创建的同 MAC 规则；应给 Athena 规则加稳定 comment/专属 chain/set，只删除自身规则。
- nft 与 iptables 双写而 restore 只恢复 nft，存在规则重复、规则不一致和防火墙 reload 后行为变化风险；应统一到 fw4/nftables，并对重复 block 做幂等处理。
- rename 会写 DHCP host 段并重启 dnsmasq；若同 MAC 存在多段，仅更新第一条匹配记录。设备名有长度/控制字符校验，但 JSON 转义逻辑仍应统一。

### 12.2 家长控制（`athena-parent.sh`）

- MAC、星期 0-6、HH:MM 范围有基础校验；跨午夜时会将次日星期集合整体平移。
- set/clear 写入 `athena.parent`，重建 `/etc/nftables.d/10-athena-parent.nft`，然后 reload firewall；属于真实防火墙规则生成与重载，不是单纯定时显示。
- 当前每个 MAC 生成独立 base chain，并各自挂到 forward hook、priority 0；需在 Athena 当前 nftables/nft 版本上验证多 base chain 同 hook 同优先级的排序语义，以及规则文件由 fw4 include 的实际加载位置。不能只凭脚本生成成功判断规则生效顺序。
- 星期参数允许重复值；list 直接把 UCI 字符串拼为 JSON 数组，异常/旧配置可能输出重复或非规范值。建议归一化去重，并对已有配置做生成前校验。
- 生成规则前直接删除旧规则文件，缺少临时文件 + 原子 rename；生成中断可能留下空/不完整规则文件。应先生成临时文件、语法检查成功后原子替换，再 reload；失败保留旧规则。

### 12.3 无线与访客网络（`athena-wireless.sh`）

- SSID/密码/信道/频宽采用白名单校验；常规无线设置写 `wireless` 并 commit，属于真实无线重载操作。
- 访客网络确实创建独立 `br-guest`、静态网段、DHCP、独立 firewall zone 和 guest→wan forwarding；无线接口设置 `isolate=1`，guest zone input/forward 为 REJECT，代码没有创建 guest→lan 转发。静态结构符合隔离方向，但仍需真机验证 fw4 实际规则、IPv4/IPv6、客户端互访及主 LAN 可达性。
- guest_clear_internal 会按固定名称删除 `network.guest`、`dhcp.guest`、`firewall.guest_zone`、`firewall.guest_fwd`，并删除所有 name=br-guest 的 network device。若用户已有同名配置，会被覆盖/删除；应在创建前检测冲突、使用专属标记/唯一 section，并备份原值。
- 访客网络跨写 wireless/network/dhcp/firewall 四份配置并分别 commit，随后依次 wifi reload、dnsmasq restart、firewall reload；中途失败没有事务式回滚，且脚本可能留下部分配置。需加分阶段备份与失败恢复，不可简单套用 LuCI 单配置 apply。
- guest_get 仅通过 wireless iface 的 network='guest' 判断启用状态，不核验 bridge、DHCP、zone 和 forwarding 是否完整；页面可能显示“已开启”但隔离链不完整。

### 12.4 密码修改（`athena-passwd.sh`）

- 新密码限制 8-128 字节、拒绝冒号和控制字符；通过 shadow 中 root hash 校验当前密码，再用 chpasswd/passwd 更新 root，Dropbear 共用 shadow。
- 若 root hash 为空、`!` 或 `*`，当前代码直接放行，不验证传入的当前密码；在当前认证会话仍受 rpcd ACL 严格保护的前提下不一定构成匿名漏洞，但不应把“锁定/空密码”自动等同用户当前密码验证成功。建议改为依赖已认证会话并明确提示，或对锁定状态采用安全失败策略。
- 无 openssl 时脚本直接信任已认证 rpcd 会话；必须确保该脚本 ACL 只授予已认证管理员，而非匿名/访客会话。

### 12.5 偏好、主题与界面入口

- `athena-prefs.sh` 使用 `/etc/athena-prefs.conf`，仅允许四个 key；值有白名单/范围校验，权限由 `umask 077` 限制。写入采用临时文件替换，但没有锁，多请求并发写可能互相覆盖。
- `athena-theme.sh` 对 palette/dark 做白名单，数值超 100 截断；非法 dark 值会被忽略但仍返回成功，且主题配置仍依赖 `uci commit athena`。应统一配置存储源并对非法输入明确报错。
- `athena-ui.sh` 的 mode/last 有白名单；set/mark 会改写 `/www/index.html`，属于设备全局入口行为。zoom 已改用 prefs 文件，和 UCI 镜像并存。
- 偏好文件与 UCI 镜像并存，部分脚本读取顺序不同；应明确唯一权威源，避免设置保存成功但刷新后读取到旧 UCI 值。

### 12.6 定时重启、维护与日志

- `athena-reboot.sh` 对时间和星期做基础校验；enable/disable 会修改 root crontab 并重启 cron；now 会延迟一秒直接 reboot。定时任务是系统级副作用，应保留明确状态提示。
- `athena-reset.sh` 只认固定字符串 `--confirm` 后执行 `firstboot -y` 并异步重启；前端确认框不构成后端授权。且脚本无论 firstboot 成败最后都 `exit 0`，RPC 调用者必须解析 JSON 的 `ok`，不能只看退出码。
- `athena-log.sh clear` 会清空 logread 与 dmesg 缓冲区；export 会在 `/www/athena-log` 生成临时日志并 300 秒后删除。日志可能包含设备标识/网络信息，导出目录和 HTTP 访问权限需核对。

### 12.7 存储、备份与升级的剩余检查点

- USB 挂载/格式化入口限定 `/dev/sd[a-z][0-9]+` 且检查 sysfs USB 路径、挂载/swap、系统分区；mount point 固定 `/mnt/usb`。整体保护较完整，但 format 的检查与 mkfs 之间仍有设备热插拔/设备节点替换竞态；执行前需重新解析 sysfs 设备身份，并考虑锁。
- 配置备份恢复限制文件名并 realpath 校验备份目录，检查 tar.gz 可读；但 `restore-upload` 走固定 `/tmp/athena-restore.b64` 与 `/tmp/athena-restore.tar.gz`，缺少并发锁/上传者绑定，多个会话可能互相覆盖文件。恢复前 tar 列表检查仅验证归档可读，没有显式限制归档成员只能属于受允许的配置路径；需核对 sysupgrade -r 的过滤策略。
- 固件 verify 有结构与机型检查，但检查只在 verify 分支；flash 分支只调用当前平台已知不可靠的 `sysupgrade -T`。这是 P0：完整校验必须在 flash 内重新执行，并锁定文件路径/哈希。
- 自动备份 cron 与手动配置备份都属于设备持久化配置操作；应核对计划设置参数边界、并发写和失败清理。
