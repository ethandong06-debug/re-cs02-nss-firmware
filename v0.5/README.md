# v0.5 — OWPT（immortalwrt_ipq）定制固件（2026-10-08）

JDCloud RE-CS-02（京东云雅典娜）基于 **OWPT（ones20250/immortalwrt_ipq main）** 源码栈重编的固件，目标：修复 v0.4 在 WanAll 桥 + VLAN + PPPoE 拓扑下 NSS 加速失效的问题，让实测跑回 ~1.5G。

## 构建信息

| 项 | 值 |
|---|---|
| 源码 | ones20250/immortalwrt_ipq `main`（OWPT IPQ 分支） |
| Kernel | 6.18 系 |
| NSS 接入方式 | **独立包体系**（`package/qca-nss/qca-nss-clients` 等），含 `002-compat-bridge-vlan-lag-portifmgr-linux-6.18.patch`（portifmgr 端口接口管理器 6.18 兼容补丁） |
| 配置参考 | ones20250/Openwrt-AX6600：`Config/IPQ60XX-WIFI-YES.txt` + `GENERAL_AX6600.txt` + `GENERAL_AX6600_PLUS.txt`，追加 `CONFIG_TARGET_ROOTFS_INITRAMFS=y` / kmod-oaf / luci-app-appfilter / argon |
| 默认 LAN | `192.168.10.1/24` |
| 包管理 | apk |
| 构建机器 | 本地 VirtualBox（8C/10GB/swap8G），`make -j6` 完成 |

## 固件与 SHA256

| 文件 | 大小 | SHA256 |
|---|---|---|
| initramfs-uImage.itb | 148.63 MB | `5e5787f0b4253891d19c273a1752fd8bd3bdec4b6da83f523b09b722eda6d97a` |
| squashfs-factory.bin | 146.07 MB | `2e4f940e4e2e356cc49913cbba6ce1e3df650c550872965ad1dd7b0b0b5b425f` |
| squashfs-sysupgrade.bin | 145.69 MB | `38a4ae7d5a145f7d7899122e145f13e5c8b753f41a1807e268d5006659e02a95` |

校验：`sha256sum -c v0.5/sha256sums.txt`

## 与 v0.4 的关键差异（预期修复点）

1. **NSS 独立包 + portifmgr 6.18 兼容补丁**：修复桥内 VLAN/LAG 端口接口管理——对应 v0.4 `31 is not valid physical port` 的根因。
2. Kernel 6.18（较 v0.4 的 6.12 新，驱动栈完整度更高）。
3. 内置：NSS 全套 + OpenClash + kmod-oaf + luci-app-appfilter + argon + dnsmasq-full + initramfs 验证镜像。

详见 `ROOT_CAUSE_LibWrt_vs_OWPT.md`。

## 实机验证状态

- ⏳ **待刷机验证**（2026-10-08 交付）：sysupgrade 不保留配置刷入后，验证：
  1. `cat /sys/kernel/debug/ecm/ecm_db/iface_count` 非 0，且测速时 connection_count / accelerated_count 增长；
  2. 外网测速回到 ~1.2-1.5G（WAN 原始下行约 1.2G，2.5G 口上限 2.5G）。

## 刷机

- 后台升级：LuCI → 系统 → 备份/升级 → 选 `squashfs-sysupgrade.bin`（**不保留配置**，跨源码栈必须）
- 首刷/救援：U-Boot 恢复页 → initramfs 临时启动
- ⚠️ 本固件体积 145MB+（镜像含全量软件包与 initramfs），升级耗时比 v0.4 长，请耐心等待
