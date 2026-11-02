# AthenaWrt 项目状态与交接记录

> 本文件是持续开发的项目事实来源。每次完成一个阶段后更新；新对话开始时先核对本文件与 GitHub 当前分支状态。
> 最后更新：2026-11-02

## 1. 项目与设备背景

- 设备：京东云雅典娜 Athena / RE-CS-02 / AX6600。
- 平台：Qualcomm IPQ6018，ImmortalWrt / qualcommax-ipq60xx，aarch64 Cortex-A53。
- 系统使用 APK 包管理，不是 opkg。
- 当前任务：AthenaWrt 独立 LuCI APK 的构建、签名迁移与安装验收。
- 用户没有本地编译环境；构建必须使用 GitHub Actions 云端完成。
- 目标是独立 APK，不刷整机固件。

## 2. 不可破坏的约束

不得擅自修改或破坏：
- PPPoE、VLAN（包括现网 VLAN 2044）、IPv6 PD/SLAAC。
- 防火墙、NAT、OpenClash。
- NSS/ECM 硬件加速及相关驱动配置。
- 与当前 APK 任务无关的固件配置和其他软件包。

操作原则：
- 稳定性优先；不引入未经验证的内核模块。
- 不要求用户在本地安装编译环境、运行 openssl 或执行 Linux 构建命令。
- 不绕过 APK 签名验证。
- 任何安装前先验证签名并模拟升级，确认不会卸载中文语言包或其他无关软件包。
- 未经用户明确同意，不执行路由器正式安装或网络配置变更。

## 3. GitHub 构建位置

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`
- 当前工作分支：`athenawrt/apk-fixed-signing`
- 原始基线分支：`athenawrt/phase1-p0-fixes`
- 分支地址：https://github.com/ethandong06-debug/re-cs02-nss-firmware/tree/athenawrt/apk-fixed-signing
- Athena APK 源码目录：`luci-app-athena-src/frontend/luci-app-athena/`
- 构建工作流：`.github/workflows/build-athena-apk.yml`

## 4. APK 1.2.60 签名故障定位与处理

### 已有成功构建（不是待构建状态）

- 分支：`athenawrt/phase1-p0-fixes`
- 源码提交：`ed69ea935030f37bf0916ac9653bf5bbfd878db2`
- Actions run：`41304711196`（run #23，结论 success）
- Artifact：`luci-app-athena-apk`，artifact ID `13084243143`，有效期至 2026-11-15。
- APK：`luci-app-athena-1.2.60-r1.apk`，14,683,961 bytes。
- SHA-256：`99b2d52d8d7faa8fd41e11f258d5fb08306793dacb89170f0d83809ed7b7bdf4`。
- 用户已确认路由器 `/tmp/upload.apk` 的 SHA-256 与构建产物一致；当前安装版本仍是 `1.2.59-r1`，中文语言包仍安装。

### 已确认的签名根因

- 已下载并检查原始 Actions Artifact 和 `athena-package-build.log`。
- 构建日志显示 ImmortalWrt 在 Actions runner 上生成临时 ECDSA P-256 私钥：`immortalwrt/private-key.pem`。
- 同一构建随后从私钥导出 `immortalwrt/public-key.pem`。
- `luci-app-athena-1.2.60-r1.apk` 的 `apk mkpkg` 命令明确使用该临时私钥签名。
- 原始 Artifact 未包含 `public-key.pem`，也没有保存私钥；Actions runner 已结束。因此路由器现有三个公钥不能验证该 APK，出现 `UNTRUSTED signature`。
- 这不是 APK 传输损坏：路由器端文件哈希与 Artifact 内 APK 哈希一致。
- 旧 APK 对应的公钥目前未从原始 Artifact/日志中取回。不得伪称已有对应公钥，也不得用 `--allow-untrusted` 绕过校验。

### 当前修复

- 用户取消的是 Codespaces/固定私钥 Secret 方案；不重新引导用户配置 Secret。
- 已在 `athenawrt/apk-fixed-signing` 分支更新构建工作流：成功构建后将本次构建的**公钥** `immortalwrt/public-key.pem` 复制为 `output/athenawrt-build-signing.pub` 并随 APK Artifact 上传；只导出公钥，不上传私钥。
- 修复提交：`1f7fb302081c9c5d02116dd7d2f60a86270739b8`。
- 源码页面未修改；此修复会重新执行 package-only 构建以产生一份带匹配公钥的 APK Artifact。它不是页面重写或整机固件构建。

### 修复后构建已完成（Run #24）

- 构建提交：`192807f73cb9e1db164265027fa463d9ec4f6098`（`ci: run Athena APK build on recovery branch`）。
- 后续分支 HEAD：`851c5b0dde17ec764a71017a9380ea80d2886fc5`（仅后续记录提交；本次构建对应源码/工作流提交仍为上项）。
- Actions run：`41319061077`（run #24，event=push，结论 success），所有 13 个主要步骤均成功。
- Artifact：`luci-app-athena-apk`，artifact ID `13090108299`，大小 14,685,069 bytes，创建于 2026-11-01，预计 2026-11-15 过期。
- Artifact 内含 `luci-app-athena-1.2.60-r1.apk`（14,683,958 bytes）、`athenawrt-build-signing.pub`（178 bytes）、SHA256SUMS、构建日志及源码元数据。
- APK SHA-256：`6b553a1f571bfa7335a705e713ebd12594434a4c7a466a3afdcd38d97e2434fc`。
- 公钥文件 SHA-256：`a7961c8c7994823d983f922af84f834463fbd4f0a5e8e02ea635bbd0365e4b3c`。
- 已用 OpenSSL 成功解析公钥：ECDSA P-256 / prime256v1，PEM 格式有效；未发现私钥被放入 Artifact。
- 构建日志确认 `luci-app-athena` 版本 `1.2.60-r1`、架构 `noarch`，由本次 runner 的 `immortalwrt/private-key.pem` 签名；同一构建也生成了 `luci-i18n-athena-zh-cn`，但 Artifact 只上传主 APK 和匹配公钥。
- 当前仍未在 Athena 路由器上导入该公钥、执行设备端 APK 签名验证或模拟升级；因此不能宣称设备端签名验收已通过。

### 后续原则

- 不创建 Codespaces，不生成或配置长期固定私钥 Secret。
- 先取得同一次构建产出的 APK 与公钥，核对公钥格式、文件哈希，并在路由器验证 APK 签名。
- 再做 APK 模拟升级，确认不会移除 `luci-i18n-athena-zh-cn` 或其他无关包。
- 未经用户明确同意，不执行正式安装；不改 PPPoE、VLAN、IPv6、防火墙、OpenClash 或 NSS/ECM。

## 5. 构建工作流注意事项

- 当前工作流定义了 `workflow_dispatch`。
- 当前工作流 `push` 触发分支列表已包含 `main`、`athenawrt/phase1-p0-fixes` 与 `athenawrt/apk-fixed-signing`；Run #24 实际由该分支的 push 触发。
- 本分支当前工作流不依赖长期固定签名 Secret；使用本次 runner 的临时密钥并仅导出公钥。
- 不得在日志中输出私钥；不得把私钥写入 Artifact、缓存或构建日志。

## 6. 后续对话交接流程

新对话开始时：
1. 读取本文件。
2. 核对 GitHub 当前分支 HEAD、工作流文件和最近 Actions 运行记录。
3. 区分已完成、已提交但未运行、运行失败、待用户操作四种状态。
4. 从“尚未完成”中的第一项继续，不重复已完成步骤。
5. 每次提交后更新本文件，记录新的提交 SHA、运行链接/结果、产物和验收状态。

## 7. 当前下一步

1. 将 Run #24 Artifact 中的 `athenawrt-build-signing.pub` 导入 Athena 的 APK 信任密钥目录（仅公钥）。
2. 在路由器上用当前系统的 APK 工具验证 `luci-app-athena-1.2.60-r1.apk` 签名；若验证失败，停止，不绕过信任校验。
3. 签名验证通过后执行模拟升级/依赖求解，重点确认不会卸载 `luci-i18n-athena-zh-cn`、LuCI 或其他无关软件包。
4. 把模拟结果交由用户确认；未经用户明确同意，不执行正式安装。
5. 安装验收完成后再进入前端审计/页面功能验收。

## 8. 已取消的 Codespaces 方案

用户已明确表示不需要固定签名密钥初始化流程。此前拟定的 Codespaces、ECDSA P-256 私钥生成和 Repository Secret 配置步骤全部暂停，不应继续引导用户执行。

## 9. 第一阶段前端/后端安全审计（2026-11-02，进行中）

本节记录当前分支源码静态审计结果。仅审查源码，没有对路由器执行任何命令，也没有修改网络配置、安装或刷写。

### 已核实的调用链数量

- SPA 页面 index.html 中，直接调用的 athena-*.sh RPC 入口为 24 个。
- 第 25 个脚本是 athena-single.sh：它由已授权的 athena-mode.sh 在单臂配置流程中承担实际配置，不是独立的前端 RPC 入口。
- 因此“25 个后端脚本”对应 24 个前端 RPC 入口 + 1 个内部执行脚本。
- ACL 对 24 个直接入口均有 file.exec 授权。
- Makefile 共安装 36 个 libexec 文件（含 .sh 与 .uc），包含主入口、legacy 回退脚本、ucode 实现及内部 helper。7 个脚本未单独出现在 ACL 中：status-legacy、single、services-legacy、resources-legacy、packages-legacy、wanip、logcap。需要按内部调用关系分类，不应盲目全部加入 ACL。
- Makefile 注释仍写“后端脚本（23 个）”，与实际清单不一致，需要统一。

### 磁盘管理

- athena-disk.sh 的格式化只接受 /dev/sd[a-z][0-9]+ 真实块设备分区，并要求 sysfs 路径包含 USB 设备路径。
- 拒绝正在挂载或作为 swap 使用的目标，并检查根、/rom、/overlay 与内核 root 参数。
- 支持 ext4、vfat、exfat、f2fs；挂载目录目前允许 /mnt/usb 及其子目录。
- 前端格式化目标也限制为 /dev/sdXn。
- 待补强：挂载/交换设备别名解析与格式化前后的真实挂载状态复核；共享目录固定为 /mnt/usb 后，应将挂载流程与 filebrowser 启停联动，避免 USB 未挂载时仍暴露根目录。

### 文件共享（高优先级缺陷）

已确认 init 脚本 root/etc/init.d/filebrowser 实际执行：初始管理员账号/密码固定为 root/admin；监听 0.0.0.0:8081；根目录为 /。

99-athena-filebrowser.sh 仅写入 UCI 的 filebrowser.root_dir=/mnt，但 init 脚本没有读取该 UCI 项，因此不能限制实际 filebrowser 根目录。前端旧提示一处显示 root/admin，另一处提示密码与路由器管理密码一致，均不符合随机密码要求。

必须修复为：首次启动随机生成高熵密码、仅绑定当前 LAN 管理地址、根目录严格为 /mnt/usb；USB 未挂载或 LAN 地址不可确认时不启动服务；前端通过受 ACL 保护的后端入口安全读取初始密码，不在源码/日志中写死密码。

### 软件包管理（高优先级缺陷）

- 前端提供安装和卸载；当前版本没有升级按钮，但后端仍保留 upgrade <pkg> 命令。
- athena-packages-legacy.sh 的 remove 直接执行 apk del，upgrade 直接执行 apk upgrade。
- 当前后端未见 OpenClash、NSS/ECM 或关键系统组件的保护名单/拒绝逻辑。
- 仅隐藏前端按钮不足以保护系统；必须在后端对 remove 和 upgrade 双重拦截，并在前端隐藏受保护包的操作。软件源索引刷新 apk update 不等同于升级已安装软件包。

### 维护/恢复/网络操作的风险点（继续审计）

- athena-mode.sh / athena-single.sh 会修改 network、wireless、DHCP、firewall、VLAN/bridge、WAN/IPv6 相关 UCI 配置，并可能重启 network / firewall / Wi-Fi。仅做静态审查，禁止在本轮对路由器执行。
- athena-upgrade.sh 包含 sysupgrade 刷写入口；本轮不调用。
- athena-backup.sh 包含配置恢复入口；需要继续检查备份文件名校验、路径穿越和恢复前提示。
- athena-resources.sh 有进程 stop/restart 功能，已对若干网络、无线、拨号、DNS 和管理进程做保护；仍需检查 PID/进程身份校验和服务重启行为。
- athena-services-legacy.sh 对核心 init 服务有启停保护；需继续核对动态服务发现是否会把 filebrowser 等应用错误地视为可启停，以及其与 U 盘挂载状态的协调。

### 当前验收状态

- [x] 磁盘格式化已有真实 USB 分区与挂载/swap/系统分区防护（待补强复核）。
- [x] 24 个直接 RPC 入口与 ACL 匹配。
- [x] 识别第 25 个脚本为单臂内部 helper athena-single.sh。
- [ ] 文件共享随机密码、LAN-only 监听、/mnt/usb 根目录修复。
- [ ] 软件包管理后端保护 OpenClash、NSS/ECM 和关键系统组件。
- [ ] 维护、诊断、资源、备份恢复及网络操作剩余调用链审计。
- [ ] 修正 Makefile 脚本数量注释和状态文档中的统计口径。
- [ ] 完成全部静态检查、构建、Artifact 内容检查（主 APK + 中文语言包 APK + 匹配公钥）。
- [ ] 设备端验签、模拟升级与用户确认；在用户明确同意前不正式安装。

### 调用链统计更正（2026-11-02）

进一步对当前正式 SPA index.html 的全部 RPC 调用进行扫描后，发现页面共有 81 处 athenaRPC.exec 调用，其中 78 处是字面量目标，3 处使用动态参数；去重后仍是 24 个不同的直接后端脚本入口。athena-mode.sh 中没有调用 athena-single.sh。athena-single.sh 虽被 Makefile 安装，但当前正式 SPA 与 athena-mode.sh 均未发现调用它的证据，因此应暂列为“已安装但未证实被调用的脚本”，不能计入前端 25 个有效调用链。之前本节将其描述为 athena-mode.sh 的内部 helper，现予以更正。需要继续查明用户提到的第 25 个脚本是否来自另一前端文件、动态 cfg.f 配置或旧版本清单；在查明前不宣称 25 项已闭环。

### 维护/诊断/资源操作补充审计（2026-11-02）

- athena-backup.sh 的 restore、download、export 分支把用户参数直接拼接到 /etc/athena-backup/$FILE，未将文件名限制为程序生成的 config-时间戳.tar.gz 格式，也未拒绝 ../ 等路径片段。download/export 存在越界读取风险；restore 也可能尝试从备份目录之外读取归档。必须加入严格文件名白名单，并验证目标 realpath 位于备份目录内。
- athena-resources.sh 的 stop/restart 使用 PID 后直接 kill -9，按当前 PID 重新读取进程名并拒绝若干核心进程；尚未验证前端提交的 PID 与采样时进程身份是否一致，存在 PID 重用竞态。其保护名单未覆盖 OpenClash/Mihomo 与 NSS/ECM 相关进程。
- athena-services-legacy.sh 的 CORE_INIT 保护名单包含网络、DNS、无线、管理等核心服务，但当前未覆盖 openclash 和 qca-nss-ecm；动态 init.d 枚举可能将它们当成普通第三方服务显示启停按钮。需要将 OpenClash 与 NSS/ECM 服务加入后端不可启停名单，前端同步显示受保护状态。
- athena-reset.sh 的 --confirm 参数会执行 firstboot -y 并延迟重启；正式 SPA 的 doReset 直接发送该参数。前端有二次确认弹窗时仍需核对弹窗是否确实是唯一入口；后端当前没有一次性确认令牌。
- athena-upgrade.sh 的 flash 分支会执行 sysupgrade；前端在上传后先执行 verify 并检查 compatible、SHA256 后才显示刷写确认，但后端 flash 本身仍可直接被 RPC 调用。审计/测试期间禁止调用 flash。
- athena-diag.sh 的 ping 参数尚未严格限制 CNT 为小范围纯数字；应限制 1-10，HOST/DNS 参数应做格式校验并对 JSON 控制字符转义，避免非预期参数和格式破坏。
- 正式 SPA 的网络模式应用通过 athena-mode.sh single-bg / router / ap / bypass 执行；这些操作会改写网络配置并重启网络/Wi-Fi，且 AP/旁路由分支会调用 nss_off。审计期间不调用这些动作；用户要求保留现网 PPPoE/VLAN/IPv6/防火墙/NSS/ECM，因此未来任何网络模式改动必须先获得明确授权。

以上均为静态源码发现，尚未修复或在设备上验证。

### 进一步核对：服务保护与前端确认流程（2026-11-02）

- 当前正式 SPA 的网络模式按钮先调用 confirmApply 弹出确认框，再调用 athena-mode.sh；单臂模式改用 single-bg 并轮询 progress。确认框提示会重建 VLAN/网桥、短时断网，但后端动作确实会提交网络配置并重启网络/Wi-Fi。审计期间未调用。
- athena-mode.sh 内部包含 nss_off（停止 qca-nss-ecm 并修改 firewall flow_offloading 字段）及 nss_on 逻辑；AP/旁路由切换路径可能触及 NSS/ECM。用户当前要求保留现网配置，因此该入口只能作为高风险网络维护操作审计，不得执行。
- athena-services-legacy.sh 的动态 init.d 枚举会把未列入 CORE_INIT 的服务视为普通第三方服务；当前保护名单未覆盖 openclash、qca-nss-ecm。服务管理页面可能出现停止/禁用按钮，必须补后端保护，不能只隐藏 UI。
- athena-resources.sh 的进程操作后端也未覆盖 OpenClash/Mihomo、ECM/NSS 进程名；需要扩展保护名单，并考虑 PID 复用竞态。
- 正式 SPA 的恢复出厂入口先由页面确认框触发，但后端只检查 --confirm 字符串，没有一次性确认令牌。后续应评估为后端增加更强的二次确认机制，避免误调用。
- athena-diag.sh ping 命令将用户提供的 count 直接传给 ping -c；目前没有限定为 1-10 的纯数字。需要在后端校验，不能信任前端输入。

注意：本轮仅更新项目审计记录，没有修改这些后端脚本，也没有运行会改变路由器配置的命令。

## 10. 第一阶段安全修复提交记录（2026-11-02，待 CI 验证）

以下均为 GitHub 源码变更，不代表已在 Athena 路由器安装或执行。用户现有 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash、NSS/ECM 配置未被本轮操作触碰。

### 已提交的源码修复

**磁盘与文件共享**
- 磁盘格式化增加 sysfs USB 设备确认、真实分区检查、块设备 holders 检查、挂载/交换分区别名解析，并拒绝系统分区及与系统分区同一物理盘上的分区。
- USB 管理挂载点固定为 /mnt/usb；挂载后复核 /proc/mounts，再尝试启动 filebrowser；卸载前停止 filebrowser，卸载失败则尝试恢复服务。
- filebrowser 改为随机 24 字节十六进制管理员密码，保存在 /etc/filebrowser.password（权限 0600）；绑定当前 LAN 静态或 DHCP 地址，根目录固定 /mnt/usb。USB 未挂载或 LAN 地址不可确认时不启动。
- LuCI 通过已授权的 athena-services.sh 子命令读取密码；仅在 /mnt/usb 确认挂载且 filebrowser 进程运行时返回密码。
- 新增 block hotplug：共享 USB 分区移除时停止 filebrowser，插入时延迟尝试重启；Makefile 已加入安装清单。
- 旧 99-athena-filebrowser.sh 改为说明性 no-op，避免继续写入未被 init 脚本读取的 UCI root_dir。

**软件包、服务和进程保护**
- 软件包后端增加包名校验和受保护包名单；卸载、单包升级拒绝 OpenClash、NSS/ECM、内核模块、网络/防火墙/DNS/PPPoE/无线、LuCI 与 Athena 关键组件。
- 已安装的受保护包不能通过“安装”入口变相升级；前端对受保护包隐藏卸载按钮，后端仍做最终拦截。
- 服务管理把 openclash、qca-nss-ecm、qca-nss-drv、qca-nss 纳入不可启停名单；资源管理保护 OpenClash/Mihomo/ECM/NSS 进程。
- 资源进程操作增加 PID starttime 与 comm 二次核验，并限制 init.d 重启路径，降低 PID 复用和进程名路径注入风险。

**维护、诊断和网络参数**
- 备份 restore/download/export 限定备份目录内文件名，拒绝路径穿越和目录外 symlink；自动备份保留数限制为 1-30。
- 诊断 ping 次数限制 1-10，目标地址、域名和 DNS 参数增加字符/长度校验。
- 家长控制和设备管理增加 MAC 校验；设备名称/备注限制长度并拒绝控制字符。
- 偏好设置限制 key 白名单（kpi_order、res_kth、ui_zoom、speed_unit）和对应 value 格式；点阵屏/灯光设置增加后端范围校验。
- 无线配置增加 SSID、密码、频段、信道、频宽校验；不再以 network restart 作为 wifi reload 的回退，避免无线操作连带重启 PPPoE/VLAN 网络。
- 访客网络不再使用固定默认密码，要求明确输入密码；清理匿名 br-guest device，避免重复启用后叠加桥设备。
- WiFi 恢复默认时生成随机密码并由 LuCI 显示；即使无线重载未确认，也会返回已生成密码及 reload 状态。
- 组网模式增加协议、PPPoE 凭据、静态 IPv4/掩码/网关/DNS 校验；单臂模式可沿用现有 PPPoE 凭据，主路由模式切换协议时清除不相关的旧 WAN 字段。AP/旁路由确认框明确警告会停止 NSS/ECM。
- 密码修改增加 8-128 字节、冒号和控制字符校验。

### 调用链统计口径（最终待复核）

- 当前正式 SPA 页面扫描到 81 处 athenaRPC.exec 调用，24 个不同的直接后端脚本目标；ACL 中 24 个直接目标均有 file.exec 授权。
- Makefile 安装 36 个 libexec 文件：31 个 Shell 文件 + 5 个 ucode 文件。
- 其中 6 个 Shell 文件为内部回退/依赖：status-legacy、services-legacy、resources-legacy、packages-legacy、wanip、logcap；另有 athena-single.sh 虽安装，但当前正式 SPA 与 athena-mode.sh 未发现调用它的证据。
- 所以不能将当前代码描述为“25 个前端直接入口”。目前准确口径为 24 个直接入口、6 个已识别内部依赖、1 个未证实调用的单臂 helper。用户所指的第 25 个入口仍待与原清单逐项对照。

### CI 与交付

- Workflow Shell 语法检查扩展到 usr/libexec、etc/init.d、etc/uci-defaults 和 etc/hotplug.d/block；JavaScript 语法检查保留。
- Artifact 收集规则已要求同一构建中恰好存在 1 个 luci-app-athena 主 APK 与 1 个 luci-i18n-athena-zh-cn 中文语言包 APK，并一并上传匹配公钥。
- 本轮最新 workflow run 仍待完成；尚未获得这些修复源码的最终构建成功结果，也尚未核验最终 Artifact 内容。
- 设备端公钥验签、模拟升级、安装和真机功能验收均未执行。未经用户明确同意不安装，不刷机，不改动现有网络配置。

### 文件共享的外部依赖风险

- 当前 workflow 固定下载 File Browser v2.63.23。上游仓库已于 2026-08-31 归档，官方说明此后不再提供修复或安全更新；其 README 也提醒不要直接暴露到互联网，并建议关闭命令执行功能。当前代码已限制为 LAN 地址和 /mnt/usb，但“仅 LAN 可访问”不能消除软件本身停止维护的风险。
- 因此 File Browser 保留为现有设计下的受限共享服务，不应配置公网端口映射或 WAN 访问；后续如需长期公网访问，应先评估替代的受维护方案。

### 最近一次构建排队状态

- 最新源码提交：`f1448776fa15c3815389f855e7436305043dd8b2`（偏好设置 KPI 排序校验兼容部分顺序）。
- 对应 Actions Run #162：`41367339743`，当前状态 pending。
- 其前序 Run #103（旧提交 `180dbed6...`）仍显示 in_progress，卡在 `Build required host tools`；因此最新 Run #162 尚未开始执行。Run #103 的静态语法检查已通过，但该结果不覆盖后续新增修复。
- filebrowser 数据库路径现为 `/etc/filebrowser-data.db`，使用 File Browser 正确的 `-d` 数据库参数；旧版 `/etc/filebrowser.db` 文件不再被当作数据库打开，避免把旧配置文件误当 SQLite 数据库。

### 文件共享加固补充

- File Browser 数据库独立存放于 `/etc/filebrowser-data.db`，统一使用 CLI 的 `-d` 数据库参数，避免将旧 `/etc/filebrowser.db` 配置文件误当数据库。
- 初始化和管理员用户更新均显式清空可执行命令列表并设置 `perm.execute=false`；LuCI 显示的是首次生成的随机密码，并提示若用户在 File Browser 内自行改密，显示值不会自动同步。
- 最新源码提交 `e2416d0422356b9a6fc6fe8650e39c5f7ab0fb80`；对应 Actions Run #166（ID `41367497484`）处于 pending。Run #103 仍占用同一 concurrency group，最新构建尚未开始。

### CI 语法检查修正与最新运行

- Run #167（`41367580124`）失败原因已定位：Shell 检查误把 `athena-status.uc` 等 ucode 文件交给 `sh -n`，不是源码语法错误。
- Workflow 已修正为：libexec 仅检查 `*.sh`；`etc/init.d`、`etc/uci-defaults`、`etc/hotplug.d/block` 中的脚本仍检查。不会把 `.uc` 误判为 Shell。
- Run #168（`41367634146`，提交 `09c531ac...`）的静态语法与元数据检查已通过；File Browser 固定版本二进制下载步骤也已通过。当前正在安装构建依赖，后续 ImmortalWrt 获取、host tools、目标工具链和 APK 编译仍未完成。
- Workflow concurrency 已改为按分支分组并取消同分支过期构建，避免新提交长期排在旧构建之后。

### APK 签名边界（重要）

- 当前 workflow 使用每次 Actions runner 生命周期内的临时签名密钥；Artifact 只保留与该 APK 匹配的公钥，私钥留在临时 runner 中销毁。
- 这不是跨构建持久化的固定密钥。每次构建都必须使用同一 Artifact 中的匹配公钥；不能拿 Run #24 的公钥验签 Run #168 的 APK。
- 尚未创建或配置长期私钥 Secret，也未把任何公钥导入 Athena 路由器。若要实现跨构建稳定信任，需要用户另行确认安全密钥保管方案；当前不擅自把私钥提交到仓库或配置 Secret。

### 调用链自动化核对

- Workflow 已增加前端 `athenaRPC.exec()` 目标、Makefile 安装项、rpcd ACL `file.exec` 的自动交叉检查，并校验唯一动态目标 `cfg.f` 由 `confirmApply('athena-mode.sh', ...)` 提供。
- 自动核对结果：24 个直接目标全部在 Makefile 安装并获 ACL 授权；31 个 Shell 文件中识别 6 个内部依赖和 1 个未引用的 `athena-single.sh`。这项检查已随 Run #170 的静态检查步骤通过。
- Run #170（`41367892120`，提交 `340f8dc0...`）静态语法、JSON 元数据、前后端调用链检查及 File Browser 二进制下载均已通过；当前正在安装构建依赖，APK 构建尚未开始。

### 文件共享依赖的待决事项（安装阻断项）

- 当前构建仍包含原版 File Browser v2.63.23。上游已归档且停止安全维护，因此即使已实施 LAN 绑定、随机密码、/mnt/usb 限定、命令执行禁用和 USB 拔除停止服务，也不能把它描述为无已知维护风险。
- 已核对一个可替代方案：FileBrowser Quantum v2.0.2-stable，提供 linux-arm64 单文件构建，配置支持 `http.listen`、独立 source path 和随机初始管理员密码，且近期版本持续修复安全问题；但它改用 YAML 配置和 SQLite，二进制体积也明显大于当前版本，需重做 init、密码展示和服务验收。
- 未经用户确认，不自动切换依赖。当前 Run #170 只用于验证现有源码构建流程；即使 APK 构建成功，也不应在用户确认文件共享依赖前正式安装。


### Run #170 构建完成与 Artifact 核验（2026-11-02）

- Actions Run #170：`41367892120`，源码/工作流提交 `340f8dc017997d0eadcfa800875aea985d6096bc`，结论 **success**。
- 13 个主要步骤全部成功：静态 Shell/JavaScript/JSON 检查、File Browser 依赖下载与校验、ImmortalWrt 构建系统获取、host tools、目标工具链、仅编译 luci-app-athena、APK/SHA256 校验、Artifact 上传。
- Artifact：`luci-app-athena-apk`，ID `13109568947`，大小 14,693,926 bytes，创建于 2026-11-02 01:33 UTC，预计 2026-11-16 01:33 UTC 过期。
- Artifact ZIP 已下载并检查，包含：
  - `luci-app-athena-1.2.60-r1.apk`，14,690,354 bytes。
  - `luci-i18n-athena-zh-cn-0.apk`，952 bytes。
  - `athenawrt-build-signing.pub`，178 bytes。
  - `SHA256SUMS.txt`、`size.txt`、`file-type.txt`、`athena-source-build-metadata.tar.gz`、`athena-package-build.log`。
- SHA-256 已对 Artifact 中实际解出的三个文件重新计算，并与 `SHA256SUMS.txt` 完全一致：
  - 主 APK：`d605a078fa86c1a6a679129dca7c5d9122847952524bcc7e501c0dfd6b1be12e`
  - 中文语言包 APK：`ebf03be9e5d779f9f1170058bae78e3a656dcb0e72c76ff035abb1fb3f434bf3`
  - 本次构建公钥：`e1e1de6584b5d04d45cb5d54be0ef7a4b8cdbd33cb407a3b36b1a0d59b9af1b9`
- 构建日志确认目标为 `aarch64_cortex-a53_musl`，只构建 `luci-app-athena` 与中文语言包，没有构建整机固件。
- **签名限制仍然存在**：公钥只匹配 Run #170 的 APK；私钥未导出，当前没有跨构建固定信任密钥。设备端导入公钥、验签、模拟升级均未执行。
- **文件共享依赖阻断仍然存在**：Artifact 内仍打包原版 File Browser v2.63.23。原版项目已归档，不再有安全维护；在替代方案确认和重新构建前，不将此 Artifact 作为可安装交付物。
- 本轮没有连接或操作 Athena 路由器，没有安装 APK，没有修改 PPPoE、VLAN、IPv6、防火墙、OpenClash 或 NSS/ECM。
- 当前结论：**源码 CI 构建通过，Artifact 文件与哈希核验通过；设备端签名验收、模拟升级、依赖风险处置和正式安装均未完成。**


### FileBrowser Quantum 替换实施记录（2026-11-02，CI 验证中）

用户已明确同意将原版 File Browser 替换为 FileBrowser Quantum v2.0.2-stable。当前分支已完成以下源码修改：

- 构建工作流固定下载上游 Release `v2.0.2-stable` 的 `linux-arm64-filebrowser`，SHA-256 固定为 `03eac074efc1b0ef3cb39882c04eeee26027049d261b6b6706650d4ac2d8e21c`；下载后安装为包内 `/usr/bin/filebrowser`。
- 上游二进制实际识别为 ELF 64-bit ARM aarch64、静态链接；其 GoReleaser 配置对 Linux ARM64 使用 `aarch64-linux-musl`，与 Athena 的 musl 用户态匹配。该信息来自上游 v2.0.2-stable 源码构建配置。
- init.d 改为 Quantum YAML 配置：监听当前 LAN IPv4、端口 8081、SQLite 数据库独立存放于 `/etc/filebrowser-quantum.sqlite`、共享源固定为 `/mnt/usb`、缓存放在 USB 内隐藏目录 `/mnt/usb/.athena-filebrowser-cache`；USB 未真实挂载或 LAN 地址不可确认时不启动。
- 首次启动时使用 Quantum 官方 CLI `user set admin --password ... -a --no-input -c ...` 初始化管理员；随机密码沿用本机 24 字节随机十六进制值并保存在 `/etc/filebrowser.password`（0600）。密码仅在数据库不存在时用于初始化，不写入 YAML 持久配置，因此之后在 Quantum Web UI 修改密码不会被服务重启覆盖。
- 服务启停仍由 procd 管理；SQLite 与配置文件权限限制为 root-only；保留原 USB block hotplug 自动停止/恢复逻辑。
- LuCI 文件共享弹窗改为显示 Quantum 管理员账号 `admin`，状态名称改为 FileBrowser Quantum。
- 原版 File Browser 数据库不会被当成 Quantum SQLite 数据库复用或自动迁移；USB 上的用户文件仍在原目录，Quantum 会创建自己的新数据库。原版数据库文件不主动删除。

### Quantum CI 运行情况

- Run #180（ID `41378831412`）失败于二进制版本检查：Actions runner 是 x86_64，工作流直接执行了 AArch64 文件，返回 Permission denied / exit 126。静态检查、前后端调用链检查、二进制下载和 SHA-256 校验均已通过；这不是二进制损坏。
- 已修正工作流：安装 `qemu-user-static`，通过 `qemu-aarch64-static` 在 x86_64 runner 上执行 Quantum ARM64 的版本检查和 SQLite 管理员初始化 smoke test。
- Run #181（ID `41378905625`，提交 `50399117936121f2e481d2d7d1e60bce111ca61a`）当前进行中：静态语法与调用链检查通过；Quantum ARM64 二进制下载与 SHA-256 校验通过；正在安装构建依赖；QEMU smoke test、ImmortalWrt package-only 编译、Artifact 校验仍待完成。
- 目前尚未证明 Quantum 在 Athena 真机上的运行时内存占用或 USB 文件操作兼容性；需要后续真机验收。不得把 CI 通过等同于设备功能验收。
- 本阶段仅修改 GitHub 源码与 Actions；没有操作路由器，没有安装 APK，没有改动 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 或 NSS/ECM。
- 新 Artifact 在 Quantum 构建成功且完成哈希检查前，不得作为可安装包交付；之后仍须先完成设备端匹配公钥验签与 APK 模拟升级，再由用户明确确认安装。


### Quantum CI 补充状态（2026-11-02）

- Run #181 的 QEMU 步骤已实际通过：ARM64 二进制的 `version` 命令成功，且 `user set admin --password ... -a --no-input -c config.yaml` 成功创建 SQLite 数据库。
- 随后为 procd 启动命令增加 `umask 077`，确保 Quantum 运行时创建的 SQLite/WAL 等文件使用私有权限。该改动提交为 `1f375cebb021273115e70fbd3d60d6e9914033a2`。
- 最新 Actions Run #182：ID `41378970658`，对应上述提交；静态语法/元数据/调用链检查通过，Quantum 二进制下载与校验通过，当前正在安装构建依赖。QEMU smoke test 与完整 package-only 构建仍待完成。
- Run #181 为较早源码快照；最终以 Run #182（或更新提交对应的后续 Run）作为 Quantum 版本的构建验收依据。


### FileBrowser Quantum 替换完成与 Run #182 验收（2026-11-02）

用户已明确确认采用 FileBrowser Quantum v2.0.2-stable。当前源码对应提交 `1f375cebb021273115e70fbd3d60d6e9914033a2`，Actions Run #182（ID `41378970658`）已 **success**，14 个步骤全部通过。

**依赖与二进制**
- 上游 Release：`gtsteffaniak/filebrowser v2.0.2-stable`，非 beta/prerelease；官方 Linux ARM64 asset 名为 `linux-arm64-filebrowser`，大小 26,498,676 bytes。
- 上游 Release asset SHA-256：`03eac074efc1b0ef3cb39882c04eeee26027049d261b6b6706650d4ac2d8e21c`；workflow 下载后执行 sha256sum 校验。
- 该二进制以 musl/aarch64 构建，目标架构与 Athena IPQ6018 / aarch64 Cortex-A53 / musl 相符。
- Workflow 使用 QEMU 在 x86_64 runner 上运行 ARM64 二进制：`version` 命令通过；使用 `user set admin --password ... -a --no-input -c config.yaml` 成功初始化 SQLite 数据库。
- 构建日志确认二进制被安装到 APK staging 的 `/usr/bin/filebrowser`，且 init.d、hotplug 与服务脚本均被安装。Quantum 二进制随主 APK 打包，不是设备端运行时下载。

**当前服务配置**
- Quantum 配置使用 YAML；监听地址为检测到的当前 LAN IPv4，端口 8081，不监听 0.0.0.0。
- 唯一共享 source 固定为 `/mnt/usb`；仅当真实 USB 分区挂载在该路径且 LAN 地址可确认时启动。
- SQLite 数据库位于 `/etc/filebrowser-quantum.sqlite`；配置位于 `/etc/filebrowser-quantum.yaml`；缓存位于 USB 内隐藏目录 `/mnt/usb/.athena-filebrowser-cache`。
- 首次初始化生成 24 字节随机密码，保存于 `/etc/filebrowser.password`，权限 0600；配置不持久写入 `auth.adminPassword`，避免服务重启覆盖用户在 Web UI 修改的密码。
- procd 运行命令使用 `umask 077`；USB block hotplug 在共享分区移除时停止服务，插入时延迟尝试重启；磁盘挂载/卸载流程与服务启停联动。
- LuCI 显示 Quantum 名称、LAN 访问地址和首次随机管理员凭据；若用户之后在 Quantum Web UI 修改密码，LuCI 仍显示首次生成密码并明确提示不会同步更新。
- 原版 File Browser 数据库不迁移、不覆盖；USB 用户文件仍位于 `/mnt/usb`，Quantum 创建独立数据库。旧数据库文件不主动删除。

**Run #182 构建产物**
- Artifact：`luci-app-athena-apk`，ID `13114103893`，ZIP 大小 24,586,232 bytes，创建于 2026-11-02 03:36 UTC，预计 2026-11-16 03:36 UTC 过期。
- Artifact ZIP 已下载并检查，含主 APK、中文语言包 APK、匹配公钥、SHA256SUMS、构建日志与源码元数据。
- 主 APK：`luci-app-athena-1.2.60-r1.apk`，24,548,134 bytes；SHA-256 `0661b4cf4626c6a85c078b655e9c0c479fcfc23529ef429fd34f4921eeeaea3c`。
- 中文语言包：`luci-i18n-athena-zh-cn-0.apk`，957 bytes；SHA-256 `ecb94a56f80f51a6d8007a616540537a94327aa88dcce462445ebe6c3a1e5d09`。
- 匹配公钥：`athenawrt-build-signing.pub`，178 bytes；SHA-256 `caf2624aa6c4852bf293db613ed45629be4eff23cd1f2cf0ebc764d810e120f1`。OpenSSL 已成功解析为 ECDSA P-256 公钥。
- 对 Artifact 解出的三个文件重新计算 SHA-256，均与 `SHA256SUMS.txt` 一致。
- 构建目标为 `aarch64_cortex-a53_musl`，仅构建独立 LuCI APK 与中文语言包，没有构建或刷写整机固件。

**验收边界**
- [x] Quantum v2.0.2-stable 版本固定、ARM64 二进制 SHA-256 校验。
- [x] QEMU ARM64 CLI 版本检查及管理员/SQLite 初始化 smoke test。
- [x] Shell/JavaScript/JSON 静态检查及前后端调用链检查。
- [x] ImmortalWrt host tools、目标工具链、package-only APK 构建。
- [x] 主 APK、中文语言包、公钥及 SHA-256 清单上传和校验。
- [ ] Athena 真机运行、内存占用、登录/改密、上传/下载/删除、USB 拔除/重插、LAN 监听范围验收。
- [ ] 设备端导入本次构建匹配公钥、APK 签名验证及模拟升级。
- [ ] 用户确认后才正式安装。

**安全边界**
- 本次构建仍使用每次 Actions runner 临时生成的签名私钥；Artifact 只含本次匹配公钥，不能用于验证其他构建。
- 不要用 Run #170 的 APK/公钥替代 Run #182；Run #182 的公钥只匹配 Run #182 主 APK。
- 当前仅源码与 CI 通过；没有连接 Athena 路由器，没有安装 APK，没有修改 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 或 NSS/ECM。
- 在设备端验签和模拟升级前，不将 APK 视为已批准安装；真机 Quantum 行为仍须单独验收。


### APK 签名与依赖模拟修复记录（2026-11-02）

- 最新源码提交 `a623859e9cb038db2d9e04f24fa52fd976989600` 对应 Actions Run #185（ID `41386836386`）已完成，结果为 **failure**。
- Run #185 的目标工具链安装和 `luci-app-athena` 1.2.60-r2 编译均通过；主 APK 与中文语言包 APK 的 SHA-256 签名验证均显示 `OK`。
- 失败仅发生在最后的 APK 依赖模拟步骤：`ERROR: Unable to read database: No such file or directory`，退出码 99。Artifact 上传因该步骤失败而跳过。
- 根因已定位：APK-tools 3 的 `--initdb` 是 `apk add` 子命令选项，不是当前命令中的全局选项。此前工作流把它放在 `add` 前，临时 root 数据库因此未初始化。
- 已在提交 `ce8854f485aa65ff1bcf2226f236e2cefa522d69` 修正命令顺序，将 `--initdb` 移至 `add` 后；上游 apk-tools `src/app_add.c` 将该选项定义于 ADD_OPTIONS，并在解析时设置 `APK_OPENF_CREATE`。
- 修复提交已触发 Actions Run #186（ID `41391283496`），当前状态 queued；以该次运行是否完成签名验证、依赖模拟及 Artifact 上传作为下一验收依据。
- 当前仍未在 Athena 真机安装或运行本次 APK；未修改 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 或 NSS/ECM。不得将 Run #185 的 APK 作为正式交付物。


### Run #186 失败复盘与临时数据库修正（2026-11-02）

- 当前分支 HEAD 在修复前为 `a6e380073208d8d6b9847ac9889a36db4b427222`；Run #186（ID `41391283496`）已完成，结论 **failure**。
- Run #186 的静态检查、Quantum ARM64 QEMU smoke test、ImmortalWrt host tools、目标工具链、Athena 主 APK/中文语言包编译均通过；两个 APK 的签名验证均显示 `OK`。
- 失败发生在临时 root 的依赖模拟：将 `--initdb` 放在 `add` 后虽修正了选项位置，但仍与 `--simulate` 放在同一事务中；该模拟事务未创建 APK 数据库，报 `Unable to read database: No such file or directory`，退出码 99。Artifact 未上传。
- 修复方案：在一次独立的、仅针对 mktemp 临时 root 的非模拟事务中，使用本次构建匹配的公钥安装目标 `libc` 与 `libgcc1` 基础运行库并初始化 APK 数据库；随后对 Athena 主 APK 与中文语言包执行独立的 `--simulate` 依赖求解。此过程不访问路由器、不触碰主机包数据库，也不绕过签名验证。
- 已更新工作流文件 `.github/workflows/build-athena-apk.yml`；等待本次提交触发的 Actions 运行，以实际结果验收。若模拟阶段仍失败，继续依据 job log 定位，不将失败产物交付。
- 设备端验签、模拟升级、Quantum 真机功能验收和正式安装仍未执行；用户现有 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash、NSS/ECM 均未触碰。


### Run #187 失败定位与 Run #188 复测（2026-11-02）

- Run #187（ID `41397501643`，提交 `875bc0afba25dc452204d32f8ece563d836bf110`）的静态检查、Quantum ARM64 QEMU smoke test、ImmortalWrt 获取、host tools、目标工具链、Athena 主 APK/中文语言包编译均通过；两个 APK 的签名验证均显示 `OK`。
- 失败发生在验证步骤的临时 root APK 数据库初始化命令。日志明确报错：`ERROR: Use --usermode to allow creating database as non-root`，退出码 99。不是源码编译错误，也不是 APK 签名错误；Artifact 上传被跳过。
- 已在提交 `ecff7b81ba62421aae80b645ac84435a1ca9a68f` 将 `--usermode` 加入仅用于 mktemp 临时 root 的数据库 bootstrap 命令。该参数不会修改宿主机或 Athena 路由器的包数据库。
- 对应 Run #188（ID `41436896339`）已启动，静态检查、Quantum QEMU smoke test、ImmortalWrt 获取和 package-only 配置均通过；最近检查时正在执行 `Build required host tools`，尚未进入目标工具链、APK 编译和依赖模拟阶段。
- 下一步：等待 Run #188 完成；若失败，读取本次 job log 的首个真实错误再修复，不重复猜测参数。只有签名验证、临时数据库初始化、Athena 主 APK/中文语言包依赖模拟全部通过并成功上传 Artifact，才进入 Artifact 文件与哈希核验。
- 本次仍未连接 Athena 真机、未导入公钥、未安装 APK、未刷写固件，也未更改 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 或 NSS/ECM。

### Run #188 构建成功与 Artifact 核验（2026-11-02）

- Actions Run #188：ID `41436896339`，分支 `athenawrt/apk-fixed-signing`，提交 `ecff7b81ba62421aae80b645ac84435a1ca9a68f`，结论 **success**。
- Job `Build luci-app-athena for Athena IPQ60xx` 已完成；14 个主要步骤全部成功，包括静态语法/元数据检查、FileBrowser Quantum ARM64 QEMU smoke test、ImmortalWrt host tools、目标工具链、仅编译 Athena APK、APK 签名与依赖验证、Artifact 上传。
- Artifact：`luci-app-athena-apk`，ID `13141127620`，ZIP 大小 24,585,952 bytes，创建于 2026-11-02 12:12:17 UTC，预计 2026-11-16 12:12:16 UTC 过期。
- Artifact ZIP 已下载并检查，包含主 APK、中文语言包 APK、本次匹配公钥、SHA256SUMS、构建日志、源码元数据：
  - 主 APK：`luci-app-athena-1.2.60-r2.apk`，24,548,136 bytes；SHA-256 `417db3ef8d4012f1977fb0941ab858703a1e43c5ce130e68a2a2b031ccf7ad78`。
  - 中文语言包：`luci-i18n-athena-zh-cn-0.apk`，954 bytes；SHA-256 `347bbfa24a29f2f7f75ea85eb08269bd249a3fbf64604a93e6a025bda9464654`。
  - 本次构建公钥：`athenawrt-build-signing.pub`，178 bytes；SHA-256 `a2d0c1168d114ba03dd332b295d31a63928faad899ab4d02c090b8d9b84b31f0`；OpenSSL 成功解析为 ECDSA P-256 公钥。
- 已从 Artifact ZIP 实际解出上述三个文件并重新计算 SHA-256，均与 `SHA256SUMS.txt` 完全一致；Artifact 本身未过期。
- 构建日志确认目标为 `aarch64_cortex-a53_musl`，只构建独立 `luci-app-athena` APK 与中文语言包，没有构建或刷写整机固件。
- **验收边界**：CI 的 APK 验签和临时 root 依赖模拟步骤均成功；这仅证明构建流水线通过。设备端尚未导入本次公钥、验签或模拟升级；FileBrowser Quantum 的 Athena 真机功能也尚未验收。
- **签名限制**：本次仍使用 Actions runner 临时签名密钥；Artifact 中的公钥只匹配 Run #188 的 APK。不能用于验证其他 Run 的 APK，私钥不在 Artifact 中。
- 本轮没有连接 Athena 真机、没有安装 APK、没有刷写固件，也没有修改 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 或 NSS/ECM。正式安装仍须等待设备端验签、模拟升级通过及用户明确确认。


## 11. AthenaWrt 1.2.60-r2 设备端安装验收记录（2026-11-02）

### GitHub 当前状态核对

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`。
- 工作分支：`athenawrt/apk-fixed-signing`。
- 本次核对时分支 HEAD：`a40f2312f519f78b73cca74068731d8e804a483d`，提交说明：`docs: record successful Athena APK run 188 and artifact verification`。
- 最新 Actions：Build Athena LuCI APK，Run #188，ID `41436896339`，对应构建提交 `ecff7b81ba62421aae80b645ac84435a1ca9a68f`，状态 completed / **success**。
- Run #188 的 14 个主要步骤全部成功：静态语法与元数据检查、FileBrowser Quantum ARM64 QEMU smoke test、ImmortalWrt host tools、目标工具链、仅编译 Athena APK、APK 签名与 SHA-256 校验、Artifact 上传。
- 最近一次运行序列：#188 success；#187 failure；#186 failure；#185 failure；#184 cancelled。#187/#186/#185 的失败是构建临时 APK 数据库初始化参数问题，已由 #188 的 `--usermode` 修复验证。
- 当前未发现 Run #188 之后更新的 Actions 运行记录。分支 HEAD 是记录 Run #188 结果的文档提交；Run #188 的实际构建源码提交仍为 `ecff7b81ba62421aae80b645ac84435a1ca9a68f`。

### 设备端实际安装结果

用户已在 Athena（ImmortalWrt SNAPSHOT r1-20261017，APK-tools 3.0.5，aarch64）完成 1.2.60-r2 安装：

- 主 APK：`luci-app-athena-1.2.60-r2.apk`。
- 中文包：`luci-i18n-athena-zh-cn-0.apk`。
- 设备端实际 SHA-256 与 Artifact 的 `SHA256SUMS.txt` 一致：
  - 主 APK：`417db3ef8d4012f1977fb0941ab858703a1e43c5ce130e68a2a2b031ccf7ad78`。
  - 中文包：`347bbfa24a29f2f7f75ea85eb08269bd249a3fbf64604a93e6a025bda9464654`。
  - 构建公钥：`a2d0c1168d114ba03dd332b295d31a63928faad899ab4d02c090b8d9b84b31f0`。
- 使用 `apk --keys-dir /tmp/athena-run188 verify` 验证两个本地 APK，均返回 `OK`。
- `apk adbdump` 确认主包名 `luci-app-athena`、版本 `1.2.60-r2`、架构 `noarch`、依赖 `libc`；中文包名 `luci-i18n-athena-zh-cn`、版本 `0`、架构 `noarch`，依赖主包。
- 模拟安装计划只涉及两个目标包：主程序从 `1.2.60-r1` 升级到 `1.2.60-r2`；中文包从 `0.261023.42061` 降为包内版本 `0`。模拟输出同时出现系统软件源缓存索引 `UNTRUSTED signature` 警告，但本地两个 APK 的独立签名验证均已通过；正式安装命令最终返回 `OK: 98.7 MiB in 392 packages`。
- 安装前已备份 `/etc/config/athena` 与 `/etc/apk/world` 至 `/tmp/athena-backup-1260/`。
- 主包 post-upgrade 阶段触发了 root 密码提示，出现 `Bad password: too weak` 及恢复提示 `{"ok":true,"restored":true}`。随后用户使用原有 root 密码新建 SSH 连接成功；确认原密码仍可用。BusyBox 的 `passwd -S` 不支持，读取 root shadow 条目只确认存在密码哈希，未将哈希内容作为密码信息保存。
- 用户打开 LuCI 首页后反馈“看不出来有什么问题”，随后确认“没什么大问题”。这属于首页初步目视验收，不等于全站页面、按钮、后端调用链和 FileBrowser Quantum 真机功能已完成验收。

### 当前设备验收结论与边界

- [x] 两个 APK 的设备端 SHA-256 与 Artifact 清单一致。
- [x] 两个 APK 使用本次构建公钥验签成功。
- [x] 模拟升级只涉及 Athena 主包和中文语言包。
- [x] 1.2.60-r2 主包与中文包正式安装成功。
- [x] 原 root 密码仍可通过新 SSH 会话登录。
- [x] LuCI 首页初步目视检查未发现明显问题（用户反馈）。
- [ ] 全站页面分类、入口、功能边界和重复项审计。
- [ ] 全部前端按钮/参数/RPC 与后端实现逐项映射，区分真实实现、只读展示、占位/无效控件。
- [ ] 后端权限、输入校验、错误处理、回滚和危险操作保护复核。
- [ ] FileBrowser Quantum 真机运行与 USB/LAN/文件操作验收。
- [ ] 网络、系统维护、灯光等页面的低风险只读验收；任何可能修改网络或系统状态的动作须另行确认。

### 下一阶段工作要求

用户当前明确希望先整体分析 AthenaWrt 全站页面功能分类与功能实现，再制定优化方案。先做静态源码审计和功能映射，不要立即改 CSS、重写页面或开始大规模代码修改。

必须保留：PPPoE、现网 VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM 及其现有运行逻辑。不得刷写固件，不得执行网络模式切换、恢复出厂、sysupgrade、服务停用或其他高风险动作。

建议交付《AthenaWrt 全站功能架构与实现审计清单》，至少包括：现有菜单树/页面入口、按用户任务重组的分类建议、每页真实功能与数据来源、按钮及参数对应的后端 RPC、权限与安全边界、重复/过时/无效入口、缺陷等级、建议保留/合并/移动/修复项。完成清单后再由用户确认优化范围。



## 12. 全站功能分类、替代性与去留优化方案（2026-11-02）

- 新增方案文档：`docs/ATHENAWRT-FUNCTION-ARCHITECTURE-OPTIMIZATION-PLAN.md`。
- 文档提交：`a02baca159a57bb1cf1e74e5909942fff1f7a420`。
- 本次只新增文档，没有修改前端、后端、APK、工作流或路由器运行配置。
- 方案采用五种决策：保留、合并、替代、移除、重做。
- 已基于菜单定义、rpcd ACL、约 291 KB / 4,218 行 SPA、Makefile、24 个 RPC 入口及主要 Shell/ucode 后端、init 脚本做静态分析。
- 初步结论：保留 Athena 硬件专属仪表盘、三频 WiFi 简化入口、设备识别、点阵屏/LED、必要的单臂 VLAN 专用能力和 Athena 外观偏好；优先将通用服务、软件包、日志、进程、基础网络与维护操作交给原生 LuCI；SSH 假开关和未集成完整管理按钮建议移除；FileBrowser 建议拆为可选包；DNS 域名推测的活跃应用应降级为可选并标明推测性质。
- P0 审查项：rpcd ACL 写权限范围；单臂模式脚本对网络/NSS-ECM 的影响；`athena-netcheck` 依据单一 LAN IP 条件自动回退并重启 network 的行为。
- P1 审查项：状态加载函数静默吞错、历史预览稿重复函数定义、访客网络隔离验收、设备拉黑/家长控制规则持久化、FileBrowser 可选拆包。
- 保护红线再次确认：不得改变 PPPoE、现网 VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT、OpenClash、NSS/ECM 现有配置和运行逻辑；不得在当前在线设备上测试网络切换、自动回退、格式化、sysupgrade 或恢复出厂。
- 当前阶段：**方案已提交，等待用户审阅和确认；尚未执行功能删改或代码重构。**
- 下一步：按方案阶段 A 建立逐页面、逐控件、逐参数、逐 RPC、逐后端动作的完整映射清单；之后再由用户确认每项功能的去留。先不改 CSS、不重写 SPA、不做大规模代码修改。



## 13. 网络回滚设计原则补充（2026-11-02）

- 用户明确提出：系统原生已有的能力应优先复用原生接口，避免 Athena 重复造轮子。
- 已核对 OpenWrt LuCI/UCI 文档：存在带超时自动回滚的配置应用机制，以及确认、主动回滚、待回滚状态查询能力。
- 已将方案调整为：Athena 网络变更优先复用当前 ImmortalWrt 固件实际提供的 LuCI/UCI 回滚机制；不另造通用回滚计时器。
- 接入前仍须核对设备当前 LuCI 版本、接口路径、RPC/HTTP 调用方式、ACL/会话权限、超时配置，并确认回滚覆盖单臂网络变更的全部相关配置。
- 原生机制无法覆盖的 Athena 硬件专属步骤，才评估独立保护逻辑。
- 此项仍是设计原则，不代表已经修改或测试设备网络回退代码。

