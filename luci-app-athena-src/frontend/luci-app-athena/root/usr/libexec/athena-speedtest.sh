#!/bin/sh
# ============================================================
#  AthenaWrt 网络测速（v1.2.52 重写）
#
#  为什么改：
#   1) 旧版 4 路并发 curl 全是 HTTPS，A53 四核做 TLS 解密本身就顶到 ~1.3Gbps，
#      2000M 线路也会被算成 1300；且旧版只取「最快那一路」的全程平均值，
#      把 TCP 慢启动也平均进去了 → 双重低估。
#   2) 旧版节点选择是假的：case 只认 cloudflare/tuna/sh-ct，选"重庆联通"也会落到同一组 URL。
#
#  现在：
#   - 引擎一：iperf3（信通院 speedtest.cata.net，固件自带 /usr/bin/iperf3）
#   - 引擎二：纯 HTTP 多流（163/中科大/清华/华为云/腾讯/阿里，无 TLS）
#   - 计量：直接读 WAN 网卡的 /proc/net/dev 字节计数，取 3 秒峰值窗口，
#     不受单个 curl 进程 CPU 限制影响（NSS 卸载的字节同样计入网卡统计）
#   - 选源：按公网 IP 归属运营商（athena-wanip.sh）排序，自动/手动可选
#
#  用法：
#    athena-speedtest.sh auto            自动（默认）
#    athena-speedtest.sh iperf3          只用信通院 iperf3
#    athena-speedtest.sh mirrors         只用公共镜像多流
#    athena-speedtest.sh unit get|set X  网速显示单位（存 athena-prefs，uci 仅镜像）
#  输出：单行 JSON
# ============================================================

CMD="${1:-auto}"
PREFS=/usr/libexec/athena-prefs.sh
WANIP=/usr/libexec/athena-wanip.sh
json_esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

# ---------- 单位（存文件，uci 只镜像；实测 uci commit 会报 Invalid argument） ----------
if [ "$CMD" = "unit" ]; then
	SUB="${2:-get}"
	case "$SUB" in
		get)
			U=$(/usr/libexec/athena-prefs.sh get speed_unit 2>/dev/null)
			[ -z "$U" ] && U=$(uci -q get athena.speedtest.unit 2>/dev/null)
			case "$U" in Mbps|MB/s) ;; *) U="Mbps" ;; esac
			echo "{\"ok\":true,\"unit\":\"$U\"}"
			;;
		set)
			U="${3:-}"
			case "$U" in Mbps|MB/s) ;; *) echo '{"ok":false,"msg":"单位仅支持 Mbps|MB/s"}'; exit 1 ;; esac
			/usr/libexec/athena-prefs.sh set speed_unit "$U" >/dev/null 2>&1
			uci -q set athena.speedtest.unit="$U" 2>/dev/null
			uci -q commit athena 2>/dev/null
			echo "{\"ok\":true,\"unit\":\"$U\"}"
			;;
		*)
			echo '{"ok":false,"msg":"未知 unit 子命令（get|set）"}'
			exit 1
			;;
	esac
	exit 0
fi

# ---------- 时延 / 抖动（223.5.5.5 在重庆联通实测可用；失败退回默认网关） ----------
# BusyBox ping -q 只输出 min/avg/max，没有 mdev；抖动用 max-avg 近似，界面上标注"估"。
ping_stats() {
	ping -c 5 -q "$1" 2>/dev/null | awk '/min\/avg\/max/{
		if (match($0, /[0-9.]+\/[0-9.]+\/[0-9.]+/)) {
			s = substr($0, RSTART, RLENGTH); n = split(s, a, "/");
			if (n >= 2) printf "%.3f %.3f", a[2], (n >= 3 ? a[3] - a[2] : 0);
		}
		exit
	}'
}
PING_HOST="223.5.5.5"
RTT=$(ping_stats "$PING_HOST")
if [ -z "$RTT" ]; then
	_gw=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')
	[ -n "$_gw" ] && { PING_HOST="$_gw"; RTT=$(ping_stats "$_gw"); }
fi
AVG_MS=$(printf '%s' "$RTT" | awk '{print ($1 == "" ? 0 : $1)}')
JITTER_MS=$(printf '%s' "$RTT" | awk '{print ($2 == "" ? 0 : $2)}')
# ---------- WAN 网卡（默认路由出口；单臂下是 pppoe-wan） ----------
IFACE=$(ip route get 223.5.5.5 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p' | head -1)
[ -z "$IFACE" ] && IFACE=pppoe-wan
rx_bytes() { awk -v i="$IFACE" 'index($1, i ":") > 0 { print $2; exit }' /proc/net/dev 2>/dev/null; }

# ---------- 公网 IP / 运营商（用缓存，不阻塞） ----------
ISP=$(/usr/libexec/athena-wanip.sh get 2>/dev/null | sed -n 's/.*"isp":"\([^"]*\)".*/\1/p')

# ---------- 测速源（纯 HTTP；已在本机实测均返回 200，ISO 6.5GB 足够跑满） ----------
SRC_TENCENT="http://dldir1.qq.com/weixin/Windows/WeChatSetup.exe"
SRC_163="http://mirrors.163.com/ubuntu-releases/26.04/ubuntu-26.04-desktop-amd64.iso"
SRC_USTC="http://mirrors.ustc.edu.cn/ubuntu-releases/26.04/ubuntu-26.04-desktop-amd64.iso"
SRC_TUNA="http://mirrors.tuna.tsinghua.edu.cn/ubuntu-releases/26.04/ubuntu-26.04-desktop-amd64.iso"
SRC_HW="http://mirrors.huaweicloud.com/ubuntu-releases/26.04/ubuntu-26.04-desktop-amd64.iso"
SRC_ALI="http://mirrors.aliyun.com/ubuntu/ls-lR.gz"

sources_for() {
	case "$1" in
		联通) printf '%s\n' "$SRC_TENCENT" "$SRC_163" "$SRC_USTC" "$SRC_HW" "$SRC_TUNA" "$SRC_ALI" ;;
		电信) printf '%s\n' "$SRC_163" "$SRC_TENCENT" "$SRC_HW" "$SRC_USTC" "$SRC_ALI" "$SRC_TUNA" ;;
		移动) printf '%s\n' "$SRC_HW" "$SRC_TUNA" "$SRC_163" "$SRC_TENCENT" "$SRC_ALI" "$SRC_USTC" ;;
		*)    printf '%s\n' "$SRC_163" "$SRC_USTC" "$SRC_TUNA" "$SRC_HW" "$SRC_TENCENT" "$SRC_ALI" ;;
	esac
}

# ---------- 引擎：纯 HTTP 多流 + 网卡计数 ----------
measure_http() {
	rm -rf /tmp/athena-spd 2>/dev/null
	mkdir -p /tmp/athena-spd 2>/dev/null
	streams=0
	for u in $1; do
		[ -z "$u" ] && continue
		streams=$((streams + 1))
		curl -s -o /dev/null --max-time 14 "$u" >/dev/null 2>&1 &
	done
	[ "$streams" -eq 0 ] && return 0
	prev=$(rx_bytes); [ -z "$prev" ] && prev=0
	peak=0; tot=0; cnt=0; r1=0; r2=0; r3=0; t=0
	while [ "$t" -lt 12 ]; do
		sleep 1
		t=$((t + 1))
		cur=$(rx_bytes); [ -z "$cur" ] && cur=$prev
		d=$((cur - prev)); prev=$cur
		[ "$d" -lt 0 ] && d=0
		tot=$((tot + d)); cnt=$((cnt + 1))
		r3=$r2; r2=$r1; r1=$d
		if [ "$t" -ge 3 ]; then
			w=$(( (r1 + r2 + r3) * 8 * 10 / 3000000 ))
			[ "$w" -gt "$peak" ] && peak=$w
		fi
	done
	wait 2>/dev/null
	HTTP_PEAK=$peak          # Mbps ×10
	HTTP_AVG=0
	[ "$cnt" -gt 0 ] && HTTP_AVG=$(( tot * 8 * 10 / (cnt * 1000000) ))
	HTTP_STREAMS=$streams
	return 0
}

# ---------- 引擎：iperf3（信通院） ----------
measure_iperf3() {
	IPERF_MBPS=""; IPERF_NODE=""
	command -v iperf3 >/dev/null 2>&1 || return 0
	for node in speedtest.cata.net speedtest2.cata.net; do
		bps=$(iperf3 -c "$node" -p 5201 -t 6 -J --connect-timeout 2 2>/dev/null | grep -o '"bits_per_second":[0-9.]*' | tail -1 | cut -d: -f2)
		[ -z "$bps" ] && continue
		IPERF_MBPS=$(awk -v s="$bps" 'BEGIN{printf "%.1f", s/1000000}')
		IPERF_NODE=$node
		break
	done
	return 0
}

HTTP_PEAK=0; HTTP_AVG=0; HTTP_STREAMS=0
IPERF_MBPS=""; IPERF_NODE=""
ENGINE=""

case "$CMD" in
	iperf3)
		measure_iperf3
		NODE_NAME="中国信通院 iperf3"
		;;
	mirrors)
		measure_http "$(sources_for "$ISP")"
		NODE_NAME="公共镜像多流"
		;;
	*)
		# auto：先 iperf3（有就用），再 HTTP 多流；两者都测，取较高值
		measure_iperf3
		measure_http "$(sources_for "$ISP")"
		if [ -n "$ISP" ]; then NODE_NAME="自动（${ISP}优先）"; else NODE_NAME="自动"; fi
		;;
esac

# ---------- 汇总：取两者较高者 ----------
DL_X10=$HTTP_PEAK
DL_SRC="http"
if [ -n "$IPERF_MBPS" ]; then
	ip_x10=$(awk -v v="$IPERF_MBPS" 'BEGIN{printf "%d", v*10+0.5}')
	if [ "$ip_x10" -gt "$DL_X10" ]; then DL_X10=$ip_x10; DL_SRC="iperf3"; fi
fi
DL_INT=$((DL_X10 / 10)); DL_DEC=$((DL_X10 % 10))
AVG_INT=$((HTTP_AVG / 10)); AVG_DEC=$((HTTP_AVG % 10))
[ "$DL_SRC" = "iperf3" ] && ENGINE="iperf3"
if [ "$DL_SRC" = "http" ]; then
	if [ "$HTTP_PEAK" -gt 0 ]; then ENGINE="http-multi"; else ENGINE="none"; fi
fi

# ---------- 上传（iperf3，解析 sender 行；不可用则 null） ----------
UP_MBPS=""
if command -v iperf3 >/dev/null 2>&1; then
	for node in speedtest.cata.net speedtest2.cata.net; do
		line=$(iperf3 -c "$node" -p 5201 -t 3 --connect-timeout 2 2>/dev/null | grep -E 'sender$' | tail -1)
		[ -z "$line" ] && continue
		val=$(echo "$line" | awk '{print $(NF-2)}')
		unit=$(echo "$line" | awk '{print $(NF-1)}')
		case "$unit" in
			Mbits/sec) UP_MBPS=$(awk -v v="$val" 'BEGIN{printf "%.1f", v}') ;;
			Gbits/sec) UP_MBPS=$(awk -v v="$val" 'BEGIN{printf "%.1f", v*1000}') ;;
			Kbits/sec) UP_MBPS=$(awk -v v="$val" 'BEGIN{printf "%.1f", v/1000}') ;;
			*) continue ;;
		esac
		break
	done
fi

printf '{"ok":true,"download_mbps":%s.%s,"avg_mbps":%s.%s,"upload_mbps":%s,"ping_ms":%s,"jitter_ms":%s,"node":"%s","engine":"%s","streams":%s,"iface":"%s","isp":"%s","iperf3_mbps":%s}' \
	"$DL_INT" "$DL_DEC" "$AVG_INT" "$AVG_DEC" \
	"${UP_MBPS:-null}" "$AVG_MS" "$JITTER_MS" \
	"$(json_esc "$NODE_NAME")" "$ENGINE" "$HTTP_STREAMS" "$IFACE" "$(json_esc "$ISP")" \
	"${IPERF_MBPS:-null}"
