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

# 1. WAN 连接
WAN_DEV=$(uci -q get network.wan.device 2>/dev/null)
WAN_PROTO=$(uci -q get network.wan.proto 2>/dev/null)
WAN_IP=$(ip -4 addr show 2>/dev/null | grep -E "inet .* ${WAN_DEV:-wan}" | awk '{print $2}' | head -1)
if [ -n "$WAN_IP" ]; then
	add wan ok "WAN 连接" "已获取 IP：$WAN_IP（$WAN_PROTO）"
else
	add wan warn "WAN 连接" "未获取到外网 IP（协议 $WAN_PROTO），请检查拨号"
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
	local dis
	dis=$(uci -q get "wireless.$r.disabled" 2>/dev/null)
	{ [ -z "$dis" ] || [ "$dis" = "0" ]; } && RADIO_UP=$((RADIO_UP+1))
done
if [ "$RADIO_TOTAL" -eq 0 ]; then
	add wifi warn "无线网络" "未检测到 radio，请检查无线驱动"
else
	add wifi ok "无线网络" "三频已启用 $RADIO_UP/$RADIO_TOTAL"
fi

# 4. NSS 加速
if [ -x /etc/init.d/qca-nss-ecm ] || [ -x /etc/init.d/nss ]; then
	# 内核模块（nss_ecm / nss-dp）或用户态 ecm 进程任一存在即视为运行
	NSS_STATE=warn
	grep -qE 'nss_ecm|nss-dp' /proc/modules 2>/dev/null && NSS_STATE=ok
	pgrep -f 'qca-nss|/ecm|nss-ecm' >/dev/null 2>&1 && NSS_STATE=ok
	[ "$NSS_STATE" = "ok" ] && add nss ok "NSS 硬件加速" "加速引擎运行中" || add nss warn "NSS 硬件加速" "加速模块存在但未运行"
else
	add nss warn "NSS 硬件加速" "未检测到 NSS 模块（可能未集成）"
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
