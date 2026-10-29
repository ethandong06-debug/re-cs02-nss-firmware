#!/bin/sh
# ============================================================
#  AthenaWrt — 文件共享（filebrowser-go）默认配置
#  若固件编入了 luci-app-filebrowser-go：端口 8081、根目录 /mnt
#  未编入时 uci 写操作无实际服务，无副作用
# ============================================================

uci -q set filebrowser.filebrowser=filebrowser
uci -q set filebrowser.filebrowser.port='8081'
uci -q set filebrowser.filebrowser.root_dir='/mnt'
uci -q commit filebrowser

exit 0
