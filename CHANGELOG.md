# RE-CS-02 NSS Firmware — 变更记录

## v0.1-lan10（2026-10-07，当前归档版本）

- **变更**：默认 LAN 网段 `192.168.1.1/24` → `192.168.10.1/24`
- **改动点**：`package/base-files/files/bin/config_generate` 第 166 行默认 lan 地址（唯一改动，patch 见 `patches/0001-lan-ip-192.168.10.1.patch`）
- **连带影响**：DHCP 范围自动跟随为 192.168.10.100–249（dnsmasq 基于 lan 地址计算，未写死）；OpenWrt 管理入口变为 `http://192.168.10.1`
- **不变**：U-Boot 恢复页仍为 `192.168.1.1`（独立网络）；内核 6.12.108 / NSS 栈 / WiFi / 2.5G 全部组件与已验证的 v0.1 一致
- **镜像**（新 SHA256）：
  - initramfs `ebb1bb7156556b1f042ec3975897c5795a3ee919a7ad2d469f08fc2a0a16f019`
  - factory `b9fd46a72182f4def7293ab021dae7672fb55937093465b7b7d1eaecb22d9836`
  - sysupgrade `0284ff193f6b8f4b741b8b0134de2b8570f8facd104943a82895e62e763aee42`
- **验证状态**：硬件验证基于 192.168.1.1 版完成（2.5G/NSS/三频 WiFi 全过）；LAN IP 变更版需在 v0.2 刷写后复验管理入口
- **构建备注**：增量重编译期间修复环境问题两处——tmp 符号链接失效重建、busybox 构建产物损坏（clean 后重编）

## v0.1（2026-10-01，初版）

- 首个 initramfs 验证固件，默认 LAN `192.168.1.1/24`
- 实机验证（2026-10-07）：2.5G=2500Mb/s、NSS 全套加载、三频 WiFi 全起（详见 `VERIFICATION_RESULT_v0.1.md`）
