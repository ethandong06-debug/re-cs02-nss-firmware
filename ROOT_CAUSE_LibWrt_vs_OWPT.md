# LibWrt vs OWPT 测速差距根因分析

> 结论先行：**差距根因是 NSS 硬件加速栈对「自定义桥内 VLAN + PPPoE」拓扑的端口映射支持不同**。LibWrt 25.12-nss 的内核补丁式 NSS 栈无法为 WanAll 桥内的 VLAN/PPPoE 流量建立硬件加速实例；OWPT（immortalwrt_ipq）以独立包 + portifmgr 兼容补丁补齐了端口接口管理，预期恢复 ~1.5G。

## 一、实测证据链（v0.4 / LibWrt 25.12-nss）

| 证据 | 数值/现象 | 指向 |
|---|---|---|
| 测速 | WiFi160 握手 2400Mbps，外网实测 600~800M（峰值勉强 1000M） | NAT 路径瓶颈 |
| 有线对照 | 2.5G 口直连测速同样 ~600M | 排除空口，瓶颈在 NAT/路由层 |
| ECM 加速计数 | 测速中 `tcp/udp_accelerated_count=0`，`connection_count=0` | 无连接被 ECM 接管 |
| ECM 异常统计 | `v4_ported_from/to_hierarchy_creation_fail` = 23292 / 41555 | 加速层级创建失败（端口归属） |
| dmesg | `nss_vlan_mgr: WanAll: 31 is not valid physical port` | NSS VLAN 管理器不认识 WanAll 桥的 VLAN→物理端口映射 |
| NSS debugfs | 无 vlan / bridge 实例创建 | 驱动侧未建立加速路径 |
| 桥内流量统计 | `v4_bridge_routed_packet_wrong_hook` 1268万 / `v4_bridge_local_packets_ignored` 879万 | 桥内流量未走 ECM 预期 hook |

**定位**：用户拓扑为「WanAll 自定义桥 + VLAN + PPPoE」单臂/多业务方案。NSS 硬件加速要求驱动能识别每个逻辑端口（VLAN/桥成员）到物理端口（ssdk port）的映射。LibWrt 25.12-nss 把 NSS 以 **kernel 补丁栈**（patches-6.12/0600~0607）打入，其 vlan-mgr/bridge-mgr 端口规划是内置的，遇到自定义 WanAll 桥时端口号（31）越界/无法匹配 → 加速实例创建失败 → 全部流量退回软件 NAT（nf_flow_table 也因 ECM 冲突未启用）→ 下行被 CPU NAT 限制在 ~600M-1G。

## 二、OWPT（immortalwrt_ipq）做了什么不同

| 项 | LibWrt 25.12-nss（v0.4） | OWPT immortalwrt_ipq（v0.5） |
|---|---|---|
| Kernel | 6.12.108 | 6.18 系 |
| NSS 形态 | 内核补丁（patches-6.12/0600~0607） | 独立包（package/qca-nss/qca-nss-clients 等） |
| 端口管理 | 内置 vlan-mgr/bridge-mgr，自定义桥支持弱 | **portifmgr 端口接口管理器** + `002-compat-bridge-vlan-lag-portifmgr-linux-6.18.patch` |
| 桥内 VLAN/LAG | 报 `31 is not valid physical port` | 补丁显式兼容 bridge/vlan/lag 端口接口 |
| PPPoE 卸载 | 有 qca-nss-drv-pppoe 但端口映射失败 | 同栈 + 正确端口归属 |
| 预期效果 | NAT 软件路径 600-1000M | NSS 硬件卸载后回到 ~1.2-1.5G |

## 三、为什么 v0.4 的多次修补无效

尝试过：关闭 ECM bridge VLAN filtering、hairpin_mode、add_wanif、br-netfilter 开关、重启 ECM 重注册——ECM 侧计数仍为 0，dmesg 持续报 `31 is not valid physical port`。因为问题在内核侧 NSS vlan-mgr 对自定义桥的**端口号映射能力**，用户态开关无法绕过。

## 四、v0.5 验证清单（判定标准）

1. `cat /sys/kernel/debug/ecm/ecm_db/iface_count` → 非 0；
2. 测速中 `cat /sys/kernel/debug/ecm/ecm_db/connection_count` 与 `ecm_nss_ipv4/accelerated_count` 增长；
3. dmesg 不再出现 `not valid physical port`；
4. 外网测速 ~1.2-1.5G（2.5G 口，WiFi160 下）。

全部通过 → 本差距结论成立，v0.5 即为修复版；后续迭代基于 v0.5 栈继续。
