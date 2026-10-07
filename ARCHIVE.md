# RE-CS-02 NSS v0.1 硬件验证固件 — 归档说明

> 本目录是 **JDCloud RE-CS-02（京东云雅典娜，IPQ6010 / qualcommax-ipq60xx）** 的第一阶段硬件验证固件归档。
> 初版编译日期：2026-10-01；**LAN IP 变更版（192.168.10.1）：2026-10-07**。本阶段**只用于 initramfs 临时内存启动验证，尚未刷写 eMMC**。
>
> **变更（2026-10-07）**：默认 LAN 网段由 `192.168.1.1/24` 改为 `192.168.10.1/24`（patch：`patches/0001-lan-ip-192.168.10.1.patch`，仅改 `config_generate` 一行，DHCP 范围自动跟随为 192.168.10.100–249）。其余组件与已验证的 v0.1 完全一致。

## 1. 构建基线（冻结，不可变）

| 项 | 值 |
|---|---|
| Repository | https://github.com/LiBwrt/LibWrt |
| Branch | `25.12-nss` |
| Commit SHA | `3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70` |
| Commit Date | 2026-09-30 07:59:51 +0800 |
| Kernel | 6.12.108（qualcommax KERNEL_PATCHVER=6.12） |
| Toolchain | aarch64_cortex-a53 musl，gcc 14.3.0 |
| Target / Subtarget | `qualcommax` / `ipq60xx` |
| Device Profile | `Device/jdcloud_re-cs-02`（config@cp03-c3，EmmecImage） |
| NSS feed（关键） | qosmio/nss-packages @ `0d970dbf0185e3f53709bd803e8a466598023c57` |
| 默认 LAN | `192.168.10.1/24`（DHCP 192.168.10.100–249） |

其余 feeds SHA 见 `feeds.conf.frozen`。

## 2. 文件清单（每个文件的准确信息）

| 文件 | 字节数 | SHA256 | 用途 | 是否可刷 |
|---|---:|---|---|---|
| `libwrt-...-initramfs-uImage.itb` | 20,154,184 | `ebb1bb7156556b1f042ec3975897c5795a3ee919a7ad2d469f08fc2a0a16f019` | **本阶段唯一验证镜像**：经 U-Boot 恢复页临时加载到内存运行，重启即失，不碰 eMMC | 仅临时 RAM 启动，禁止写盘 |
| `libwrt-...-squashfs-factory.bin` | 19,947,673 | `b9fd46a72182f4def7293ab021dae7672fb55937093465b7b7d1eaecb22d9836` | 首刷镜像（自动附带生成） | **本阶段禁止刷写** |
| `libwrt-...-squashfs-sysupgrade.bin` | 19,261,713 | `0284ff193f6b8f4b741b8b0134de2b8570f8facd104943a82895e62e763aee42` | 系统升级镜像（自动附带生成） | **本阶段禁止刷写** |
| `final.config` | 309,537 | `240b76a5317ca4d3dda0ac8eaf37f2b4cbd7dd66d42d2970dc160daafccd6310` | `make defconfig` 后的最终 .config，复现构建的依据 | — |
| `package.manifest` | 9,152 | `5fd552a3ebdf48e67df4900b25dda07649e4135e2bc66c0b9a442b1a2194caee` | 固件内 273 个包清单（含版本） | — |
| `feeds.conf.frozen` | 945 | `63108347d4b56accc14533681ccb5bc91a7489e39c3a5589f5c05025c8a4eb9e` | 全部 feeds 冻结到指定 SHA（含 nss=0d970dbf） | — |
| `sha256sums.txt` | — | 见本表三个镜像 | 构建系统原生生成的校验和（与上表一致） | — |
| `patches/0001-lan-ip-192.168.10.1.patch` | — | — | **LAN IP 变更 patch（2026-10-07 新增）**：`config_generate` 默认 lan 地址 192.168.1.1 → 192.168.10.1 | — |

校验命令：`sha256sum -c sha256sums.txt`（在镜像同目录）。

## 3. 固件内容核验要点（已在编译产物中确认存在）

- NSS 全套：`kmod-qca-nss-dp / -drv(11.4) / -ecm / -pppoe / -vlan-mgr / -bridge-mgr / -wifi-meshmgr / kmod-nss-ifb / kmod-qca-ssdk(CPPE) / nss-firmware-ipq60xx`
- WiFi：`kmod-ath11k-ahb/-pci` + `ath11k-firmware-qcn9074`（QCN9024）+ `ipq-wifi-jdcloud_re-cs-02`（BDF）
- PPPoE：`kmod-pppoe / ppp-mod-pppoe / luci-proto-ppp`
- LuCI（light + 中文）+ `wpad-openssl`
- **未包含**：OpenClash / PassWall / Docker / 广告插件 / 自定义 60s 回滚 / 自定义 watchdog

## 4. 未改项（安全边界）

- 未修改 DTS、未改 Kernel patch（沿用分支自带 130 个 qualcommax patches-6.12）、未改 U-Boot、未动 GPT/分区/ART。
- **新增自研 patch 仅 1 个**：`patches/0001-lan-ip-192.168.10.1.patch`（LAN 默认 IP）。

## 5. 实机验证状态（2026-10-07，旧镜像 192.168.1.1 已验证）

- v0.1（192.168.1.1 版）实机验证**全部通过**：2.5G=2500Mb/s、NSS 全套加载、三频 WiFi 全起、LAN/DHCP 正常（详见 `VERIFICATION_RESULT_v0.1.md`）。
- **LAN IP 变更版（192.168.10.1）仅改动默认网段，其余组件与已验证版一致；需在 v0.2 刷写后复验管理入口 `http://192.168.10.1`**。
- 未实测：PPPoE NSS 卸载、单臂 VLAN+PPPoE+NSS 组合、IPv6 双栈。
- 已知非阻塞：ath11k `regd update : -22` 告警（不影响 AP）。
