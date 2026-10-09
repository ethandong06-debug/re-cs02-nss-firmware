# v0.6 —— OWPT 栈精简版（中间版本，无独立归档）

## 版本说明

- **源码栈**：OWPT（immortalwrt_ipq），内核 Linux 6.18
- **变更内容**：在 v0.5 基础上精简——移除 PassWall2 及无用组件（Samba/NFS 共享、openclash 冗余等），保留核心路由 + ECM/NSS 硬件加速 + OpenClash
- **验证状态**：✅ 已实测通过（性能与 v0.7 一致：千兆 + 副路由 2000M 级）

## 归档说明

- **无独立二进制**：v0.6 编译产物被 v0.7 增量编译覆盖（编译机 bin/targets 目录），SHA256 未单独留存
- **如需复现**：基于 OWPT 源码树（ones20250/immortalwrt_ipq）按本版特性重编即可；v0.7 即本版 + adblock/diskman/nlbwmon/wol/zerotier 五个增量插件

## 版本定位

- v0.6 的意义：验证"精简不影响性能"，并为 v0.7 的最终功能集奠定基线
- 日常使用请直接选用 **v0.7**（推荐版，Release 下载）
