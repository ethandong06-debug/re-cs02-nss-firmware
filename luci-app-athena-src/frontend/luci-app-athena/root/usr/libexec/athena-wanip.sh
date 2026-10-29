#!/bin/sh
# ============================================================
#  AthenaWrt — 公网 IP / 运营商查询（v1.2.52）
#  用途：概览页"外网 IP"、拓扑"互联网"节点、测速按运营商选源
#  特点：纯 HTTP（无 TLS 开销，A53 上快）；结果缓存 10 分钟；
#        缓存过期时先返回旧值并在后台刷新，绝不阻塞页面。
#  用法：
#    athena-wanip.sh get        {"ip":"27.10.61.56","isp":"联通","age":12,"stale":0}
#    athena-wanip.sh refresh    强制刷新（阻塞，手动按钮用）
# ============================================================

CACHE=/tmp/athena-wanip.json
STAMP=/tmp/athena-wanip.stamp
LOCK=/var/run/athena-wanip.lock
TTL=600

json_esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
now() { date +%s; }

# 运营商英文名 → 中文短名（测速选源与界面显示用）
isp_cn() {
	case "$1" in
		*[Uu]nicom*) echo "联通" ;;
		*[Tt]elecom*|*Chinanet*) echo "电信" ;;
		*[Mm]obile*|*CMCC*) echo "移动" ;;
		*[Bb]roadnet*|*[Gg]uangdian*) echo "广电" ;;
		*[Ee]ducation*|*[Cc]ernet*) echo "教育网" ;;
		'') echo "" ;;
		*) echo "$1" ;;
	esac
}

fetch_now() {
	local ip="" isp="" raw
	ip=$(curl -s -m 5 http://ip.3322.net 2>/dev/null | tr -d '\r\n ')
	case "$ip" in ''|*[!0-9.]*) ip="" ;; esac
	if [ -z "$ip" ]; then
		ip=$(curl -s -m 5 http://members.3322.org/dyndns/getip 2>/dev/null | tr -d '\r\n ')
		case "$ip" in ''|*[!0-9.]*) ip="" ;; esac
	fi
	if [ -z "$ip" ]; then
		ip=$(curl -s -m 5 http://api.ipify.org 2>/dev/null | tr -d '\r\n ')
		case "$ip" in ''|*[!0-9.]*) ip="" ;; esac
	fi
	[ -z "$ip" ] && [ -f "$CACHE" ] && ip=$(sed -n 's/.*"ip":"\([^"]*\)".*/\1/p' "$CACHE")
	if [ -n "$ip" ]; then
		raw=$(curl -s -m 5 "http://ip-api.com/line/$ip?fields=isp" 2>/dev/null | tr -d '\r\n')
		isp=$(isp_cn "$raw")
	fi
	printf '{"ip":"%s","isp":"%s","ts":%s}' "$(json_esc "$ip")" "$(json_esc "$isp")" "$(now)" > "$CACHE.tmp"
	mv "$CACHE.tmp" "$CACHE"
	now > "$STAMP"
}

warm() {
	mkdir "$LOCK" 2>/dev/null || return 0
	( fetch_now >/dev/null 2>&1; rmdir "$LOCK" 2>/dev/null ) &
}

# 死锁自愈：锁目录存在但进程没了、或超过 120 秒
if [ -d "$LOCK" ]; then
	_pid=$(cat "$LOCK/pid" 2>/dev/null)
	_age=$(( $(now) - $(cat "$LOCK/since" 2>/dev/null || echo 0) ))
	if [ -n "$_pid" ] && ! kill -0 "$_pid" 2>/dev/null; then rmdir "$LOCK" 2>/dev/null
	elif [ "$_age" -gt 120 ] 2>/dev/null; then rmdir "$LOCK" 2>/dev/null; fi
fi

case "${1:-get}" in
	get)
		age=0
		[ -f "$STAMP" ] && age=$(( $(now) - $(cat "$STAMP" 2>/dev/null || echo 0) ))
		if [ -s "$CACHE" ]; then
			if [ "$age" -gt "$TTL" ] 2>/dev/null; then warm; stale=1; else stale=0; fi
			printf '%s\n' "$(cat "$CACHE")" | sed "s/}$/, \"age\":$age, \"stale\":$stale}/"
		else
			warm
			echo '{"ip":"","isp":"","age":0,"stale":1,"note":"正在后台查询公网 IP"}'
		fi
		;;
	refresh)
		fetch_now
		printf '%s\n' "$(cat "$CACHE")" | sed 's/}$/, "age":0, "stale":0}/'
		;;
	*)
		echo '{"ok":false,"msg":"usage: get|refresh"}'
		exit 1
		;;
esac
