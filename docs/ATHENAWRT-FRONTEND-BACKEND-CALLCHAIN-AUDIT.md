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
4. ACL 除 24 个专用脚本外，还授权 `file.exec` 执行 `/etc/init.d/network`、`ping`、`nslookup`、`ubus` 等路径，并对 `file` 提供 exec/write，对多份 UCI 配置提供写权限。需进一步逐项证明这些额外权限是否必要、是否可缩小到专用 RPC；不能只看脚本白名单数量。
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
