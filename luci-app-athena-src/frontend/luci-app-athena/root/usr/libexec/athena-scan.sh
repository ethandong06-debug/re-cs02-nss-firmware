#!/bin/sh
# AthenaWrt 一键体检
# 用法: athena-scan.sh
# 输出单行 JSON：逐项检查 WAN / DNS / 无线 / NSS / 磁盘 / 温度，给出 ok/warn/err 与建议

json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

ITEMS=""
SCORE=0; CNT=0
add() {
	local k="$1" status="$2" name="$3" detail="$4" ok=false
	[ "$status" = "ok" ] && ok=true
	case "$status" in
		ok) SCORE=$((SCORE+10)) ;;
		warn) SCORE=$((SCORE+5)) ;;
	esac
	CNT=$((CNT+1))
	[ -n "$ITEMS" ] && ITEMS="$ITEMS,"
	ITEMS="$ITEMS{\"key\":\"$k\",\"status\":\"$status\",\"ok\":$ok,\"name\":\"$(printf '%s' "$name" | json_str)\",\"detail\":\"$(printf '%s' "$detail" | json_str)\"}"
}

# 1. WAN 连接：优先按默认路由接口取地址，兼容 PPPoE、DHCP 与 VLAN 子接口。
WAN_DEV=$(uci -q get network.wan.device 2>/dev/null)
WAN_PROTO=$(uci -q get network.wan.proto 2>/dev/null)
WAN_IF=$(ip -4 route show default 2>/dev/null | awk 'NR==1 {for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}')
WAN_IP=""
for ifc in "$WAN_IF" pppoe-wan wan "$WAN_DEV"; do
	[ -n "$ifc" ] || continue
	WAN_IP=$(ip -4 -o addr show dev "$ifc" 2>/dev/null | awk 'NR==1 {print $4}')
	[ -n "$WAN_IP" ] && break
done
if [ -n "$WAN_IP" ]; then
	add wan ok "WAN 连接" "接口 ${WAN_IF:-$WAN_DEV} 已获取 IP：$WAN_IP（$WAN_PROTO）"
else
	add wan warn "WAN 连接" "未检测到 WAN IPv4 地址（协议 $WAN_PROTO），请检查拨号或上联"
fi

# 2. DNS
if nslookup www.qq.com >/dev/null 2>&1; then
	add dns ok "DNS 解析" "域名解析正常"
else
	add dns err "DNS 解析" "无法解析域名，检查 DNS 设置"
fi

# 3. 无线
RADIO_UP=0; RADIO_TOTAL=0
for r in $(uci -q show wireless 2>/dev/null | sed -n 's/^wireless\.\(radio[0-9]*\)=wifi-device$/\1/p'); do
	RADIO_TOTAL=$((RADIO_TOTAL+1))
	# 未设置 disabled（空）= 启用；显式 0 = 启用；仅显式 1 才算关闭
	dis=$(uci -q get "wireless.$r.disabled" 2>/dev/null)
	{ [ -z "$dis" ] || [ "$dis" = "0" ]; } && RADIO_UP=$((RADIO_UP+1))
done
if [ "$RADIO_TOTAL" -eq 0 ]; then
	add wifi warn "无线网络" "未检测到 radio，请检查无线驱动"
else
	add wifi ok "无线网络" "已启用 $RADIO_UP/$RADIO_TOTAL 个射频"
fi

# 4. NSS/ECM 模块状态：只报告模块是否加载，不虚构实时硬件卸载命中率。
NSS_DP=0; ECM_LOADED=0
grep -q '^qca_nss_dp ' /proc/modules 2>/dev/null && NSS_DP=1
grep -qE '^(ecm|qca_nss_ecm) ' /proc/modules 2>/dev/null && ECM_LOADED=1
if [ "$NSS_DP" = "1" ] && [ "$ECM_LOADED" = "1" ]; then
	add nss ok "NSS/ECM 模块" "NSS-DP 与 ECM 核心模块已加载；此项不代表每条流量均命中硬件卸载"
else
	add nss warn "NSS/ECM 模块" "未同时检测到 NSS-DP 与 ECM 核心模块，请检查固件模块状态"
fi

# 5. 存储（eMMC / USB 挂载）
STORAGE_COUNT=$(grep -cE " /(mnt|overlay|data)" /proc/mounts 2>/dev/null)
[ "$STORAGE_COUNT" -gt 0 ] && add disk ok "存储挂载" "检测到 $STORAGE_COUNT 个存储挂载点" || add disk warn "存储挂载" "无外置存储挂载"

# 6. 温度
TEMP=0
for f in /sys/class/thermal/thermal_zone*/temp; do
	[ -r "$f" ] || continue
	t=$(cat "$f" 2>/dev/null)
	[ -n "$t" ] && [ "$t" -gt "$TEMP" ] 2>/dev/null && TEMP=$t
done
TEMP=$((TEMP/1000))
if [ "$TEMP" -le 0 ]; then
	add temp ok "芯片温度" "传感器未上报（被动散热）"
elif [ "$TEMP" -lt 80 ]; then
	add temp ok "芯片温度" "${TEMP}°C，正常"
else
	add temp warn "芯片温度" "${TEMP}°C，偏高"
fi

[ "$CNT" -gt 0 ] 2>/dev/null && SCORE=$((SCORE/CNT))
echo "{\"ok\":true,\"score\":$SCORE,\"items\":[$ITEMS]}"
