# AthenaWrt 当前源码复核与全站调用链补充审计

> 日期：2026-11-03  
> 分支：`athenawrt/apk-fixed-signing`  
> 本文性质：只读源码复核、功能调用链补充与去留建议；不代表功能已修改或设备已验收。  
> 保护红线：不改 PPPoE、VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM；不刷机、不切换网络、不重启、不格式化、不执行危险 RPC。

## 1. 本次复核基线

### 1.1 GitHub 分支、提交与工作流

| 项目 | 当前证据 |
|---|---|
| 仓库 | `ethandong06-debug/re-cs02-nss-firmware` |
| 分支 | `athenawrt/apk-fixed-signing` |
| 最新 HEAD | `bdb639b270a80701501f8c3b4e9afb869e655581` |
| HEAD 提交说明 | `docs: remove reverted C3-A implementation checkpoint` |
| 最近源码提交 | `e355f81fd508575ba2e07c4b9939aab60ebddd9c` |
| 源码提交说明 | `revert: restore Athena UI before C3-A trial` |
| 当前 SPA blob | `c48b01b2cce85e73a5367699a8bfee55fd96aa73` |
| 最近成功构建 | Actions Run #191，ID `41472009979` |
| Run #191 源码提交 | `e355f81fd508575ba2e07c4b9939aab60ebddd9c` |
| 构建结果 | success；14 个主要步骤成功 |
| Artifact | `luci-app-athena-apk`，ID `13160465732` |

HEAD `bdb639b` 是文档提交，当前 SPA 源码仍来自 `e355f81`。Run #191 成功构建的版本仍标记为 `1.2.60-r2`，并非新版本号。

Run #191 构建日志记录：
- 主 APK：`luci-app-athena-1.2.60-r2.apk`，24,545,434 bytes。
- 主 APK SHA-256：`2ad9c9972db775d71b767bd9c7e2d068f3b2019572ee7c7150b60becf48287be`。
- 中文包：`luci-i18n-athena-zh-cn-0.apk\)，952 bytes。
- 中文包 SHA-256：`e1ab1827afcb6f93017ac278fa7b6ba645b18c7bd00f3383de29968abe057727`。
- 两个 APK 的构建端签名验证均为 `OK\)，临时 APK 数据库依赖模拟通过，Artifact 上传成功。
- 构建期间出现 Makefile recipe override 警告和 Node.js 20 弃用警告；未导致本次构建失败，仍应作为构建维护项跟踪。

### 1.2 设备端验收与 Run #191 的区别

当前项目状态文档记录的真机安装对应 Run #188（ID `41436896339`），设备已安装 `1.2.60-r2\)，两个 APK 的设备端 SHA-256 与 Run #188 Artifact 清单一致，设备端验签通过，模拟升级与正式安装通过，原 root 密码 SSH 登录成功，LuCI 首页完成初步目视检查。

Run #188 设备端主 APK SHA-256：
`417db3ef8d4012f1977fb0941ab858703a1e43c5ce130e68a2a2b031ccf7ad78`

Run #188 设备端中文包 SHA-256：
`347bbfa24a29f2f7f75ea85eb08269bd249a3fbf64604a93e6a025bda9464654`

**Run #191 的主 APK SHA-256 与 Run #188 不同，Run #191 Artifact 尚无设备安装记录。** 两次包的版本字符串都为 1.2.60-r2，不能因此认定二者代码内容相同。当前设备端验收结论只适用于 Run #188 对应的实际安装包；不能把 Run #191 的构建成功等同于其源码已经真机验收。

尚未完成的设备验收仍包括：全站逐页面/逐按钮验收、FileBrowser Quantum 真机验收、访客网络隔离验收、服务/进程/日志功能专项验收，以及原生 LuCI 菜单路径核验。

### 1.3 当前源码规模与调用数量

当前正式 SPA：
- `index.html`：4,106 行、284,481 字节。
- 扫描到 `athenaRPC.exec(...)`：79 处。
- 唯一直接 RPC 脚本目标：24 个。
- 动态脚本目标：1 个，变量 `cfg.f`。
- 旧审计文档中 4,218 行、291,149 字节、82 处调用的数字属于旧源码基线，不能继续作为当前数字。

Makefile 当前安装 36 个 libexec 文件：
- 31 个 Shell 文件：24 个正式前端入口、6 个内部 legacy/helper、1 个尚未证明有调用者的 `athena-single.sh\)。
- 5 个 ucode 文件。
- rpcd ACL 对 24 个正式脚本入口提供执行授权。
- `athena-single.sh` 没有发现正式 SPA 或 `athena-mode.sh` 调用证据，暂列为“已安装但未证实被调用”，不得擅自删除。
- `athena-services.sh filebrowser-password` 子命令存在，但当前 SPA 搜索不到调用点；它不是第 25 个脚本入口。

## 2. 当前页面、控件、参数、RPC 与后端调用链

说明：
- 下表按当前 SPA 最终生效的函数定义整理；同名函数以文件中最后生效的定义为准。
- “本地”表示没有设备配置副作用；“真实 RPC”表示源码确有后端调用，不等于设备功能已通过验收。
- 页面中的静态 HTML 和 JS 动态生成的 modal/row 同时存在；静态源代码中的控件数不能直接当作同一时刻的可见控件数。

### 2.1 概览

| 控件/动作 | 前端函数 | 参数/状态 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| WiFi、设备、网络、高级入口 | `goto()`、`navGo()` | 页面 ID | 无 | 本地导航，保留 |
| CPU、内存、WAN、IPv6、运行时间、在线设备 | 状态渲染/定时刷新 | 无 | `athena-status.sh`；设备数据由 status/client 采集 | 只读，保留 |
| 活跃应用 | 应用卡渲染 | 最近时间窗 | `athena-apps.sh list` | DNS/OAF 域名线索推测，不是 DPI；需明确标注 |
| 访客网络快捷操作 | `toggleGuest()` | enabled/disabled | `athena-wireless.sh guest get/enable/disable` | 真实写操作；访客密码前端当前固定，须重做 |
| KPI 排序 | `openSortModal()`、排序保存函数 | KPI ID 顺序 | `athena-prefs.sh get/set` | 本地拖动 + 偏好持久化，保留 |
| 网络拓扑 | 静态 HTML | 固定设备数、端口、VLAN 文案 | 无 | 非实时数据；当前标注“示意”仍有硬编码误导，移除首页主卡候选 |

### 2.2 WiFi

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 总开关 | `toggleWifiAll()` | all | `athena-wireless.sh enable/disable all` | 真实写操作 |
| 三频开关 | `toggleBand()` | b24/b52/b58 | `athena-wireless.sh enable/disable <band>` | 真实写操作 |
| 编辑 SSID/密码/信道/频宽/加密 | `editBand()`、`saveBand()` | band、SSID、密码、channel、bandwidth、encryption | `athena-wireless.sh set` | 真实写操作；高级无线配置优先原生 LuCI |
| 访客网络状态 | `loadGuest()` | 无 | `athena-wireless.sh guest get` | 只读 |
| 访客网络启用 | `openGuestModal()`、`saveGuest()` | SSID、password | `athena-wireless.sh guest enable <ssid> <password>` | 当前前端把密码硬编码为 12345678，必须重做 |
| 访客网络关闭 | `toggleGuest()` | disable | `athena-wireless.sh guest disable` | 真实写操作；多配置非事务写入 |
| 恢复默认 WiFi | `resetWifi()`、`doResetWireless()` | reset-defaults | `athena-wireless.sh reset-defaults` | 后端生成随机密码并返回 password；前端当前显示固定 12345678 且丢弃返回值，必须修复后才能开放 |

### 2.3 设备

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 全部/在线/离线 | `switchDevTab()` | all/online/offline | 无 | 本地筛选 |
| 新设备提醒 | `devNew()` | 无 | 无直接 RPC；依赖已加载的设备列表 | 当前函数只切到全部列表并高亮第 0 行，不能准确定位 NEW_DEVS；重做 |
| 设备列表/详情 | `loadStatus()`、`devDetail()` | MAC/设备索引 | `athena-status.sh`、`athena-client.sh list` | 只读 |
| 备注 | `saveDevNote()` | MAC、note | `athena-client.sh note` | UCI 写入 |
| 改名 | `doRename()` | MAC、name | `athena-client.sh rename` | DHCP host/UCI 写入 |
| 认识/取消认识 | `knowDev()` 等 | MAC | `athena-client.sh know/unlearn` | UCI 写入 |
| 拉黑/解除拉黑 | `doBlock()`、`doUnblock()` | MAC | `athena-client.sh block/unblock` | nftables/iptables/UCI 写入；规则所有权与 IPv6 需专项验证 |
| 家长控制 | `openParentAdd()`、`saveParent()`、`cancelParent()` | MAC、星期、开始/结束时间 | `athena-parent.sh list/set/clear` | nftables/UCI 写入；原子更新和跨日规则需专项验证 |

### 2.4 网络

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 模式选择 | `pickMode()`、`setWanProto()` | router/single/bypass/ap、协议 | 暂存前端表单 | 本地状态，不代表已应用 |
| 保存并应用 | `saveApply()`、`confirmApply()`、`doApply()` | 模式、WAN 协议、账号、密码、VLAN 等 | `athena-mode.sh` 对应 router/single-bg/ap/bypass 流程 | 高风险网络写操作；本轮禁止执行 |
| 单臂进度 | 进度轮询 | task/status | `athena-mode.sh progress` | 只读 |
| 一键体检 | `runScan()` | 无 | `athena-scan.sh` | 只读检测/探测 |
| 连通性诊断 | `runDiag()` | 诊断类型 | `athena-diag.sh check` | 外部探测 |
| Ping | `runPing()` | host/count 等 | `athena-diag.sh ping` | 外发探测；参数须后端校验 |
| 测速 | `changeSpeedNode()`、`runSpeed()` | 节点/引擎 | `athena-speedtest.sh` | 产生公网流量 |
| PPPoE 密码输入框 | HTML onchange | 无 | 仅 `done('宽带密码已更新')`，无 RPC | 假编辑控件；改为只读状态或原生 LuCI 入口，不得伪称已修改 |

### 2.5 存储

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 刷新磁盘 | `refreshDisks()`、`loadDisks()` | list | `athena-disk.sh list` | 只读 |
| 挂载 | `mountUsb()` | USB 分区、固定 /mnt/usb | `athena-disk.sh mount` | 真实写操作 |
| 卸载 | `umountUsb()` | USB 分区 | `athena-disk.sh umount` | 真实写操作 |
| 格式化 | `fmtDisk()`、`fmtDiskDo()` | 设备、ext4/vfat/exfat/f2fs | `athena-disk.sh format` | 不可逆；后端限定真实 USB 分区并拒绝挂载/swap/系统盘；当前静态 HTML 仍显示 eMMC 格式化按钮，必须隐藏/禁用 |
| 打开文件共享 | `openFbModal()` | LAN hostname、8081 | 访问 FileBrowser Quantum | 真实服务入口，但当前前端凭据错误 |
| FileBrowser 初始密码读取 | 后端 `athena-services.sh filebrowser-password` | 无 | 返回 username=admin 和随机密码 | 后端能力存在；SPA 当前没有调用点，凭据链未闭合 |

### 2.6 灯光

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 点阵屏状态/刷新 | `loadMatrixAll()` | get | `athena-matrix.sh get` | 只读 |
| 点阵屏总开关、亮度、模式、项目、夜间计划 | `toggleMatrix()`、`setMatrixLight()`、`setMatrixProfile()`、`toggleMatrixItem()`、`toggleMatrixNight()`、`setNightTime()`、`setNightLevel()` | key/value | `athena-matrix.sh set <key> <value>` | 硬件配置，保留 |
| LED 呼吸灯 | `loadLed()`、`toggleBreath()` | breath 0/1 | `athena-led.sh get/set` | 硬件配置，保留 |
| 完整管理入口 | `openMatrixFull()` | iframe 路径 `/admin/services/athena_led` | 原生 LuCI 页面 | 当前已改为 iframe 跳转，不再是旧文档所述 toast；目标菜单路径尚未取得设备证据，列为待验收而非已确认可用 |

### 2.7 维护

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| 重启状态 | `loadRebootStatus()` | status | `athena-reboot.sh status` | 只读 |
| 立即重启 | `doReboot()` | now | `athena-reboot.sh now` | 高影响系统操作 |
| 定时重启 | `openRebootSched()`、`saveRebootSched()` | enable/disable、时间、星期 | `athena-reboot.sh enable/disable` | crontab 写入 |
| 固件上传 | `startUpgradeUpload()` | 文件 multipart | `/cgi-bin/cgi-upload` | 上传，不是 RPC file.write |
| 固件校验 | 上传后 verify | 固件路径 | `athena-upgrade.sh verify` | 结构/机型/哈希校验 |
| 固件刷写 | `doFlashConfirm()` | 文件路径、keep 0/1 | `athena-upgrade.sh flash` | 变砖级危险操作；当前 flash 后端未重复执行 verify 的完整检查，P0 |
| 恢复出厂 | `doReset()` | `--confirm` | `athena-reset.sh --confirm` | 不可逆；固定确认字符串不是一次性令牌 |
| 手动备份 | `backupNow()` | create | `athena-backup.sh create` | 真实备份 |
| 备份列表/下载 | `openBackupList()`、`downloadBackup()` | list/download、文件名 | `athena-backup.sh list/download` | 文件读取 |
| 恢复备份 | `restoreBackup()`、`doRestore()` | restore/restore-upload | `athena-backup.sh restore/restore-upload` | 覆盖配置并重启；固定临时上传文件存在并发覆盖风险 |
| 自动备份 | `toggleAutoBackup()`、`saveAutoBackup()` | daily/weekly、时间、保留份数 | `athena-backup.sh schedule get/set/disable` | 持久化计划 |

### 2.8 高级

| 控件/动作 | 前端函数 | 参数 | RPC / 后端 | 类型与结论 |
|---|---|---|---|---|
| CPU/内存切换 | `pickRes()` | cpu/mem | 无 | 本地显示切换 |
| 资源数据 | `loadResources()` | 无 | `athena-resources.sh` | 只读 |
| 进程停止/重启 | `procAct()`、`doProcAction()` | PID、stop/restart | `athena-resources.sh stop/restart <pid>` | 高风险；当前后端使用 kill -9，建议 TERM→复核→KILL |
| 服务列表 | `loadServices()` | list | `athena-services.sh list` | 只读 |
| 服务启停/重启 | `svcAct()` | service id、0/1 | `athena-services.sh set <id> <0|1>` | 高风险；核心服务有保护，但动态 init 名称缺少路径白名单 |
| 服务详情/原生页面 | `openSvcWin()`、`openSvcPage()` | path/port/url | 服务返回的菜单路径、端口或 URL | 主要为页面导航 |
| 软件包管理 | `openPkgManager()`、`pkgTab()`、`pkgLoadAvail()`、`pkgRender()` | installed/available、package name | `athena-packages.sh list/install/remove` | 最终定义为真实动态管理；后端保护关键包，前端仍应隐藏受保护包的卸载操作 |
| 检查更新 | `checkUpdate()` | update | `athena-packages.sh update` | 仅刷新 APK 仓库索引，不升级已安装软件；按钮应改名 |
| 日志查看 | `openSyslog()`、`loadLog()`、`logLv()`、`logRender()` | level/search | `athena-log.sh` | 真实读取 |
| 日志导出/清空 | `exportLog()`、`clearLog()` 函数存在 | export/clear | `athena-log.sh export/clear` | 当前可见按钮却调用 `done()`，最终日志 modal 也未接入这两个动作；当前不可达/假反馈 |
| 修改管理密码 | `savePassword()` | current/new/sync | `athena-passwd.sh` | 真实账号操作 |
| SSH 开关 | 最终 `toggleSsh()` | 无 | 无 RPC，仅 toast“始终启用” | 假开关，移除候选 |
| 网速单位 | `setUnit()` | Mbps/MB/s | `athena-speedtest.sh unit set` + localStorage | 偏好 |
| 主题 | `loadTheme()`、`setThemeMode()`、`saveGlassTheme()` | palette/dark/数值 | `athena-theme.sh get/set` | 偏好 |
| 默认界面 | `setDefaultUi()` | athena/native/last | `athena-ui.sh set` | 偏好 |
| 缩放/KPI 排序 | `setUiZoom()`、`stepUiZoom()`、排序保存 | 范围/KPI ID | `athena-prefs.sh`、`athena-ui.sh` | 偏好 |

## 3. 24 个正式 RPC 脚本入口清单

以下名称均已在当前 SPA/动态目标与 Makefile/ACL 中交叉核对。每个脚本的完整参数校验、UCI/文件/服务副作用仍以既有 `ATHENAWRT-FRONTEND-BACKEND-CALLCHAIN-AUDIT.md` 第 11–14 节为详细静态审计基线。

| RPC 脚本 | 主要页面 | 当前调用动作/参数类别 | 处理建议 |
|---|---|---|---|
| `athena-status.sh` | 概览/设备/维护 | 状态读取、速率 | 保留只读 |
| `athena-client.sh` | 设备 | list/note/rename/know/unlearn/block/unblock | 保留，规则所有权重做 |
| `athena-apps.sh` | 概览 | list | 可选/降级，明确 DNS 推测 |
| `athena-wireless.sh` | WiFi/概览 | get/enable/disable/set/reset-defaults/guest get/enable/disable | 保留，访客与随机密码 UI 重做 |
| `athena-mode.sh` | 网络 | progress/router/single-bg/ap/bypass | 保留专用向导，后端强保护 |
| `athena-scan.sh` | 网络 | 体检 | 保留只读 |
| `athena-diag.sh` | 网络 | check/ping/dns | 保留诊断 |
| `athena-speedtest.sh` | 网络/高级 | 测速节点、unit get/set | 保留，说明流量与口径 |
| `athena-disk.sh` | 存储 | list/mount/umount/format | 保留 USB 管理，格式化危险隔离 |
| `athena-matrix.sh` | 灯光 | get/set key/value | 保留 |
| `athena-led.sh` | 灯光 | get/set breath | 保留 |
| `athena-theme.sh` | 高级 | get/set/reset | 保留偏好 |
| `athena-ui.sh` | 高级/入口 | get/set/mark/sync/zoom | 保留偏好与入口 |
| `athena-reboot.sh` | 维护 | status/now/enable/disable | 基础操作优先原生，计划可保留 |
| `athena-backup.sh` | 维护 | create/list/restore/download/restore-upload/schedule | 重做上传锁与确认 |
| `athena-parent.sh` | 设备 | list/set/clear | 保留，规则生成重做 |
| `athena-services.sh` | 高级/存储 | list/set；另有 filebrowser-password 子命令 | 通用服务管理优先原生；接通凭据读取 |
| `athena-resources.sh` | 高级 | 资源读取/stop/restart PID | 只读摘要保留，操作优先原生 |
| `athena-packages.sh` | 高级 | list/install/remove/update；后端单包 upgrade 能力 | 原生 APK 管理优先，保留关键包保护 |
| `athena-upgrade.sh` | 维护 | check/verify/flash | 原生 Flash Operations 优先；flash 后端 P0 |
| `athena-reset.sh` | 维护 | --confirm | 原生恢复流程优先，后端令牌重做 |
| `athena-log.sh` | 高级 | list/export/clear | 原生日志优先，修复按钮接线 |
| `athena-passwd.sh` | 高级 | current/new/sync | 原生密码管理优先 |
| `athena-prefs.sh` | 高级/概览 | get/set/del/list | 保留 Athena 专属偏好 |

### 3.1 内部脚本与未闭环项

- 内部 legacy/helper：`athena-status-legacy.sh`、`athena-services-legacy.sh`、`athena-resources-legacy.sh`、`athena-packages-legacy.sh`、`athena-wanip.sh`、`athena-logcap.sh`。
- ucode 文件：`athena-status.uc`、`athena-services.uc`、`athena-resources.uc`、`athena-packages.uc`、`athena-rate.uc`。
- `athena-single.sh`：已安装但没有发现正式调用者，先保留，待确认历史兼容/外部调用者。
- `athena-services.sh filebrowser-password`：后端已实现，前端没有调用点，当前 FileBrowser 凭据 UI 与实际初始化逻辑不匹配。
- 当前 SPA 的直接 RPC 只使用 ubus `session.login`、`system.info`、`file.exec`、`file.write`；没有直接调用 ubus UCI 对象或 `network.device.status`、`network.wireless.status`。ACL 中其他授权应在确认其他调用者后收敛，不能只凭 SPA 扫描直接删除。

## 4. 当前源码回退后确认的功能/安全问题

### 4.1 必须先修正的前后端不一致

| 位置 | 当前事实 | 风险/影响 | 建议 |
|---|---|---|---|
| WiFi 访客网络 | 前端 `saveGuest()` 传入固定密码 `12345678`；后端允许该参数通过合法长度校验 | 默认凭据固定，违反此前安全方案 | 改为用户明确输入或安全随机生成；密码仅在授权后显示 |
| WiFi 恢复默认 | 后端生成 16 位随机十六进制密码并在 JSON 返回；前端仍展示固定 `12345678`，`doResetWireless()` 不读取返回字段 | 用户恢复后拿不到真实密码，页面信息错误 | 前端只显示后端实际返回的随机密码，并提供一次性复制/确认 |
| FileBrowser | init 脚本生成 48 位随机密码，用户名 admin，绑定 LAN IP，根目录 /mnt/usb；前端提示 root/admin | 登录失败且错误暴露默认凭据 | 调用受 ACL 保护的 `filebrowser-password`，管理员主动查看时显示；状态以服务检查结果为准 |
| PPPoE 密码 | 网络页输入框 onchange 只执行 `done('宽带密码已更新')` | 误导用户以为 PPPoE 凭据已修改 | 改为只读/遮罩状态，或跳转原生网络接口页；不得增加第二套 PPPoE 编辑器 |
| eMMC 格式化 | 静态 HTML 仍显示 `fmtDisk('emmc')` | 与“仅真实 USB 分区格式化”产品边界冲突 | 前端隐藏/禁用 eMMC 格式化；后端当前 USB 设备校验仍须保留 |
| 日志导出/清空 | 页面按钮调用 `done()`；最终 `openSyslog()` modal 只有筛选与关闭 | 显示成功但没有实际导出/清空 | 连接 `exportLog()/clearLog()` 并检查返回值，或移除入口 |
| SSH | 最终 `toggleSsh()` 只提示“SSH 服务由系统安全策略管理，始终启用” | 假开关 | 移除开关，保留只读状态/原生管理入口 |
| 新设备提醒 | 当前 `devNew()` 只切换全部列表并高亮第 0 行 | 不能定位真实新设备 | 使用 NEW_DEVS/MAC 集合定位实际新设备；无新设备时明确提示 |
| 软件包 | 最终动态包列表可调用真实后端，但 installed tab 对所有包都渲染卸载按钮 | 关键包保护只在后端拒绝，UI 仍诱导操作 | 前端与后端使用同一受保护包清单；后端仍为最终边界 |
| 软件源更新 | `checkUpdate()` 调用 `athena-packages.sh update` | 只是刷新索引，不是升级已安装包 | 文案改为“刷新软件源索引/软件列表” |

### 4.2 静态示例数据和失败状态

当前 HTML 初始结构含有硬编码拓扑、设备数、VLAN 3066、磁盘容量、FileBrowser 运行状态、服务状态、进程样例和系统信息占位值。部分模块由 RPC 成功后重绘，但多个 loader 的 catch 为空；当 RPC 失败时，静态样例可能留在页面上，造成“数据正常”的错觉。

必须统一数据状态：
1. loading：加载中。
2. live：真实数据及更新时间。
3. stale：显示最后成功时间。
4. error：显示失败原因和重试。
5. unsupported：设备/驱动不支持。
6. never 用演示数据冒充当前设备真实状态。

当前概览拓扑标为“示意”，但内部仍写死互联网、光猫、Athena、LAN1–LAN3、WiFi 设备数、br-iptv 和 VLAN 3066。该信息不得用于判断现网物理拓扑或现网 VLAN；建议移除首页主卡，若保留只能作为明确的可编辑示意模板。

### 4.3 旧优化文档中需要更正的描述

- “打开完整管理”当前函数已经变成 iframe 跳转 `/admin/services/athena_led`，不再是旧文档所述的纯 toast；但目标菜单路径仍未取得设备端证据。
- 软件包管理最终函数已接入动态 `pkgTab/pkgLoadAvail/pkgRender`，不是整个页面都为静态演示；不过保护包的前端禁用仍缺失。
- FileBrowser 文档曾描述前端读取随机密码；当前 SPA 没有 `filebrowser-password` 调用点，现状应判为未闭环。
- 当前源文件 4,106 行、284,481 字节；旧规划文档中的 4,218 行、约 291 KB 已过期。
- 当前直接 RPC 调用扫描为 79 处，24 个脚本目标；旧状态文档的 81/82 处计数属于旧快照。

## 5. 后端 P0/P1 复核（不执行）

| 优先级 | 文件/入口 | 静态发现 | 结论 |
|---|---|---|---|
| P0 | `athena-upgrade.sh flash` | flash 只调用 `sysupgrade -T`；脚本注释承认当前平台该测试对任意数据可能返回成功；没有在 flash 内重复执行 verify 的完整 tar 结构/机型校验 | 刷写前必须在后端 flash 分支重新验证文件、目标机型、结构和受控路径；当前不调用 |
| P0 | `athena-services-legacy.sh set` | 动态服务分支把传入 id 直接拼到 `/etc/init.d/$init`，缺少 init 名称白名单、拒绝路径分隔符和 realpath 目录约束 | 修复路径边界前不应开放动态服务启停 |
| P0 | rpcd ACL | SPA 实际仅需 file.exec 专用脚本和 file.write 备份上传；ACL 仍有未发现 SPA 调用者的 UCI read/write、ubus status、通用 ubus/file.exec 授权 | 做调用者核查后最小化；不能在未核对其他调用者前直接删 |
| P1 | `athena-reset.sh` | 固定 `--confirm` 字符串；firstboot 失败时输出 ok=false 但脚本最终 exit 0 | 使用短时一次性确认票据；正确传播失败退出码 |
| P1 | `athena-backup.sh restore-upload` | 固定 /tmp 上传文件名，缺少并发锁/会话绑定；仅 tar 可读性检查，没有明确限制归档成员允许路径 | 增加上传锁、文件绑定、归档成员白名单和后端确认 |
| P1 | `athena-wireless.sh guest_enable/disable` | 跨 wireless/network/dhcp/firewall 多份配置写入；guest_clear_internal 按固定 section/name 删除配置；失败时没有事务回滚 | 备份原配置、冲突检测、分阶段提交和失败回滚 |
| P1 | `athena-client.sh` | block 同时写 nft/iptables，restore 只恢复 nft；unblock 搜索范围可能删除其他组件同 MAC 规则 | 统一 fw4/nftables，使用 Athena 专属 chain/set/comment |
| P1 | `athena-parent.sh` | 规则文件直接替换前删除旧文件；多个 base chain 同 hook/priority；星期值去重/原子更新不足 | 临时文件生成、语法检查、原子 rename，专项核验 hook |
| P1 | `athena-resources.sh` | 进程终止使用 kill -9；虽有 PID starttime/comm 复核和关键进程保护 | TERM→等待→复核→必要时 KILL；服务重启优先走 init/原生服务管理 |

以上为静态源码发现，没有调用危险入口，没有更改任何系统配置。

## 6. 原生 LuCI / 已有插件替代判断

OpenWrt LuCI 上游的基础菜单结构包含 Status、System、Services、Network 等管理域；具体叶子页面由设备实际安装的 LuCI 应用、菜单 JSON 与 ACL 决定。上游结构可作为能力参照，不能代替 Athena 真机菜单核验。

| Athena 功能 | 原生/已有能力 | 建议 |
|---|---|---|
| 通用接口、PPPoE、DHCP、静态地址、IPv6、DNS | LuCI Network、协议模块 | 替代 Athena 通用网络编辑器；Athena 只保留状态摘要和单臂专用向导 |
| 防火墙、NAT、端口转发、区域 | luci-app-firewall / fw4 | 原生替代 |
| WiFi 高级无线参数 | LuCI Wireless | 原生替代；Athena 保留三频快捷控制 |
| 软件包安装/卸载/升级 | 当前 ImmortalWrt APK 包管理与对应 LuCI 页面 | 原生替代；Athena 后端关键包保护仍可保留为安全层 |
| 服务启停 | LuCI System/Startup | 原生替代通用 init 管理；Athena 只读显示 OpenClash/NSS/ECM/FileBrowser 关键状态 |
| 进程管理 | 原生 LuCI Processes（若当前构建安装） | 原生替代任意进程 kill UI |
| 系统/内核日志 | LuCI System Log / Kernel Log | 原生替代完整日志查看器；Athena 可保留告警摘要 |
| root 密码 | LuCI System/Administration | 原生替代重复密码管理 |
| sysupgrade、备份/恢复 | LuCI Flash Operations | 原生替代自制刷写 UI；Athena 可保留计划摘要/快捷入口 |
| 设备备注、新设备识别、家长控制 | 原生租约/防火墙只有部分能力 | Athena 保留并修复 |
| NSS/ECM 状态 | Athena 设备专属采集 | 只读保留；禁止增加启停开关 |
| LED/点阵屏 | Athena 硬件专属驱动 | 保留 |
| FileBrowser Quantum | 当前专用服务 | 作为可选组件保留；不扩展 NAS/Samba |

设备端仍需只读核对具体菜单路径和 ACL；未经核验，不直接删除 Athena 入口或替换操作。

参考：
- OpenWrt LuCI 基础菜单定义：https://github.com/openwrt/luci/blob/master/modules/luci-base/root/usr/share/luci/menu.d/luci-base.json
- LuCI 技术参考：https://openwrt.org/docs/techref/luci
- OpenWrt 用户指南索引：https://openwrt.org/docs/guide-user/start

## 7. 五类最终处置建议

### 保留
- 实时上下行速度、CPU/内存、WAN/IPv6、在线设备等首页只读摘要。
- Athena 三频 WiFi 快捷控制。
- 设备识别、备注、已知设备与家长控制（修复规则边界后）。
- Athena 单臂/VLAN 专用向导，但独立放入专家入口并加后端确认/回滚。
- LED、点阵屏、Athena 外观/单位/KPI/缩放偏好。
- USB 只读识别与受限 FileBrowser 可选组件。
- NSS/ECM 真实运行状态只读显示。

### 合并
- 概览/设备/高级页重复的设备与服务状态使用统一数据源。
- 点阵屏、状态灯和夜间计划合并为设备指示灯分组，驱动仍独立。
- 手动备份、自动备份、备份列表归入维护的同一备份区。
- 新设备提醒并入设备列表筛选，不维护第二套设备状态。
- 访客网络入口统一在 WiFi 页，首页只保留快捷状态/入口。

### 替代
- 通用网络、Firewall/NAT、DHCP/DNS、WiFi 高级参数 → 原生 LuCI。
- 通用软件包管理、服务启停、进程管理、日志、root 密码、sysupgrade/配置恢复 → 原生 LuCI。
- 原生替代必须先确认设备实际页面、包和 ACL，不能仅按上游路径假设。

### 移除候选
- SSH 假开关。
- PPPoE 密码“编辑”假控件。
- 日志导出/清空的 done() 假反馈，若不接真实 RPC 则移除。
- 首页静态拓扑主卡（或降级为明确示意，不再呈现当前 VLAN/设备状态）。
- 硬编码服务、磁盘、设备、CPU/温度等演示状态。
- 没有调用者的脚本/旧函数仅在全仓库核对外部调用者后再移除；`athena-single.sh` 暂不删除。

### 重做
- 访客网络密码输入与四份 UCI 配置事务。
- WiFi 恢复默认随机密码回显。
- FileBrowser 随机凭据读取、状态和 LAN 地址展示。
- 服务动态 init 名称白名单/路径约束。
- 固件 flash 后端完整复验。
- 恢复出厂一次性确认与错误码。
- 备份上传锁、归档成员限制。
- 设备拉黑与家长控制 nftables 规则所有权/原子更新。
- 状态加载失败/过期/不支持的 UI 模型。
- 进程终止从直接 KILL 改为受控流程。

## 8. 实施前门槛与本轮边界

1. 本报告只形成审计与建议，不代表用户已经批准任何功能删除、合并或替代。
2. 先由用户确认五类处置矩阵，再决定是否开始 C3 页面整理。
3. 即使获准实施低风险前端工作，也必须先修复当前回退引入的假功能和前后端不一致。
4. 后端 P0 必须先完成静态整改与独立测试；不得在当前在线 Athena 上试错。
5. 设备端原生 LuCI 菜单核验采用只读命令，不修改网络或服务。
6. PPPoE、VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM 继续列为保护对象。
7. 本轮未改 CSS、未重写页面、未删除或修改任何功能源码、未修改 ACL/Makefile/工作流、未构建新 APK、未操作设备。

## 9. 审计结论

阶段 A 的静态架构与主要调用链已有完整基线；本次补充复核发现旧清单中部分描述已过时，并确认 C3-A 回退后的 UI 存在新的假控件、硬编码凭据和前后端不一致。当前不应直接开始 CSS/页面优化。

下一步应先由用户确认本报告的五类处置建议，再将设备端原生 LuCI 菜单与 ACL 做只读核验；随后确定 C3-A 的低风险范围。危险网络/存储/刷写动作仍须单独授权，不能由本审计自动触发。
