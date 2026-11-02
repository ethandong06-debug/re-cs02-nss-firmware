#!/bin/sh
# ============================================================
#  AthenaWrt — 轻量偏好存储（v1.2.52）
#  背景：真机实测 `uci commit athena` 会返回 "uci: Invalid argument"，
#        导致界面缩放 / 网速单位等设置写不进 /etc/config，刷新即回默认。
#        这里用一个纯文本文件做权威存储，uci 只做尽力而为的镜像。
#  存储：/etc/athena-prefs.conf   每行 key=value（覆盖 /etc 可写 overlay，重启后仍在）
#  用法：
#    athena-prefs.sh get <key>        输出原值（不存在则输出空）
#    athena-prefs.sh set <key> <val>  写入并返回 {"ok":true}
#    athena-prefs.sh list             输出全部 key=value
#    athena-prefs.sh del <key>        删除某键
# ============================================================

P=/etc/athena-prefs.conf
K="${2:-}"
V="${3:-}"

umask 077
valid_key() {
	case "$1" in kpi_order|res_kth|ui_zoom|speed_unit) return 0 ;; esac
	return 1
}
valid_value() {
	case "$K" in
		kpi_order)
			printf '%s\n' "$V" | awk -F, 'NF != 4 { exit 1 } { for (i=1; i<=NF; i++) if ($i !~ /^(cpu|mem|up|dev)$/ || seen[$i]++) exit 1 }' || return 1
			;;
		res_kth) case "$V" in 0|1) ;; *) return 1 ;; esac ;;
		ui_zoom) case "$V" in ''|*[!0-9]*) return 1 ;; esac; [ "$V" -ge 80 ] 2>/dev/null && [ "$V" -le 120 ] 2>/dev/null || return 1 ;;
		speed_unit) case "$V" in Mbps|MB/s|KB/s) ;; *) return 1 ;; esac ;;
		*) return 1 ;;
	esac
	return 0
}

case "$1" in
	get)
		valid_key "$K" || { echo '{"ok":false,"msg":"不允许的偏好键"}'; exit 1; }
		[ -n "$K" ] || { echo '{"ok":false,"msg":"缺 key"}'; exit 1; }
		[ -f "$P" ] && grep -m1 "^$K=" "$P" 2>/dev/null | cut -d= -f2-
		;;
	set)
		valid_key "$K" || { echo '{"ok":false,"msg":"不允许的偏好键"}'; exit 1; }
		valid_value || { echo '{"ok":false,"msg":"偏好值不合法"}'; exit 1; }
		[ -n "$K" ] || { echo '{"ok":false,"msg":"缺 key"}'; exit 1; }
		[ -f "$P" ] || : > "$P" 2>/dev/null
		if grep -q "^$K=" "$P" 2>/dev/null; then
			tmp="$P.tmp.$$"
			sed "s|^$K=.*|$K=$V|" "$P" > "$tmp" 2>/dev/null && mv "$tmp" "$P"
		else
			printf '%s=%s\n' "$K" "$V" >> "$P"
		fi
		echo '{"ok":true}'
		;;
	del)
		valid_key "$K" || { echo '{"ok":false,"msg":"不允许的偏好键"}'; exit 1; }
		[ -n "$K" ] || { echo '{"ok":false,"msg":"缺 key"}'; exit 1; }
		if [ -f "$P" ]; then
			tmp="$P.tmp.$$"
			grep -v "^$K=" "$P" > "$tmp" 2>/dev/null && mv "$tmp" "$P"
		fi
		echo '{"ok":true}'
		;;
	list)
		[ -f "$P" ] && cat "$P"
		;;
	*)
		echo '{"ok":false,"msg":"usage: get|set|del|list"}'
		exit 1
		;;
esac
