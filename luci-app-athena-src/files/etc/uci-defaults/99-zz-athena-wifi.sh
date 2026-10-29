#!/bin/sh
# ============================================================
#  AthenaWrt 最终无线品牌覆盖 (uci-defaults，仅首启执行一次)
#  排序在 99-jdc-wifi 之后，覆盖其 SSID/密码/国家码
# ============================================================
#
# 三频默认（与前端「无线三频」页一致）：
#   radio 2.4G          -> SSID Athena-2.4G
#   radio 5.2G(HE160)   -> SSID Athena-5G-Game   (QCN9074 4×4 游戏频段)
#   radio 5.8G(HE80)    -> SSID Athena-5G        (板载 IPQ6018 2×2 影音频段)
#   密码统一 12345678，WPA2-PSK，国家码 CN
#
# 说明：依据 wireless.radioN.band + htmode 动态区分 5.2G/5.8G，
#       不依赖 radio 编号（真机 radio0=5.8G / radio1=2.4G / radio2=5.2G）。

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

	# 该 radio 下第一个 wifi-iface 应用品牌 SSID + 密码
	idx=$(uci show wireless 2>/dev/null | grep -oE "wireless\.@wifi-iface\[[0-9]+\]\.device='radio${r}'" | grep -oE '\[[0-9]+\]' | head -1 | tr -d '[]')
	if [ -n "$idx" ]; then
		uci -q set "wireless.@wifi-iface[$idx].ssid=$SSID"
		uci -q set "wireless.@wifi-iface[$idx].encryption=psk2"
		uci -q set "wireless.@wifi-iface[$idx].key=$BASE_KEY"
	fi
done

uci commit wireless 2>/dev/null

exit 0
