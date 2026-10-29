#!/bin/sh
# ============================================================
#  AthenaWrt 最终无线品牌覆盖 (uci-defaults)
#  说明：wifi detect (mac80211.uc) 是无线配置的真正生成点，本脚本作为
#        双保险兜底——若未来时序变化导致本脚本在 wireless 配置生成后执行，
#        可再次覆盖 SSID/密码/国家码。
#  兼容 wifi-iface 具名 section (default_radioN) 与匿名 section (@wifi-iface[N])。
#
#  三频默认：
#    2.4G          -> Athena-2.4G
#    5.2G (HE160)  -> Athena-5G-Game   (QCN9074 4×4 电竞频段)
#    5.8G (HE80)   -> Athena-5G        (板载 2×2 影音频段)
#  密码统一 12345678，WPA2-PSK，国家码 CN
# ============================================================

BASE_KEY='12345678'

for r in 0 1 2; do
	band=$(uci -q get "wireless.radio${r}.band")
	[ -z "$band" ] && continue
	htmode=$(uci -q get "wireless.radio${r}.htmode")

	case "$band" in
		2g) SSID='Athena-2.4G' ;;
		5g)
			case "$htmode" in
				*160*) SSID='Athena-5G-Game' ;;
				*)     SSID='Athena-5G' ;;
			esac
			;;
		*) continue ;;
	esac

	# 国家码 CN（5.8G 149-165 / 5.2G 36-64 均可用）
	uci -q set "wireless.radio${r}.country=CN"
	uci -q set "wireless.radio${r}.disabled=0"

	# 找到 device=radio${r} 的 wifi-iface section（兼容具名 default_radioN 与匿名 @wifi-iface[N]）
	iface=$(uci -q show wireless 2>/dev/null | grep -E "\.device='radio${r}'$" | head -1 | sed "s/\.device=.*//")
	if [ -n "$iface" ]; then
		uci -q set "${iface}.ssid=$SSID"
		uci -q set "${iface}.encryption=psk2"
		uci -q set "${iface}.key=$BASE_KEY"
	fi
done

uci commit wireless 2>/dev/null

exit 0
