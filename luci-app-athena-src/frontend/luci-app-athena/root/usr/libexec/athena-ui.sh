#!/bin/sh
# ============================================================
#  AthenaWrt — 界面模式管理（管理台 ⇄ LuCI 原生界面）
#  命令：
#    get                输出 {"mode":"last","last":"athena"}
#    set <athena|native|last>   设置默认界面并同步 /www/index.html
#    mark <athena|native>       记录最近使用的界面（默认入口跟随用）
#    sync               按当前配置重新生成 /www/index.html
#  配置：
#    uci athena.ui.mode  = athena | native | last（默认 last=跟随上次）
#    uci athena.ui.last  = athena | native（最近一次使用的界面）
# ============================================================

sync_index() {
	local MODE LAST TARGET
	MODE=$(uci -q get athena.ui.mode 2>/dev/null)
	LAST=$(uci -q get athena.ui.last 2>/dev/null)
	[ -z "$MODE" ] && MODE=last
	[ -z "$LAST" ] && LAST=athena

	case "$MODE" in
		native) TARGET='/cgi-bin/luci/' ;;
		last)
			if [ "$LAST" = "native" ]; then
				TARGET='/cgi-bin/luci/'
			else
				TARGET='luci-static/resources/view/athena/index.html'
			fi
			;;
		*) TARGET='luci-static/resources/view/athena/index.html' ;;
	esac

	cat > /www/index.html <<EOF
<!DOCTYPE html>
<html>
	<head>
		<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
		<meta http-equiv="Pragma" content="no-cache" />
		<meta http-equiv="Expires" content="0" />
		<meta http-equiv="refresh" content="0; URL=$TARGET" />
	</head>
	<body>
		<a href="$TARGET">AthenaWrt</a>
	</body>
</html>
EOF
}

get_mode() {
	local MODE LAST
	MODE=$(uci -q get athena.ui.mode 2>/dev/null)
	LAST=$(uci -q get athena.ui.last 2>/dev/null)
	[ -z "$MODE" ] && MODE=last
	[ -z "$LAST" ] && LAST=athena
	echo "{\"mode\":\"$MODE\",\"last\":\"$LAST\"}"
}

case "$1" in
	get)
		get_mode
		;;
	set)
		case "$2" in
			athena|native|last)
				uci set athena.ui.mode="$2"
				uci commit athena
				sync_index
				echo "{\"ok\":true,\"mode\":\"$2\"}"
				;;
			*)
				echo '{"ok":false,"msg":"mode 必须是 athena|native|last"}'
				exit 1
				;;
		esac
		;;
	mark)
		case "$2" in
			athena|native)
				uci set athena.ui.last="$2"
				uci commit athena
				echo '{"ok":true}'
				;;
			*)
				echo '{"ok":false,"msg":"mark 必须是 athena|native"}'
				exit 1
				;;
		esac
		;;
	sync)
		sync_index
		echo '{"ok":true}'
		;;
	zoom)
		# v1.2.52：真机实测 `uci commit athena` 报 "uci: Invalid argument"（缩放在刷新后回 100%），
		# 改为 /etc/athena-prefs.conf 为权威存储，uci 只在能写通时镜像一份。
		case "${2:-get}" in
			get)
				Z=$(/usr/libexec/athena-prefs.sh get ui_zoom 2>/dev/null)
				[ -z "$Z" ] && Z=$(uci -q get athena.ui.zoom 2>/dev/null)
				case "$Z" in ''|*[!0-9]*) Z=100 ;; esac
				[ "$Z" -lt 80 ] 2>/dev/null && Z=80
				[ "$Z" -gt 120 ] 2>/dev/null && Z=120
				echo "{\"ok\":true,\"zoom\":$Z}"
				;;
			set)
				V="${3:-100}"
				case "$V" in ''|*[!0-9]*) V=100 ;; esac
				[ "$V" -lt 80 ] 2>/dev/null && V=80
				[ "$V" -gt 120 ] 2>/dev/null && V=120
				/usr/libexec/athena-prefs.sh set ui_zoom "$V" >/dev/null 2>&1
				uci -q set athena.ui.zoom="$V" 2>/dev/null
				uci -q commit athena 2>/dev/null
				echo "{\"ok\":true,\"zoom\":$V}"
				;;
			*)
				echo '{"ok":false,"msg":"zoom 支持 get|set <80-120>"}'
				exit 1
				;;
		esac
		;;
	*)
		echo '{"ok":false,"msg":"usage: get|set <mode>|mark <athena|native>|sync"}'
		exit 1
		;;
esac

exit 0
