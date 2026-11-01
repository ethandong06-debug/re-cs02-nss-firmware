#!/bin/sh
# AthenaWrt 定时重启
# 用法:
#   athena-reboot.sh status                 查看当前定时重启
#   athena-reboot.sh enable <HH:MM> <星期>  设置（星期：* 或 0-6，逗号分隔）
#   athena-reboot.sh disable                关闭
#   athena-reboot.sh now                    立即重启
# 输出单行 JSON

CMD="${1:-status}"
CRON_FILE="/etc/crontabs/root"

json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# 从 crontab 提取 athena 定时重启条目
get_cron() {
	grep -n "# athena-reboot" "$CRON_FILE" 2>/dev/null | head -1
}

case "$CMD" in
	status)
		line=$(get_cron)
		if [ -n "$line" ]; then
			# 格式: min hour day mon dow reboot # athena-reboot
			set -- $(echo "$line" | cut -d: -f2-)
			echo "{\"ok\":true,\"enabled\":true,\"min\":\"$1\",\"hour\":\"$2\",\"dow\":\"$5\"}"
		else
			echo '{"ok":true,"enabled":false}'
		fi
		;;
	enable)
		HHMM="${2:-04:00}"; DOW="${3:-*}"
		HH=$(echo "$HHMM" | cut -d: -f1)
		MM=$(echo "$HHMM" | cut -d: -f2)
		case "$HHMM" in [0-9][0-9]:[0-9][0-9]) ;; *) echo '{"ok":false,"msg":"时间格式应为 HH:MM"}'; exit 1 ;; esac
		[ "$HH" -le 23 ] 2>/dev/null && [ "$MM" -le 59 ] 2>/dev/null || { echo '{"ok":false,"msg":"时间必须在 00:00-23:59"}'; exit 1; }
		case "$DOW" in
			*) if [ "$DOW" != "*" ]; then
				for d in $(echo "$DOW" | tr ',' ' '); do case "$d" in 0|1|2|3|4|5|6) ;; *) echo '{"ok":false,"msg":"星期值必须为 * 或 0-6"}'; exit 1 ;; esac; done
			fi ;;
		esac
		# 先移除旧条目
		sed -i '/# athena-reboot/d' "$CRON_FILE" 2>/dev/null
		echo "$MM $HH * * $DOW reboot # athena-reboot" >> "$CRON_FILE"
		/etc/init.d/cron restart >/dev/null 2>&1 || /etc/init.d/crond restart >/dev/null 2>&1
		echo "{\"ok\":true,\"msg\":\"已设置 $DOW $HH:$MM 定时重启\"}"
		;;
	disable)
		sed -i '/# athena-reboot/d' "$CRON_FILE" 2>/dev/null
		/etc/init.d/cron restart >/dev/null 2>&1 || /etc/init.d/crond restart >/dev/null 2>&1
		echo '{"ok":true,"msg":"定时重启已关闭"}'
		;;
	now)
		echo '{"ok":true,"msg":"设备即将重启"}'
		( sleep 1; reboot ) >/dev/null 2>&1 &
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 status|enable|disable|now）"}'
		exit 1
		;;
esac
