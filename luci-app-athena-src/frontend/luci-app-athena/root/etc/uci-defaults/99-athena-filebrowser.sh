#!/bin/sh
# filebrowser 的实际监听地址、共享根目录与 USB 挂载检查统一由
# /etc/init.d/filebrowser 管理。旧版 UCI root_dir=/mnt 不会被该 init
# 脚本读取，故不再写入无效配置，避免造成共享目录已受限的错觉。
exit 0
