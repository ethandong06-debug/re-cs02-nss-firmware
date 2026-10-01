# RE-CS-02 NSS v0.1 硬件验证固件 — 归档说明

> 本目录是 **JDCloud RE-CS-02（京东云雅典娜，IPQ6010 / qualcommax-ipq60xx）** 的第一阶段硬件验证固件归档。
> 编译日期：2026-10-01（Asia/Shanghai）。本阶段**只用于 initramfs 临时内存启动验证，尚未刷写 eMMC**。

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

其余 feeds SHA 见 `feeds.conf.frozen`。

## 2. 文件清单（每个文件的准确信息）

| 文件 | 字节数 | SHA256 | 用途 | 是否可刷 |
|---|---:|---|---|---|
| `libwrt-...-initramfs-uImage.itb` | 20,157,004 | `34ae3a1367558b6c908214f001261b999647b09f9eb0e327ff3a0beabcc73f60` | **本阶段唯一验证镜像**：经 U-Boot 恢复页临时加载到内存运行，重启即失，不碰 eMMC | 仅临时 RAM 启动，禁止写盘 |
| `libwrt-...-squashfs-factory.bin` | 19,945,261 | `2440c4a52346ee3a6d160054ad8dc08936a7bbdd3ae56bd0200432e8a5dcb6ff` | 首刷镜像（自动附带生成） | **本阶段禁止刷写** |
| `libwrt-...-squashfs-sysupgrade.bin` | 19,261,713 | `5ffa8499810054b129e8735112e684fd8d7df5d9b20c8735112e684fd8d7590862f78778bf6` | 系统升级镜像（自动附带生成） | **本阶段禁止刷写** |
| `final.config` | 309,537 | `240b76a5317ca4d3dda0ac8eaf37f2b4cbd7dd66d42d2970dc160daafccd6310` | `make defconfig` 后的最终 .config，复现构建的依据 | — |
| `package.manifest` | 9,152 | `5fd552a3ebdf48e67df4900b25dda07649e4135e2bc66c0b9a442b1a2194caee` | 固件内 273 个包清单（含版本） | — |
| `feeds.conf.frozen` | 945 | `63108347d4b56accc14533681ccb5bc91a7489e39c3a5589f5c05025c8a4eb9e` | 全部 feeds 冻结到指定 SHA（含 nss=0d970dbf） | — |
| `sha256sums.txt` | 840 | `24a3629d1b8125bdf3c85d580dd2c907d680dcda8c2d35c3305aa8a3e32a6b94` | 构建系统原生生成的校验和（与上表一致） | — |

校验命令：`sha256sum -c sha256sums.txt`（在镜像同目录）。

## 3. 固件内容核验要点（已在编译产物中确认存在）

- NSS 全套：`kmod-qca-nss-dp / -drv(11.4) / -ecm / -pppoe / -vlan-mgr / -bridge-mgr / -wifi-meshmgr / kmod-nss-ifb / kmod-qca-ssdk(CPPE) / nss-firmware-ipq60xx`
- WiFi：`kmod-ath11k-ahb/-pci` + `ath11k-firmware-qcn9074`（QCN9024）+ `ipq-wifi-jdcloud_re-cs-02`（BDF）
- PPPoE：`kmod-pppoe / ppp-mod-pppoe / luci-proto-ppp`
- LuCI（light + 中文）+ `wpad-openssl`
- **未包含**：OpenClash / PassWall / Docker / 广告插件 / 自定义 60s 回滚 / 自定义 watchdog

## 4. 未改项（安全边界）

- 未修改 DTS、未改 Kernel patch（沿用分支自带 130 个 qualcommax patches-6.12）、未改 U-Boot、未动 GPT/分区/ART。
- 未新增任何自研 patch。

## 5. 当前风险（实机验证前）

- initramfs **未实机启动**；2.5G（QCA8081 sgmii/SGMII_PLUS）、PPPoE NSS 卸载、单臂 VLAN+PPPoE+NSS 组合均**未实测**。
- 验证顺序：U-Boot 恢复页 → initramfs 临时启动 → 逐项确认 → 全部通过后才进入 sysupgrade 阶段。
