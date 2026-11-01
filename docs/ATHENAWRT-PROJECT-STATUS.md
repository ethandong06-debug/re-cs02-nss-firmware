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

## 4. 固定 APK 签名迁移

### 目标

从 1.2.60 及更高版本开始，所有 AthenaWrt APK 使用同一把长期固定私钥签名。

- 私钥仅保存在 GitHub Actions Repository Secret：`ATHENAWRT_APK_SIGNING_KEY`。
- 对应公钥随构建产物提供，安装到路由器 `/etc/apk/keys/`。
- 私钥不得提交到 Git、放入 APK、上传到路由器或写入项目文档。
- 构建流程必须在缺少 Secret 时明确失败，不允许退回临时密钥或无签名构建。
- 正式构建后，使用 APK 工具验证包签名，并提供公钥、校验和等产物。

### 已完成

- 已从真实构建仓库和工作流确认构建来源。
- 已创建分支 `athenawrt/apk-fixed-signing`。
- 已修改 `.github/workflows/build-athena-apk.yml`，仅修改构建工作流，没有改动 Athena 前后端业务代码或网络配置。
- 工作流读取 `ATHENAWRT_APK_SIGNING_KEY` Secret；检查私钥；从私钥导出公钥；构建后验证 APK 签名；输出公钥和 SHA256 校验文件。
- 已确认新分支相对原始分支 ahead 2、behind 0；当时比较结果仅涉及构建工作流。
- 已核对工作流文件当前存在 `workflow_dispatch`，可在 GitHub Actions 页面手动选择该分支运行。
- 当前分支最新已知工作流修正提交：`9835a687eea52d239c67d32eb4cc72c0f44bd645`。
- 当前工作流文件 Blob SHA（2026-11-01 核对）：`de0fcf232bfe0071ccb2bd11ff848b77eb1b18cd`。

### 尚未完成

1. 创建并执行一次性云端密钥初始化流程。
2. 将生成的私钥保存到 Repository Secret `ATHENAWRT_APK_SIGNING_KEY`。
3. 清理临时私钥 Artifact。
4. 在新分支手动运行正式 APK 构建工作流。
5. 下载 APK、公钥和校验文件，检查版本、架构、依赖及签名。
6. 在路由器安装公钥并验证 APK 信任链。
7. 模拟升级，确认不会移除中文语言包或其他无关包。
8. 用户确认后再正式安装，并验收服务和 LuCI 页面。

### 临时密钥初始化安全注意

此前讨论的一种方案是由 GitHub Actions 云端生成密钥，并通过短期 Artifact 取出私钥，再保存为 Repository Secret。用户已同意该思路，但必须明确：
- Artifact 中的私钥在删除前可能被拥有仓库读取权限的人下载。
- 若采用，Artifact 保留期应设为 1 天；用户取出并保存 Secret 后立即删除 Artifact。
- 不得声称初始化工作流已经创建或密钥已经生成；截至本文件更新时，这两项均未完成。
- 若 GitHub 写入操作被安全控制拦截，不得尝试绕过；应说明限制并提供安全替代方式。

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

先处理固定签名密钥的安全初始化。不要修改 AthenaWrt 前端页面、后端功能或路由器网络配置。