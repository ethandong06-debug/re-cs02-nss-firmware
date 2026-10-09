# RE-CS-02 NSS Firmware — 变更记录

## v0.5（2026-10-08，OWPT 源码栈）

- **变更**：源码栈从 LibWrt 25.12-nss 切换为 **OWPT ones20250/immortalwrt_ipq main**（Kernel 6.18 系）
- **动机**：v0.4 在 WanAll 桥 + VLAN + PPPoE 拓扑下 NSS 加速失效（`31 is not valid physical port`、ECM 加速计数 0、实测 600~1000M）
- **关键差异**：NSS 独立包体系（qca-nss-clients）+ `002-compat-bridge-vlan-lag-portifmgr-linux-6.18.patch`（portifmgr 端口接口管理器）——修复桥内 VLAN/LAG 端口映射
- **配置参考**：ones20250/Openwrt-AX6600 `Config/IPQ60XX-WIFI-YES.txt` + `GENERAL_AX6600.txt` + `GENERAL_AX6600_PLUS.txt`，追加 initramfs / kmod-oaf / luci-app-appfilter / argon
- **镜像**（SHA256 见 `v0.5/sha256sums.txt`）：initramfs 148.63MB / factory 146.07MB / sysupgrade 145.69MB
- **验证状态**：⏳ 待刷机验证（ECM iface_count 非 0 + 测速回 ~1.5G）
- **备注**：完整 .config/buildinfo 在编译机 VM（/home/vboxuser/owpt-build），后续可补充入库

## v0.4（2026-10-07~08，LibWrt 25.12-nss）

- **变更**：LibWrt 25.12-nss 全功能版——NSS 全套 + OpenClash 0.47.156 + kmod-oaf + luci-app-appfilter + luci-theme-argon 2.4.7 + WiFi radio2 HE160；默认 LAN 192.168.10.1
- **镜像**（SHA256 见 `v0.4/sha256sums.txt`）：initramfs 28.63MB / factory 29.32MB / sysupgrade 28.68MB
- **实测结论**：WiFi160 握手 2400M 但外网实测 600~1000M；2.5G 有线同 ~600M → 瓶颈在 NAT/NSS 未接管
- **根因**：NSS vlan-mgr 无法映射 WanAll 自定义桥内 VLAN/PPPoE（`31 is not valid physical port`）；br-netfilter/hairpin/add_wanif 修补无效 → 催生 v0.5 换栈
- 完整包清单：`v0.4/libwrt-...-manifest`（319 包）

## v0.1-lan10（2026-10-07，当前归档版本）

- **变更**：默认 LAN 网段 `192.168.1.1/24` → `192.168.10.1/24`
- **改动点**：`package/base-files/files/bin/config_generate` 第 166 行默认 lan 地址（唯一改动，patch 见 `patches/0001-lan-ip-192.168.10.1.patch`）
- **连带影响**：DHCP 范围自动跟随为 192.168.10.100–249；OpenWrt 管理入口变为 `http://192.168.10.1`
- **不变**：U-Boot 恢复页仍为 `192.168.1.1`（独立网络）；内核 6.12.108 / NSS 栈 / WiFi / 2.5G 全部组件与已验证的 v0.1 一致
- **镜像**（新 SHA256）：
  - initramfs `ebb1bb7156556b1f042ec3975897c5795a3ee919a7ad2d469f08fc2a0a16f019`
  - factory `b9fd46a72182f4def7293ab021dae7672fb55937093465b7b7d1eaecb22d9836`
  - sysupgrade `0284ff193f6b8f4b741b8b0134de2b8570f8facd104943a82895e62e763aee42`
- **验证状态**：硬件验证基于 192.168.1.1 版完成（2.5G/NSS/三频 WiFi 全过）；**v0.1-lan10 已于同日复验通过**——br-lan=192.168.10.1/24 生效，2.5G/三频/NSS 无回归（见 `VERIFICATION_RESULT_v0.1.md` ②）
- **构建备注**：增量重编译期间修复环境问题两处——tmp 符号链接失效重建、busybox 构建产物损坏（clean 后重编）

## v0.1（2026-10-01，初版）

- 首个 initramfs 验证固件，默认 LAN `192.168.1.1/24`
- 实机验证（2026-10-07）：2.5G=2500Mb/s、NSS 全套加载、三频 WiFi 全起（详见 `VERIFICATION_RESULT_v0.1.md`）
