# RE-CS-02 NSS v0.1 — 实机验证记录

> **版本说明**：本记录基于 **192.168.1.1 版**镜像（SHA256 `34ae3a13…`）。2026-10-07 起默认 LAN 已改为 **192.168.10.1**（v0.1-lan10，仅此一处变更，其余组件完全一致），需在 v0.2 刷写后复验管理入口 `http://192.168.10.1`。

- 验证日期：2026-10-07
- 方式：initramfs 临时内存启动（U-Boot 恢复页加载，未写 eMMC）
- 固件：`libwrt-...-initramfs-uImage.itb`（SHA256 `34ae3a13…`）
- 内核：6.12.108 aarch64（uname 确认）

## 判定结果

| 检查项 | 结果 | 证据 |
|---|---|---|
| 内核 6.12.108 | ✅ | `Linux LibWrt 6.12.108 #0 SMP PREEMPT ... aarch64` |
| 2.5G WAN（QCA8081） | ✅ | `ethtool wan` → `Speed: 2500Mb/s`、`Link detected: yes` |
| NSS 栈 | ✅ | `qca_nss_drv`(622KB, 被 ath11k/mac80211/ecm/pppoe/vlan 使用)、`qca_nss_dp`、`qca_ssdk`(1.1MB)、`qca_nss_pppoe/vlan/bridge_mgr/wifi_meshmgr/lag_mgr/l2tpv2/gre/pptp/map_t/tun6rd/tunipip6/vxlanmgr`、`ecm` 全部加载 |
| 三频 WiFi | ✅ | `iw dev`：phy1=2.4G(ch1, 20MHz)、phy2=5G低(ch36, 80MHz, 5210)、phy0=QCN9024(PCIe)，三个 AP 接口均 up，SSID=LibWrt |
| 内存 | ✅ | ~900MB RAM，used ~227MB，available ~577MB，无 swap |

## 已知问题（不阻塞，记录观察）

1. **ath11k regd update -22**：三个 phy 反复出现 `failed to perform regd update : -22` 并触发内核 WARN 栈（非 panic）。判断为 QCN9074 固件与内核 regdb 交互的已知怪癖（802.11d 域更新被固件拒绝），**不影响 AP 工作**。v0.2 持续观察。
2. **BusyBox ip 无 `-br`**：`ip -br addr` 报 usage，非故障，改用 `ip addr`。
3. **ethtool supported modes 报告不全**：仅列 10baseT，为 nss-dp ethtool 驱动实现不完整；实际协商速率由 ssdk 上报，`2500Mb/s` 可信。

## 尚未验证（v0.2 计划内）

- LAN DHCP 客户端获取（电脑插 LAN 口验证）
- PPPoE 拨号 / 自动重拨（需真实账号）
- VLAN + PPPoE + NSS 组合、单臂 trunk 双 VLAN
- IPv6 双栈 + NSS
- 24h / 72h / 7×24 长时间稳定性

## 结论

**v0.1 硬件验证通过**：2.5G 协商成功、NSS 栈完整加载、三频 WiFi 全部启动。允许进入 v0.2（刷 sysupgrade，24h 基础功能测试）。
