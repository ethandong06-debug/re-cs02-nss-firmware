#!/bin/sh
# AthenaWrt 软件包清单入口 v1.2.51
#   `list installed`（无关键字）-> ucode 直读 /lib/apk/db/installed      实测 1.41s -> 0.16s
#   其余全部交给 athena-packages-legacy.sh：
#     - available（无关键字）在 legacy 里"读缓存 + 后台预热"，页面永不等待
#     - install / remove / update / upgrade / 带关键字搜索 本来就该真跑 apk
#   ucode 不可用、数据库缺失或输出异常时自动回退，页面不会白屏。

case "$1" in
list)
	if [ "${2:-installed}" = "installed" ] && [ -z "${3:-}" ] \
		&& [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-packages.uc ]; then
		_out=$(/usr/bin/ucode /usr/libexec/athena-packages.uc 2>/dev/null)
		case "$_out" in
		'{"ok":true,"packages":[{"'*)
			printf '%s\n' "$_out"
			exit 0
			;;
		esac
	fi
	;;
esac

exec /usr/libexec/athena-packages-legacy.sh "$@"
