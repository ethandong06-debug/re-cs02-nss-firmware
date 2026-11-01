#!/bin/sh
# AthenaWrt 点阵屏配置：严格校验输入，避免非法 UCI 值写入驱动配置。
# 用法：get | set <key> <value>
set -u
CMD="${1:-get}"

g() { uci -q get "athena_led.general.$1" 2>/dev/null || true; }
disp() { [ "$1" = "1" ] && echo false || echo true; }
bool() { case "$1" in 0|1) return 0 ;; *) return 1 ;; esac; }
level() { case "$1" in 0|1|2|3|4|5|6|7) return 0 ;; *) return 1 ;; esac; }
valid_time() {
	case "$1" in [0-2][0-9]:[0-5][0-9]) ;; *) return 1 ;; esac
	H="${1%%:*}"
	[ "$H" -le 23 ] 2>/dev/null
}
reload() {
	[ -x /etc/init.d/athena_led ] || return 1
	/etc/init.d/athena_led restart >/dev/null 2>&1
}

case "$CMD" in
	get)
		EN=$(g enabled); LL=$(g light_level); NL=$(g night_light_level)
		NS=$(g night_start); NE=$(g night_end); PF=$(g profile_mode)
		CK=$(g disable_led_clock); MD=$(g disable_led_medal)
		UP=$(g disable_led_up); DN=$(g disable_led_down); NN=$(g night_light_enable)
		case "$LL" in 0|1|2|3|4|5|6|7) ;; *) LL=5 ;; esac
		case "$NL" in 0|1|2|3|4|5|6|7) ;; *) NL=1 ;; esac
		valid_time "$NS" || NS="22:00"
		valid_time "$NE" || NE="07:00"
		case "$PF" in single|multi) ;; *) PF="multi" ;; esac
		[ "$EN" = "1" ] && EN=true || EN=false
		[ "$NN" = "1" ] && NN=true || NN=false
		CK=$(disp "$CK"); MD=$(disp "$MD"); UP=$(disp "$UP"); DN=$(disp "$DN")
		printf '{"ok":true,"enabled":%s,"light_level":%s,"night":%s,"night_start":"%s","night_end":"%s","night_level":%s,"profile":"%s","clock":%s,"medal":%s,"up":%s,"down":%s}\n' "$EN" "$LL" "$NN" "$NS" "$NE" "$NL" "$PF" "$CK" "$MD" "$UP" "$DN"
		;;
	set)
		KEY="${2:-}"; VAL="${3:-}"
		[ -n "$KEY" ] || { echo '{"ok":false,"msg":"缺少配置项"}'; exit 1; }
		case "$KEY" in
			enabled|night)
				bool "$VAL" || { echo '{"ok":false,"msg":"开关值必须为 0 或 1"}'; exit 1; }
				if [ "$KEY" = "night" ]; then UCI_KEY=night_light_enable; else UCI_KEY=enabled; fi
				;;
			light_level|night_level)
				level "$VAL" || { echo '{"ok":false,"msg":"亮度范围必须为 0-7"}'; exit 1; }
				if [ "$KEY" = "night_level" ]; then UCI_KEY=night_light_level; else UCI_KEY=light_level; fi
				;;
			night_start|night_end)
				valid_time "$VAL" || { echo '{"ok":false,"msg":"时间格式必须为 00:00-23:59"}'; exit 1; }
				UCI_KEY="$KEY"
				;;
			profile)
				case "$VAL" in single|multi) ;; *) echo '{"ok":false,"msg":"显示模式只能为 single 或 multi"}'; exit 1 ;; esac
				UCI_KEY=profile_mode
				;;
			clock|medal|up|down)
				bool "$VAL" || { echo '{"ok":false,"msg":"显示开关值必须为 0 或 1"}'; exit 1; }
				case "$KEY" in clock) UCI_KEY=disable_led_clock ;; medal) UCI_KEY=disable_led_medal ;; up) UCI_KEY=disable_led_up ;; down) UCI_KEY=disable_led_down ;; esac
				[ "$VAL" = "1" ] && VAL=0 || VAL=1
				;;
			*) echo '{"ok":false,"msg":"未知配置项"}'; exit 1 ;;
		esac
		uci -q set "athena_led.general.$UCI_KEY=$VAL" || { echo '{"ok":false,"msg":"写入配置失败"}'; exit 1; }
		uci commit athena_led || { echo '{"ok":false,"msg":"保存配置失败"}'; exit 1; }
		if ! reload; then
			echo '{"ok":false,"saved":true,"msg":"配置已保存，但点阵屏服务重载失败"}'
			exit 1
		fi
		printf '{"ok":true,"key":"%s","val":"%s"}\n' "$KEY" "$VAL"
		;;
	*) echo '{"ok":false,"msg":"未知命令（支持 get|set）"}'; exit 1 ;;
esac
