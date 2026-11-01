#!/bin/sh
# AthenaWrt 用户偏好存储。仅允许前端实际使用的有限键，避免任意写入和 sed 注入。
P=/etc/athena-prefs.conf
CMD="${1:-}"
K="${2:-}"
V="${3:-}"
umask 077

valid_key() {
	case "$1" in kpi_order|res_kth|ui_zoom|ui_mode|ui_last) return 0 ;; *) return 1 ;; esac
}
valid_value() {
	case "$K" in
		ui_zoom)
			case "$V" in ''|*[!0-9]*) return 1 ;; esac
			[ "$V" -ge 80 ] 2>/dev/null && [ "$V" -le 120 ] 2>/dev/null
			;;
		res_kth)
			case "$V" in 0|1) return 0 ;; *) return 1 ;; esac
			;;
		ui_mode)
			case "$V" in athena|native|last) return 0 ;; *) return 1 ;; esac
			;;
		ui_last)
			case "$V" in athena|native) return 0 ;; *) return 1 ;; esac
			;;
		kpi_order)
			[ -n "$V" ] && [ "${#V}" -le 32 ] || return 1
			case "$V" in ,*|*,|*,,*|*[!a-z,]*) return 1 ;; esac
			OLDIFS="$IFS"; IFS=','
			for item in $V; do
				case "$item" in cpu|mem|up|dev) ;; *) IFS="$OLDIFS"; return 1 ;; esac
			done
			IFS="$OLDIFS"
			return 0
			;;
		*) return 1 ;;
	esac
}

case "$CMD" in
	get)
		valid_key "$K" || { echo '{"ok":false,"msg":"不支持的偏好项"}'; exit 1; }
		[ -f "$P" ] && awk -F= -v k="$K" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' "$P"
		;;
	set)
		valid_key "$K" && valid_value || { echo '{"ok":false,"msg":"偏好值无效"}'; exit 1; }
		tmp="$P.tmp.$$"
		if [ -f "$P" ]; then
			awk -F= -v k="$K" -v v="$V" 'BEGIN { done=0 } $1 == k { if (!done) { print k "=" v; done=1 } next } { print } END { if (!done) print k "=" v }' "$P" > "$tmp" || { rm -f "$tmp"; echo '{"ok":false,"msg":"写入偏好失败"}'; exit 1; }
		else
			printf '%s=%s\n' "$K" "$V" > "$tmp" || { rm -f "$tmp"; echo '{"ok":false,"msg":"写入偏好失败"}'; exit 1; }
		fi
		chmod 600 "$tmp" && mv "$tmp" "$P" || { rm -f "$tmp"; echo '{"ok":false,"msg":"保存偏好失败"}'; exit 1; }
		echo '{"ok":true}'
		;;
	del)
		valid_key "$K" || { echo '{"ok":false,"msg":"不支持的偏好项"}'; exit 1; }
		if [ -f "$P" ]; then
			tmp="$P.tmp.$$"
			awk -F= -v k="$K" '$1 != k { print }' "$P" > "$tmp" && chmod 600 "$tmp" && mv "$tmp" "$P" || { rm -f "$tmp"; echo '{"ok":false,"msg":"删除偏好失败"}'; exit 1; }
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
