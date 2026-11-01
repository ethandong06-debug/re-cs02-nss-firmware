#!/bin/sh
# AthenaWrt 三色状态灯（内核 GPIO LED）与绿色呼吸灯控制。
# 红/绿/蓝状态只读；仅允许切换绿色 LED 的 heartbeat/default-on trigger。
CMD="${1:-get}"

find_led() {
	local c="$1" p
	for p in "/sys/class/leds/$c" "/sys/class/leds/$c:status" "/sys/class/leds/led_status_$c" "/sys/class/leds/status:$c" "/sys/class/leds/$c:power" "/sys/class/leds/$c:boot" "/sys/class/leds/$c:running"; do
		[ -d "$p" ] && { echo "$p"; return 0; }
	done
	p=$(ls -d /sys/class/leds/*"$c"* 2>/dev/null | head -n 1)
	[ -n "$p" ] && [ -d "$p" ] && { echo "$p"; return 0; }
	return 1
}
led_on() {
	[ -n "$1" ] || { echo false; return; }
	local b
	b=$(cat "$1/brightness" 2>/dev/null)
	[ -n "$b" ] && [ "$b" -gt 0 ] 2>/dev/null && echo true || echo false
}
led_trigger() {
	[ -n "$1" ] || { echo ""; return; }
	cat "$1/trigger" 2>/dev/null | sed -n 's/.*\[\([^]]*\)\].*/\1/p'
}

LED_GREEN=$(find_led green)
LED_RED=$(find_led red)
LED_BLUE=$(find_led blue)

case "$CMD" in
	get)
		T=$(led_trigger "$LED_GREEN")
		[ "$T" = heartbeat ] && B=true || B=false
		printf '{"ok":true,"breathing":%s,"red":%s,"green":%s,"blue":%s}\n' "$B" "$(led_on "$LED_RED")" "$(led_on "$LED_GREEN")" "$(led_on "$LED_BLUE")"
		;;
	set)
		KEY="${2:-}"; VAL="${3:-}"
		[ "$KEY" = breath ] || { echo '{"ok":false,"msg":"仅支持 breath 控制"}'; exit 1; }
		case "$VAL" in 0|1) ;; *) echo '{"ok":false,"msg":"呼吸灯值必须为 0 或 1"}'; exit 1 ;; esac
		[ -n "$LED_GREEN" ] || { echo '{"ok":false,"msg":"未找到绿色 LED（GPIO LED 未就绪）"}'; exit 1; }
		[ -w "$LED_GREEN/trigger" ] || { echo '{"ok":false,"msg":"绿色 LED trigger 不可写"}'; exit 1; }
		if [ "$VAL" = 1 ]; then TARGET=heartbeat; else TARGET=default-on; fi
		printf '%s\n' "$TARGET" > "$LED_GREEN/trigger" 2>/dev/null || { echo '{"ok":false,"msg":"切换 LED 模式失败"}'; exit 1; }
		ACTUAL=$(led_trigger "$LED_GREEN")
		[ "$ACTUAL" = "$TARGET" ] || { echo '{"ok":false,"msg":"内核未接受该 LED 模式"}'; exit 1; }
		uci -q set "athena.led.breathing=$VAL" || { echo '{"ok":false,"msg":"保存呼吸灯状态失败"}'; exit 1; }
		uci commit athena || { echo '{"ok":false,"msg":"提交呼吸灯状态失败"}'; exit 1; }
		[ "$VAL" = 1 ] && echo '{"ok":true,"breathing":true,"msg":"呼吸灯已开启"}' || echo '{"ok":true,"breathing":false,"msg":"呼吸灯已关闭"}'
		;;
	boot)
		B=$(uci -q get athena.led.breathing 2>/dev/null)
		if [ "$B" = 1 ] && [ -n "$LED_GREEN" ] && [ -w "$LED_GREEN/trigger" ]; then
			echo heartbeat > "$LED_GREEN/trigger" 2>/dev/null
		fi
		exit 0
		;;
	*) echo '{"ok":false,"msg":"未知命令（支持 get|set|boot）"}'; exit 1 ;;
esac
