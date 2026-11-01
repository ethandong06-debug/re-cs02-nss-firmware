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

## 4. 固定 APK 签名迁移（已暂停）

### 用户决定

用户于 2026-11-01 明确决定不继续 Codespaces 固定密钥初始化流程，恢复原有 APK 构建流程。

### 已完成

- 曾创建分支 `athenawrt/apk-fixed-signing` 并尝试改造构建工作流以读取固定签名 Secret。
- 用户取消固定密钥方案后，已将该分支的 `.github/workflows/build-athena-apk.yml` 恢复为原始基线分支 `athenawrt/phase1-p0-fixes` 的工作流内容。
- 恢复提交：`c71585b688e3e5b66bdf2acc27f52176831f6fbf`。
- 恢复后的工作流 Blob SHA：`7cb91ae35f6ef89fadd8af62071f6989acb1d40a`，与原始基线工作流 Blob SHA 完全一致。
- 恢复后的工作流不再读取 `ATHENAWRT_APK_SIGNING_KEY`，不要求 Codespaces，也不执行固定公钥导出步骤。

### 明确未完成

- 尚未触发 GitHub Actions 构建。
- 尚未生成或验证新的 APK。
- 尚未检查 APK 的签名、版本、架构和依赖。
- 尚未进行路由器端模拟升级或正式安装。
- 不要声称固定签名密钥已创建；该方案已暂停。

### 后续原则

- 当前按用户决定使用恢复后的原有构建流程继续第一阶段验收。
- 不要重新要求用户创建 Codespaces、生成密钥或配置 Repository Secret，除非用户以后主动重新提出固定签名需求。
- 仍须遵守 APK 安装前的签名/包管理检查和模拟升级要求；不得绕过设备端现有信任校验。
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

1. 核对恢复后的工作流文件与基线一致。
2. 通过 GitHub Actions 手动运行 `athenawrt/apk-fixed-signing` 分支的 `Build Athena LuCI APK`。
3. 检查运行结果与 Artifact；构建成功后再审查 APK 版本、架构、依赖、签名和 SHA-256。
4. 只有完成设备侧安全检查和模拟升级后，才向用户提出正式安装。

## 8. 已取消的 Codespaces 方案

用户已明确表示不需要固定签名密钥初始化流程。此前拟定的 Codespaces、ECDSA P-256 私钥生成和 Repository Secret 配置步骤全部暂停，不应继续引导用户执行。