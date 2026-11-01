# AthenaWrt 项目状态与交接记录

> 本文件是持续开发的项目事实来源。每次完成一个阶段后更新；新对话开始时先核对本文件与 GitHub 当前分支状态。
> 最后更新：2026-11-02

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

### 修复后构建已完成（Run #24）

- 构建提交：`192807f73cb9e1db164265027fa463d9ec4f6098`（`ci: run Athena APK build on recovery branch`）。
- 后续分支 HEAD：`851c5b0dde17ec764a71017a9380ea80d2886fc5`（仅后续记录提交；本次构建对应源码/工作流提交仍为上项）。
- Actions run：`41319061077`（run #24，event=push，结论 success），所有 13 个主要步骤均成功。
- Artifact：`luci-app-athena-apk`，artifact ID `13090108299`，大小 14,685,069 bytes，创建于 2026-11-01，预计 2026-11-15 过期。
- Artifact 内含 `luci-app-athena-1.2.60-r1.apk`（14,683,958 bytes）、`athenawrt-build-signing.pub`（178 bytes）、SHA256SUMS、构建日志及源码元数据。
- APK SHA-256：`6b553a1f571bfa7335a705e713ebd12594434a4c7a466a3afdcd38d97e2434fc`。
- 公钥文件 SHA-256：`a7961c8c7994823d983f922af84f834463fbd4f0a5e8e02ea635bbd0365e4b3c`。
- 已用 OpenSSL 成功解析公钥：ECDSA P-256 / prime256v1，PEM 格式有效；未发现私钥被放入 Artifact。
- 构建日志确认 `luci-app-athena` 版本 `1.2.60-r1`、架构 `noarch`，由本次 runner 的 `immortalwrt/private-key.pem` 签名；同一构建也生成了 `luci-i18n-athena-zh-cn`，但 Artifact 只上传主 APK 和匹配公钥。
- 当前仍未在 Athena 路由器上导入该公钥、执行设备端 APK 签名验证或模拟升级；因此不能宣称设备端签名验收已通过。

### 后续原则

- 不创建 Codespaces，不生成或配置长期固定私钥 Secret。
- 先取得同一次构建产出的 APK 与公钥，核对公钥格式、文件哈希，并在路由器验证 APK 签名。
- 再做 APK 模拟升级，确认不会移除 `luci-i18n-athena-zh-cn` 或其他无关包。
- 未经用户明确同意，不执行正式安装；不改 PPPoE、VLAN、IPv6、防火墙、OpenClash 或 NSS/ECM。

## 5. 构建工作流注意事项

- 当前工作流定义了 `workflow_dispatch`。
- 当前工作流 `push` 触发分支列表已包含 `main`、`athenawrt/phase1-p0-fixes` 与 `athenawrt/apk-fixed-signing`；Run #24 实际由该分支的 push 触发。
- 本分支当前工作流不依赖长期固定签名 Secret；使用本次 runner 的临时密钥并仅导出公钥。
- 不得在日志中输出私钥；不得把私钥写入 Artifact、缓存或构建日志。

## 6. 后续对话交接流程

新对话开始时：
1. 读取本文件。
2. 核对 GitHub 当前分支 HEAD、工作流文件和最近 Actions 运行记录。
3. 区分已完成、已提交但未运行、运行失败、待用户操作四种状态。
4. 从“尚未完成”中的第一项继续，不重复已完成步骤。
5. 每次提交后更新本文件，记录新的提交 SHA、运行链接/结果、产物和验收状态。

## 7. 当前下一步

1. 将 Run #24 Artifact 中的 `athenawrt-build-signing.pub` 导入 Athena 的 APK 信任密钥目录（仅公钥）。
2. 在路由器上用当前系统的 APK 工具验证 `luci-app-athena-1.2.60-r1.apk` 签名；若验证失败，停止，不绕过信任校验。
3. 签名验证通过后执行模拟升级/依赖求解，重点确认不会卸载 `luci-i18n-athena-zh-cn`、LuCI 或其他无关软件包。
4. 把模拟结果交由用户确认；未经用户明确同意，不执行正式安装。
5. 安装验收完成后再进入前端审计/页面功能验收。

## 8. 已取消的 Codespaces 方案

用户已明确表示不需要固定签名密钥初始化流程。此前拟定的 Codespaces、ECDSA P-256 私钥生成和 Repository Secret 配置步骤全部暂停，不应继续引导用户执行。