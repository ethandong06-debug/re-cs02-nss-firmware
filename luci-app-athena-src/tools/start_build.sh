#!/bin/sh
# AthenaWrt NSS 定制固件编译启动脚本（增量编译）
cd ~/athena-build/nss/openwrt
setsid sh -c 'make -j$(nproc) V=s > ~/athena-build/nss/logs/athena-final.log 2>&1 < /dev/null' &
echo "BUILD_STARTED pid=$!"
exit 0
