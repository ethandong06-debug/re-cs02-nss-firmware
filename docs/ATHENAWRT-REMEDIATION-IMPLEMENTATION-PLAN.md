# AthenaWrt 阶段 B：整改实施方案（设计稿）

> 状态：设计稿，待用户确认；本文件只记录实施方案，不代表已修改源码。
> 日期：2026-11-02
> 仓库：`ethandong06-debug/re-cs02-nss-firmware`
> 分支：`athenawrt/apk-fixed-signing`

## 1. 本阶段边界与保护条件

阶段 B 将阶段 A 静态审计发现转成有依赖关系的实施任务。当前只允许：
- 阅读源码、核对调用关系、更新 Markdown 方案和状态文档。
- 在不触碰设备配置的前提下设计单元测试、静态检查和验收用例。

当前不允许：
- 修改任何 Shell/ucode/JS/CSS/ACL/Makefile/工作流源码。
- 触发新 APK 构建或安装。
- 在 Athena 真机执行网络模式切换、重启网络/无线/防火墙、服务启停、恢复、刷写、恢复出厂、格式化等动作。

不可突破的设备保护项：
- PPPoE、VLAN 2044、IPv6 PD/SLAAC、现有防火墙/NAT、OpenClash、NSS/ECM 的配置和运行逻辑保持不变。
- 不关闭 NSS/ECM；不把 NSS 状态伪装成可由页面开关控制。
- 不刷固件、不恢复出厂、不改变当前 VLAN/桥接布局。
- 任何需要验证网络变更的测试必须在独立测试环境进行；当前在线路由器只做只读验收。

## 2. 总体实施顺序

| 顺序 | 任务组 | 优先级 | 先决条件 | 实施边界 |
|---|---|---|---|---|
| B0 | 建立基线、回归用例与保护清单 | P0 | 无 | 只读、静态 |
| B1 | 服务脚本路径校验、升级 flash 后端复验、恢复出厂返回码 | P0 | B0 | 不执行危险命令；先做离线测试 |
| B2 | rpcd ACL 最小权限收敛 | P0 | B1；完整调用者盘点 | 不在真机远程试错，必须有控制台/回退方案 |
| B3 | 高危操作后端确认票据与互斥锁设计 | P0 | B0、B1 | 不替代既有备份/回退；先做离线验证 |
| B4 | 设备拉黑/家长控制 nftables 规则模型 | P1 | B0 | 保留功能，统一规则所有权 |
| B5 | 访客网络四配置事务化 | P1 | B0 | 初期关闭写入口，直到测试通过 |
| B6 | 备份恢复上传并发隔离、USB 格式化竞态 | P1 | B0、B3 | 不在真机执行恢复或格式化 |
| B7 | 进程管理、偏好配置与状态一致性 | P1 | B0 | 先做兼容性测试 |
| B8 | 页面去留、原生 LuCI 导航与文案收敛 | P2 | 对应原生页面已核实 | 不删除底层能力 |
| B9 | 构建、安装包验签与分层验收 | 全阶段 | 每组完成 | 先静态/离线，再低风险真机 |

## 3. B0：基线与回归保护

### 工作项
1. 固定源码基线：记录分支 HEAD、每个待改文件 blob SHA、已安装设备版本和当前 APK SHA256。
2. 从当前设备导出只读状态作为验收基线：`ubus call system board`、`uci show network`、`uci show firewall`、`uci show dhcp`、`uci show wireless`、`uci show athena`、PPPoE/IPv6/NSS/ECM/OpenClash 状态。
3. 建立明确禁止修改清单：`network.wan`、`network.wan6`、现有 VLAN 2044 设备和关联接口、现有 bridge/VLAN 布局、WAN 防火墙 zone/NAT、OpenClash 配置、NSS/ECM 相关服务/模块/参数。
4. 建立只读功能回归清单：首页速率、CPU/内存、三频状态、设备列表、系统信息、服务状态、磁盘状态、日志读取。
5. 将危险动作标记为“离线模拟/独立测试环境”，不放入当前设备测试步骤。

### 验收
- 保护项有明确基线值和变更前后 diff。
- 每个后续 PR/提交列出改动文件与受影响配置范围。
- 任一改动意外触及保护清单，立即停止该任务，不继续构建/部署。

## 4. B1：P0 后端输入与刷写安全

### B1.1 服务动态 init.d 名称边界

目标文件：`athena-services-legacy.sh`（由 `athena-services.sh set` 转发）。

当前问题：动态分支把用户提供的 `id` 拼入 `/etc/init.d/$id`，仅检查可执行性；核心服务保护是字符串比较。

设计：
1. 对命令参数严格校验：`id` 仅允许 `[A-Za-z0-9_-]+`，拒绝斜杠、反斜杠、点号、空白、控制字符和 `..`。
2. 使用 `readlink -f` 解析 init 脚本实际路径；要求解析结果严格位于 `/etc/init.d/` 目录内，且是可执行普通文件。
3. 解析后名称仍需与请求 id 完全一致；禁止 symlink 跳出目录。
4. 对核心服务采用规范化后的服务名/真实路径双重保护；保护 OpenClash、NSS/ECM、network、firewall、dnsmasq、netifd、rpcd、uhttpd、dropbear 等关键项。
5. 已知静态服务继续走静态映射；动态服务若不满足规则直接拒绝，不做路径猜测。
6. 操作结果检查每条 enable/start/stop/disable 返回码；部分失败应返回 `ok:false` 和明确阶段，不得统一回报成功。

验收：合法普通服务名通过；`../`、绝对路径、带斜杠、编码/控制字符、软链接越界、核心服务名全部拒绝；不存在服务拒绝；服务命令失败返回失败。

### B1.2 固件升级 flash 内重复完整校验

目标文件：`athena-upgrade.sh)。

当前问题：`verify` 分支检查 sysupgrade tar 结构和目标机型；`flash` 分支只检查文件存在并调用本平台已知不能作为充分判据的 `sysupgrade -T`。直接 RPC 可以跳过前端 verify。

设计：
1. 把验证提取为唯一的 `verify_firmware()`，供 verify 和 flash 两个分支调用，禁止维护两套逻辑。
2. 当前前端上传目标限定为固定路径 `/tmp/athena-fw-upload.bin`；若仍需兼容 base64 旧路径，必须显式列出唯一允许路径，不接受任意路径。
3. flash 开始时重新检查文件存在、普通文件、非符号链接、合理大小范围，并计算 SHA-256。
4. 验证 sysupgrade tar 的顶层目录、CONTROL、kernel、root 必需成员和本机 board_name；tar 成员不得通过绝对路径或 `..` 逃逸。
5. 将 `sysupgrade -T` 仅作为附加检查，不作为唯一验证依据。
6. `KEEP` 只允许精确值 `0` 或 `1`；其余值拒绝。
7. 完整验证通过后才允许返回“准备刷写”；真正启动刷写前再核对文件未变化（至少比较 SHA-256）。
8. 任何失败不得删除原始上传文件，不得启动 sysupgrade；输出明确失败 JSON 和非零退出码。
9. 验证逻辑必须可在离线测试目录运行；测试仅使用伪造 tar/无效包，不执行真实 sysupgrade。

验收：任意非 tar、损坏 tar、缺少成员、错误机型、路径穿越成员、超限文件、文件校验后被替换、非法 KEEP 均拒绝；有效测试固件只通过验证，不实际刷写。

### B1.3 恢复出厂退出码

目标文件：`athena-reset.sh)。

设计：
- 未提供确认参数时继续只返回 `need_confirm`，不执行 firstboot。
- 确认参数不再只靠固定字符串作为唯一授权；待 B3 票据流程接入。
- `firstboot -y` 失败时返回 JSON `ok:false` 且非零退出码；成功后再安排延迟重启。
- 检查后台 reboot 命令的启动反馈；不把“已执行重启”与“已成功恢复”混为一谈。

验收：用 PATH mock firstboot/reboot；模拟 firstboot 成功/失败，确认 JSON 与退出码一致；测试中绝不执行真实 firstboot/reboot。

## 5. B2：rpcd ACL 最小权限收敛

目标文件：`root/usr/share/rpcd/acl.d/luci-app-athena.json)。

当前 ACL 事实：
- SPA 直接使用 `session.login`、`system.info`、`file.exec`、`file.write`。
- 当前 ACL 还包含七个 UCI 包的 read/write、`athena.status`、`network.device.status`、`network.wireless.status`、通用 network/ping/nslookup/ubus exec，以及旧固件上传路径授权。
- `file.write` 当前用于 `/tmp/athena-restore.b64`；固件上传使用 cgi-upload multipart 到 `/tmp/athena-fw-upload.bin`，两条链路必须分开看。

设计：
1. 对整个源码仓库执行全文搜索：所有 `ubus call`、`rpc.declare`、`fs.exec`、`file.exec`、`file.write`、UCI JS API、历史页面、LuCI 菜单和依赖插件调用。
2. 将 ACL 的每个对象/方法/路径分为：当前主 SPA 必需、其他包必需、历史遗留、未证实。
3. 优先移除无调用者的通用执行入口：`/etc/init.d/network`、`ping`、`nslookup`、`ubus`；不允许通用 shell/解释器入口。
4. 逐项核实七份 UCI read/write 和三个状态 ubus read。只有确认所有合法调用者均不依赖后才删除；不以主 SPA 没调用作为唯一依据。
5. 保留明确的 Athena 专用脚本路径白名单，不用通配符。
6. `/tmp/athena-fw.b64`、旧固件上传 read/write 权限只有在全仓库与实际 cgi-upload 路径核查完成后才移除。
7. 对 `file.write` 恢复上传通道先做并发隔离方案；在隔离机制未定前不贸然收紧到导致恢复功能失效。

验收：
- 生成 ACL 前后差异表，每一条授权都有调用者证据。
- 用未授权 ubus 请求验证被拒绝；用正常主 SPA 登录和只读页面验证不回归。
- ACL 更新必须在独立测试环境验证登录、状态、每个 Athena 脚本入口和备份上传；当前在线设备不作为首次试验对象。

## 6. B3：高风险操作确认票据与互斥锁

适用操作：网络模式切换、配置恢复、恢复出厂、固件刷写、磁盘格式化。

设计原则：
1. 前端弹窗只是用户交互，不是安全边界；后端必须再次验证。
2. 采用 prepare/commit 两阶段：prepare 返回随机高熵票据；commit 必须提交票据和完全相同的操作类型/参数。
3. 票据存放在 root-only 临时目录，权限 0700/0600，短有效期（例如 60-120 秒），一次性消费；消费后立即删除。
4. 票据绑定规范化参数摘要（例如模式、VLAN、接口、KEEP、磁盘设备身份、备份文件 SHA），不能只绑定动作名称。
5. 同一危险类别使用原子锁（mkdir 锁目录或经目标 BusyBox 确认可用的 flock）；并发请求拒绝，不覆盖正在执行的事务。
6. 错误、超时、进程退出后清理票据和锁；异常残留需带 PID/时间/操作摘要，不能自动执行下一步。
7. 票据不替代配置备份、设备身份校验、固件复验、UCI diff、网络自检和现有回退。
8. 若无法可靠绑定 rpcd 会话，必须明确票据只提供短期一次性授权，不声称具备用户身份绑定；再评估通过前端显式传递 session token 的风险与必要性。

网络模式额外设计：
- 先对当前配置导出并做保护项 diff；任何 PPPoE、VLAN 2044、wan6、OpenClash、NSS/ECM 相关变更超出允许白名单即拒绝。
- 原生 LuCI UCI session rollback 只有在确认它能覆盖 network/wireless/dhcp/firewall/athena staged changes 后才可接入；CLI `uci commit` 不在该事务内。
- 硬件 VLAN 预创建、NSS/ECM 处理、网络重启和开机自检属于外部副作用，必须单独设计顺序与补偿动作。
- 不把当前三条不等价回退路径简单合并；先写清状态机和每一步可恢复点。
- 目前只设计，不在现网验证。

验收：票据缺失/过期/重复/错动作/错参数/并发提交均拒绝；票据仅能使用一次；锁残留可安全恢复；模拟故障不触碰真实网络。

## 7. B4：设备拉黑与家长控制规则统一

目标文件：`athena-client.sh`、`athena-parent.sh`、必要时 `athena-boot` 和 fw4 include 文件。

### 7.1 设备拉黑
- 停止在整个 ruleset 搜索 MAC 并删除任意匹配 handle。
- 规则必须具有 Athena 可识别的所有权标记（专属 chain/set 或稳定 comment）。
- block/unblock/restore 必须幂等；重复 block 不产生重复规则。
- 统一到 fw4/nftables；不再同时维护 nft 与 iptables 两套规则，除非明确支持旧平台且有独立版本适配。
- 规则持久化与 firewall reload/boot 恢复必须使用同一机制，不能一个写临时规则、另一个启动时重复追加。

### 7.2 家长控制
- 先确认目标 nft 版本、fw4 include 加载点和现有规则结构。
- 避免每个 MAC 创建独立 forward base chain；优先单一 Athena base chain，再按 MAC/时间生成规则，确保同 hook/priority 的顺序确定。
- 星期列表规范化、去重、排序；读旧配置时也做严格解析，非法配置不进入规则生成。
- 先写临时规则文件，执行语法检查；通过后原子 rename，再 reload firewall。
- 失败时保留旧规则文件和旧配置；reload 失败应恢复文件并重新加载旧规则。

验收：规则重复执行幂等；unblock 只删除 Athena 自己的规则；nft 语法检查失败不替换旧文件；多 MAC 同时生效且跨午夜规则正确。所有防火墙行为在独立测试环境验证。

## 8. B5：访客网络配置事务化

目标文件：`athena-wireless.sh)。

当前风险：固定名称 `athena_guest`、`network.guest`、`br-guest`、`dhcp.guest`、`firewall.guest_zone`、`firewall.guest_fwd` 被无条件删除/重建；四份 UCI 分别 commit，中途失败无整体回滚。

设计：
1. 创建前检查上述 section/device 是否存在；只有存在 Athena 明确所有权标记时允许更新/删除。无标记或冲突时拒绝覆盖并报告冲突项。
2. 使用专属标记记录 Athena 创建的 guest 资源；关闭时只删除带标记的资源。
3. 对 wireless/network/dhcp/firewall 做带权限保护的事务备份；建立互斥锁，避免并发配置。
4. 先在 UCI staged state 中完成全部修改，再执行配置语法/结构检查；保存前生成 diff。
5. 分包 commit 时若任何一步失败，按备份恢复四份配置；随后仅在独立测试环境执行 wifi/dnsmasq/firewall reload 并核验。
6. guest_get 不只看 wireless iface.network，还核验 bridge、DHCP、firewall zone、forwarding 的完整性；状态分为完整启用/部分损坏/关闭。
7. 初期入口策略：未完成隔离验收前，访客网络启用入口默认关闭或显示“暂不可用”，不能让用户误以为隔离已经完整。

验收：同名用户配置不被覆盖；部分配置失败可回滚；guest 到 LAN/路由器管理面被拒绝，guest 到 WAN 按设计放行；IPv4/IPv6 均测试。

## 9. B6：备份恢复与 USB 格式化

### 9.1 配置恢复上传
目标文件：`athena-backup.sh`、SPA 上传适配层、rpcd ACL。

- 固定 `/tmp/athena-restore.b64` 在上传阶段就可能被并发覆盖；仅在 restore-upload 启动后加锁不足以解决上传阶段竞争。
- 首选评估是否能使用受限 cgi-upload/专用上传处理器，为每次上传分配唯一临时文件并在服务端绑定操作票据。
- 若保留 rpcd file.write 固定路径，必须至少在 UI 禁止并发、上传前清理、上传完成后计算大小/hash、恢复前锁定；同时明确它不能完全防止两个已认证 RPC 会话同时写入，不能宣称彻底解决并发。
- 对 tar 成员列表进行路径白名单检查；确认 sysupgrade -r 对归档成员的实际过滤行为，不依赖“tar 可读”作为安全验证。
- 恢复前校验摘要、归档结构、允许配置范围和一次性确认票据；恢复失败输出真实错误。

### 9.2 USB 格式化
目标文件：`athena-disk.sh`。

- 保留当前真实 USB 分区、挂载状态、swap、系统盘检查。
- 在格式化前重新解析设备节点、major/minor、sysfs 物理路径、USB 父设备和挂载状态；mkfs 前再次复核一致。
- 使用设备身份锁，拒绝设备在检查与执行之间发生变化。
- 文件系统类型使用严格白名单；mkfs 命令和参数固定映射，不拼接任意命令。
- 页面展示设备型号、容量、分区、挂载点和将被清除的数据范围，要求后端一次性票据确认。

验收：模拟热插拔/设备节点变化/系统盘/挂载分区/swap/非法文件系统全部拒绝；不在当前设备上执行 mkfs。

## 10. B7：进程、偏好与状态真实性

### 10.1 进程管理
目标文件：`athena-resources.sh`。
- 保留现有 PID、starttime、comm 二次核验和关键服务保护。
- 先发送 SIGTERM，等待有限宽限期；再次核对 PID 身份后，只有进程仍存在且身份相同才允许 SIGKILL。
- restart 只允许通过经过白名单的 init.d 服务；不能把任意进程名当作 init 脚本名。
- UI 明确显示“结束进程”而不是“重启服务”，区分两种操作。

### 10.2 偏好存储
目标文件：`athena-prefs.sh`、`athena-theme.sh`、`athena-ui.sh`。
- 明确每个 key 的唯一权威存储源；UCI 镜像只能作为兼容迁移，不得双向随意覆盖。
- 写入统一使用锁、临时文件、权限 0600、原子 rename。
- 非法值必须返回失败，不能忽略非法字段却返回 ok:true。
- 迁移完成后保留旧配置读取兼容，写入只写新权威源。

### 10.3 状态真实性
- RPC 失败必须显示失败/最后成功时间，不显示默认样例数据冒充实时状态。
- 区分配置状态与运行状态；例如无线 UCI disabled 与 radio 实际 up 分开显示。
- NSS/ECM 状态必须来源于设备实际运行态，只读显示；不提供开关。
- DNS/OAF 活跃应用明确标注为“域名线索推测”，不宣称 DPI。

## 11. B8：页面功能去留与原生 LuCI 导航

| Athena 页面/功能 | 处理建议 | 实施条件 |
|---|---|---|
| 概览 | 保留实时速率、资源、WAN/IPv6 摘要 | 统一错误/过期状态；硬件加速展示不冒充开关 |
| WiFi | 保留三频常用快捷设置 | 高级参数跳原生 LuCI；访客网络通过 B5 后才开放 |
| 设备 | 保留设备识别、备注、拉黑 | B4 规则所有权与持久化通过测试 |
| 网络 | 保留单臂/VLAN 专家向导和只读诊断 | B3 保护状态机通过独立环境验收；普通网络设置跳原生 LuCI |
| 存储 | 保留 USB 识别、挂载状态 | 格式化移入危险操作；FileBrowser 必须 LAN 绑定和 /mnt/usb 目录限制 |
| 灯光 | LED 与点阵屏合并为设备灯光 | 删除未集成“完整管理”入口前确认没有其他调用者 |
| 维护 | 保留 Athena 自动备份策略、定时重启偏好 | 通用升级/恢复优先链接原生 LuCI；Athena 后端安全修复前不开放危险快捷操作 |
| 高级 | 保留 Athena 专属偏好、关键状态 | 通用服务/进程/软件包/日志优先原生 LuCI；移除 SSH 假开关 |

原生页面替代前，必须在当前固件确认对应菜单确实存在、权限可用、功能完整；不能仅按上游 LuCI 常见路径推断。

## 12. 测试与验收分层

### T0：静态检查
- Shell 脚本语法：目标 BusyBox ash 兼容。
- JSON/ACL JSON 语法校验。
- ucode 语法与运行时版本校验。
- 全仓库 RPC 调用搜索与 ACL 对照。
- 检查所有命令返回码、临时文件权限、锁清理、错误 JSON。

### T1：离线 mock 测试
- 使用 PATH mock 的 uci/nft/fw4/sysupgrade/firstboot/reboot/wifi/init.d/mkfs。
- 所有高危命令替换为记录参数并返回可控状态的 mock。
- 测试非法参数、边界参数、失败注入、并发、进程中断。
- 测试环境必须与真机 rootfs/配置隔离，不能把 mock 脚本安装到在线路由器。

### T2：独立设备/虚拟环境
- 验证 nft 规则、guest 隔离、UCI 回滚、原生 LuCI session rollback、升级包验证和 ACL 行为。
- 网络测试覆盖 PPPoE、VLAN、IPv6、OpenClash、NSS/ECM 的保护项；Athena 项目不应擅自更改这些项目。
- 模式切换/网络回滚只在可恢复的独立设备执行。

### T3：当前 Athena 真机低风险验收
- 仅只读页面、状态刷新、页面导航、日志读取、无写入的参数校验失败用例。
- 不执行任何会重启服务或改变网络/系统状态的用例。
- 需要写入或危险动作时，必须另行列出操作、影响、备份、回退和用户确认。

### T4：APK 与发布验收
- GitHub Actions 构建成功。
- APK 包名/版本/架构正确，签名验证通过。
- 安装前校验 SHA256；保留现有配置和 APK 回退包。
- 安装后只先做只读检查；网络保护项逐一核对。
- 构建成功不等于功能验收通过。

## 13. 建议实施批次（每批独立提交）

1. **Batch 0：基线和测试框架**（只新增测试与文档，不改运行逻辑）。
2. **Batch 1：服务路径校验 + reset 退出码**（不碰网络/升级/ACL）。
3. **Batch 2：upgrade flash 复验**（离线伪造包测试，不执行 sysupgrade）。
4. **Batch 3：ACL 调用者盘点与最小化**（先在独立测试环境验证）。
5. **Batch 4：确认票据公共模块**（只完成模块与 mock 测试，尚不接入网络/刷写）。
6. **Batch 5：设备拉黑与家长控制规则统一**（独立 nft 环境）。
7. **Batch 6：访客网络事务化**（独立无线/防火墙环境）。
8. **Batch 7：备份上传和 USB 格式化保护**（不在真机执行恢复/mkfs）。
9. **Batch 8：进程、偏好、状态反馈**。
10. **Batch 9：页面导航和功能收敛**。
11. **Batch 10：完整构建、验签、分层验收**。

每个 Batch 必须独立提交、独立测试、更新状态文档；失败时只回退该批，不跨批叠加不确定改动。

## 14. 阶段 B 当前结论

- 已根据当前分支源码核对 ACL、动态服务启停、升级、恢复出厂、网络模式、访客网络、设备拉黑、家长控制、备份恢复、进程管理的关键实现。
- 上述设计是整改方案，不是实施结果。
- 阶段 B 的下一步应是确认方案边界和任务排序；在确认前不修改源码、ACL、工作流，不构建 APK，不操作当前 Athena 设备。
