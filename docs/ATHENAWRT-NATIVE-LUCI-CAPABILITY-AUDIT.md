# AthenaWrt 原生 LuCI 能力核对（C2-D）

> 日期：2026-11-02
> 对象：GitHub 当前分支 `athenawrt/apk-fixed-signing` 的构建配置和仓库内菜单定义
> 重要边界：这是构建输入静态核对，不是 Athena 设备实时菜单/ACL/功能验收。

## 1. 核对范围与证据

本次读取：
- `final.config`（SHA `bd6ee8ae3b7f394cbd251c2f5e598abdf919ad2d`）
- `luci-app-athena-src/configs/packages.list`（SHA `8cd12375cfa459e4c8a0ed2edf8ec784c1bba5ef`）
- `luci-app-athena-src/configs/jdcloud_re-cs-02.seed`（SHA `709a97f84475065a4c6c3df5d5a78cc4b239732a`）
- `luci-app-athena-src/frontend/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json`（SHA `ec5e21aeea6a1276a674510bfe9eb39dc2085686`）
- `luci-app-athena-src/frontend/luci-app-athena/Makefile`（SHA `755cb7e22f18907e90694c887c10d7d081662fda`）

仓库没有包含完整的 ImmortalWrt feeds 源码、最终 rootfs 菜单树或设备当前 `/usr/share/luci/menu.d` 与 ACL 文件快照，因此无法仅从仓库证明当前设备页面是否实际可见、可访问和可正常保存。

## 2. 构建配置明确选入的 LuCI 基础能力

`final.config` 显示以下组件为启用：
- `luci`、`luci-base`、`luci-light`
- `luci-mod-admin-full`
- `luci-mod-network`
- `luci-mod-status`
- `luci-mod-system`
- `luci-app-firewall`
- `luci-app-package-manager`
- `luci-proto-ipv6`、`luci-proto-ppp`
- `luci-i18n-base-zh-cn`、`luci-i18n-firewall-zh-cn`、`luci-i18n-package-manager-zh-cn`
- `rpcd`、`rpcd-mod-file`、`rpcd-mod-iwinfo`、`rpcd-mod-ucode`、`rpcd-mod-luci`、`rpcd-mod-rrdns`

据此可得：
1. 当前构建配置具有 LuCI 网络、状态、系统基础模块。
2. 防火墙和 APK 软件包管理存在明确的构建选入证据。
3. IPv6/PPP 协议页面支持包存在构建选入证据，但不能由此断定 PPPoE/VLAN 当前运行配置或菜单每项功能。
4. 这些组件是“构建配置选入”，仍需在设备上核验菜单、权限和实际功能。

## 3. 专用 LuCI 应用包的配置冲突

当前仓库的 `configs/packages.list` 声明选择：
- `luci-app-firewall`
- `luci-app-ddns`
- `luci-app-ttyd`
- `luci-app-fullconenat-sonic`
- `luci-app-athena-led`
- Athena 相关依赖/语言包。

但当前 `final.config` 对应项存在差异：
- `luci-app-firewall=y`：一致。
- `luci-app-ddns`：显示未选入。
- `luci-app-ttyd`：显示未选入。
- `luci-app-diskman`、`luci-app-filebrowser`、`luci-app-ksmbd`、`luci-app-samba4`：显示未选入。
- `luci-app-openclash`、`luci-app-passwall`、`luci-app-smartdns`、`luci-app-adguardhome`、`luci-app-dockerman`、`luci-app-nlbwmon`、`luci-app-vnstat2`、`luci-app-wol`、`luci-app-upnp`、`luci-app-sqm`、`luci-app-mwan3`：显示未选入。
- `luci-app-cpufreq=y`：已选入。

这说明 `packages.list` 和 `final.config` 不能作为同一最终镜像的完整一致证据。可能原因包括配置文件滞后、构建阶段覆盖、不同构建快照或包清单未被当前 workflow 完整应用；在核对 workflow 生成链前，不做原因定论。

## 4. 当前原生 LuCI 替代判定矩阵

| Athena 功能 | 原生能力证据 | 当前结论 | 下一步 |
|---|---|---|---|
| 通用网络接口/协议 | `luci-mod-network`、PPP/IPv6 proto 包选入 | 原生替代候选 | 设备上核对接口/协议页面、ACL、保存行为；Athena 单臂/VLAN 向导保留 |
| 状态/系统信息 | `luci-mod-status`、`luci-mod-system` 选入 | 原生替代候选 | 核对状态、进程、启动项、计划任务等实际菜单 |
| 防火墙 | `luci-app-firewall` 选入且中文包选入 | 有较强构建证据 | 核对页面可见性、nftables 后端和现有防火墙规则编辑行为 |
| APK 软件包管理 | `luci-app-package-manager` 选入且中文包选入 | 有较强构建证据 | 核对安装/卸载/升级保护；Athena 关键包保护不能只依赖 UI |
| 无线高级设置 | `luci-mod-network` 基础模块 | 候选，不可直接删除 Athena 三频管理 | 核对无线菜单、三频 radio 映射、保存/重载行为 |
| DDNS | packages.list 选入，但 final.config 未选入 | 未确认 | 先解决构建配置冲突，再核对设备菜单和服务 |
| 网页终端 | packages.list 选入，但 final.config 未选入 | 未确认 | 不把 ttyd 当作系统原生默认能力 |
| USB 磁盘管理 | final.config 中 diskman 未选入 | 没有当前构建证据 | Athena USB 管理暂保留 |
| 文件共享 | filebrowser/Samba/ksmbd 对应 LuCI app 未选入；Athena 包自带 FileBrowser | Athena 专属 | 保留受限 USB 文件访问；不新增 NAS/Samba |
| 进程/服务/日志 | 有基础系统模块，但未逐项确认菜单实现 | 未确认 | 不以 `luci-mod-system` 名称推断所有管理页都存在 |
| 固件升级/配置恢复 | 基础 LuCI 存在不等于升级/恢复路径已验收 | 未确认 | 先核对当前页面、设备兼容性和保留配置行为 |

## 5. Athena 自己的 LuCI 菜单定义

Athena 菜单 JSON 当前只定义：
- `admin/athena`：AthenaWrt SPA 主页面。
- `admin/athena/advanced`：alias 到 `admin/status`，标题为“高级模式（LuCI）”。

这说明 Athena 的“高级模式（LuCI）”不是一个完整的新页面，而是跳转到原生 `admin/status` 菜单树。具体可见的子菜单仍由当前固件中其他 LuCI 包的菜单 JSON 和 ACL 决定。

## 6. 功能去留的当前决定

### 可以确定保留
- Athena 专属首页实时网速和设备摘要。
- Athena 三频 WiFi 快捷管理。
- 设备识别、备注、拉黑、家长控制。
- Athena 单臂/VLAN 专用向导和诊断。
- Athena USB 设备识别、挂载管理及受限 FileBrowser。
- Athena 专属 LED/点阵屏、定时维护和自动备份偏好。
- NSS/ECM 只读状态，不增加开关。

### 原生替代候选，暂不删除 Athena 代码
- 通用网络接口/协议配置。
- 通用防火墙配置。
- 通用软件包管理。
- 通用状态、系统信息及部分系统管理。

### 暂不确认原生替代
- 无线高级参数、DDNS、网页终端、USB 磁盘管理、服务/进程/日志、固件升级/恢复。
- 原因：缺少设备实时菜单与权限证据，或仓库构建配置存在冲突。

## 7. 需要设备端只读核验的最小证据

为完成最终菜单确认，需要从当前 Athena 设备只读采集：
1. `ls -1 /usr/share/luci/menu.d/`
2. `ls -1 /usr/share/rpcd/acl.d/`
3. `apk info | grep -E '^(luci|rpcd|firewall|ddns|ttyd|diskman|filebrowser|samba|ksmbd)'`
4. LuCI 页面中“状态 / 系统 / 网络”展开后的菜单名称。

以上均为只读命令，不改配置、不重启服务、不触发网络变更。设备证据拿到后，再把“候选”升级为“已确认可替代”或“保留 Athena”。

## 8. 本轮结论

- 仓库构建配置明确包含 LuCI 网络、状态、系统、防火墙、APK 软件包管理基础能力。
- 当前 `packages.list` 与 `final.config` 在 DDNS、ttyd 等包上不一致，必须先核实构建链，不能用其中任一文件冒充设备实际安装清单。
- Athena 当前菜单只将“高级模式（LuCI）”指向 `admin/status`；并未在 Athena 包中声明完整原生菜单。
- 本轮没有删除、隐藏或重定向任何功能；没有修改源码、ACL、workflow、APK 或设备配置。
