# RE-CS-02 NSS v0.1 — 实机验证步骤与后续路线

> 当前固件：initramfs 验证镜像（未刷写 eMMC）。本文件说明现在要做什么、怎么判定通过、以及通过后怎么走。

## 0. 当前情况

- v0.1 固件已编译完成并归档（见 README.md / ARCHIVE.md）。
- 设备已刷第三方 U-Boot，可进入 Web 恢复页。
- **尚未实机启动过这个固件**。本阶段目标：用 initramfs 临时内存启动，确认硬件基本可用，再决定是否刷 sysupgrade。
- 未实测的关键点：2.5G 协商（QCA8081）、PPPoE NSS 卸载、单臂 VLAN+PPPoE+NSS 组合。

## 1. 准备

1. 从本仓库下载 `libwrt-...-initramfs-uImage.itb`（20,157,004 B，SHA256 `34ae3a13…`）。
2. 电脑网线插路由器 **LAN 口**（1G 口）。
3. 电脑网卡设固定 IP：`192.168.1.10` / 掩码 `255.255.255.0` / 网关 `192.168.1.1`。

## 2. 进入 U-Boot Web 恢复页

1. 路由器断电。
2. 按住 reset 不松手 → 插电 → 约 10 秒后松开。
3. 浏览器开 `http://192.168.1.1`，看到第三方 U-Boot 恢复界面。
4. 进不去就断电重试，时序以该 U-Boot 版本为准。

## 3. 上传启动（只选 initramfs）

- 选 **initramfs / RAM 启动 / 临时加载** 栏，上传 `.itb`。
- **不要点**任何写 flash / eMMC / factory / sysupgrade / bootloader 的按钮。
- 启动后等 1–2 分钟。

## 4. 启动后验证（SSH `root@192.168.1.1`，无密码）

逐条执行并记录输出：

```sh
uname -a                                   # 期望 Linux 6.12.108
ip -br addr                                # 列出全部接口，找 2.5G WAN 口名
lsmod | grep -E "nss|ssdk"                 # 期望看到 drv/ecm/dp/pppoe/vlan-mgr/bridge-mgr
dmesg | grep -iE "ath11k|firmware" | tail -30   # 期望无 firmware missing / bdf not found
iw dev                                     # 期望 3 个 WiFi phy（2.4G / 5G低 / 5G高 QCN9024）
ethtool wan | grep -iE "speed|link"       # wan 换成第2步看到的口名；期望 2500Mb/s
free -m
for z in /sys/class/thermal/thermal_zone*/temp; do echo -n "$z: "; cat $z; done
```

## 5. 判定标准

| 检查项 | 通过 | 不通过（不代表失败） |
|---|---|---|
| 内核 6.12.108 | uname 正确 | 版本不对 |
| NSS 栈 | drv/ecm/dp/pppoe/vlan-mgr/bridge-mgr 都在 | 缺模块 → 发 dmesg |
| WiFi 固件 | 无 missing/bdf 报错，3 个 phy 出现 | QCN9024 报错 → 发日志 |
| 2.5G WAN | ethtool 显示 2500Mb/s | 显示 1000Mb/s / No link → 记录，需调 phy-mode |
| 启动 | SSH/LuCI 可进，uptime 增长 | 启动失败 → 断电回原系统，发现象 |

## 6. 安全退出

验证完**直接断电**。initramfs 在内存，重启后回到原系统，无残留。

## 7. 后续路线（按门控推进，每步需人工确认）

1. **v0.1 本阶段**：initramfs 临时启动 → 上面 7 项验证 → 记录结果。
2. **v0.2**：验证通过后刷 sysupgrade → 24 小时基础功能（PPPoE 拨号/重拨、DHCP、DNS、NAT、IPv6）。
3. **v0.3**：72 小时组合场景 —— 2.5G WAN+VLAN+PPPoE+NAT、单臂 trunk 双 VLAN 验证，加持续下载压力。
4. **v1.0**：7×24 家庭负载运行，记录 CPU/内存/温度/日志，确认长期稳定后才算正式主路由。

每完成一阶段，对应固件、.config、manifest、SHA256 会作为新 commit 推到本仓库。

## 8. 红线

- 全程不点写 flash/eMMC 按钮。
- 未验证通过前不刷 factory/sysupgrade。
- 不改 U-Boot / GPT / ART。
- 不加入 OpenClash/PassWall/Docker 等非必要包。
