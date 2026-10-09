# v0.7 —— OWPT 栈 / Linux 6.18（推荐版）

> Release 页面：https://github.com/ethandong06-debug/re-cs02-nss-firmware/releases/tag/v0.7

## 版本说明

- **源码栈**：OWPT（immortalwrt_ipq，ImmortalWrt IPQ 专用分支），内核 Linux 6.18
- **包管理**：apk
- **定位**：7×24 小时稳定运行的家庭/小型网络核心路由器（PPPoE + NAT + 硬件加速 + 三频 WiFi）

## 固件特性

- PPPoE 拨号 / DHCP / NAT / **ECM+NSS 硬件加速全链路**
- WiFi：radio2 160MHz（ipq-wifi + ath11k qcn9074），实测无线千兆
- 插件：OpenClash、luci-app-adblock、luci-app-diskman、nlbwmon、wol、zerotier
- 精简：v0.6 起移除 PassWall2 及无用组件
- 默认管理地址：**http://192.168.10.1**

## 实测结果（2026-10-09）

| 指标 | 结果 |
|---|---|
| 有线直连 | 千兆线速达标 |
| WiFi（160MHz） | 千兆达标 |
| 副路由 2.5G AP 桥接 | 下载 2298 Mbps / 上传 134 Mbps |
| 时延 / 抖动 / 丢包 | 2.92 ms / 0.12 ms / 0% |

## 文件与 SHA256

| 文件 | SHA256 |
|---|---|
| immortalwrt-...-initramfs-uImage.itb | 16456ae297901f65cb2db0d8e5fe77c796e3ab188b7225d85aafbaa08a44ae4d |
| immortalwrt-...-squashfs-factory.bin | 3988d65743ad9a5a8eae0822da3b4f5b61299ded0b9cef97071bf2316a48dec8 |
| immortalwrt-...-squashfs-sysupgrade.bin | b9c8a4ddda4470dffe1fbb11c33ed85554f20d6120e68546a39e0ec0586886b9 |

校验：`sha256sum -c sha256sums.txt`（Release 资产已核对，上传后 SHA256 与本地一致）

## 刷写指引

1. **跨栈升级（从 LibWrt v0.4 等）**：刷 `squashfs-factory.bin`（原厂 Web 后台或 U-Boot），**务必重置配置**，不要保留旧配置
2. **同栈升级（v0.5/v0.6 及本版后续）**：后台 系统-升级 选 `squashfs-sysupgrade.bin`
3. **临时验证**：`initramfs-uImage.itb`（U-Boot/TFTP 临时启动，不写入正式分区）

## 构建信息

- 构建机：Ubuntu 22.04（VirtualBox 编译机）
- 产物目录：owpt-build/bin/targets/qualcommax/ipq60xx/
- 构建时间：2026-10-09 12:11（UTC+8）
- 内核：Linux 6.18（CONFIG_LINUX_6_18=y）
