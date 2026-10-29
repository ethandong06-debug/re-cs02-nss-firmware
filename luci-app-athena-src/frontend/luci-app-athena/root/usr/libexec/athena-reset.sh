#!/bin/sh
# AthenaWrt 恢复出厂设置
# 用法: athena-reset.sh [--confirm]
# 无 --confirm 时仅返回提示；带 --confirm 时执行 firstboot + 重启

if [ "$1" != "--confirm" ]; then
	echo '{"ok":false,"need_confirm":true,"msg":"恢复出厂将清除所有配置并重启，请二次确认"}'
	exit 0
fi

# 执行恢复出厂（firstboot 会标记下次启动清除 overlay）
firstboot -y >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
	echo '{"ok":true,"msg":"已标记恢复出厂，设备即将重启"}'
	# 延迟重启，确保响应已返回前端
	( sleep 2; reboot ) >/dev/null 2>&1 &
else
	echo '{"ok":false,"msg":"恢复出厂失败"}'
fi
exit 0
