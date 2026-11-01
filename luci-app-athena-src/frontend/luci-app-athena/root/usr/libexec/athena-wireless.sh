#!/bin/sh
# AthenaWrt 无线三频配置
# 用法:
#   athena-wireless.sh get                        读取三频配置（JSON）
#   athena-wireless.sh enable all|b24|b52|b58     开启全部/单频
#   athena-wireless.sh disable all|b24|b52|b58    关闭全部/单频
#   athena-wireless.sh set <band> <ssid> <pwd> <channel> <bw> <enc>  更新单频配置
# 三频 radio 映射（已按真机 `uci show wireless` 校准）：
#   radio0 = 板载 IPQ6018 5.8G  (band 5g, path platform/soc@0/c000000.wifi)
#   radio1 = 板载 IPQ6018 2.4G  (band 2g, path .../c000000.wifi+1)
#   radio2 = PCIe QCN9074 5.2G 游戏频段 (path ...pcie.../0000:01:00.0)
#   b24 -> radio1   b52 -> radio2   b58 -> radio0

CMD="${1:-get}"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g; s/\r//g'; }

GUEST_IFACE="athena_guest"
GUEST_SSID="Athena-Guest"
GUEST_IP="192.168.30.1"

band_radio() { case "$1" in b24) echo 1;; b52) echo 2;; b58) echo 0;; esac; }

# 找到 radio 对应的默认 wifi-iface（匿名 @wifi-iface[N] 与具名段都匹配）
find_iface() {
	local radio="$1"
	uci -q show wireless 2>/dev/null | grep -E "wireless\.[^.]+\.device='$radio'$" | grep -v "wireless\.$GUEST_IFACE\." | head -1 | cut -d. -f2 | cut -d= -f1
}

# encryption: uci -> 前端
uci2enc() {
	case "$1" in
		none) echo "开放（无加密）" ;;
		sae-mixed) echo "WPA2/WPA3-PSK" ;;
		sae) echo "WPA3-SAE" ;;
		psk2|psk-mixed|psk) echo "WPA2-PSK" ;;
		*) echo "WPA2/WPA3-PSK" ;;
	esac
}
# encryption: 前端 -> uci
enc2uci() {
	case "$1" in
		"开放（无加密）") echo "none" ;;
		"WPA3-SAE"|"WPA3-PSK") echo "sae" ;;
		"WPA2/WPA3-PSK"|"WPA3/WPA2"|"WPA2/WPA3") echo "sae-mixed" ;;
		"WPA2-PSK") echo "psk2" ;;
		*) echo "" ;;
	esac
}
# htmode: uci -> 前端
htmode2bw() {
	case "$1" in
		HT40|VHT40|HE40) echo "40MHz" ;;
		HT80|VHT80|HE80) echo "80MHz" ;;
		HT160|VHT160|HE160) echo "160MHz" ;;
		*) echo "20MHz" ;;
	esac
}
# bw: 前端 -> uci（按 band 区分 2.4G HT / 5G VHT）
bw2htmode() {
	local band="$1" bw="$2"
	case "$bw" in
		40MHz) [ "$band" = "2g" ] && echo "HT40" || echo "VHT40" ;;
		80MHz) echo "VHT80" ;;
		160MHz) echo "VHT160" ;;
		*) [ "$band" = "2g" ] && echo "HT20" || echo "VHT20" ;;
	esac
}

# 频段能力（前端信道下拉 / 频宽按实际可设范围，不一股脑全列）：
#   b24 2.4G:   信道 1-13，频宽 20/40MHz
#   b52 5.2G:   信道 36-64（QCN9074 游戏频段），频宽 20/40/80/160MHz
#   b58 5.8G:   信道 149-165（板载 IPQ6018），频宽 20/40/80MHz（高端信道法规不支持 160）
band_caps() {
	case "$1" in
		b24) echo "chs=auto,1,2,3,4,5,6,7,8,9,10,11,12,13|bws=20MHz,40MHz" ;;
		b52) echo "chs=auto,36,40,44,48,52,56,60,64|bws=20MHz,40MHz,80MHz,160MHz" ;;
		b58) echo "chs=auto,149,153,157,161,165|bws=20MHz,40MHz,80MHz" ;;
	esac
}

emit_band() {
	local id="$1" idx="$2"
	local radio="radio$idx"
	[ "$(uci -q get "wireless.$radio" 2>/dev/null)" = "wifi-device" ] || { printf '{"id":"%s","on":false,"missing":true}' "$id"; return; }
	local disabled=$(uci -q get "wireless.$radio.disabled" 2>/dev/null)
	local ch=$(uci -q get "wireless.$radio.channel" 2>/dev/null); [ -z "$ch" ] && ch="auto"
	local htmode=$(uci -q get "wireless.$radio.htmode" 2>/dev/null)
	local iface=$(find_iface "$radio")
	local ssid=""; enc=""
	if [ -n "$iface" ]; then
		ssid=$(uci -q get "wireless.$iface.ssid" 2>/dev/null)
		enc=$(uci -q get "wireless.$iface.encryption" 2>/dev/null)
	fi
	local caps chs bws
	caps=$(band_caps "$id")
	chs="${caps#chs=}"; chs="${chs%%|*}"
	bws="${caps#*|bws=}"
	# 真实运行态：uci 只表示"是否禁用"，radio 可能因驱动/初始化失败而实际没起来，
	# 用 network.wireless status 的 up 字段校正，避免前台显示"已开启"却搜不到 SSID。
	local real_up="" real_check=false
	if command -v ubus >/dev/null 2>&1; then
		real_check=true
		real_up=$(ubus call network.wireless status 2>/dev/null | jsonfilter -e "@.$radio.up" 2>/dev/null)
	fi
	local on=true
	if [ "$disabled" = "1" ] || { [ "$real_check" = true ] && [ "$real_up" != "true" ]; }; then on=false; fi
	printf '{"id":"%s","on":%s,"ssid":"%s","ch":"%s","bw":"%s","enc":"%s","chs":"%s","bws":"%s","uci_off":%s,"radio_up":%s}' \
		"$id" "$on" \
		"$(printf '%s' "$ssid" | json_str)" "$ch" "$(htmode2bw "$htmode")" "$(uci2enc "$enc")" "$chs" "$bws" \
		"$([ "$disabled" = "1" ] && echo true || echo false)" \
		"$([ "$real_check" = true ] && [ "$real_up" != "true" ] && echo false || echo true)"
}

do_get() {
	local any_on=false idx disabled real_up
	for idx in 0 1 2; do
		[ "$(uci -q get "wireless.radio$idx" 2>/dev/null)" = "wifi-device" ] || continue
		disabled=$(uci -q get "wireless.radio$idx.disabled" 2>/dev/null)
		[ "$disabled" = "1" ] && continue
		real_up=""
		if command -v ubus >/dev/null 2>&1; then
			real_up=$(ubus call network.wireless status 2>/dev/null | jsonfilter -e "@.radio$idx.up" 2>/dev/null)
			[ "$real_up" = "true" ] || continue
		fi
		any_on=true
	done
	printf '{"ok":true,"on":%s,"bands":[' "$any_on"
	printf '%s,' "$(emit_band b24 1)"
	printf '%s,' "$(emit_band b52 2)"
	printf '%s]}' "$(emit_band b58 0)"
}

do_switch() {
	local action="$1" target="$2"
	local radios=""
	case "$target" in all|b24|b52|b58) ;; *) echo '{"ok":false,"msg":"目标频段无效"}'; exit 1 ;; esac
	if [ "$target" = "all" ]; then radios="0 1 2"; else radios="$(band_radio "$target")"; fi
	[ -n "$radios" ] || { echo '{"ok":false,"msg":"未找到目标无线设备"}'; exit 1; }
	for idx in $radios; do
		local radio="radio$idx"
		[ "$(uci -q get "wireless.$radio" 2>/dev/null)" = "wifi-device" ] || continue
		if [ "$action" = "enable" ]; then
			uci -q delete "wireless.$radio.disabled" 2>/dev/null
		else
			uci set "wireless.$radio.disabled=1"
		fi
	done
	uci commit wireless 2>/dev/null
	if [ "$action" = "enable" ]; then
		# 开启时显式 wifi up 目标 radio：仅 wifi reload 时部分频段（QCN9074 5.2G）
		# 首次上电不会真正拉起，表现为"显示已开启但搜不到"，需再开关一次才恢复
		for idx in $radios; do wifi up "radio$idx" >/dev/null 2>&1; done
		wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1
		for idx in $radios; do wifi up "radio$idx" >/dev/null 2>&1; done
	else
		wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1
	fi
	printf '{"ok":true,"msg":"无线已%s"}' "$([ "$action" = "enable" ] && echo 开启 || echo 关闭)"
}

do_set() {
	local band="$1" ssid="$2" pwd="$3" ch="$4" bw="$5" enc="$6"
	[ -z "$band" ] && { echo '{"ok":false,"msg":"缺少频段"}'; exit 1; }
	local idx=$(band_radio "$band"); [ -z "$idx" ] && { echo '{"ok":false,"msg":"未知频段"}'; exit 1; }
	local radio="radio$idx"
	[ "$(uci -q get "wireless.$radio" 2>/dev/null)" = "wifi-device" ] || { echo '{"ok":false,"msg":"无线设备不存在"}'; exit 1; }
	local iface=$(find_iface "$radio")
	[ -z "$iface" ] && { echo '{"ok":false,"msg":"无线接口不存在"}'; exit 1; }
	local band_type=$(uci -q get "wireless.$radio.band" 2>/dev/null)
	local enc_u=$(enc2uci "$enc")
	local ssid_bytes=$(printf '%s' "$ssid" | wc -c | tr -d ' ')
	[ "$ssid_bytes" -ge 1 ] && [ "$ssid_bytes" -le 32 ] || { echo '{"ok":false,"msg":"WiFi 名称长度必须为 1-32 字节"}'; exit 1; }
	printf '%s' "$ssid" | LC_ALL=C grep -q '[[:cntrl:]]' && { echo '{"ok":false,"msg":"WiFi 名称不能包含控制字符"}'; exit 1; }
	case "$band" in
		b24) case "$ch" in auto|1|2|3|4|5|6|7|8|9|10|11|12|13) ;; *) echo '{"ok":false,"msg":"2.4G 信道必须为 auto 或 1-13"}'; exit 1 ;; esac
			case "$bw" in 20MHz|40MHz) ;; *) echo '{"ok":false,"msg":"2.4G 仅支持 20/40MHz"}'; exit 1 ;; esac ;;
		b52) case "$ch" in auto|36|40|44|48|52|56|60|64) ;; *) echo '{"ok":false,"msg":"5.2G 信道必须为 auto 或 36-64 的标准信道"}'; exit 1 ;; esac
			case "$bw" in 20MHz|40MHz|80MHz|160MHz) ;; *) echo '{"ok":false,"msg":"5.2G 频宽无效"}'; exit 1 ;; esac ;;
		b58) case "$ch" in auto|149|153|157|161|165) ;; *) echo '{"ok":false,"msg":"5.8G 信道必须为 auto 或 149-165 的标准信道"}'; exit 1 ;; esac
			case "$bw" in 20MHz|40MHz|80MHz) ;; *) echo '{"ok":false,"msg":"5.8G 仅支持 20/40/80MHz"}'; exit 1 ;; esac ;;
	esac
	if [ -n "$pwd" ]; then
		pwd_bytes=$(printf '%s' "$pwd" | wc -c | tr -d ' ')
		[ "$pwd_bytes" -ge 8 ] && [ "$pwd_bytes" -le 63 ] || { echo '{"ok":false,"msg":"WiFi 密码长度必须为 8-63 字节"}'; exit 1; }
		printf '%s' "$pwd" | LC_ALL=C grep -q '[[:cntrl:]]' && { echo '{"ok":false,"msg":"WiFi 密码不能包含控制字符"}'; exit 1; }
	fi
	[ -n "$enc_u" ] || { echo '{"ok":false,"msg":"不支持的无线加密方式，请重新选择"}'; exit 1; }
	# 防呆：当前接口无密码（开放）且用户未填新密码 → 拒绝保存，避免继续以开放/无密码状态造成困惑
	local cur_key=$(uci -q get "wireless.$iface.key" 2>/dev/null)
	if [ "$enc_u" != "none" ] && [ -z "$pwd" ] && [ -z "$cur_key" ]; then
		echo '{"ok":false,"msg":"该频段当前无密码（开放网络），请填写新密码后再保存"}'
		exit 1
	fi
	uci set "wireless.$radio.channel=$ch" || { echo '{"ok":false,"msg":"信道配置写入失败"}'; exit 1; }
	uci set "wireless.$radio.htmode=$(bw2htmode "$band_type" "$bw")" || { echo '{"ok":false,"msg":"频宽配置写入失败"}'; exit 1; }
	uci set "wireless.$iface.ssid=$ssid" || { echo '{"ok":false,"msg":"WiFi 名称写入失败"}'; exit 1; }
	uci set "wireless.$iface.encryption=$enc_u" || { echo '{"ok":false,"msg":"加密方式写入失败"}'; exit 1; }
	if [ "$enc_u" = "none" ]; then
		uci -q delete "wireless.$iface.key" 2>/dev/null
	elif [ -n "$pwd" ]; then
		# 密码留空 = 不修改（保持原 key），避免前端默认值覆盖真机密码
		uci set "wireless.$iface.key=$pwd"
	fi
	uci commit wireless 2>/dev/null || { echo '{"ok":false,"msg":"无线配置提交失败"}'; exit 1; }
	wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1 || { echo '{"ok":false,"saved":true,"msg":"配置已保存，但无线重载失败"}'; exit 1; }
	echo '{"ok":true,"msg":"无线配置已保存并生效"}'
}

# ---- 恢复默认无线：生成随机强密码，避免通用默认口令 ----
do_reset_defaults() {
	local pass
	pass=$(od -An -N12 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n')
	[ "${#pass}" -eq 24 ] || { echo '{"ok":false,"msg":"无法生成安全 WiFi 密码"}'; exit 1; }
	for r in 0 1 2; do
		band=$(uci -q get "wireless.radio${r}.band" 2>/dev/null)
		[ -z "$band" ] && continue
		htmode=$(uci -q get "wireless.radio${r}.htmode" 2>/dev/null)
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
		uci -q delete "wireless.radio${r}.disabled" 2>/dev/null
		uci -q delete "wireless.radio${r}.channel" 2>/dev/null
		iface=$(uci -q show wireless 2>/dev/null | grep -E "\.device='radio${r}'$" | head -1 | sed "s/\.device=.*//")
		if [ -n "$iface" ]; then
			uci -q set "${iface}.ssid=$SSID"
			uci -q set "${iface}.encryption=psk2"
			uci -q set "${iface}.key=$pass"
			# 清除 WPA3 残留（PMF/SAE），避免手机按 WPA3 方式连接 WPA2 网络报"密码错误"
			uci -q delete "${iface}.ieee80211w" 2>/dev/null
		fi
	done
	uci commit wireless 2>/dev/null || { echo '{"ok":false,"msg":"无线默认配置提交失败"}'; exit 1; }
	wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1 || { echo '{"ok":false,"saved":true,"msg":"配置已保存，但无线重载失败"}'; exit 1; }
	printf '{"ok":true,"password":"%s","msg":"无线已恢复默认，已生成随机密码"}\\n' "$pass"
}

# ---- 访客网络（2.4G 多 BSS + guest 独立桥 + 防火墙隔离）----
guest_clear_internal() {
	uci -q delete "wireless.$GUEST_IFACE" 2>/dev/null
	uci -q delete "network.guest" 2>/dev/null
	uci -q delete "network.br_guest" 2>/dev/null
	uci -q delete "dhcp.guest" 2>/dev/null
	uci -q delete "firewall.guest_zone" 2>/dev/null
	uci -q delete "firewall.guest_fwd" 2>/dev/null
}

guest_get() {
	local en=false ssid="$GUEST_SSID"
	local iface=$(uci -q show wireless 2>/dev/null | grep -E "wireless\.[A-Za-z0-9_]+\.network='guest'$" | head -1 | cut -d. -f2 | cut -d= -f1)
	if [ -n "$iface" ]; then
		en=true
		local s=$(uci -q get "wireless.$iface.ssid" 2>/dev/null)
		[ -n "$s" ] && ssid="$s"
	fi
	printf '{"ok":true,"enabled":%s,"ssid":"%s"}' "$en" "$(printf '%s' "$ssid" | json_str)"
}

guest_enable() {
	local ssid="${1:-$GUEST_SSID}" pwd="${2:-}"
	local radio="radio1"
	SSID_BYTES=$(printf '%s' "$ssid" | wc -c | tr -d ' ')
	PWD_BYTES=$(printf '%s' "$pwd" | wc -c | tr -d ' ')
	[ "$SSID_BYTES" -ge 1 ] && [ "$SSID_BYTES" -le 32 ] || { echo '{"ok":false,"msg":"访客 WiFi 名称长度必须为 1-32 字节"}'; exit 1; }
	[ -n "$pwd" ] && [ "$PWD_BYTES" -ge 8 ] && [ "$PWD_BYTES" -le 63 ] || { echo '{"ok":false,"msg":"请设置 8-63 字节访客 WiFi 密码，不再使用通用默认密码"}'; exit 1; }
	printf '%s' "$ssid$pwd" | LC_ALL=C grep -q '[[:cntrl:]]' && { echo '{"ok":false,"msg":"访客 WiFi 名称或密码不能包含控制字符"}'; exit 1; }
	[ "$(uci -q get "wireless.$radio" 2>/dev/null)" = "wifi-device" ] || { echo '{"ok":false,"msg":"2.4G 无线设备不存在"}'; exit 1; }
	guest_clear_internal
	uci set "wireless.$GUEST_IFACE=wifi-iface"
	uci set "wireless.$GUEST_IFACE.device=$radio"
	uci set "wireless.$GUEST_IFACE.mode=ap"
	uci set "wireless.$GUEST_IFACE.ssid=$ssid"
	uci set "wireless.$GUEST_IFACE.encryption=psk2"
	uci set "wireless.$GUEST_IFACE.key=$pwd"
	uci set "wireless.$GUEST_IFACE.network=guest"
	uci set "wireless.$GUEST_IFACE.isolate=1"
	# guest 独立桥（无有线端口，仅挂无线 BSS；hostapd 会把 network=guest 的 iface 自动加入该桥）
	uci set "network.guest=interface"
	uci set "network.guest.proto=static"
	uci set "network.guest.device=br-guest"
	uci set "network.guest.ipaddr=$GUEST_IP"
	uci set "network.guest.netmask=255.255.255.0"
	uci add network device >/dev/null 2>&1
	uci set "network.@device[-1].name=br-guest"
	uci set "network.@device[-1].type=bridge"
	uci set "dhcp.guest=dhcp"
	uci set "dhcp.guest.interface=guest"
	uci set "dhcp.guest.start=100"
	uci set "dhcp.guest.limit=150"
	uci set "dhcp.guest.leasetime=12h"
	uci set "firewall.guest_zone=zone"
	uci set "firewall.guest_zone.name=guest"
	uci set "firewall.guest_zone.network=guest"
	uci set "firewall.guest_zone.input=REJECT"
	uci set "firewall.guest_zone.output=ACCEPT"
	uci set "firewall.guest_zone.forward=REJECT"
	uci set "firewall.guest_fwd=forwarding"
	uci set "firewall.guest_fwd.src=guest"
	uci set "firewall.guest_fwd.dest=wan"
	uci commit wireless 2>/dev/null; uci commit network 2>/dev/null; uci commit dhcp 2>/dev/null; uci commit firewall 2>/dev/null
	wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1
	/etc/init.d/dnsmasq restart >/dev/null 2>&1
	/etc/init.d/firewall restart >/dev/null 2>&1
	echo '{"ok":true,"msg":"访客网络已开启"}'
}

guest_disable() {
	guest_clear_internal
	uci commit wireless 2>/dev/null; uci commit network 2>/dev/null; uci commit dhcp 2>/dev/null; uci commit firewall 2>/dev/null
	wifi reload >/dev/null 2>&1 || /etc/init.d/network restart >/dev/null 2>&1
	/etc/init.d/dnsmasq restart >/dev/null 2>&1
	/etc/init.d/firewall restart >/dev/null 2>&1
	echo '{"ok":true,"msg":"访客网络已关闭"}'
}

case "$CMD" in
	get) do_get ;;
	enable) do_switch enable "${2:-all}" ;;
	disable) do_switch disable "${2:-all}" ;;
	set) do_set "$2" "$3" "$4" "$5" "$6" "$7" ;;
	reset-defaults) do_reset_defaults ;;
	guest)
		case "${2:-get}" in
			get) guest_get ;;
			enable) guest_enable "${3:-$GUEST_SSID}" "${4:-}" ;;
			disable) guest_disable ;;
			*) echo '{"ok":false,"msg":"未知 guest 子命令（get|enable|disable）"}'; exit 1 ;;
		esac
		;;
	*) echo '{"ok":false,"msg":"未知命令（支持 get|enable|disable|set|guest）"}'; exit 1 ;;
esac
