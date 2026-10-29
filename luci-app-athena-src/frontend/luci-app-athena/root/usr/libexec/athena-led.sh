#!/bin/sh
# AthenaWrt 三色状态灯（red/green/blue GPIO LED）+ 呼吸灯控制
# 真机三色 LED 由内核 GPIO LED 子系统管理（DTS led_status_red/green/blue，gpio57/58/79）：
#   红 = led-failsafe / led-upgrade；绿 = led-running（正常运行常亮）；蓝 = led-boot
# 用法:
#   athena-led.sh get                      读取三色灯状态 + 呼吸灯开关（JSON）
#   athena-led.sh set breath 0|1           开关呼吸灯（green 设为 heartbeat 呼吸 / default-on 常亮）
# 说明：呼吸灯通过 green LED 的 trigger 切换实现，持久化到 athena.led.breathing

CMD="${1:-get}"

# 自动探测 LED sysfs 目录：不同内核/设备树命名可能不同，按常见命名逐个尝试
find_led() {
	# $1 = 颜色关键字（red / green / blue）
	local c="$1" p
	for p in \
		"/sys/class/leds/$c" \
		"/sys/class/leds/$c:status" \
		"/sys/class/leds/led_status_$c" \
		"/sys/class/leds/status:$c" \
		"/sys/class/leds/$c:power" \
		"/sys/class/leds/$c:boot" \
		"/sys/class/leds/$c:running" \
		; do
		[ -d "$p" ] && { echo "$p"; return 0; }
	done
	# 回退：按名字模糊匹配（取第一个）
	p=$(ls -d /sys/class/leds/*"${c}"* 2>/dev/null | head -n 1)
	[ -n "$p" ] && echo "$p" && return 0
	return 1
}

LED_GREEN=$(find_led green)
LED_RED=$(find_led red)
LED_BLUE=$(find_led blue)

# 读 LED 是否点亮（brightness > 0）
led_on() {
	[ -n "$1" ] || { echo false; return; }
	local b=$(cat "$1/brightness" 2>/dev/null)
	[ -n "$b" ] && [ "$b" -gt 0 ] 2>/dev/null && echo true || echo false
}
led_trigger() {
	[ -n "$1" ] || { echo ""; return; }
	cat "$1/trigger" 2>/dev/null | sed -n 's/.*\[\([^]]*\)\].*/\1/p'
}

# 呼吸开 = green trigger 是 heartbeat
breath_state() {
	local t=$(led_trigger "$LED_GREEN")
	[ "$t" = "heartbeat" ] && echo true || echo false
}

case "$CMD" in
	get)
		B=$(breath_state)
		echo "{\"ok\":true,\"breathing\":$B,\"red\":$(led_on "$LED_RED"),\"green\":$(led_on "$LED_GREEN"),\"blue\":$(led_on "$LED_BLUE")}"
		;;
	set)
		KEY="${2:-}"; VAL="${3:-0}"
		case "$KEY" in
			breath)
				if [ -z "$LED_GREEN" ]; then
					echo '{"ok":false,"msg":"未找到绿色 LED（内核 GPIO LED 未就绪）"}'
					exit 1
				fi
				if [ "$VAL" = "1" ]; then
					echo heartbeat > "$LED_GREEN/trigger" 2>/dev/null
					uci -q set athena.led.breathing='1'
					echo '{"ok":true,"breathing":true,"msg":"呼吸灯已开启"}'
				else
					echo default-on > "$LED_GREEN/trigger" 2>/dev/null
					uci -q set athena.led.breathing='0'
					echo '{"ok":true,"breathing":false,"msg":"呼吸灯已关闭"}'
				fi
				uci commit athena 2>/dev/null
				;;
			*) echo '{"ok":false,"msg":"未知配置项（支持 breath）"}'; exit 1 ;;
		esac
		;;
	boot)
		# 开机恢复呼吸灯状态：读持久化的 athena.led.breathing，若为 1 则把 green 设为 heartbeat
		B=$(uci -q get athena.led.breathing 2>/dev/null)
		if [ "$B" = "1" ] && [ -n "$LED_GREEN" ]; then
			echo heartbeat > "$LED_GREEN/trigger" 2>/dev/null
		fi
		exit 0
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 get|set|boot）"}'
		exit 1
		;;
esac
