# AthenaWrt 项目状态（唯一交接入口）

> 新对话只需先读本文件，再核对本分支最新 HEAD 与最近一次 Actions。详细技术证据按需查阅第 7 节列出的两份审计文档，不再逐份读取历史计划。
> 更新日期：2026-11-03

## 1. 当前项目

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`
- 分支：`athenawrt/apk-fixed-signing`
- 本次核对基线 HEAD：`bbe414753ae28c3e05756f58337917b0473e4687`
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

- 最新已知 Actions：Run #191，ID `41472009979`，结果 success。
- 构建源码提交：`e355f81fd508575ba2e07c4b9939aab60ebddd9c`。
- Artifact：`luci-app-athena-apk`，ID `13160465732`，SHA-256：`075589b93982401f8100a8a2984483e88d5a4b66ecf8c641d0979510ed1c5665`。
- Run #191 Artifact 尚未有设备安装验收记录；不能把它视为已安装。
- Run #188 对应的 1.2.60-r2 已在设备验收：签名验证、模拟升级、正式安装、原 root 密码 SSH 登录和首页初步目视检查通过。
- 版本号相同不代表 APK 相同；Run #191 与 Run #188 的产物必须按各自 SHA-256 区分。
- Run #191 链接：https://github.com/ethandong06-debug/re-cs02-nss-firmware/actions/runs/41472009979

## 4. 当前审计基线

当前正式 SPA 源码来自 `e355f81fd508575ba2e07c4b9939aab60ebddd9c`：
- `index.html`：4,106 行，284,481 bytes。
- 79 处 RPC 调用；24 个直接后端脚本入口，另有动态目标需结合参数来源理解。
- Makefile 安装 36 个 libexec 文件，包含 Shell、ucode、legacy fallback 和 helper；不能把安装文件数等同 RPC 数。
- 设备已安装菜单与 Athena ACL 已核对；Athena 主菜单、LED 独立菜单、原生 LuCI 菜单和 package-manager ACL 均已采集。
- 设备包信息确认当前安装版本为 1.2.60-r2。APK cache 的 video 源缺失警告与本次只读盘点无关，不作为本项目待办。

## 5. 已确认的重点问题（静态审计，未修复）

**P0**
1. Athena ACL 对多组 UCI 配置开放读写，并允许额外 file.exec 路径（network init、ping、nslookup、ubus）；需确认其他调用者后收敛。
2. 固件 flash 后端必须独立重复完整机型/镜像结构校验，不能信任前端先行 verify。
3. 恢复出厂、网络模式、备份恢复等危险操作不能只依赖固定确认字符串或前端弹窗。
4. 原生 LuCI 包管理 ACL 允许安装/卸载/升级；Athena 的关键包保护不自动覆盖原生包管理入口。

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
- Athena ACL：允许读取 system/network/wireless 状态；UCI 写权限涉及 athena、network、wireless、dhcp、system、ddns、ttyd；授权 24 个脚本及额外系统命令路径。
- Athena LED 是独立菜单/ACL，使用 `athena_led` UCI；不能仅凭名称认定与主界面 LED 重复。
- 原生 package-manager ACL 包含 install/remove/update/upgrade；未体现 Athena 关键包保护。
- 设备安装包清单包含 legacy/ucode/helper 文件，必须按调用关系判断是否冗余。

## 7. 仅保留的技术证据文档

需要查具体细节时再打开，不作为每次启动必读：
1. `docs/ATHENAWRT-CURRENT-SOURCE-REVALIDATION.md`：当前源码复核、页面/功能与版本基线。
2. `docs/ATHENAWRT-FRONTEND-BACKEND-CALLCHAIN-AUDIT.md`：控件、RPC、参数、后端分支、ACL 和风险证据。

本文件是唯一进度入口。历史规划和重复清单已从活动文档集中清理；Git 历史仍保留原提交，可追溯。

## 8. 下一步（精简流程）

1. 只补齐会影响安全/正确性的未决问题，不再重复盘点已确认的普通 UI 控件。
2. 优先核对 P0：ACL 额外权限调用者、flash 后端复验、危险操作确认边界、原生包管理关键包保护边界。
3. 再核对 P1：访客网络事务、nftables 规则所有权、USB 身份竞态、FileBrowser 真机验收、首页网速数据源。
4. 输出一份精简整改清单，按“必须修 / 建议修 / 保留不动”分类。
5. 用户确认后才修改源码；每个逻辑批次单独提交、构建和验收。
6. 仅在确有新 APK 时才要求设备验收；无需为纯文档提交反复安装。

**当前阶段：静态审计收敛中。当前没有授权修改功能源码、CSS、ACL、构建工作流或设备配置。**
