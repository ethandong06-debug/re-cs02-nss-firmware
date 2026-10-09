# RE-CS-02 NSS Firmware 归档

JDCloud **RE-CS-02（京东云雅典娜，IPQ6018 / qualcommax-ipq60xx）** NSS 硬件加速固件构建归档。

## 版本矩阵

| 版本 | 源码栈 | Kernel | 状态 | 定位 |
|---|---|---|---|---|
| [v0.1](v0.1 说明见文末) | LiBwrt/LibWrt 25.12-nss | 6.12.108 | ✅ 硬件验证通过 | initramfs 临时启动验证（2.5G/NSS/三频 WiFi） |
| [v0.4](v0.4/README.md) | LiBwrt/LibWrt 25.12-nss | 6.12.108 | ⚠️ 功能验证（NSS 未接管） | 三频 + OpenClash + oaf + argon + 160MHz；实测 600~1000M |
| [v0.5](v0.5/README.md) | OWPT ones20250/immortalwrt_ipq | 6.18 系 | ✅ 实测达标 | NSS 独立包 + portifmgr 补丁；副路由实测下载 2298 Mbps |
| v0.6 | OWPT | 6.18 系 | ✅ 已验证 | 精简版（移除 PassWall2 等无用组件）；无独立归档（二进制已被 v0.7 编译覆盖） |
| [v0.7](v0.7/README.md) | OWPT | 6.18 系 | ✅ 推荐版 | v0.6 基础上 +adblock/diskman/nlbwmon/wol/zerotier；有线/无线千兆，副路由 2000M 级 |

## Release 下载（固件本体）

| 版本 | Release | 内容 |
|---|---|---|
| v0.7 | https://github.com/ethandong06-debug/re-cs02-nss-firmware/releases/tag/v0.7 | initramfs 114.6MB / factory 112MB / sysupgrade 111.6MB（SHA256 见 Release 说明） |
| v0.4 | https://github.com/ethandong06-debug/re-cs02-nss-firmware/releases/tag/v0.4 | initramfs 28.6MB / factory 29.3MB / sysupgrade 28.7MB（SHA256 见 Release 说明） |
| v0.5 | aka 短链（>100MB 单文件限制，见下方） | initramfs 148.63MB / factory 146.07MB / sysupgrade 145.69MB |
| v0.1 | 仓库根目录三镜像（19-20MB） | 见文末 |

## 关键文档

| 文件 | 说明 |
|---|---|
| `ARCHIVE.md` | 逐文件归档说明（字节/SHA256/用途/可刷性/风险） |
| `ROOT_CAUSE_LibWrt_vs_OWPT.md` | **v0.4 测速瓶颈根因分析 + OWPT 修复结论**（先读这个） |
| `VERIFICATION.md` / `VERIFICATION_RESULT_v0.1.md` | v0.1 实机验证步骤与结果 |
| `CHANGELOG.md` | 版本变更记录（含 v0.6/v0.7） |
| `final.config` / `feeds.conf.frozen` / `package.manifest` | v0.1 构建复现依据 |
| `sha256sums.txt` | v0.1 校验和 |
| `v0.4/` | v0.4 固件说明 + 校验和 + 完整包清单（319 包） |
| `v0.5/` | v0.5 固件说明 + 校验和 + 下载链接 |
| `v0.6/` | v0.6 变更说明（无独立二进制归档） |
| `v0.7/` | v0.7 说明 + 校验和 + Release 链接 |
| `patches/` | 自研 patch（LAN IP 192.168.10.1 等） |

## 核心结论（2026-10-09 更新）

- 用户拓扑：WanAll 自定义桥 + VLAN + PPPoE（单臂/多业务）。
- v0.4（LibWrt NSS 内核补丁栈）在该拓扑下 NSS 加速无法接管：`nss_vlan_mgr: WanAll: 31 is not valid physical port`，ECM hierarchy_creation_fail 2.3万/4.1万，实测下行 600~1000M（WiFi160 握手 2400M）。
- v0.5 起切 **OWPT（immortalwrt_ipq，NSS 独立包 + portifmgr 6.18 兼容补丁）**：端口映射修复，NSS 完整卸载 PPPoE/NAT。
- **v0.7 最终实测：有线/无线均达千兆线速；副路由（2.5G AP 桥接）下载 2298 Mbps / 上传 134 Mbps / 时延 2.92 ms / 丢包 0%。** 根因分析见 `ROOT_CAUSE_LibWrt_vs_OWPT.md`。

## v0.1（仓库根目录三镜像）

- 源码：LiBwrt/LibWrt `25.12-nss` @ `3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70`，Kernel 6.12.108，NSS feed qosmio/nss-packages @ `0d970dbf0185e3f53709bd803e8a466598023c57`
- 默认 LAN：`192.168.10.1/24`（2026-10-07 由 192.168.1.1 变更，patch 见 `patches/0001-lan-ip-192.168.10.1.patch`）
- 镜像：initramfs-uImage.itb / squashfs-factory.bin / squashfs-sysupgrade.bin（19-20MB）
- 校验：`sha256sum -c sha256sums.txt`

## 安全边界

- 未改 DTS / Kernel patch / U-Boot / GPT 分区 / ART。
- 任何写 flash/eMMC 的操作都需人工确认；跨源码栈升级（v0.4→v0.5/0.7）**必须不保留配置**。
- U-Boot 恢复页固定 `192.168.1.1`；OpenWrt 固件管理入口 **`http://192.168.10.1`**。

## v0.5 大文件说明

v0.5 三镜像（145~148MB）超过 GitHub 单文件 100MB 上限，固件本体通过[下载链接](https://aka.doubaocdn.com/s/aIUbusa9KM)（sysupgrade）、[factory](https://aka.doubaocdn.com/s/iZKhnNdVil)、[initramfs](https://aka.doubaocdn.com/s/T4tZNzfGQr) 获取，或从编译机 VM 导出（/home/vboxuser/owpt-build，注意该目录已被 v0.7 产物覆盖）。
