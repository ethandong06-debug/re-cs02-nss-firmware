# AthenaWrt 项目状态与交接记录

> 本文件是持续开发的项目事实来源。每次完成一个阶段后更新；新对话开始时先核对本文件与 GitHub 当前分支状态。
> 最后更新：2026-11-01

## 1. 项目与设备背景

- 设备：京东云雅典娜 Athena / RE-CS-02 / AX6600。
- 平台：Qualcomm IPQ6018，ImmortalWrt / qualcommax-ipq60xx，aarch64 Cortex-A53。
- 系统使用 APK 包管理，不是 opkg。
- 当前任务：AthenaWrt 独立 LuCI APK 的构建、签名迁移与安装验收。
- 用户没有本地编译环境；构建必须使用 GitHub Actions 云端完成。
- 目标是独立 APK，不刷整机固件。

## 2. 不可破坏的约束

不得擅自修改或破坏：
- PPPoE、VLAN（包括现网 VLAN 2044）、IPv6 PD/SLAAC。
- 防火墙、NAT、OpenClash。
- NSS/ECM 硬件加速及相关驱动配置。
- 与当前 APK 任务无关的固件配置和其他软件包。

操作原则：
- 稳定性优先；不引入未经验证的内核模块。
- 不要求用户在本地安装编译环境、运行 openssl 或执行 Linux 构建命令。
- 不绕过 APK 签名验证。
- 任何安装前先验证签名并模拟升级，确认不会卸载中文语言包或其他无关软件包。
- 未经用户明确同意，不执行路由器正式安装或网络配置变更。

## 3. GitHub 构建位置

- 仓库：`ethandong06-debug/re-cs02-nss-firmware`
- 当前工作分支：`athenawrt/apk-fixed-signing`
- 原始基线分支：`athenawrt/phase1-p0-fixes`
- 分支地址：https://github.com/ethandong06-debug/re-cs02-nss-firmware/tree/athenawrt/apk-fixed-signing
- Athena APK 源码目录：`luci-app-athena-src/frontend/luci-app-athena/`
- 构建工作流：`.github/workflows/build-athena-apk.yml`

## 4. APK 1.2.60 签名故障定位与处理

### 已有成功构建（不是待构建状态）

- 分支：`athenawrt/phase1-p0-fixes`
- 源码提交：`ed69ea935030f37bf0916ac9653bf5bbfd878db2`
- Actions run：`41304711196`（run #23，结论 success）
- Artifact：`luci-app-athena-apk`，artifact ID `13084243143`，有效期至 2026-11-15。
- APK：`luci-app-athena-1.2.60-r1.apk`，14,683,961 bytes。
- SHA-256：`99b2d52d8d7faa8fd41e11f258d5fb08306793dacb89170f0d83809ed7b7bdf4`。
- 用户已确认路由器 `/tmp/upload.apk` 的 SHA-256 与构建产物一致；当前安装版本仍是 `1.2.59-r1`，中文语言包仍安装。

### 已确认的签名根因

- 已下载并检查原始 Actions Artifact 和 `athena-package-build.log`。
- 构建日志显示 ImmortalWrt 在 Actions runner 上生成临时 ECDSA P-256 私钥：`immortalwrt/private-key.pem`。
- 同一构建随后从私钥导出 `immortalwrt/public-key.pem`。
- `luci-app-athena-1.2.60-r1.apk` 的 `apk mkpkg` 命令明确使用该临时私钥签名。
- 原始 Artifact 未包含 `public-key.pem`，也没有保存私钥；Actions runner 已结束。因此路由器现有三个公钥不能验证该 APK，出现 `UNTRUSTED signature`。
- 这不是 APK 传输损坏：路由器端文件哈希与 Artifact 内 APK 哈希一致。
- 旧 APK 对应的公钥目前未从原始 Artifact/日志中取回。不得伪称已有对应公钥，也不得用 `--allow-untrusted` 绕过校验。

### 当前修复

- 用户取消的是 Codespaces/固定私钥 Secret 方案；不重新引导用户配置 Secret。
- 已在 `athenawrt/apk-fixed-signing` 分支更新构建工作流：成功构建后将本次构建的**公钥** `immortalwrt/public-key.pem` 复制为 `output/athenawrt-build-signing.pub` 并随 APK Artifact 上传；只导出公钥，不上传私钥。
- 修复提交：`1f7fb302081c9c5d02116dd7d2f60a86270739b8`。
- 源码页面未修改；此修复会重新执行 package-only 构建以产生一份带匹配公钥的 APK Artifact。它不是页面重写或整机固件构建。

### 尚未完成

- 尚未运行修复后的 workflow。
- 尚未取得新 Artifact 中的匹配公钥与 APK。
- 尚未把公钥安装到路由器或执行签名验证。
- 尚未执行 APK 模拟升级或正式安装。

### 后续原则

- 不创建 Codespaces，不生成或配置长期固定私钥 Secret。
- 先取得同一次构建产出的 APK 与公钥，核对公钥格式、文件哈希，并在路由器验证 APK 签名。
- 再做 APK 模拟升级，确认不会移除 `luci-i18n-athena-zh-cn` 或其他无关包。
- 未经用户明确同意，不执行正式安装；不改 PPPoE、VLAN、IPv6、防火墙、OpenClash 或 NSS/ECM。

## 5. 构建工作流注意事项

- 当前工作流定义了 `workflow_dispatch`。
- 当前 `push` 触发分支列表是 `main` 与 `athenawrt/phase1-p0-fixes`，不包含 `athenawrt/apk-fixed-signing`。因此在新分支上应通过 GitHub Actions 的手动运行入口选择该分支，不要误以为向新分支 push 会自动触发。
- 运行前必须确认 Repository Secret 已配置。
- 不得在日志中输出私钥；不得把 Secret 写入 Artifact、缓存或构建日志。

## 6. 后续对话交接流程

新对话开始时：
1. 读取本文件。
2. 核对 GitHub 当前分支 HEAD、工作流文件和最近 Actions 运行记录。
3. 区分已完成、已提交但未运行、运行失败、待用户操作四种状态。
4. 从“尚未完成”中的第一项继续，不重复已完成步骤。
5. 每次提交后更新本文件，记录新的提交 SHA、运行链接/结果、产物和验收状态。

## 7. 当前下一步

1. 在 GitHub Actions 手动运行 `athenawrt/apk-fixed-signing` 分支的 `Build Athena LuCI APK`（该分支不在 push 触发列表中）。
2. 确认 Artifact 同时包含 `luci-app-athena-*.apk` 与 `athenawrt-build-signing.pub`。
3. 核验 APK 和公钥哈希、签名及包元数据；先把公钥安全导入路由器并验证 APK 签名。
4. 执行模拟升级，确认中文语言包和其他无关包不会被移除；经用户明确同意后才正式安装。

## 8. 已取消的 Codespaces 方案

用户已明确表示不需要固定签名密钥初始化流程。此前拟定的 Codespaces、ECDSA P-256 私钥生成和 Repository Secret 配置步骤全部暂停，不应继续引导用户执行。