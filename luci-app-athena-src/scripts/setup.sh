#!/bin/bash
# ============================================================
#  AthenaWrt 定制固件 — 构建环境初始化脚本 (在编译虚拟机内执行)
#  全新 clone ImmortalWrt + 配置 feeds + 生成 .config + defconfig
#  不复用任何既有构建产物
# ============================================================
set -e

# BUILD_ROOT = 本脚本所在目录的上一级
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="$(dirname "$SCRIPT_DIR")"
SRC="$BUILD_ROOT/immortalwrt"
LOG="$BUILD_ROOT/setup.log"

# ---- 干净环境 (不继承既有 PATH 里的 wrapper) ----
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
# 自建 git 加速配置 (GitHub -> ghfast.top 公共加速通道)
export GIT_CONFIG_GLOBAL="$BUILD_ROOT/configs/gitconfig"
export GIT_SSL_NO_VERIFY=0
# Go 模块走国内代理 (标准 Go 设置)
export GOPROXY="https://goproxy.cn,direct"

# 自建 curl 镜像映射 (GitHub/内核/GNU -> 加速镜像), 不走既有 wrapper
mkdir -p "$BUILD_ROOT/bin"
cp -f "$BUILD_ROOT/scripts/mirror-curl.sh" "$BUILD_ROOT/bin/curl"
chmod +x "$BUILD_ROOT/bin/curl"
export PATH="$BUILD_ROOT/bin:$PATH"

exec > >(tee -a "$LOG") 2>&1
echo "=== AthenaWrt 构建环境初始化 $(date '+%F %T') ==="

# ---- 1. 克隆源码 (shallow, 直连 GitHub) ----
if [ ! -d "$SRC/.git" ]; then
  echo ">>> 克隆 ImmortalWrt 源码 (master, shallow)..."
  git clone --depth 1 https://github.com/immortalwrt/immortalwrt.git "$SRC"
else
  echo ">>> 源码目录已存在, 跳过 clone"
fi
cd "$SRC"

# ---- 1.5 修复源码下载镜像源 (移除 302 重定向到 SourceForge 的慢源, 避免下载卡死) ----
echo ">>> 修复 projectsmirrors.json 镜像源..."
[ -f scripts/projectsmirrors.json.bak ] || cp scripts/projectsmirrors.json scripts/projectsmirrors.json.bak
sed -i '/sources\.cdn\.openwrt\.org/d; /mirror2\.immortalwrt\.org/d; /mirror\.immortalwrt\.org\/sources/d' scripts/projectsmirrors.json

# ---- 2. 写入 feeds 配置 (含 kenzok8 插件源) ----
echo ">>> 写入 feeds.conf.default..."
cat > feeds.conf.default <<'EOF'
src-git packages https://github.com/immortalwrt/packages.git;master
src-git luci https://github.com/immortalwrt/luci.git;master
src-git routing https://github.com/openwrt/routing.git;master
src-git telephony https://github.com/openwrt/telephony.git;master
src-git kenzo https://github.com/kenzok8/openwrt-packages
src-git small https://github.com/kenzok8/small
EOF

# ---- 3. 更新并安装 feeds ----
echo ">>> feeds update -a ..."
./scripts/feeds update -a
echo ">>> feeds install -a ..."
./scripts/feeds install -a

# ---- 4. 拷贝定制覆盖层 (files/ -> 源码树 files/，OpenWrt 根文件系统覆盖层) ----
echo ">>> 拷贝 files 覆盖层..."
if [ -d "$BUILD_ROOT/files" ]; then
  mkdir -p "$SRC/files"
  cp -r "$BUILD_ROOT/files/." "$SRC/files/"
  # uci-defaults 脚本需可执行
  chmod +x "$SRC"/files/etc/uci-defaults/*.sh 2>/dev/null || true
fi

# ---- 5. 生成 .config (种子 + 插件清单) ----
echo ">>> 生成 .config..."
cp "$BUILD_ROOT/configs/jdcloud_re-cs-02.seed" .config
while IFS= read -r pkg; do
  case "$pkg" in
    ''|'#'*) continue ;;
  esac
  echo "CONFIG_PACKAGE_${pkg}=y" >> .config
done < "$BUILD_ROOT/configs/packages.list"

# ---- 6. defconfig (解析依赖) ----
echo ">>> make defconfig ..."
make defconfig

# ---- 7. 追加非 Kconfig 配置 (本地镜像源 + 中文界面 + 品牌版本) ----
# 注: 这些非 Kconfig 符号会被 defconfig 清除, 必须在 defconfig 之后追加
echo ">>> 追加本地镜像/中文/品牌配置..."
cat >> .config <<'EOF'
CONFIG_LOCALMIRROR="https://sources.openwrt.org;https://mirror2.openwrt.org/sources"
CONFIG_LUCI_LANG_zh_Hans=y
CONFIG_VERSION_DIST="AthenaWrt"
CONFIG_VERSION_NUMBER="v1.2.60"
CONFIG_VERSION_REPO="https://github.com/immortalwrt/immortalwrt"
CONFIG_VERSION_MANUFACTURER="JDCloud"
CONFIG_VERSION_PRODUCT="Athena"
CONFIG_VERSION_DESCRIPTION="AthenaWrt v1.2.60 for JDCloud RE-CS-02 (IPQ6010)"
EOF

echo "=== 初始化完成 $(date '+%F %T'), 可开始 make ==="
