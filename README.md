# RE-CS-02 NSS Firmware 归档

JDCloud **RE-CS-02（京东云雅典娜，IPQ6018 / qualcommax-ipq60xx）** NSS 硬件加速固件构建归档。

## 版本矩阵

| 版本 | 源码栈 | Kernel | 状态 | 定位 |
|---|---|---|---|---|
| [v0.1](v0.1 说明见文末) | LiBwrt/LibWrt 25.12-nss | 6.12.108 | ✅ 硬件验证通过 | initramfs 临时启动验证（2.5G/NSS/三频 WiFi） |
| [v0.4](v0.4/README.md) | LiBwrt/LibWrt 25.12-nss | 6.12.108 | ⚠️ 功能验证（NSS 未接管） | 三频 + OpenClash + oaf + argon + 160MHz；实测 600~1000M |
| [v0.5](v0.5/README.md) | OWPT ones20250/immortalwrt_ipq | 6.18 系 | ⏳ 待实机验证 | NSS 独立包 + portifmgr 补丁，预期恢复 ~1.5G |

## 关键文档

| 文件 | 说明 |
|---|---|
| `ARCHIVE.md` | 逐文件归档说明（字节/SHA256/用途/可刷性/风险） |
| `ROOT_CAUSE_LibWrt_vs_OWPT.md` | **v0.4 测速瓶颈根因分析 + v0.5 修复预期**（先读这个） |
| `VERIFICATION.md` / `VERIFICATION_RESULT_v0.1.md` | v0.1 实机验证步骤与结果 |
| `CHANGELOG.md` | 版本变更记录 |
| `final.config` / `feeds.conf.frozen` / `package.manifest` | v0.1 构建复现依据 |
| `sha256sums.txt` | v0.1 校验和 |
| `v0.4/` | v0.4 固件说明 + 校验和 + 完整包清单（319 包） |
| `v0.5/` | v0.5 固件说明 + 校验和（三镜像 145MB+，见文末获取方式） |
| `patches/` | 自研 patch（LAN IP 192.168.10.1 等） |

## 核心结论（2026-10-09）

- 用户拓扑：WanAll 自定义桥 + VLAN + PPPoE（单臂/多业务）。
- v0.4（LibWrt NSS 内核补丁栈）在该拓扑下 NSS 加速无法接管：`nss_vlan_mgr: WanAll: 31 is not valid physical port`，ECM hierarchy_creation_fail 2.3万/4.1万，实测下行 600~1000M（WiFi160 握手 2400M）。
- v0.5（OWPT：NSS 独立包 + portifmgr 6.18 兼容补丁）预期修复端口映射，使 NSS 完整卸载 PPPoE/NAT → 恢复 ~1.5G。验证清单见 `ROOT_CAUSE_LibWrt_vs_OWPT.md`。

## v0.1（仓库根目录三镜像）

- 源码：LiBwrt/LibWrt `25.12-nss` @ `3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70`，Kernel 6.12.108，NSS feed qosmio/nss-packages @ `0d970dbf0185e3f53709bd803e8a466598023c57`
- 默认 LAN：`192.168.10.1/24`（2026-10-07 由 192.168.1.1 变更，patch 见 `patches/0001-lan-ip-192.168.10.1.patch`）
- 镜像：initramfs-uImage.itb / squashfs-factory.bin / squashfs-sysupgrade.bin（19-20MB）
- 校验：`sha256sum -c sha256sums.txt`

## 安全边界

- 未改 DTS / Kernel patch / U-Boot / GPT 分区 / ART。
- 任何写 flash/eMMC 的操作都需人工确认；跨源码栈升级（v0.4→v0.5）**必须不保留配置**。
- U-Boot 恢复页固定 `192.168.1.1`；OpenWrt 固件管理入口 **`http://192.168.10.1`**。

## v0.5 大文件说明

v0.5 三镜像（145~148MB）超过 GitHub 单文件 100MB 上限，本仓库存储 SHA256 + 说明；固件本体通过[下载链接](https://aka.doubaocdn.com/s/aIUbusa9KM)（sysupgrade）、[factory](https://aka.doubaocdn.com/s/iZKhnNdVil)、[initramfs](https://aka.doubaocdn.com/s/T4tZNzfGQr) 获取，或联系维护者/从编译机 VM 导出。
