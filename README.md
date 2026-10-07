# RE-CS-02 NSS Firmware 归档

JDCloud **RE-CS-02（京东云雅典娜，IPQ6010 / qualcommax-ipq60xx）** 长期稳定主路由固件的构建归档。
当前阶段：**v0.1 硬件验证固件（initramfs 临时内存启动验证，尚未刷写 eMMC）**。

## 当前状态

- 源码：LiBwrt/LibWrt `25.12-nss` @ `3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70`
- Kernel：6.12.108
- NSS feed：qosmio/nss-packages @ `0d970dbf0185e3f53709bd803e8a466598023c57`
- **默认 LAN：`192.168.10.1/24`**（2026-10-07 由 192.168.1.1 变更，patch 见 `patches/0001-lan-ip-192.168.10.1.patch`）
- 用途定位：7×24 PPPoE 主路由，重点验证 2.5G WAN / VLAN / PPPoE / NAT / 三频 WiFi
- 验证进度：v0.1（192.168.1.1 版）实机硬件验证**通过**（2.5G=2500Mb/s、NSS 全套、三频 WiFi）；PPPoE NSS 卸载、单臂 VLAN 组合**未实测**

## 仓库内容

| 文件 | 说明 |
|---|---|
| `ARCHIVE.md` | **逐文件归档说明**（每个固件的字节/SHA256/用途/可刷性/风险），先读这个 |
| `VERIFICATION.md` | **实机验证步骤 + 判定标准 + 后续 v0.2/v0.3/v1.0 路线**，现在按这个做 |
| `VERIFICATION_RESULT_v0.1.md` | v0.1 实机验证结果记录（2026-10-07，192.168.1.1 版） |
| `V0.2_PLAN.md` | v0.2 刷写 + 24h 测试方案 |
| `CHANGELOG.md` | 版本变更记录 |
| `patches/0001-lan-ip-192.168.10.1.patch` | LAN IP 变更 patch |
| `libwrt-...-initramfs-uImage.itb` | 本阶段验证镜像，仅经 U-Boot 临时加载到内存运行，**禁止写 eMMC** |
| `libwrt-...-squashfs-factory.bin` | 首刷镜像，自动附带生成，本阶段**禁止刷写** |
| `libwrt-...-squashfs-sysupgrade.bin` | 升级镜像，本阶段**禁止刷写** |
| `final.config` | 最终 .config（make defconfig 后），复现构建依据 |
| `feeds.conf.frozen` | 全部 feeds 冻结到指定 SHA |
| `package.manifest` | 固件内 273 个包清单 |
| `sha256sums.txt` | 构建系统原生校验和 |

校验：`sha256sum -c sha256sums.txt`

## 安全边界

- 未改 DTS / Kernel patch / U-Boot / GPT 分区 / ART；自研 patch 仅 1 个（LAN IP）。
- 验证顺序：U-Boot 恢复页 → initramfs 临时启动 → 逐项确认 → 全部通过后才进 sysupgrade。
- 任何写 flash/eMMC 的操作都需人工确认。
- **注意**：U-Boot 恢复页固定 `192.168.1.1`；OpenWrt 固件管理入口为 **`http://192.168.10.1`**。
