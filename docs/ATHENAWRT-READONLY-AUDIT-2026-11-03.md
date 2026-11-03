# AthenaWrt 只读源码审计记录（2026-11-03）

> 审计性质：只读静态审计；不改动功能源码、不刷机、不调用路由器操作、不执行网络/磁盘/恢复/升级动作。  
> 仓库：`ethandong06-debug/re-cs02-nss-firmware`  
> 分支：`athenawrt/apk-fixed-signing`  
> 审计快照：`37f23f3496557059d8da755618b1fe3ea877d19b`  
> 本记录区分“源码已证实”“待离线验证”“待设备验收”。源码存在不等于设备功能验收通过。

## 1. 范围与结论

本轮核验了当前分支树、Athena SPA 主页面、RPC ACL、备份/恢复、固件升级、恢复出厂、磁盘管理、网络模式及启动回退脚本，并盘点了当前 libexec 后端脚本目录。上一轮已对网络模式调用链进行专项审计。本记录不是所有后端脚本逐行安全审计，也不是设备验收报告；未完成的部分在末尾明确列出。

### 总体判断

- **P0 阻断项**：网络模式切换存在跨配置全局 `uci commit` 风险；单臂模式失败状态与前端轮询结束条件不一致；备份自动清理在备份失败时仍可能清理旧文件；恢复/升级/恢复出厂均属于不可逆或高影响操作，缺少设备外带救援和完整离线测试证据。
- **P1 高优先级**：RPC ACL 将通用 `file.exec` 和 `file.write` 能力授予 Athena ACL 用户，虽有脚本路径清单，但需确认 rpcd file 插件实际路径白名单语义、session 角色继承和写入目标限制；包管理、服务启停、NAS 安装卸载、家长控制、防火墙改写需继续做逐命令审计。
- **P2 一般优先级**：页面状态模型、按钮成功/失败反馈、图表数据真实性、过期/备用脚本与无效控件统一清点。
- **不建议当前进入设备验收**：网络模式切换、配置恢复、固件升级、恢复出厂、磁盘格式化。

## 2. 当前源码身份

| 项目 | 当前核验值 |
|---|---|
| 分支 HEAD | `37f23f3496557059d8da755618b1fe3ea877d19b` |
| SPA `index.html` blob | `59e8ff71d648407cae5112fc6b00a2648bbdfd98` |
| RPC ACL blob | `14d195323a41cf66f0b685d50dec2df6c0e029e5` |
| `athena-backup.sh` | `a60048ae6bd8e397d61c8d47877a67f63c7a1771` |
| `athena-upgrade.sh` | `2381608c4b35c081fbe3b9ce5e2a0ee76bfed32f` |
| `athena-reset.sh` | `5222750b9fc7b1911339d95ff2c0bdb80bc39764` |
| `athena-disk.sh` | `f3ff465497d961a5e7b3ffe6196e263a32ca9bf2` |
| `athena-mode.sh` | `5576abf8d687efe401259cb0c71d8c0b7c7787d7` |
| `athena-netcheck` | `213002006bb3324b7a2cef461a17bd064447609e` |
| `athena-vlan-pre` | `feebfdcf238c62f2eee84da6e7f2dd43534d269a` |

## 3. 高危操作调用链

### 3.1 配置备份与恢复

链路：SPA `index.html` → `athenaRPC.exec()` → rpcd file.exec/file.write → ACL `luci-app-athena.json` → `/usr/libexec/athena-backup.sh` → `sysupgrade -b/-r`。

已证实：
- 手动备份使用 `sysupgrade -b /etc/athena-backup/config-<timestamp>.tar.gz`。
- 备份列表只列出 `config-*.tar.gz`；下载经 base64 返回前端 Blob，不再将备份复制到 Web 根目录。
- 恢复文件名限定 `config-*.tar.gz`，拒绝路径分隔符、`..`、符号链接/目录逃逸，并用 `tar -tzf` 检查归档可读性。
- 上传恢复先通过 `file.write` 写入 `/tmp/athena-restore.b64`，再 base64 解码到 `/tmp/athena-restore.tar.gz`，通过 tar 检查后调用 `sysupgrade -r`。
- 自动备份支持 daily/weekly/monthly、保留 1–30 份，写入 root crontab 并提交 `athena` UCI。
- `autobackup()` 调用 `sysupgrade -b` 后未检查命令返回码/目标文件完整性，就按 keep 值清理旧备份。**风险：存储满、sysupgrade 失败或生成空/不完整文件时，仍可能删除较旧的有效备份。**
- `schedule_set` 在重写 crontab 前做频率、时间格式、数值范围、保留份数校验；但配置和 crontab 是两处状态，异常中断时可能不同步。
- `restore` 与 `restore-upload` 只验证 tar 可读性，不在 Athena 层逐项检查归档路径/文件清单/机型/固件版本；实际恢复语义依赖系统 `sysupgrade -r`。
- 自动备份失败没有可见的持久化最近结果/告警证据。

建议：
1. 先检查 `sysupgrade -b` 返回码、文件存在、非空、tar 完整性；全部通过后才执行保留策略。
2. 保留策略改为先生成新备份并验证，再原子替换/清理；清理失败不得影响有效备份。
3. 上传恢复增加大小上限、上传临时文件生命周期清理、并发锁和文件权限检查；校验 tar 成员路径不得为绝对路径或含 `..`。
4. 恢复前显示“覆盖全部配置、重启、可能改变管理地址”的明确提示；设备验收需有串口/U-Boot/TFTP救援路径和已验证备份。
5. 备份/恢复需要离线测试覆盖损坏归档、超大文件、磁盘满、重复请求、并发请求、路径穿越、权限失败和恢复后管理面可达性。

### 3.2 固件升级

链路：SPA 上传 → `athena-upgrade.sh verify` → 前端显示校验结果/保留配置选项 → `athena-upgrade.sh flash` → 后端重新校验 → `sysupgrade`。

已证实：
- 后端只接受固定临时路径或符合格式的 `/tmp/athena-fw-verified-<数字>.bin`，拒绝符号链接。
- 校验 SHA256、归档结构、机型目录、CONTROL/kernel/root，并拒绝归档内非普通文件/目录成员。
- flash 阶段不信任前端 verify 结果，重新校验文件和 SHA256，复制到受保护暂存文件后再次校验，并执行 `sysupgrade -T`。
- 用目录锁避免并发刷写；keep 仅允许 0/1；0 调用 `sysupgrade -n`，1 调用保留配置的 `sysupgrade`。
- 后端没有在线升级源，check 返回 latest=null；页面是手动上传固件流程。
- 刷写通过后台子进程延迟执行，RPC 成功响应表示“已安排”，不代表刷写成功或设备启动成功。
- 前端升级路径存在 SPA 中上传、verify、flash 的调用；当前静态审计未在真实设备验证文件上传分块、最大大小、进度、重启后状态和回滚。

建议：
1. 不允许用普通网络连通或 RPC 返回 ok 作为刷机成功验收；必须用启动后版本、分区/设备树、LAN/Wi-Fi、PPPoE、IPv6、NSS/ECM、日志逐项核验。
2. 增加固件来源/签名可信性说明。SHA256 只能证明文件一致性，不能证明发布者可信。
3. 检查上传分块的总大小上限、临时文件清理、重复上传、并发校验、空间不足处理。
4. 保留配置升级必须先对备份内容做兼容性审查；不同版本配置迁移不应默认安全。
5. 未完成带外救援演练前不得进行设备刷写。

### 3.3 恢复出厂

链路：SPA `prepare` → 后端生成 32-byte 随机十六进制 token、60 秒 TTL → 用户确认 → `confirm token` → 消费 token → `firstboot -y` → 延迟 reboot。

已证实：
- token 采用 openssl 随机数，校验 64 位小写十六进制，带时间戳，过期/重放失败。
- 用 lock 防止并发确认；确认码先删除再执行 `firstboot -y`。
- `firstboot` 成功后后台延迟 2 秒重启。
- 这是破坏性操作，不存在 Athena 层配置回滚。

建议：增加设备型号/操作影响说明、当前配置备份提示、带外恢复确认；只在测试机执行验收。注意“恢复出厂”是否清除 overlay、保留哪些分区，必须按当前系统 firstboot 实现验证，不能从按钮文案推断。

### 3.4 USB 磁盘管理

链路：SPA `athena-disk.sh list/mount/umount/format` → ACL → `athena-disk.sh`。

已证实：
- 允许写操作的设备必须是 `/dev/sd[a-z][0-9]+` 的真实分区、块设备存在、sysfs 中有 partition 标记、无 holders，且 sysfs 真实路径位于 USB 设备树。
- mount 只允许挂载到 `/mnt/usb`，检查设备未挂载、挂载点未占用；挂载成功后尝试重启 FileBrowser。
- umount 前若 FileBrowser 正使用该挂载点则停止；卸载失败会尝试恢复 FileBrowser。
- format 仅允许 ext4/vfat/exfat/f2fs，拒绝挂载中/交换分区、系统启动或根文件系统分区。
- list 会枚举 mmcblk、sd、nvme 物理盘并显示分区信息；这不代表它们都可格式化。
- eMMC 格式化入口已从当前页面规划中移除；后端仍保留 format 命令，但其校验只接受真实 USB 分区。

建议：
1. 格式化前 UI 必须显示设备型号、容量、分区名、文件系统和明确不可恢复警告，二次确认需绑定目标设备。
2. 对 sysfs USB 路径判断做不同 USB 控制器/设备树的离线兼容测试；不要仅依赖字符串匹配。
3. 对 mount/umount/format 加互斥锁，检查 NAS/FileBrowser/其他进程占用和挂载别名。
4. 设备验收只用可丢弃 USB 测试盘，不使用路由器 eMMC/NVMe。

## 4. RPC ACL 与权限边界

当前 ACL 文件声明：
- `ubus.file` 允许 `exec` 与 `write`。
- `file.exec` 对多个固定 `/usr/libexec/athena-*.sh` 路径授权。
- `file.write` 允许 `/tmp/athena-restore.b64`。
- Athena 页面可调用脚本包括状态、模式、客户端、服务、资源、诊断、日志、密码、软件包、备份、恢复出厂、重启、升级、磁盘、主题、矩阵、LED、无线、测速、UI、家长控制、应用识别、偏好、NAS、加速等。

判断：
- 固定脚本路径列表比开放任意路径执行更收敛，但 `file.exec` 允许执行的脚本本身是 root 权限操作面；真正的参数校验必须在每个脚本内部完成。
- ACL 中通用 file.exec/write 的作用范围和会话角色映射尚未用设备 rpcd 实际配置确认；不能只凭 ACL JSON 宣称最小权限已经验收。
- restore upload 的 `file.write` 目标是固定 /tmp 文件，但需要确认 file 插件是否禁止路径前缀/符号链接绕过，并确认用户会话无法将写入参数变成任意路径。
- 需要检查 LuCI 菜单 ACL、rpcd ACL、ubus session ACL 是否一致；脚本路径可调用不代表所有脚本参数均安全。

## 5. 网络模式与冷启动回退（上一轮专项结论合并）

已证实：
- SPA 调用 `athena-mode.sh`，通过 `file.exec` RPC 执行；RPC adapter 以当前 session 调用 `/ubus/`，把 stdout 解析为 JSON，非零返回码报错。
- 模式脚本会对 network、wireless、dhcp、firewall、athena 多份 UCI 配置分别 commit，并异步重启 network。可能把其他 LuCI 尚未 apply 的 staged changes 一并提交。
- 单臂模式存在延迟自检，启动后 8 秒左右检查 br-lan 管理 IP；失败分支主要从备份恢复 network 并将 Athena mode 改为 router，不能据现有证据认定五份配置均恢复。
- `athena-netcheck` 开机 45 秒后检查单臂模式 br-lan 管理 IP，异常则调用 router 模式并重启 network。
- `athena-vlan-pre` 在 network 启动前预创建 wan.<VID> VLAN 子接口，只有 athena.system.mode=single 时生效。
- NSS/ECM 保护逻辑会尝试启动 qca-nss-ecm，并关闭 firewall flow_offloading；尚无运行态设备验证。
- 前端进度轮询依赖成功状态文案（“完成/已生效”）结束；后端回滚/失败文案不匹配时，前端可能持续轮询。

结论：网络模式是当前最高风险模块。修复 UCI 提交边界、失败状态协议和全量回滚范围，并完成离线故障注入测试前，不进入设备验收。不得通过“先 CLI commit 再假定 LuCI apply_rollback 能恢复”的方式实现事务。

## 6. 其他功能与去留原则

| 模块 | 初步处理意见 | 依据/下一步 |
|---|---|---|
| 原生 LuCI 网络、无线、DHCP、防火墙、软件包、服务管理 | 保留原生 | Athena 不重复造轮子，不改原生菜单/ACL/通用后端 |
| Athena 首页/设备概览 | 保留 | 所有指标必须来自真实 RPC；无数据要显示未知/不可用，不可填样例 |
| 网络模式向导 | 保留但阻断发布 | UCI 事务与失败回滚问题未解决 |
| 备份/恢复 | 保留但加固 | 自动清理、上传校验、恢复兼容性需整改 |
| 固件升级 | 保留但阻断发布 | 签名可信性、上传边界、设备救援和真实刷机验收未完成 |
| 恢复出厂 | 保留但加强确认 | 一次性 token 已实现；设备级影响需核验 |
| USB 磁盘管理 | 保留 USB 范围 | 格式化危险确认和设备兼容测试待做；eMMC 格式化入口不恢复 |
| NAS（KSMBD/Samba4） | 保留为可选方案 | 当前源码有 APK 依赖模拟、包保护、USB 挂载检查；软件源/ABI/实际 SMB 读写未验收 |
| NSS/ECM 状态 | 保留只读状态 | 不让页面直接改核心 NSS/ECM 运行逻辑 |
| 软件包管理 | Athena 不替代原生 | 保护核心包；安装/卸载必须继续审计 APK 事务和包名白名单 |
| 服务启停 | Athena 可做简化视图 | 不重复原生 LuCI；服务 ID 到 init.d 的映射和参数需继续审计 |
| 家长控制 | 保留候选 | nftables 规则原子更新、跨午夜规则、回滚待离线测试 |
| FileBrowser | 可选保留 | 状态接口不返回密码；主动读取密码接口属于敏感操作，需核对 ACL/页面二次确认 |
| 日志、诊断、测速、LED、主题、偏好 | 保留轻量工具 | 非核心，逐个核对真实数据、超时、错误提示、资源占用 |
| 遗留脚本/备份页面/重复入口 | 移除候选而非直接删除 | 先确认无调用方、无兼容依赖、无升级迁移用途 |

## 7. 构建与发布状态

此前记录的 GitHub Actions Run #201（run id 41586151703）静态检查和 FileBrowser ARM64 冒烟通过，但 APK 签名阶段因缺少 `ATHENAWRT_APK_SIGNING_KEY` Secret 阻塞，未生成可安装 APK。该记录必须在下一次发布前重新读取 Actions 最新运行结果；本次没有重跑构建，也没有安装验收。

## 8. 必须完成的整改/验证清单

### P0 — 设备验收前阻断
- [ ] 网络模式切换改为不会提交其他 LuCI staged changes 的事务边界。
- [ ] 网络模式失败状态统一为结构化状态码/终态；前端轮询必须能识别失败、回滚完成、超时。
- [ ] 单臂切换备份并恢复所有实际被改动的 UCI 配置；回滚路径要检查恢复返回值并验证管理 IP、LAN、Wi-Fi。
- [ ] 备份成功验证通过后才能清理旧备份。
- [ ] restore upload 增加大小限制、并发控制、归档成员安全校验、失败清理。
- [ ] rpcd file.exec/file.write ACL 在设备上验证角色映射、路径限制和符号链接边界。
- [ ] 固件升级完成离线故障注入、空间不足、损坏包、错误机型、SHA 不一致、并发刷写测试。
- [ ] 建立并演练串口/U-Boot/TFTP 带外救援流程；未演练不刷设备。

### P1 — 功能发布前
- [ ] APK package manager：完整审计 `athena-packages-legacy.sh` 的包名校验、核心包保护、apk simulate、实际 add/del/update/upgrade。
- [ ] services：审计服务 ID 映射、启停白名单、重启流程、超时和返回状态。
- [ ] NAS：检查 KSMBD/Samba4 两套配置、切换清理、用户权限、密码存储、卸载保留配置、内核 ABI。
- [ ] 家长控制：检查 nftables 规则生成/删除、原子替换、跨午夜、重复 MAC、IPv6、规则 reload 失败恢复。
- [ ] 密码/账号：核对当前 LuCI 认证上下文、密码 hash 类型、弱密码提示、失败次数/锁定策略。
- [ ] 日志/资源：核对敏感信息脱敏、日志轮转、进程列表准确性和性能开销。
- [ ] SPA 全按钮清点：区分真实操作、只读刷新、无效按钮、无调用处理器、重复入口。
- [ ] 检查 legacy/ucode 双实现输出 schema 是否一致，回退路径是否有覆盖测试。

### P2 — 体验与维护
- [ ] 统一 loading/success/error/empty/stale/unsupported 状态。
- [ ] 图表只展示真实历史数据，数据不足时明确说明采样范围。
- [ ] 逐页核对移动端、桌面端、键盘操作和触控目标。
- [ ] 清理已确认无调用方的遗留备份文件和重复实现（先做引用分析，不直接删除）。
- [ ] 维护版本、变更记录、安装包 SHA256、构建工作流和回滚说明。

## 9. 测试矩阵（不得直接在主路由器上做破坏性测试）

| 类别 | 离线/CI 测试 | 测试设备验收 |
|---|---|---|
| 备份 | 成功/失败/空文件/损坏归档/路径穿越/磁盘满/保留策略 | 备份下载、恢复、重启后配置与管理面 |
| 升级 | 错误机型/坏 tar/符号链接/特殊成员/SHA 不匹配/并发/空间不足 | 仅救援条件齐备的测试机刷写 |
| 恢复出厂 | token 过期/重放/并发/firstboot 失败 | 可串口恢复的测试机 |
| 磁盘 | 非 USB、整盘、系统分区、mounted、swap、holders、异常 sysfs | 可丢弃 USB 盘 |
| 网络模式 | staged config 冲突、重启失败、VLAN 不存在、DHCP 冲突、管理 IP 丢失、回滚失败 | 带外救援就绪的测试机 |
| ACL | 未授权 session、非白名单路径、参数注入、符号链接、写入越界 | 设备 rpcd/session 实测 |
| NAS/包管理 | 模拟事务、依赖冲突、ABI 不匹配、卸载失败、服务启动失败 | 独立测试盘和测试设备 |

## 10. 下一阶段执行顺序

1. 完成尚未逐行审计的后端：`athena-packages-legacy.sh`、`athena-services-legacy.sh`、`athena-parent.sh`、`athena-nas.sh`、`athena-passwd.sh`、`athena-log.sh`、`athena-client.sh`、`athena-wireless.sh`、`athena-resources.sh`、`athena-status.sh` 等。
2. 建立 SPA 全量按钮清单，逐项映射到函数、RPC、ACL、后端 case、系统副作用和返回状态。
3. 将审计问题转成独立修复任务；先修 P0，不在审计记录提交时顺手改源码。
4. 做离线/CI 测试和构建；签名 Secret 配置后再产出 APK。
5. 最后安排有带外救援条件的设备验收。用户明确批准前不刷机、不执行危险操作。

## 11. 审计边界声明

本记录不能证明当前设备上运行的 APK 与本分支源码一致；不能证明所有脚本均已逐行审计；不能证明备份可恢复、固件可启动、网络模式可回滚、NSS/ECM 已运行或 NAS 可用。上述事项均须通过独立测试和设备证据闭环。
