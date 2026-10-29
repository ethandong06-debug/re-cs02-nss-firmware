#!/bin/bash
# ============================================================
#  AthenaWrt 定制固件 — 编译脚本 (在 setup.sh 完成后执行)
#  京东云雅典娜 AX6600 (JDCloud RE-CS-02 / IPQ6010)
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="$(dirname "$SCRIPT_DIR")"
SRC="$BUILD_ROOT/immortalwrt"
LOG="$BUILD_ROOT/build.log"

# 干净环境 + 自建镜像加速
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export GIT_CONFIG_GLOBAL="$BUILD_ROOT/configs/gitconfig"
export GOPROXY="https://goproxy.cn,direct"
[ -e "$BUILD_ROOT/bin/curl" ] && export PATH="$BUILD_ROOT/bin:$PATH"

# 源码下载镜像 (download.pl 最高优先级, 直连国内可达的 OpenWrt 官方源, 绕过被墙的 SourceForge)
export DOWNLOAD_MIRROR="https://sources.openwrt.org;https://mirror2.openwrt.org/sources"

cd "$SRC"

exec > >(tee -a "$LOG") 2>&1
echo "======================================================"
echo " AthenaWrt 编译开始  $(date '+%F %T')"
echo " 目标: qualcommax/ipq60xx / jdcloud_re-cs-02"
echo " 并行: -j5  内存: $(free -h | awk '/Mem/{print $2}')"
echo "======================================================"

# 先预取全部源码 (并行下载, 加速后续编译)
echo ">>> 预取源码 (make download)..."
make download -j8 2>&1 || echo ">>> download 有部分失败, 继续编译 (make 会重试)"

# 正式编译
echo ">>> 开始编译 (make -j5)..."
make -j5 2>&1
RC=$?

echo "======================================================"
echo " AthenaWrt 编译结束  $(date '+%F %T')  exit=$RC"
echo "======================================================"
if [ $RC -eq 0 ]; then
  echo ">>> 产物列表:"
  ls -la "$SRC/bin/targets/qualcommax/ipq60xx/" 2>/dev/null
fi
exit $RC
