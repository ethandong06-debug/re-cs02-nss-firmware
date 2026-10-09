# v0.4 — LibWrt 25.12-nss（2026-10-07~08）

JDCloud RE-CS-02（京东云雅典娜）基于 **LibWrt 25.12-nss** 分支编译的功能验证固件。

## 构建信息

| 项 | 值 |
|---|---|
| 源码 | LiBwrt/LibWrt `25.12-nss` @ `3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70` |
| Kernel | 6.12.108 |
| NSS 接入方式 | 内核补丁栈（patches-6.12/0600~0607，NSS 直接打入 kernel） |
| NSS feed | qosmio/nss-packages @ `0d970dbf0185e3f53709bd803e8a466598023c57` |
| 默认 LAN | `192.168.10.1/24` |
| 包管理 | apk（OpenWrt 25.x 新体系） |

## 固件与 SHA256

| 文件 | 大小 | SHA256 |
|---|---|---|
| initramfs-uImage.itb | 28.63 MB | `1a51b635d2cbf46b880bd3b171815a9a7384205c00e038d9735afe066fc2d199` |
| squashfs-factory.bin | 29.32 MB | `bd23a6d0edc828e94db41c524c29f4053fc71b61d0a911b253700d61803e67ad` |
| squashfs-sysupgrade.bin | 28.68 MB | `c93271c28506ece94a0a66ddd0128d1708d98366f3d96fbdcac32ef4480bdff5` |

校验：`sha256sum -c v0.4/sha256sums.txt`

## 主要内置功能

- NSS 硬件加速全套（qca-nss-drv / dp / ecm / ssdk / vlan-mgr / bridge-mgr / pppoe）
- 三频 WiFi（2.4G + 5G 内建 + 5G PCIe QCN9074，radio2 支持 HE160）
- OpenClash 0.47.156 + dnsmasq-full + nft-tproxy（完整代理链）
- kmod-oaf / luci-app-appfilter（上网行为管理）
- luci-theme-argon 2.4.7 现代化主题
- PPPoE / VLAN / 单臂 / 旁路由能力

完整包清单见同目录 `libwrt-qualcommax-ipq60xx-jdcloud_re-cs-02.manifest`（319 个包）。

## 已知问题（本版本实测结论）

1. **WanAll 自定义桥内 VLAN+PPPoE 拓扑下 NSS 加速未接管**：ECM 测速时 `accelerated_count=0`，exception 统计 `v4_ported_from/to_hierarchy_creation_fail` 高达 23292 / 41555；dmesg 报 `nss_vlan_mgr: WanAll: 31 is not valid physical port`——NSS 栈无法把自定义桥内的 VLAN/PPPoE 流量映射到物理端口。
2. **实测下行 ~600-1000M**：WiFi160 握手 2400Mbps，但 NAT 走软件路径，外网测速 600~800M（峰值勉强 1000M）；同拓扑 2.5G 有线测速同样约 600M，证明瓶颈在 NAT/NSS 而非空口。
3. br-netfilter / hairpin_mode / add_wanif 等多轮修复补丁无效（本版本已含相关尝试）。

**结论**：v0.4 验证了 WiFi/三频/硬件完好，但该 NSS 栈对自定义桥内 VLAN 拓扑支持不足 → 催生 v0.5（换 OWPT 源码栈，见 `v0.5/README.md` 与 `ROOT_CAUSE_LibWrt_vs_OWPT.md`）。

## 刷机

- 后台升级：LuCI → 系统 → 备份/升级 → 选 `squashfs-sysupgrade.bin`（建议不保留配置）
- 首刷/救援：U-Boot 恢复页（固定 192.168.1.1）→ initramfs 临时启动验证
