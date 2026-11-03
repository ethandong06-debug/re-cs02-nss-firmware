# AthenaWrt 项目状态（唯一交接入口）

> 新对话只需先读本文件，再核对本分支最新 HEAD 与最近一次 Actions。详细技术证据按需查阅第 7 节列出的两份审计文档，不再逐份读取历史计划。
> 更新日期：2026-11-03

## 1. 当前项目

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`
- 分支：`athenawrt/apk-fixed-signing`
- 本轮 Athena 源码提交：`91a811d36958a4e6107687e9c133dd628c7d02cc`（后续文档提交不改变源码基线）
- 设备：JDCloud Athena RE-CS-02 / IPQ6018，ImmortalWRT SNAPSHOT r1-20261017。
- 交付形式：独立 LuCI APK，通过 GitHub Actions 构建；不编译/刷写整机固件。
- 当前设备安装：`luci-app-athena-1.2.60-r2`（Run #188 对应版本）。

## 2. 不可突破的约束

未经用户明确授权，不得：
- 修改或破坏 PPPoE、VLAN 2044、IPv6 PD/SLAAC、防火墙/NAT。
- 停止、关闭或改变 OpenClash、NSS/ECM 及相关驱动/硬件加速。
- 刷写固件、恢复出厂、切换网络模式、重启网络、格式化磁盘或执行其他高风险设备操作。
- 删除或替换用户现有功能。

只做独立 APK；不要求用户搭建本地编译环境；不绕过 APK 签名验证。

## 3. 最新构建与设备验收

- 本轮包版本已提升为 `1.2.60-r3`，避免与设备当前安装的 r2 同版本冲突。
- 最新构建：Run #197，ID `41565253767`，源码提交 `91a811d36958a4e6107687e9c133dd628c7d02cc`；当前状态为 in progress，正在构建 Athena APK，尚无最终 Artifact/SHA256。
- Run #197 的静态检查已通过：Shell 语法、ACL/menu JSON、24 个直接 RPC 脚本与 Makefile/ACL 对应关系、3 段内嵌 JavaScript Node 语法。
- Run #192 因第一次提交的内嵌 JS 转义错误失败；后续已修正，Run #193–196 因新提交取代旧源码而取消。以 Run #197 为最终验证。
- 设备当前已验收基线仍是 `luci-app-athena-1.2.60-r2`（Run #188）；r3 尚未安装，不能视为设备验收通过。
- Run #197：https://github.com/ethandong06-debug/re-cs02-nss-firmware/actions/runs/41565253767
- Run #188 对应的 r2 已通过签名验证、模拟升级、正式安装、原 root 密码 SSH 登录和首页初步目视检查。

## 4. 当前审计基线

当前正式 SPA 源码基线经本轮 Athena 专项修改，源代码提交为 `91a811d36958a4e6107687e9c133dd628c7d02cc`：
- `index.html` 在保留原 CRLF 行尾的前提下，只修改固件刷写 SHA 传递、恢复出厂确认交互和 Athena 软件包保护入口；没有 CSS 重写或页面重构。
- 79 处 RPC 调用；24 个直接后端脚本入口，另有动态目标需结合参数来源理解。
- Makefile 安装 36 个 libexec 文件，包含 Shell、ucode、legacy fallback 和 helper；不能把安装文件数等同 RPC 数。
- 设备已安装菜单与 Athena ACL 已核对；Athena 主菜单、LED 独立菜单、原生 LuCI 菜单和 package-manager ACL 均已采集。
- 设备包信息确认当前安装版本为 1.2.60-r2。APK cache 的 video 源缺失警告与本次只读盘点无关，不作为本项目待办。

## 5. 本轮 Athena 专项整改结果

**已修改（仅 Athena 自有文件，9 个文件；无原生 LuCI 文件改动）**
1. Athena ACL 收敛为 24 个直接 RPC 脚本的执行权限，以及恢复备份所需的单一路径写权限；删除未见调用依据的通用 UCI 权限和 network init/ping/nslookup/ubus 额外执行授权。
2. `athena-upgrade.sh` 的 verify/flash 共用完整校验：固定临时路径、拒绝符号链接、完整 tar 成员路径检查、本机 board 目录、CONTROL/kernel/root、SHA256；flash 再次校验并复制到 root-only 暂存文件，增加并发锁和 `sysupgrade -T`。
3. Athena 服务管理仅允许静态审计白名单 `ddns`、`ttyd`、`matrix` 启停；动态发现服务只读展示，后端校验 ID、状态和 init 名。
4. 恢复出厂改为 256-bit 随机一次性确认码，60 秒有效、消费后才执行 `firstboot`；失败返回非零，前端按真实结果反馈。
5. Athena 网络模式原有 `nss_off()` 调用点改为保持/启动 NSS/ECM，不再停止 `qca-nss-ecm` 或删除硬件加速相关配置。
6. Athena 软件包页面隐藏关键包安装/卸载入口；Athena 后端保护 OpenClash、NSS/ECM、内核、网络栈和关键 LuCI，并预演 APK 事务，阻止依赖事务间接升级/降级/移除受保护组件。
7. Makefile 包版本提升至 `1.2.60-r3`。

**明确排除**
- 原生 LuCI 页面、菜单、ACL、原生软件包管理器及其后端完全未修改。原生软件包管理器仍保留其原有权限，因此本轮关键包保护只覆盖 Athena 页面；通过原生软件包管理器操作不在本轮保护范围内。
- 未执行设备刷写、恢复出厂、网络模式切换、服务启停、软件包安装或卸载；未改 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash、NSS/ECM 现网配置。

**尚待验收**
- Run #197 完整构建、签名验证和 APK Artifact 尚未结束。
- r3 尚未安装到设备；固件刷写/恢复出厂/模式切换仅做静态与构建验证，不做真机危险操作。

**P1**
1. 访客网络多份 UCI 配置的事务性和失败回滚。
2. nftables 设备拉黑/家长控制规则的专属所有权、原子更新与持久化。
3. USB 格式化前后设备身份复核及热插拔竞态。
4. FileBrowser 必须随机密码、只绑定 LAN、根目录固定 /mnt/usb；设备当前包源码已有相关实现，但仍需真机专项验收。
5. 前端错误状态、预览/模拟数据与真实 RPC 数据源需区分；首页网速必须确认实际使用采集结果。
6. ACL 和后端保护必须在服务端执行，不能只隐藏前端按钮。

以上是静态源码发现，不等于设备已发生故障或功能已通过真机测试。

## 6. 已完成的设备只读核验

- Athena 菜单：`admin/athena` 指向 `athena/index`；“高级模式（LuCI）”是到 `admin/status` 的 alias。
- 本轮源码 ACL 已收敛为 Athena 专属 `file.exec` 白名单和备份上传所需的 `/tmp/athena-restore.b64` 写权限；设备端尚未安装 r3，因此设备当前实际 ACL 仍是 r2 版本。
- Athena LED 是独立菜单/ACL，使用 `athena_led` UCI；不能仅凭名称认定与主界面 LED 重复。
- 原生 package-manager ACL 的既有 install/remove/update/upgrade 权限未改动；Athena 自有软件包页面新增独立保护。
- 设备安装包清单包含 legacy/ucode/helper 文件，必须按调用关系判断是否冗余。

## 7. 仅保留的技术证据文档

需要查具体细节时再打开，不作为每次启动必读：
1. `docs/ATHENAWRT-CURRENT-SOURCE-REVALIDATION.md`：当前源码复核、页面/功能与版本基线。
2. `docs/ATHENAWRT-FRONTEND-BACKEND-CALLCHAIN-AUDIT.md`：控件、RPC、参数、后端分支、ACL 和风险证据。

本文件是唯一进度入口。历史规划和重复清单已从活动文档集中清理；Git 历史仍保留原提交，可追溯。

## 8. 下一步（精简流程）

1. 等待 Run #197 完成 `1.2.60-r3` 构建、APK 签名与依赖模拟验证；记录 Artifact ID 和 SHA256。
2. 对构建产物执行签名核对；未通过签名和哈希核对前不安装。
3. 用户确认后再进行 r3 设备安装验收；安装前备份，验证仅针对 Athena 页面，不运行任何网络模式/刷写/恢复出厂动作。
4. 后续 P1 仅在用户另行安排时处理：访客网络事务、nftables 规则所有权、USB 身份竞态、FileBrowser 真机验收、首页网速数据源。

**当前阶段：Athena 专项 P0 源码修改已提交；自动化静态检查通过；最终 r3 构建进行中。设备未改动。


## 9. 2026-11-03 文档精简记录

- 主状态文档由约 42 KB 压缩至约 5.8 KB；架构优化计划由约 25 KB 压缩至约 4.5 KB。
- `docs/` 活动文档收敛为四份：本状态文件、精简架构计划、当前源码复核、前后端调用链审计。
- 已从活动文档目录删除五份重复/阶段性进度文档：功能操作清单、功能重组规划、功能去留矩阵、原生 LuCI 能力审计、整改实施计划。其历史版本仍可通过 Git 提交历史追溯。
- 清理仅涉及 Markdown 文档；没有删除源码、测试、工作流、构建配置、固件归档或设备验收证据。
- 本次提交序列：状态精简 `856d653539f1d9d52fbea375f07ab7fe3fbc76c2`；架构计划精简 `55c9ad5663bd031dbc9ebd1986be15e049868cf2`；重复文档清理最终提交 `c22f46a44adf6ca4b326e1a8572c4b16edca192f`。
- 后续新对话默认只读本文件；只有需要具体源码证据时才读取两份详细审计文档。纯文档提交不触发 APK 构建。
