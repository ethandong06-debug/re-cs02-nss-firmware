#!/bin/sh
# AthenaWrt 点阵屏配置（对接真实驱动 athena_led，读写 /etc/config/athena_led）
# 用法:
#   athena-matrix.sh get                      读取当前配置（JSON）
#   athena-matrix.sh set <key> [val...]       设置单项并重启服务生效
#
# 真实驱动字段（athena_led.general.*，见 package/athena-led 的 athena_led.config / init）：
#   enabled 0|1            总开关
#   light_level 0-7        亮度（驱动只认 0-7）
#   profile_mode single|multi  显示模式
#   night 0|1              夜间模式开关 → night_light_enable
#   night_start/night_end  HH:MM
#   night_level 0-7        夜间亮度 → night_light_level
#   clock|medal|up|down 0|1  各区域「显示」开关（语义：1=显示；内部映射 disable_led_* 取反）
#
# 三色状态灯（red/green/blue）由内核 GPIO LED 控制，见 athena-led.sh；本脚本只管点阵屏。

CMD="${1:-get}"

g() { uci -q get "athena_led.general.$1" 2>/dev/null; }
b() { [ "$1" = "1" ] && echo true || echo false; }
reload() { [ -x /etc/init.d/athena_led ] && /etc/init.d/athena_led restart >/dev/null 2>&1; }
# disable_led_x=1 表示「关闭 x 显示」；转成「显示」语义需取反
disp() { [ "$1" = "1" ] && echo false || echo true; }

case "$CMD" in
	get)
		EN=$(g enabled); LL=$(g light_level); NL=$(g night_light_level)
		NS=$(g night_start); NE=$(g night_end); PF=$(g profile_mode)
		CK=$(g disable_led_clock); MD=$(g disable_led_medal)
		UP=$(g disable_led_up); DN=$(g disable_led_down); NN=$(g night_light_enable)
		[ -z "$LL" ] && LL=5
		[ -z "$NL" ] && NL=1
		[ -z "$NS" ] && NS="22:00"
		[ -z "$NE" ] && NE="07:00"
		[ -z "$PF" ] && PF="multi"
		[ "$EN" = "1" ] && EN=true || EN=false
		[ "$NN" = "1" ] && NN=true || NN=false
		CK=$(disp "$CK"); MD=$(disp "$MD"); UP=$(disp "$UP"); DN=$(disp "$DN")
		echo "{\"ok\":true,\"enabled\":$EN,\"light_level\":$LL,\"night\":$NN,\"night_start\":\"$NS\",\"night_end\":\"$NE\",\"night_level\":$NL,\"profile\":\"$PF\",\"clock\":$CK,\"medal\":$MD,\"up\":$UP,\"down\":$DN}"
		;;
	set)
		KEY="${2:-}"; VAL="${3:-}"
		[ -z "$KEY" ] && { echo '{"ok":false,"msg":"缺少配置项"}'; exit 1; }
		case "$KEY" in
			enabled) uci -q set "athena_led.general.enabled=$VAL" ;;
			light_level) uci -q set "athena_led.general.light_level=$VAL" ;;
			night) uci -q set "athena_led.general.night_light_enable=$VAL" ;;
			night_start) uci -q set "athena_led.general.night_start=$VAL" ;;
			night_end) uci -q set "athena_led.general.night_end=$VAL" ;;
			night_level) uci -q set "athena_led.general.night_light_level=$VAL" ;;
			profile) uci -q set "athena_led.general.profile_mode=$VAL" ;;
			# 区域显示开关：前端语义 1=显示 → 写 disable_led_* 取反
			clock) [ "$VAL" = "1" ] && uci -q set "athena_led.general.disable_led_clock=0" || uci -q set "athena_led.general.disable_led_clock=1" ;;
			medal) [ "$VAL" = "1" ] && uci -q set "athena_led.general.disable_led_medal=0" || uci -q set "athena_led.general.disable_led_medal=1" ;;
			up) [ "$VAL" = "1" ] && uci -q set "athena_led.general.disable_led_up=0" || uci -q set "athena_led.general.disable_led_up=1" ;;
			down) [ "$VAL" = "1" ] && uci -q set "athena_led.general.disable_led_down=0" || uci -q set "athena_led.general.disable_led_down=1" ;;
			*) echo '{"ok":false,"msg":"未知配置项"}'; exit 1 ;;
		esac
		uci commit athena_led 2>/dev/null
		reload
		echo "{\"ok\":true,\"key\":\"$KEY\",\"val\":\"$VAL\"}"
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 get|set）"}'
		exit 1
		;;
esac
