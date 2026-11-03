# AthenaWrt 全项目完整优化规划方案（总体架构设计与实施路线图）

> **分析与制定日期**：2026-11-03  
> **项目仓库**：`https://github.com/ethandong06-debug/re-cs02-nss-firmware`  
> **Git 分支**：`athenawrt/apk-fixed-signing`  
> **基准源码快照 SHA**：`bcf1b491e89871ac1687fd2c959da9eb20d647fe`  
> **审计与设计性质**：全项目总体设计与完整优化规划（非局部审计、不直接在无授权下改动源码、不破坏现有运行配置）。  
> **状态区分原则**：严格区分「源码已实现」「静态审计通过」「离线测试通过」「设备验收通过」。代码存在不代表功能可用，RPC 返回成功不代表系统操作成功。

---

## 一、当前项目架构总览

### 1.1 系统整体定位与形态
AthenaWrt 是针对京东云雅典娜（JDCloud RE-CS-02，基于高通 IPQ6018 / IPQ6000 SoC、512MB RAM、64GB eMMC、QCA8081 2.5G PHY、QCN9074 5.2G 独立 PCIe WiFi 芯片）定制的现代化路由器固件控制面板。
- **交付形态**：独立 LuCI 扩展包（`luci-app-athena`，当前构建版本 `1.2.60-r5`），以 APK 软件包形式分发安装于 ImmortalWrt SNAPSHOT（基于 Linux 6.6+ 内核、APK-tools 3.0.5 包管理器、NSS/ECM 硬件加速环境）。
- **非侵入原则**：不替换、不破坏底层的 Linux 系统核心与原生 LuCI 完整体系；原生 LuCI 作为“高级模式”常驻后台。

### 1.2 目录与模块物理结构
```
luci-app-athena-src/
├── Makefile                                    # 独立 APK 构建定义 (PKG_NAME:=luci-app-athena, PKG_RELEASE:=5)
├── configs/                                    # 固件种子配置与软件包清单 (jdcloud_re-cs-02.seed, packages.list)
├── frontend/
│   ├── luci-app-athena/                        # LuCI App 根目录
│   │   ├── Makefile                            # OpenWrt/ImmortalWrt 打包规则与安装目标
│   │   ├── htdocs/luci-static/resources/view/athena/
│   │   │   ├── index.html                      # 液态玻璃产品级单页 SPA (4210 行, 内联 CSS/JS/HTML)
│   │   │   └── index.js                        # LuCI View 薄壳路由重定向入口
│   │   ├── root/
│   │   │   ├── etc/
│   │   │   │   ├── config/athena               # Athena 专有 UCI 配置文件
│   │   │   │   ├── hotplug.d/block/            # 块设备热插拔脚本 (99-athena-filebrowser)
│   │   │   │   ├── init.d/                     # 自启动管理服务 (athena-boot, athena-ui, filebrowser, athena-nas, athena-vlan-pre, athena-netcheck)
│   │   │   │   └── uci-defaults/               # 首开机初始化脚本 (99-athena-defaults, 99-zz-athena-wifi.sh, 99-athena-apps-dns.sh 等)
│   │   │   ├── usr/
│   │   │   │   ├── bin/filebrowser             # FileBrowser ARM64 预编译二进制 (26.5MB)
│   │   │   │   ├── libexec/                    # 后端 RPC 脚本与 ucode 执行引擎 (38 个文件)
│   │   │   │   └── share/
│   │   │   │       ├── athena/oaf-app-map.json # 活跃应用 DNS 指纹匹配字典
│   │   │   │       ├── luci/menu.d/            # LuCI 菜单节点注册 (luci-app-athena.json)
│   │   │   │       └── rpcd/acl.d/             # ubus / rpcd 最小权限 ACL 规则 (luci-app-athena.json)
│   └── rpcd-mod-athena/                        # C 语言编译型常驻 rpcd 插件
│       └── src/athena_stats.c                  # 零 fork/exec 的 /proc 资源状态收集模块
└── .github/workflows/build-athena-apk.yml      # GitHub Actions APK 构建、静态校验与签名工作流
```

### 1.3 技术栈分层架构
1. **展示层（Presentation Layer）**：
   - 基于原生 HTML5 / CSS3（CSS 变量、Flexbox/CSS Grid、Backdrop-filter 液态玻璃视觉质感、SVG 动态渲染、Canvas 图表）。
   - 单文件 SPA 架构，无大型第三方框架（React/Vue）依赖，降低路由器 HTTP 资源消耗。
2. **控制器与通信层（Controller & RPC Adapter）**：
   - 基于 LuCI 的 `ubus` HTTP RPC 接口（`/ubus/`）。
   - 前端通过 `athenaRPC.exec()` 封装，经由 `session.access` 鉴权与 `file.exec` / `file.write` 调用后端。
3. **数据采集与业务逻辑层（Backend Business Layer）**：
   - **C 模块**：`rpcd-mod-athena`（常驻内存，`ubus call athena-stats stats`，纯 `/proc` 内存读取，无进程开销）。
   - **ucode 引擎**：`athena-status.uc`, `athena-rate.uc`, `athena-resources.uc`, `athena-services.uc`, `athena-packages.uc`（直接调用 ucode 进程内 API，高频监控降耗 90%+）。
   - **Shell 模块**：30+ 个专项 Shell 脚本负责 UCI 配置读写、系统命令编排、状态聚合及服务生命周期管理。
4. **系统底层（System & Kernel Layer）**：
   - Qualcomm NSS / ECM 硬件加速驱动、OpenWrt netifd / fw4 (nftables) / uci 体系、Linux 6.6 内核、APK-tools 3.0.5。

---

## 二、完整功能与页面清单

经过对 `index.html`（4210 行）及后端 38 个脚本的全量静态扫描，Athena 共有 **8 个顶层主菜单页面** 与 **1 个全局界面设置弹窗**，包含 46 个业务卡片/子视图、82 个 RPC 触发点及 16 个交互模态框：

| 顶层页面 | 对应 DOM ID | 核心模块 / 卡片 | 交互按钮 / 弹窗 | 后端实现入口 |
|---|---|---|---|---|
| **1. 概览** | `pg-home` | 实时网速仪表盘、核心指标卡 (CPU/内存/连接数/时长)、WAN 状态摘要、设备数量分类、活跃应用推测、网络拓扑示意图、快捷入口 | 测速跳转、体检跳转、指标卡拖拽/排序、快速重启 | `athena-status.sh` (含 `rate` 与 ucode), `athena-apps.sh`, `athena-prefs.sh`, `athena-client.sh` |
| **2. WiFi** | `pg-wifi` | 三频总开关、2.4G 频段卡、5.2G 游戏频段卡、5.8G 频段卡、访客网络卡、三频能力说明 | 单频开关、频段配置弹窗 (SSID/密码/信道/频宽/加密)、恢复默认 WiFi 弹窗、访客开关/配置 | `athena-wireless.sh` (get/set/enable/disable/guest/reset-defaults) |
| **3. 设备** | `pg-dev` | 在线设备统计、设备列表筛选器 (全部/在线/离线/已拉黑)、设备详情行、流量与信号强度、家长控制规则列表 | 设备改名弹窗、已知设备标记/取消、拉黑/解除拉黑、添加/修改家长控制规则弹窗、删除规则 | `athena-client.sh`, `athena-parent.sh`, `athena-status.sh` |
| **4. 网络** | `pg-net` | 组网模式切换器 (主路由/单臂/旁路由/AP)、WAN 接入配置 (PPPoE/DHCP/静态)、单臂 VLAN 拓扑示意与参数配置、网口物理链路状态、一键网络体检、Ping 诊断、外网测速 | 保存应用模式确认弹窗、单臂配置进度轮询浮层、开始体检、开始 Ping、开始测速 | `athena-mode.sh` (含 `single-bg`, `progress`), `athena-scan.sh`, `athena-diag.sh`, `athena-speedtest.sh` |
| **5. 存储** | `pg-st` | 存储中心总览、物理磁盘与分区列表、USB 挂载/卸载管理、FileBrowser 网页文件管理卡、NAS 网络共享卡 (KSMBD / Samba4 双方案) | 磁盘挂载/卸载、USB 格式化确认弹窗 (防错二次输入)、FileBrowser 启停/查看密码弹窗、NAS 安装/切换方案/启停/卸载弹窗、重置 NAS 凭据 | `athena-disk.sh`, `athena-services.sh` (filebrowser-password), `athena-nas.sh` |
| **6. 灯光** | `pg-light` | 前面板点阵屏开关、夜间免打扰模式、显示内容循环选择 (时间/网速/天气/CPU/连接数)、顶部三色呼吸灯状态与色彩选择 | 点阵屏开关、夜间模式时间段设定、显示项勾选保存、LED 颜色/效果切换 | `athena-matrix.sh`, `athena-led.sh` |
| **7. 维护** | `pg-keep` | 设备重启管理、定时重启计划、固件手动升级与校验、恢复出厂设置 (安全挑战码)、配置备份与恢复、系统日志与内核日志查看、管理员密码修改 | 立即重启、保存定时计划、固件上传校验/刷写弹窗、恢复出厂二次确认、立即备份、下载备份、上传恢复配置、刷新日志、修改密码 | `athena-reboot.sh`, `athena-upgrade.sh`, `athena-reset.sh`, `athena-backup.sh`, `athena-log.sh`, `athena-passwd.sh` |
| **8. 高级** | `pg-adv` | 硬件资源监控与进程管理器、受控系统服务列表、硬件加速组件只读状态 (NSS/ECM/PPE)、软件包管理器 (APK) | 进程杀死 (SIGTERM)、服务启动/停止/重启、刷新软件源索引、安装/卸载白名单软件包、跳转原生 LuCI | `athena-resources.sh`, `athena-services.sh`, `athena-accel.sh`, `athena-packages.sh` |
| **全局设置** | `ui-prefs-modal` | 主题选择 (浅色/深色/跟随系统)、默认启动页面、网速单位 (MB/s / Mbps)、界面缩放比例 (85%–115%)、首页指标卡排序 | 保存偏好、重置默认 | `athena-prefs.sh`, `athena-theme.sh`, `athena-ui.sh` |

---

## 三、前端到后端的完整调用链关系

```
[ 用户交互: Browser Web UI (index.html) ]
                  │
                  ▼
         athenaRPC.exec(target, args)
                  │
                  ▼ (HTTP POST /ubus with session token)
         [ uhttpd (Web Server) ]
                  │
                  ▼
         [ rpcd (RPC Daemon) ]
                  │
                  ├── 权限检查: /usr/share/rpcd/acl.d/luci-app-athena.json
                  │    ├─ write.ubus.file: ["exec", "write"]
                  │    └─ write.file: ["/usr/libexec/athena-*.sh": ["exec"], "/tmp/athena-restore.b64": ["write"]]
                  │
                  ├── 常驻 C 插件: rpcd-mod-athena (/proc 扫描, 零进程开销)
                  │
                  ▼
       [ /usr/libexec/athena-*.sh (后端分发器) ]
                  │
                  ├── 性能路径: 优先调用 /usr/bin/ucode athena-*.uc (进程内读文件/uci)
                  │              └─ 失败/异常自动回退: exec athena-*-legacy.sh
                  │
                  ├── 纯 Shell 执行路径 (数据安全校验 -> uci / sysfs / ip / nftables / apk)
                  │
                  ▼
       [ 系统底层组件: Linux 内核 / netifd / fw4 / uci / sysupgrade / qca-nss-ecm ]
```

### 3.1 调用链全量映射表（24 个 RPC 目标与内部辅助模块）

| 前端 RPC 目标脚本 | 对应页面 / 触发功能 | 主要子参数 / Action | 后端调用系统命令与底层路径 | 异常与回退机制 |
|---|---|---|---|---|
| `athena-status.sh` | 概览/设备/网络/全局 | `""` (全量), `rate` (网速) | 读 `/proc/net/dev`, `/proc/stat`, `/proc/meminfo`, `ubus call network.interface.wan status` | 优先 `athena-status.uc`/`athena-rate.uc`，失败回退 `athena-status-legacy.sh` |
| `athena-wireless.sh` | WiFi 页面 | `get`, `enable`, `disable`, `set`, `guest`, `reset-defaults` | `uci get/set/commit wireless`, `wifi reload` | 失败回滚原配置，不重启整网 |
| `athena-client.sh` | 设备管理 | `list`, `notes`, `rename`, `know`, `unlearn`, `block`, `unblock` | `uci athena.client.*`, `nft add/delete element inet fw4 athena_blocked` | 校验 MAC 格式，统一 fw4 nftables 专属 set |
| `athena-parent.sh` | 家长控制 | `list`, `set <mac> <days> <start> <end>`, `clear <mac>` | `uci athena.parent.*`, 写 `/etc/nftables.d/10-athena-parent.nft`, `/etc/init.d/firewall reload` | 跨午夜星期向后平移计算，临时文件原子替换 |
| `athena-mode.sh` | 网络模式向导 | `router`, `ap`, `single`, `bypass`, `single-bg`, `progress` | 备份配置至 `/etc/athena-backup/`, 操纵 `network`/`wireless`/`dhcp`/`firewall`, 重启网络 | 存在全局 `uci commit` 缺陷，待接入原生 LuCI 回滚 |
| `athena-scan.sh` | 网络体检 | `""` (执行诊断) | 检查默认密码、DNS、网关连通性、WiFi 加密等级、磁盘剩余 | 纯只读探测，超时保护 |
| `athena-diag.sh` | 网络诊断 | `check`, `ping <host> <cnt>`, `dns <domain>` | `/bin/ping -c <cnt> -W 2 <host>`, `nslookup <domain>` | 参数过滤，防命令注入 |
| `athena-speedtest.sh`| 外网测速 | `run`, `nodes`, `config` | `curl` 测速节点测流 (分块读取测速) | 15s 强制超时，防止卡死后台 |
| `athena-disk.sh` | 存储中心 | `list`, `mount`, `umount`, `format <dev> <fs>` | 读 `/sys/block`, `lsblk`, `mount /dev/sd* /mnt/usb`, `mkfs.ext4/f2fs` | 仅限真实 USB 分区，禁止触碰 eMMC/系统根分区 |
| `athena-nas.sh` | NAS 网络共享 | `status`, `install <method>`, `start`, `stop`, `uninstall`, `reset-pass` | `apk add/del --simulate`, `uci set ksmbd/samba4`, 管理 `/mnt/usb/AthenaShare` | 依赖保护阻断，数据不删除 |
| `athena-services.sh` | 服务管理 / 凭据 | `list`, `start <id>`, `stop <id>`, `filebrowser-status`, `filebrowser-password` | `/etc/init.d/<id> start/stop`, 读 `/etc/filebrowser.password` | 严格白名单过滤 (ddns/ttyd/matrix)，密码受限读取 |
| `athena-resources.sh`| 资源与进程 | `get`, `kill <pid>` | 读 `/proc/*/stat`, `kill -15 <pid>` 后等待并校验，超时才 `kill -9` | 优先 `athena-resources.uc`，回退 legacy |
| `athena-accel.sh` | 硬件加速状态 | `get` | 检查 `/sys/module/qca_nss_ecm`, `/sys/module/qca_nss_drv` 等 | 只读探测，无配置修改副作用 |
| `athena-packages.sh` | 软件包管理 | `list`, `update`, `install <pkg>`, `remove <pkg>` | `apk update`, `apk add/del --simulate` 预演后执行真实操作 | 核心包白名单保护 (OpenClash/NSS/内核等) |
| `athena-backup.sh` | 备份与恢复 | `list`, `create`, `download <file>`, `restore <file>`, `schedule_get/set` | `sysupgrade -b/-r`, `/etc/athena-backup/`, 操纵 root crontab | 恢复前校验 tar 完整性与路径穿越 |
| `athena-upgrade.sh` | 固件升级 | `verify <file>`, `flash <file> <keep>` | `tar -tzf`, 校验机型/CONTROL/SHA256, 独占锁, `sysupgrade` | 延迟执行并脱离 RPC 进程 |
| `athena-reset.sh` | 恢复出厂 | `prepare`, `confirm <token>` | 生成 256-bit 随机 hex (60s TTL), 校验后执行 `firstboot -y && reboot` | 一次性挑战码防误触与 CSRF |
| `athena-reboot.sh` | 系统重启 | `now`, `schedule_get`, `schedule_set` | `/sbin/reboot`, 写入 crontab 定时任务 | 延迟 2s 重启，保证 HTTP 响应送达 |
| `athena-log.sh` | 系统日志 | `syslog [lines]`, `dmesg [lines]` | `logread -l <lines>`, `dmesg` | 日志敏感信息脱敏 (密码/Token) |
| `athena-passwd.sh` | 密码修改 | `check`, `set <old> <new>` | `uhttpd` / `shadow` / `/usr/bin/passwd` 调用 | 密码复杂度校验，禁止空密码 |
| `athena-matrix.sh` | LED 点阵屏 | `get`, `set <switch> <night> <items>` | 写 `/etc/config/athena`, 驱动 `/dev/ttyMSM*` 或 sysfs 节点 | 格式范围校验 |
| `athena-led.sh` | 顶部三色灯 | `get`, `set <color> <mode>` | 操纵 `/sys/class/leds/*` 触发器与亮度 | 限制预置色彩与模式 |
| `athena-apps.sh` | 活跃应用识别 | `list` | 关联 DNS 缓存与 `oaf-app-map.json` | 标注为 DNS 启发式推测 |
| `athena-prefs.sh` | 用户界面偏好 | `get <key>`, `set <key> <val>` | `uci set athena.prefs.*`, `uci commit athena` | 严格 key/val 白名单 |

---

## 四、原生 LuCI 与 Athena 的职责边界

为彻底避免功能重复开发与系统冲突，确立以下边界矩阵：

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             AthenaWrt 管理控制台                                │
│                                                                                  │
│   ┌─────────────────────────────────────┐  ┌──────────────────────────────────┐  │
│   │        Athena 专属产品层 (SPA)       │  │       原生 LuCI 高级模式 (Raw)    │  │
│   │                                     │  │                                  │  │
│   │  • 雅典娜定制硬件控制 (点阵屏/LED)  │  │  • 完整网络接口/DSA 交换机配置   │  │
│   │  • 三频 WiFi 快捷聚合与管理         │  │  • 复杂防火墙区域/端口转发规则   │  │
│   │  • 单臂路由向导 (保 NSS 加速)       │  │  • 完整 DHCP/DNS/DHCPv6 细节参数 │  │
│   │  • 存储中心 (USB/FileBrowser/NAS)   │  │  • 原生软件包管理器 (完整源配置) │  │
│   │  • 设备识别、图表监控与家长控制     │  │  • OpenClash 插件管理控制台      │  │
│   │  • 一键体检、测速与引导式维护       │  │  • 完整系统日志/启动项/TTY 终端  │  │
│   └─────────────────────────────────────┘  └──────────────────────────────────┘  │
│                      │                                        │                  │
│                      ▼                                        ▼                  │
│            Athena 专有 RPC / ucode                  原生 ubus / rpcd / cbi / ucode│
└──────────────────────┼────────────────────────────────────────┼──────────────────┘
                       │                                        │
                       ▼                                        ▼
    ─────────────────────────────────────────────────────────────────────────────
                             ImmortalWrt 底层系统核心
         Linux Kernel 6.6 / netifd / fw4 (nftables) / uci / qca-nss-ecm
    ─────────────────────────────────────────────────────────────────────────────
```

### 4.1 详细分工与边界定义
1. **网络与接口**：
   - Athena 负责：日常家用模式一键切换（主路由/单臂/旁路由/AP）、WAN 快速拨号/静态配置、单臂 VLAN 自动划分向导、网口物理协商状态可视化。
   - 原生 LuCI 负责：复杂多 WAN/多 LAN 划分、DSA VLAN 过滤细化、IPTV 组播 igmpproxy、自定义静态路由、IPv6 高级前缀委派（PD）调优。
2. **无线与射频**：
   - Athena 负责：三频（2.4G / 5.2G / 5.8G）独立开关、SSID/密码/信道/频宽快捷调节、访客网络隔离、一键恢复默认。
   - 原生 LuCI 负责：802.11r 快速漫游、802.11k/v 漫游辅助、WMM 多媒体参数、Tx 功率微调、MAC 过滤白名单。
3. **防火墙与安全**：
   - Athena 负责：设备一键拉黑（独立 nftables set）、按时间段家长控制上网策略。
   - 原生 LuCI 负责：端口转发、DMZ、NAT66、自定义 nftables 脚本、完整防火墙区域（Zones）规则。
4. **存储与共享**：
   - Athena 负责：USB 硬盘挂载/安全弹出/格式化、FileBrowser 网页管理启停与凭据查看、一键安装/管理 KSMBD/Samba4 NAS。
   - 原生 LuCI 负责：NFS/FTP/WebDAV 手动高级配置、RAID/LVM 卷管理。
5. **系统维护与软件**：
   - Athena 负责：安全挑战码恢复出厂、带校验与平台检查的手动升级、受控配置备份下载/恢复、安全白名单插件安装、设备专属点阵屏/LED 调控。
   - 原生 LuCI 负责：软件源自定义配置、高级系统升级、SSH 密钥管理、TTYD 终端。

---

## 五、全部功能去留决策表

| 功能模块 / 子项 | 当前实现状态 | 决策分类 | 详细依据与处理方案 |
|---|---|---|---|
| **首页实时网速与核心指标** | 源码已实现 (ucode/rate) | **保留并优化** | 真实采集 `/proc/net/dev`，无数据展示占位符，保留 10s 平滑队列。 |
| **活跃应用识别** | 源码已实现 (DNS 匹配) | **保留并澄清** | 保留 DNS 启发式匹配，但 UI 文案明确标注为“DNS 特征推测”，不宣称为 DPI。 |
| **网络拓扑卡** | 静态示例 (写死 VLAN) | **重做** | 改造为根据当前 `athena.system.mode` 动态渲染真实拓扑；无数据时显示示意图说明。 |
| **三频 WiFi 与访客网络** | 源码已实现 (Shell) | **保留并加固** | 恢复默认密码统一为 `12345678` 并提示弱密码；访客 WiFi 独立密码与防火墙隔离。 |
| **设备改名 / 备注 / 拉黑** | 源码已实现 (Shell/nft) | **保留并加固** | 拉黑统一迁移至 fw4 专属 `athena_blocked` 集合，删除按 MAC 全局扫表逻辑。 |
| **家长控制 (时间段/星期)** | 源码已实现 (Shell/nft) | **保留并加固** | 跨午夜算法已修复，增加临时文件原子替换与 firewall reload 失败回滚。 |
| **网络模式一键切换向导** | 源码已实现 (存在提交风险) | **重做 (阻断发布)** | 改造为接入原生 LuCI 的 `apply_rollback` 事务，禁止直接命令行全局 commit。 |
| **网络体检 / Ping / 测速** | 源码已实现 (Shell) | **保留** | 补充超时截断与异常输出过滤，防止卡死。 |
| **USB 磁盘挂载 / 卸载 / 格式化** | 源码已实现 (Shell) | **保留并加固** | 彻底移除 eMMC 格式化前端入口；格式化二次输入绑定磁盘名称，严格 USB 判定。 |
| **FileBrowser 网页文件管理** | 源码已实现 (Binary+Shell) | **保留** | 凭据通过受限 RPC 主动查看并遮罩，不返回明文至页面；拔盘自动停止。 |
| **NAS 网络共享 (KSMBD/Samba4)** | 源码已实现 (r5 Shell) | **保留 (待真机验证)** | 互斥安装、APK 事务预演防破坏 OpenClash/NSS、仅共享 USB 目录。 |
| **LED 点阵屏与顶部三色灯** | 源码已实现 (Shell/sysfs) | **保留** | 雅典娜独有硬件特性，参数白名单过滤，保留开机自启恢复。 |
| **配置备份与恢复** | 源码已实现 (Shell) | **保留并加固** | 修复自动备份未成功即删除旧文件的 Bug；上传恢复增加 tar 路径穿越校验。 |
| **固件手动升级** | 源码已实现 (Shell/sysupgrade)| **保留 (阻断发布)** | 强校验机型/CONTROL/SHA256 与独占锁；须在带外救援就绪后方可验收。 |
| **恢复出厂设置** | 源码已实现 (256-bit Token) | **保留** | 60s 一次性 Token，删除前端即时生效误导，提示不可逆。 |
| **SSH 网页端开关** | 静态假开关 (无真实配置) | **移除候选** | 移至原生 LuCI 系统设置页面处理，Athena 界面不放置假开关。 |
| **PPPoE 密码只读编辑框** | 无后端支持的只读展示 | **合并至网络向导** | 日常网络向导中支持修改；概览页不保留不可保存的假编辑框。 |
| **硬件加速 (NSS/ECM) 状态** | 源码已实现 (只读探测) | **保留 (只读)** | 仅展示模块加载与内核状态，严禁提供任何可能误关 NSS 的前端开关。 |
| **Athena 软件包管理器** | 源码已实现 (ucode/Shell) | **保留 (受控辅助)** | 仅用于 Athena 插件与白名单扩展；核心包拦截保护；高级包管理转原生 LuCI。 |
| **系统日志 / 密码修改 / 重启** | 源码已实现 (Shell) | **保留** | 日志敏感信息脱敏；密码修改校验 shadow 认证；重启延迟响应。 |
| **旧版遗留脚本 (athena-single.sh 等)**| 无调用引用的孤儿脚本 | **移除候选** | 归档确认无依赖后，在清理批次中移除，精简 package 体积。 |

---

## 六、全项目问题清单及优先级划分（P0 / P1 / P2）

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                                问题优先级金字塔                                    │
│                                                                                    │
│   ▲  ┌───────────────────────────────────────────────────────────────────────┐   │
│  ╱█╲ │ P0 (阻断项 / 崩溃与失联风险):                                         │   │
│ ╱███╲│ • 网络模式切换缺少原生 UCI 回滚导致断网失联                             │   │
│╱█████╲│ • 自动备份未校验结果即删除旧文件导致备份丢失                          │   │
│───────│ • 固件升级与单臂切换在无带外救援时可能变砖                           │   │
│  P1   │ • APK 签名 Secret 缺失导致 Actions CI 构建阻断                       │   │
│ 需求与│───────────────────────────────────────────────────────────────────────┤   │
│ 安全项│ P1 (核心安全与功能闭环):                                              │   │
│       │ • rpcd ACL file.exec 范围须做真实 session 越权防护                    │   │
│       │ • 家长控制 / 访客网络多 UCI 配置写入需事务化与原子更新               │   │
│       │ • NAS 软件包安装在 APK-tools 3.0.5 上的实机兼容与依赖模拟            │   │
│       │ • 进程管理器 TERM -> KILL 流程与防误杀机制                           │   │
│───────│───────────────────────────────────────────────────────────────────────┤   │
│  P2   │ P2 (体验 / 性能 / 规范):                                              │   │
│ 体验与│ • SPA 单文件 4200+ 行过大，缺乏模块化与状态机统一管理                │   │
│ 优化项│ • 首屏静态 HTML 假数据在加载失败时未回退“不可用”状态                  │   │
│       │ • 清理无调用的遗留脚本与冗余 CSS，降低 ROM 占用                      │   │
└───────┴───────────────────────────────────────────────────────────────────────┘
```

### 6.1 P0 级问题（阻断发布与设备验收）
1. **[P0-NET-01] 网络模式切换缺少原子事务与原生回滚**
   - *证据位置*：`athena-mode.sh:40-48`, `athena-mode.sh:580-710`
   - *问题表现*：脚本内部直接执行 `uci commit network/wireless/dhcp/firewall` 并异步重启网络，若用户配置了错误参数将导致设备彻底失联且无法自动回滚；同时会强制提交其他 LuCI 页面暂存的未保存配置。
   - *整改方案*：接入原生 LuCI `/admin/uci/apply_rollback` 事务机制，由前端启动倒计时并等待重新握手确认。
2. **[P0-BAK-01] 自动备份未校验执行结果即清理旧文件**
   - *证据位置*：`athena-backup.sh:autobackup()`
   - *问题表现*：调用 `sysupgrade -b` 后未检查退出码与文件体积是否有效，直接按照保留数量删除旧备份，在磁盘空间不足或系统异常时将导致历史有效备份全部丢失。
   - *整改方案*：强制先生成新文件、执行 `tar -tzf` 完整性校验，确认有效后才执行清理。
3. **[P0-CI-01] GitHub Actions APK 签名 Secret 缺失**
   - *证据位置*：`.github/workflows/build-athena-apk.yml:114`
   - *问题表现*：Run #201 因仓库缺少 `ATHENAWRT_APK_SIGNING_KEY` Secret 导致构建终止，无法生成官方公钥签名的 APK。
   - *整改方案*：在 GitHub 仓库中配置持久化签名私钥，并在 CI 中校验公钥指纹。

### 6.2 P1 级问题（核心功能与系统安全）
1. **[P1-SEC-01] rpcd ACL 通用执行与写入权限范围**
   - *证据位置*：`root/usr/share/rpcd/acl.d/luci-app-athena.json:5-10`
   - *问题表现*：ACL 中授权了 `ubus.file: ["exec", "write"]`，虽然在 `file` 节点指定了白名单，但需确保普通未登录/只读角色无法继承该权限。
2. **[P1-FW-01] 家长控制与访客网络防火墙规则原子性**
   - *证据位置*：`athena-parent.sh:27-84`, `athena-wireless.sh:guest`
   - *问题表现*：直接覆盖写规则文件或多处修改 UCI，若中途异常会导致防火墙配置半残。需采用临时文件写入、语法预检、原子 `mv` 替换并在 reload 失败时自动回滚。
3. **[P1-NAS-01] NAS 软件包在 APK-tools 3.0.5 下的事务模拟**
   - *证据位置*：`athena-nas.sh:44-63`
   - *问题表现*：`apk add --simulate` 与 `apk del --simulate` 的文本解析需在真实目标系统上完成输出匹配，避免误判导致受保护核心包被动变更。

### 6.3 P2 级问题（性能优化与交互规范）
1. **[P2-UI-01] SPA 状态机不统一与首屏演示数据残留**
   - *证据位置*：`index.html:150-300`, `index.html:1200-1400`
   - *问题表现*：部分卡片在 RPC 请求失败或无数据时仍然保留 HTML 初始写死的数字（如 CPU 12%、设备 8 台），导致用户误解。需统一使用 5 态数据模型。
2. **[P2-CODE-01] 遗留未引用脚本与重复实现清理**
   - *证据位置*：`athena-single.sh`, `index_v1.2.22_backup.html`
   - *问题表现*：存在不再被 RPC 直接调用的历史孤儿脚本与备份文件，占用软件包体积，需归档清理。

---

## 七、全项目统一 UI/UX 设计规范

### 7.1 设计语言：Liquid Glass（液态玻璃）
Athena 确立专有的现代工控与消费级融合视觉语言，摒弃传统路由器的粗糙表单与紫白平铺模板：
- **基底与光斑**：采用多重径向渐变（Radial Gradients）模拟呼吸环境光，浅色模式为温润通透蓝灰白，深色模式为沉浸深邃暗夜黑。
- **材质系统**：
  ```css
  /* 核心卡片材质规范 */
  --card: rgba(255, 255, 255, 0.72);      /* 浅色模式: 72% 高透白 */
  --card-solid: #ffffff;
  --glass-blur: 20px;                      /* 20px 高斯毛玻璃模糊 */
  --border: rgba(20, 35, 58, 0.09);        /* 微弱外描边 */
  --shadow: 0 10px 36px rgba(31, 61, 110, 0.10); /* 柔和悬浮投影 */
  ```
  ```css
  /* 深色模式材质规范 */
  html[data-theme="dark"] {
    --card: rgba(22, 27, 38, 0.75);        /* 75% 深蓝灰 */
    --card-solid: #171c26;
    --border: rgba(255, 255, 255, 0.07);
    --shadow: 0 10px 36px rgba(0, 0, 0, 0.35);
  }
  ```
- **色彩与层级**：
  - Primary（主品牌蓝）：`#185FA5`（深色 `#4A9DE0`），用于核心操作、聚焦高亮、选中 Tab。
  - Success（正常/在线/上传）：`#16A34A`（深色 `#34D399`）。
  - Warning（警告/未保护）：`#D97706`（深色 `#F0A028`）。
  - Danger（危险/离线/错误）：`#DC2626`（深色 `#F87171`）。
  - Download（下行下载）：`#378ADD`。

### 7.2 响应式与触控基线
- **桌面端（≥1024px）**：多列自适应网格（Grid 2-3 列），导航栏固定顶部横向排列，充分利用 1560px 宽屏空间。
- **平板与移动端（<768px）**：单列弹性流式布局，卡片内边距收敛至 14px，所有点击按钮/开关的触控热区严格保证 **≥44px × 44px**，避免误触。
- **视口安全**：严格配置 `<meta name="viewport" content="width=device-width, initial-scale=1">`，保证不出现水平横向滚动条，内容纵向平滑滚动。

### 7.3 统一组件规范
1. **按钮与开关**：
   - 主按钮（`.btn.btn-primary`）：主色填充，点击带微缩微动效。
   - 危险按钮（`.btn.btn-danger`）：高亮红底，必须绑定二次确认防误触弹窗。
   - 切换开关（`.switch`）：标准 iOS 式平滑滑块，附带 `aria-checked` 无障碍支持。
2. **模态弹窗（Modals）**：
   - 居中毛玻璃遮罩，按 `Esc` 或点击遮罩可关闭（危险操作除外）。
   - 弹窗头部带明确标题与关闭按钮，底部标准操作对齐（取消居左、确定居右）。

---

## 八、前端架构与数据状态管理优化方案

### 8.1 统一数据状态机（Five-State Data Model）
前端所有数据卡片和指标必须严格遵循 **五态状态模型**，彻底根除静态演示数据污染：

```
                    ┌──────────────┐
                    │ 1. LOADING   │ 初始或刷新中 (显示呼吸骨架屏)
                    └──────┬───────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      [ RPC 请求成功 ]            [ RPC 请求失败 ]
             │                           │
      ┌──────┴───────┐            ┌──────┴───────┐
      │   2. LIVE    │            │   4. ERROR   │
      │ 真实数据更新 │            │ 显示错误与重试│
      └──────┬───────┘            └──────┬───────┘
             │                           │
      [ 定时采样中断 ]            [ 设备不支持此功能 ]
             │                           │
      ┌──────┴───────┐            ┌──────┴───────┐
      │   3. STALE   │            │5.UNSUPPORTED │
      │灰显+最后时间 │            │隐藏或显示不可用│
      └──────────────┘            └──────────────┘
```

1. **`LOADING`（加载中）**：显示微光骨架屏动画或旋转指示器，禁止显示预设的“12% CPU / 192.168.1.1”等虚构数据。
2. **`LIVE`（实时在线）**：显示后端返回的实时数据，并在卡片角落记录最后同步时间（如 `刚刚更新`）。
3. **`STALE`（数据陈旧）**：若轮询断流，保留上次数据但整体低对比度灰显，并标注 `更新于 30 秒前`。
4. **`ERROR`（获取失败）**：显示红灰色警告图标与具体错误原因，并提供 `点击重试` 按钮。
5. **`UNSUPPORTED`（不支持）**：若硬件无此模块（如未插 USB 盘、无对应传感器），直接显示 `未检测到设备` 或优雅折叠。

### 8.2 统一操作反馈与防重提交
- 所有写操作按钮在触发后立即置为 `disabled` 状态，文案切换为 `处理中...` 并显示 Spinner。
- 后端 RPC 返回 `ok: true` 后才弹出成功 Toast 并局部刷新受影响数据；返回 `ok: false` 时展示后端真实错误信息，界面状态恢复为修改前状态，严禁“假成功”。

---

## 九、后端 RPC、Shell、ucode、C 模块优化方案

### 9.1 C 模块（`rpcd-mod-athena`）优化
- **职责**：作为常驻动态库（`/usr/lib/rpcd/athena_stats.so`），提供高频资源监控 API。
- **优化点**：
  1. 采用零 fork/exec 的直接 `/proc/stat`, `/proc/meminfo`, `/proc/[pid]/stat` 解析，保持毫秒级响应。
  2. 修复 `read_cpu_totals` 与 `parse_stat` 对进程状态变化的边界保护，对内核线程进行准确过滤。
  3. 限制最大进程扫描数量为 512，防止内存突增。

### 9.2 ucode 进程内执行引擎优化
- **职责**：替代执行缓慢的多进程管道 Shell 脚本（如旧版状态脚本单次需要 294 次 `execve`，在设备上耗时 1.41s）。
- **优化点**：
  1. `athena-status.uc` 与 `athena-rate.uc`：在 ucode 解释器内直接调用 `fs.readfile()` 与 `uci.cursor()`，单次运行时间压降至 10ms 以内，支持首页 2 秒高频平滑采样。
  2. `athena-services.uc`, `athena-resources.uc`, `athena-packages.uc`：统一 JSON 输出 Schema，确保与 legacy shell 版输出完全 100% 兼容。
  3. 建立自动 fallback 机制：若目标机未安装 ucode 或执行出错，主脚本无缝降级执行 legacy shell 脚本。

### 9.3 Shell 脚本鲁棒性与安全性规范
- 所有 Shell 脚本严格声明 `set -u`（禁止未定义变量）或显式安全处理变量。
- **输出管道分离**：脚本 `stdout` 严格只输出最终的标准 JSON，所有调试、进度、错误信息一律重定向至 `stderr`（`>&2`），绝不允许混入 stdout 导致前端 `JSON.parse` 崩溃。
- 所有入参必须经过严格格式与长度白名单校验（如 `valid_mac`, `valid_ipv4`, `valid_ssid`, `valid_pass`），杜绝 Shell 元字符注入。

---

## 十、网络管理及现有配置保护方案

### 10.1 现有核心网络保护铁律
在任何情况下，优化方案与后续实施严格遵守以下不动原则：
- **现网 PPPoE 拨号配置**：保持现有账号、密码及 MTU 逻辑不变。
- **现网 VLAN 2044 与 IPTV 拓扑**：保留 wan.2044 拨号 VLAN、wan.1 内网回传与 wan.3066 IPTV 透传定义。
- **IPv6 PD / SLAAC**：保留现网 DHCPv6 客户端与下发前缀配置。
- **防火墙与 NAT**：不修改 fw4 既有区域结构与 OpenClash 重定向链。
- **NSS / ECM 硬件加速驱动**：绝不在网络脚本中调用 `stop qca-nss-ecm` 或重置加速模块。

### 10.2 原生 UCI 回滚接入架构（解决网络模式失联风险）
为彻底解决网络模式切换时的设备失联问题，放弃独立的脆弱 watchdog 脚本，全面接入 ImmortalWrt 原生 LuCI 事务机制：

```
[ Athena 页面发起模式切换 ]
            │
            ▼
1. 建立独立 UCI Session 暂存配置变更 (不执行全局 uci commit)
            │
            ▼
2. 调用 LuCI 原生 RPC: /admin/uci/apply_rollback
   └─ 系统生成一次性确认 Token，启动 60 秒自动回滚定时器
            │
            ▼
3. 系统应用新网络配置并重启 netifd
            │
            ▼
4. 前端启动重新连接探测 (在新管理 IP / 原管理 IP 轮询握手)
            │
    ┌───────┴───────┐
    ▼               ▼
[ 握手成功 ]    [ 60 秒超时未连通 ]
    │               │
    ▼               ▼
5. 前端调用:     系统内核自动触发回滚:
/admin/uci/confirm  还原所有网络配置至切换前状态
(完成永久生效)      (设备网络自动恢复)
```

---

## 十一、NSS/ECM 和系统性能优化方案

### 11.1 硬件加速状态与保护
- **只读监测机制**：`athena-accel.sh` 仅检查 `/sys/module/qca_nss_ecm`, `/sys/module/qca_nss_drv`, `/sys/kernel/debug/ecm` 的运行状态与连接数，明确告知用户“当前 NSS 硬件加速已激活”。
- **禁止前端干扰**：严禁在前端提供“开关硬件加速”的按钮，防止用户误触导致网络下陷至内核 CPU 软转发。
- **单臂路由 NSS 保障**：单臂模式严格采用三层 802.1Q 子接口（`wan.1`, `wan.2044`）桥接方案，不开 `br-lan` 的 `vlan_filtering`，确保高通 NSS 硬件加速芯片全速工作。

### 11.2 长期运行内存与 CPU 控制
- 定时轮询接口（实时网速、CPU 占用）全面切换为 ucode 或 C 模块，杜绝频繁 fork 进程导致的 CPU 尖刺。
- 浏览器端停止非当前活动 Tab 的高频轮询（通过 `document.hidden` 监听），切换至后台页面时自动暂停轮询，节省路由器 CPU 算力与网络带宽。

---

## 十二、流量统计、设备识别和历史数据方案

### 12.1 设备识别（Device Identification）
- **数据源聚合**：整合 `/tmp/dhcp.leases`（租约信息）、`/proc/net/arp`（ARP 表）、`ip neigh`（邻居发现）以及 WiFi 关联列表（`iwinfo`），生成高精度在线设备列表。
- **设备指纹与厂商库**：通过 MAC 前 3 字节（OUI）内置离线厂商特征库，精准识别 Apple、Xiaomi、Huawei、Sony 等设备品牌，用户可自定义设备名与图标。
- **活跃应用识别规范**：明确定义为基于 DNS 访问记录与 `oaf-app-map.json` 的指纹推测，界面如实标注，杜绝夸大为“深度包检测（DPI）”。

### 12.2 流量采样与平滑算法
- 实时网速采用 2 秒采样周期，在前端使用指数移动平均（EMA）进行平滑处理，消除瞬时网络抖动引起的仪表盘剧烈跳变。
- 设备历史流量保存在内存环形缓冲区（Ring Buffer）中，支持查看最近 1 小时/24 小时的流量分布趋势，不写入闪存，保护 eMMC 寿命。

---

## 十三、备份、恢复、升级和危险操作安全方案

### 13.1 配置备份与恢复安全加固
1. **备份安全（`athena-backup.sh`）**：
   - 备份文件统一保存在 `/etc/athena-backup/`，格式为 `config-YYYYMMDDHHMMSS.tar.gz`。
   - `autobackup` 逻辑改造：必须在 `sysupgrade -b` 执行成功且 `tar -tzf` 验证通过后，才允许执行保留份数清理；若生成失败，保留所有旧备份并记录错误日志。
   - 备份下载通过 base64 流式传输，不将文件复制到 Web 根目录，防止未授权外部下载。
2. **恢复安全（`restore` & `restore-upload`）**：
   - 上传恢复强制增加 10MB 大小上限拦截。
   - 严格解包预检：检查 tar 归档内的文件路径，拒绝任何包含 `../` 路径穿越、绝对路径 `/`、符号链接及设备节点的恶意压缩包。

### 13.2 固件升级安全规范（`athena-upgrade.sh`）
- **双重校验机制**：
  1. *前端上传验证（Verify）*：检查固件格式、提取 CONTROL 信息、匹配机型 `jdcloud,re-cs-02`、计算 SHA256。
  2. *后端刷写二次校验（Flash）*：后端独立从暂存区读取文件，重新执行平台兼容性检查（`sysupgrade -T`）与 SHA256 校验，防止前端篡改。
- **并发锁与进程脱离**：采用目录独占锁防止并发刷写，通过后台子进程延迟执行 `sysupgrade`，保证 RPC 响应先完整送达前端。

### 13.3 恢复出厂设置（`athena-reset.sh`）
- 采用 256-bit 加密安全随机 Token，有效生命周期为 60 秒。
- 确认操作时一次性消费 Token（即刻销毁），校验通过后延迟 2 秒调用 `firstboot -y && reboot`，杜绝 CSRF 与误触风险。

---

## 十四、软件包、NAS、服务管理优化方案

### 14.1 存储中心与 NAS 共享（`athena-nas.sh`）
- **双方案互斥管理**：提供 **KSMBD**（内核级轻量，默认推荐）与 **Samba4**（全功能兼容）二选一机制，同一时刻只允许一套 SMB 服务受 Athena 管理。
- **依赖安装安全预演**：
  - 安装前必须执行 `apk add --simulate <pkg>`。
  - 解析事务输出，若发现涉及 `openclash`, `qca-nss-*`, `kernel`, `firewall4`, `netifd`, `apk-tools` 等核心组件的升级、降级或删除，立即无条件拒绝安装。
- **严格目录与权限隔离**：
  - 共享路径严格限制在 `/mnt/usb/AthenaShare`，必须基于真实挂载的 USB 文件系统，禁止共享系统 rootfs 或 overlay 分区。
  - 自动创建独立的 `athena-nas` 系统用户与 32 字符随机密码，默认禁用 Guest 匿名访问，限制仅 LAN 接口监听。
- **卸载保护**：卸载仅停止服务并清理 Athena 安装的软件包，绝不删除磁盘上的用户数据文件。

### 14.2 FileBrowser 网页文件管理
- 预编译独立 ARM64 二进制，监听 LAN IP 的 8081 端口，根目录绑定 `/mnt/usb`。
- 随机密码保存在 `/etc/filebrowser.password`（权限 `0600`），前端提供主动点击、安全遮罩、一键复制的凭据查看弹窗；拔出 U 盘时通过 hotplug 自动停止服务。

### 14.3 关键系统组件保护白名单
在 Athena 软件包管理器与服务管理中，建立核心保护清单：
```
受保护核心组件：
├── 代理与核心: luci-app-openclash, mihomo, sing-box
├── 硬件加速:   kmod-qca-nss-drv, kmod-qca-nss-ecm, qca-ssdk
├── 系统网络栈: base-files, busybox, netifd, firewall4, nftables, odhcpd
└── 基础框架:   apk-tools, rpcd, ubus, uhttpd, kernel
```
Athena 界面隐藏以上组件的删除/替换入口，后端脚本层级实施强制拦截。

---

## 十五、安全、ACL、权限和数据保护方案

### 15.1 rpcd 最小权限 ACL 治理
- 维护 `/usr/share/rpcd/acl.d/luci-app-athena.json`：
  1. `file.exec` 严格收敛至 24 个经过安全审计的 `/usr/libexec/athena-*.sh` 绝对路径。
  2. `file.write` 仅开放受保护的临时文件 `/tmp/athena-restore.b64`。
  3. 严禁开放通用的 shell 执行或任意路径写权限。

### 15.2 敏感数据脱敏与保护
- **密码存储**：管理员密码、WiFi 密码、FileBrowser 密码、NAS 密码严禁记录到系统日志或明文持久化在 Web 目录。
- **日志脱敏**：`athena-log.sh` 在读取 `syslog` 与 `dmesg` 输出时，自动正则过滤 Token、Cookie、Password 等敏感字段。

---

## 十六、构建、签名、CI 和发布方案

### 16.1 GitHub Actions 自动化流水线
完善 `.github/workflows/build-athena-apk.yml`：
1. **静态代码质量门禁**：
   - 对所有 38 个 libexec Shell 脚本执行 `sh -n` 语法分析。
   - 对 `index.html` 内联 JavaScript 提取并执行 `node --check` 语法与运行时错误分析。
   - 对 LuCI 菜单 JSON、rpcd ACL JSON 执行严格的 Schema 与路径闭环校验（确保每个前端 RPC 调用点在 Makefile、ACL、文件系统中 100% 对应）。
2. **构建与签名机制**：
   - 依赖 GitHub Actions Secret `ATHENAWRT_APK_SIGNING_KEY` 注入官方私钥。
   - 启用 OpenWrt/ImmortalWrt 官方签名参数：`CONFIG_USE_APK=y` 与 `CONFIG_SIGN_EACH_PACKAGE=y`。
   - 自动生成 SHA256 校验和并上传 Artifact，杜绝未签名或不受信软件包进入设备。

---

## 十七、完整离线测试与设备验收矩阵

| 测试领域 | 离线 / CI 自动化测试项目 | 真机设备验收标准（须带外救援就绪） | 当前验证状态 |
|---|---|---|---|
| **前端 SPA 界面** | 1. Node.js JS 语法检查<br>2. HTML 标签闭合与 CSS 变量校验<br>3. 全屏幕断点与主题切换逻辑 | 1. 移动端/桌面端全页面渲染无错位<br>2. 按钮加载与防重提交正常<br>3. 真实数据五态展示无白屏 | 静态通过 / 待设备验收 |
| **RPC 与 ACL** | 1. 前端 RPC 与 ACL 路径 100% 匹配校验<br>2. 参数注入与越界字符测试 | 1. 登录会话调用无 Permission Denied<br>2. 非法参数被后端拦截并返回规范 JSON | 静态通过 / 待设备验收 |
| **网络模式切换** | 1. 语法检查与配置模板测试<br>2. 故障模拟与回滚分支静态核验 | 1. 单臂/主路由/AP 切换成功<br>2. 模拟断网 60s 内自动回滚恢复原网络 | 待接入原生回滚 / 待设备验收 |
| **三频 WiFi** | 1. 信道/频宽/加密参数校验函数测试<br>2. 默认密码与访客隔离逻辑 | 1. 三频独立配置生效，连接正常<br>2. 恢复默认密码为 12345678<br>3. 访客网络正常隔离且可上网 | 静态通过 / 待设备验收 |
| **存储与 NAS** | 1. APK 依赖事务模拟器逻辑测试<br>2. 磁盘路径过滤与真实 USB 判定测试 | 1. USB 挂载/卸载正常，拔盘自动停止服务<br>2. KSMBD/Samba4 正常挂载与读写<br>3. FileBrowser 正常访问 | 静态通过 / 待设备验收 |
| **备份与恢复** | 1. 损坏 tar 包、超大包、路径穿越注入测试<br>2. 自动备份失败清理拦截测试 | 1. 备份下载为完整 tar.gz<br>2. 上传恢复配置后管理面正常重连 | 静态通过 / 待设备验收 |
| **固件升级** | 1. 错误机型、坏 tar、SHA256 篡改包拦截测试<br>2. 目录独占锁并发测试 | 1. 上传官方固件校验通过<br>2. 仅在测试机且串口连接下执行真实刷写 | 阻断真机 / 离线待测 |
| **恢复出厂** | 1. Token 过期、重放、格式错误拦截测试 | 1. 输入正确确认码后设备成功 firstboot 重启 | 静态通过 / 待设备验收 |
| **NSS 硬件加速** | 1. sysfs 探测脚本兼容性测试 | 1. 确认高通硬件加速驱动运行，流量命中 NSS | 静态通过 / 待设备验收 |

---

## 八、分阶段实施计划与验收标准

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              AthenaWrt 实施路线图                                      │
│                                                                                        │
│  Phase 1: 架构收敛与安全加固 (P0/P1)                                                    │
│  ├── 1. 恢复 GitHub Actions APK 签名 Secret (解决构建阻断)                             │
│  ├── 2. 修复备份脚本 (校验成功后才清理旧文件)                                          │
│  ├── 3. 接入原生 LuCI apply_rollback 事务机制改造网络模式切换                          │
│  └── 4. 固件升级与恢复出厂安全逻辑全量闭环                                             │
│                                                                                        │
│  Phase 2: 前端重构与状态机规范化                                                       │
│  ├── 1. 全面落地数据五态模型 (彻底清理首屏静态演示数据)                                │
│  ├── 2. 统一按钮防重提交与错误反馈 Toast                                               │
│  └── 3. 优化移动端触控尺寸与图表自适应                                                 │
│                                                                                        │
│  Phase 3: 存储中心、NAS 与增值能力完善                                                 │
│  ├── 1. 验证 KSMBD / Samba4 双方案 APK 依赖事务与实机读写                             │
│  ├── 2. 完善 FileBrowser 凭据查看与生命周期管理                                         │
│  └── 3. 优化家长控制原子更新与设备识别库                                               │
│                                                                                        │
│  Phase 4: 离线自动化测试、包构建与最终设备验收                                         │
│  ├── 1. CI 全量自动化语法、ACL 映射与安全静态测试                                      │
│  ├── 2. 产出带官方持久签名的 Release APK (1.2.60-r5+)                                  │
│  └── 3. 搭建带外串口救援环境，在授权下执行真实设备验收                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 18.1 各阶段准入与准出标准
- **Phase 1 准出标准**：所有 P0 级安全缺陷代码修改完成，CI 静态分析全部通过，无任何未经验证的直接 commit 风险。
- **Phase 2 准出标准**：SPA 页面彻底消除假数据残留，所有操作具备完整的 pending/success/failure 反馈。
- **Phase 3 准出标准**：存储中心三模块（磁盘/FileBrowser/NAS）成套验证通过，核心包白名单拦截有效。
- **Phase 4 准出标准**：GitHub Actions 构建出签名完整的 APK，且在测试设备上完成全功能验收，现网 PPPoE/VLAN/IPv6/NSS 零破坏。

---

## 十九、当前未解决问题及依赖条件清单

1. **[依赖项] GitHub Actions 仓库 Secret 恢复**：
   - *说明*：需要仓库管理员在 GitHub Settings 中配置 `ATHENAWRT_APK_SIGNING_KEY` 私钥，否则 CI 无法产出合法签名的 APK。
2. **[依赖项] 原生 LuCI apply_rollback 接口参数实测**：
   - *说明*：需要在真实固件环境中抓取当前 LuCI 版本的 `/admin/uci/apply_rollback` 与 `/admin/uci/confirm` 调用报文格式，确保 Athena RPC 适配器参数完全吻合。
3. **[依赖项] 物理设备带外串口救援条件**：
   - *说明*：在执行固件升级、网络模式切换等破坏性测试前，必须确保路由器的 TTL 串口调试线或 U-Boot TFTP 救援环境可用，绝不在无救援保障的主力路由器上盲测。

---

*文档完结。本规划作为 AthenaWrt 项目后续所有开发、重构、测试与验收的总体指导依据。*
