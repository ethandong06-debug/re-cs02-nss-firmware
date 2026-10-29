#!/bin/sh
# AthenaWrt 服务清单入口 v1.2.46
# 列表逻辑已搬到 ucode：/usr/libexec/athena-services.uc
#   旧版 2.19 秒的病根不是 fork 数量，而是 O(服务 × 菜单文件)：每个 init.d 服务都要把
#   menu.d/*.json 全扫一遍 grep。新实现把菜单文件只读一遍、启用状态改看 /etc/rc.d 软链，
#   实测 2.19s → 0.03s 量级。
#   `set <id> <0|1>`（启停）仍走 shell 版，因为那本来就要真去执行 init 脚本。
#   ucode 不可用或输出异常时自动回退 athena-services-legacy.sh，页面不会空。

case "$1" in
set)
	exec /usr/libexec/athena-services-legacy.sh "$@"
	;;
esac

if [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-services.uc ]; then
	_out=$(/usr/bin/ucode /usr/libexec/athena-services.uc 2>/dev/null)
	case "$_out" in
	'{"services"'*)
		printf '%s\n' "$_out"
		exit 0
		;;
	esac
fi

exec /usr/libexec/athena-services-legacy.sh "$@"
