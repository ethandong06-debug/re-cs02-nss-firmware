#!/bin/sh
# AthenaWrt 硬件状态聚合脚本 v2
# 把系统/CPU/内存/网速/无线/存储/端口/设备/点阵屏/LED 一次性聚合成 JSON
# 供 luci-app-athena 前端轮询（rpcd file exec 或直接调用）
# 输出：单行 JSON 到 stdout

# ---- 结果缓存（3 秒）+ 并发合并 ----
# 单次执行实测 real 1.66s / user 1.27s（要 fork 几十个进程），而前端多页面
# 轮询会并发调用，不合并就会把 CPU 吃掉。3 秒内重复请求直接复用上次结果。
SCACHE=/tmp/athena-status.json
SSTAMP=/tmp/athena-status.stamp
SLOCK=/var/run/athena-status.lock
if [ -s "$SCACHE" ]; then
	_oup=$(cat "$SSTAMP" 2>/dev/null)
	_now=$(cut -d. -f1 /proc/uptime)
	if [ -n "$_oup" ] && [ $((_now - _oup)) -lt 3 ] 2>/dev/null; then
		cat "$SCACHE"
		exit 0
	fi
fi
if mkdir "$SLOCK" 2>/dev/null; then
	SOWN=1
	trap 'rmdir "$SLOCK" 2>/dev/null' EXIT INT TERM HUP
else
	# 已有实例在算：等 1 秒读它的结果，避免重叠执行
	sleep 1
	if [ -s "$SCACHE" ]; then cat "$SCACHE"; exit 0; fi
	SOWN=0
fi

# ---- JSON 字符串转义 ----
json_str() {
	sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g; s/\r//g'
}

# ---- 系统信息 ----
HOSTNAME=$(cat /proc/sys/kernel/hostname 2>/dev/null)
MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
[ -z "$MODEL" ] && MODEL=$(cat /tmp/sysinfo/model 2>/dev/null)
[ -z "$MODEL" ] && MODEL="JDCloud RE-CS-02"
UPTIME=$(cut -d. -f1 /proc/uptime)
LOAD=$(cat /proc/loadavg 2>/dev/null | awk '{print $1","$2","$3}')
KERNEL=$(uname -r)
FIRMWARE=$(cat /etc/openwrt_release 2>/dev/null | sed -n 's/^DISTRIB_DESCRIPTION=//p' | tr -d '"')
[ -z "$FIRMWARE" ] && FIRMWARE="ImmortalWRT SNAPSHOT"
# 固件版本前缀：读编译期写入的 AthenaWrt 包版本，首页/维护页显示「AthenaWrt vX.Y.Z · 系统版本」
ATHENA_VER=$(cat /usr/libexec/athena-version 2>/dev/null | tr -d ' \t\r\n')
[ -n "$ATHENA_VER" ] && FIRMWARE="AthenaWrt v${ATHENA_VER} · ${FIRMWARE}"

# ---- CPU 温度（取所有 thermal zone 最高值）----
TEMP=0
for f in /sys/class/thermal/thermal_zone*/temp; do
	[ -r "$f" ] || continue
	t=$(cat "$f" 2>/dev/null)
	[ -n "$t" ] && [ "$t" -gt "$TEMP" ] 2>/dev/null && TEMP=$t
done
TEMP=$((TEMP/1000))

# ---- 内存 ----
MEMTOTAL=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
MEMAVAIL=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
MEMUSED=$((MEMTOTAL - MEMAVAIL))
MEMPCT=0
[ "$MEMTOTAL" -gt 0 ] 2>/dev/null && MEMPCT=$((MEMUSED * 100 / MEMTOTAL))

# ---- CPU 占用（/proc/stat 双采样；首次无缓存时用 loadavg 兜底）----
NCPU=$(grep -c '^processor' /proc/cpuinfo 2>/dev/null)
[ -z "$NCPU" ] || [ "$NCPU" -le 0 ] 2>/dev/null && NCPU=4
CPU_CACHE=/tmp/athena-cpu-cache
CPU_TOTAL=0
IDLE=0; TOTAL=0
# 口径：total = user+nice+system+idle+iowait+irq+softirq（不含 steal/guest，
# guest 已含在 user 里，重复累加会让分母虚增）；idle = idle+iowait
NOW_UP=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
if [ -f "$CPU_CACHE" ]; then
	read -r OLD_IDLE OLD_TOTAL OLD_UP OLD_PCT < "$CPU_CACHE" 2>/dev/null
	IDLE=$(awk '/^cpu /{print $5+$6}' /proc/stat)
	TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8}' /proc/stat)
	DIFF_T=$((TOTAL - ${OLD_TOTAL:-0}))
	DIFF_I=$((IDLE - ${OLD_IDLE:-0}))
	WIN=$(awk -v a="$NOW_UP" -v b="${OLD_UP:-0}" 'BEGIN{printf "%.0f", a-b}')
	# 采样窗口必须 ≥2s：窗口过短时 tick 差只有个位数，整数除法会把噪声放大成几十个百分点
	if [ "$DIFF_T" -ge 80 ] 2>/dev/null && [ "${WIN:-0}" -ge 2 ] 2>/dev/null; then
		CPU_TOTAL=$(( (DIFF_T - DIFF_I) * 100 / DIFF_T ))
	elif [ -n "$OLD_PCT" ] 2>/dev/null; then
		CPU_TOTAL=${OLD_PCT:-0}
	fi
	[ "$CPU_TOTAL" -gt 100 ] 2>/dev/null && CPU_TOTAL=100
	[ "$CPU_TOTAL" -lt 0 ] 2>/dev/null && CPU_TOTAL=0
else
	LOAD1=$(echo "$LOAD" | cut -d',' -f1)
	CPU_TOTAL=$(awk -v l="$LOAD1" -v n="$NCPU" 'BEGIN{printf "%.0f", l/n*100}')
	[ "$CPU_TOTAL" -gt 100 ] 2>/dev/null && CPU_TOTAL=100
	IDLE=$(awk '/^cpu /{print $5+$6}' /proc/stat)
	TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8}' /proc/stat)
fi
echo "$IDLE $TOTAL ${NOW_UP:-0} $CPU_TOTAL" > "$CPU_CACHE" 2>/dev/null

# ---- 实时网速（两次采样差值 → Mbps）----
# 时间戳用 /proc/uptime 的浮点秒（busybox date 不支持 %N，勿用 date +%s%N）
# 上游接口口径（避免 br-lan 与 wlan* 重复累计导致网速虚高）：
#   router -> wan（物理 WAN 口）；single -> network.wan.device（v1.2.11 起原 wan 直接挂 wan.$拨号VLAN）；
#   ap / bypass -> br-lan（LAN 桥即互联网方向）
NET_CACHE=/tmp/athena-net-cache
NOW_S=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
NOW_S=$(echo "$NOW_S" | cut -d. -f1)
[ -z "$NOW_S" ] && NOW_S=$(date +%s)
MODE_X=$(uci -q get athena.system.mode 2>/dev/null); [ -z "$MODE_X" ] && MODE_X="router"
NETIF=$(uci -q get network.wan.device 2>/dev/null)
case "$MODE_X" in
	ap|bypass) NETIF="br-lan" ;;
esac
[ -z "$NETIF" ] && NETIF="wan"
RX=$(awk -v ifc="$NETIF:" 'NR>2 && $1==ifc {r+=$2} END{print r+0}' /proc/net/dev)
TX=$(awk -v ifc="$NETIF:" 'NR>2 && $1==ifc {t+=$10} END{print t+0}' /proc/net/dev)

# 单臂/拨号模式下流量也可能统计在 pppoe-wan（PPP 接口，统计字节大于二层承载），
# 回退取两者较大值，避免"网速无法显示"
if [ -e "/sys/class/net/pppoe-wan" ]; then
	RX2=$(awk -v ifc="pppoe-wan:" 'NR>2 && $1==ifc {r+=$2} END{print r+0}' /proc/net/dev)
	TX2=$(awk -v ifc="pppoe-wan:" 'NR>2 && $1==ifc {t+=$10} END{print t+0}' /proc/net/dev)
	{ [ "$RX2" -gt "$RX" ]; } 2>/dev/null && RX=$RX2
	{ [ "$TX2" -gt "$TX" ]; } 2>/dev/null && TX=$TX2
fi

RX_RATE=0; TX_RATE=0
if [ -f "$NET_CACHE" ]; then
	OLD_S=$(awk '{print $1}' "$NET_CACHE")
	OLD_RX=$(awk '{print $2}' "$NET_CACHE")
	OLD_TX=$(awk '{print $3}' "$NET_CACHE")
	DT=$((NOW_S - OLD_S))
	if [ "$DT" -gt 0 ]; then
		# 字节差值 * 8 / 1e6 = Mbps，再除以秒
		RX_RATE=$(awk -v dr=$((RX-OLD_RX)) -v dt=$DT 'BEGIN{printf "%.1f", dr*8/1000000/dt}')
		TX_RATE=$(awk -v dr=$((TX-OLD_TX)) -v dt=$DT 'BEGIN{printf "%.1f", dr*8/1000000/dt}')
	fi
fi
echo "$NOW_S $RX $TX" > "$NET_CACHE"
# 修正负值/异常（接口重置/重启/首次采样）
echo "$RX_RATE" | grep -q '^-' && RX_RATE=0
echo "$TX_RATE" | grep -q '^-' && TX_RATE=0

# ---- 无线三频（原始 ubus JSON，前端解析）----
WIRELESS=$(ubus call network.wireless status 2>/dev/null)
[ -z "$WIRELESS" ] && WIRELESS='{}'

# ---- 存储（块设备 + 挂载点）----
STORAGE=""
for dev in /sys/block/mmcblk* /sys/block/sd* /sys/block/nvme*; do
	[ -d "$dev" ] || continue
	name=$(basename "$dev")
	size_sectors=$(cat "$dev/size" 2>/dev/null || echo 0)
	size_mb=$((size_sectors/2048))
	[ "$size_mb" -le 0 ] && continue
	# 挂载点探测（mmcblk0p1 / sda1 等）
	mount=""
	fs=""
	for part in /sys/block/$name/${name}p* /sys/block/$name/${name}*; do
		[ -e "$part" ] || continue
		pname=$(basename "$part")
		mp=$(grep -E " /dev/$pname " /proc/mounts 2>/dev/null | awk '{print $2}')
		if [ -n "$mp" ]; then
			mount="$mp"
			fs=$(grep -E " /dev/$pname " /proc/mounts 2>/dev/null | awk '{print $3}')
			break
		fi
	done
	[ -z "$mount" ] && mount=$(grep -E " /dev/$name " /proc/mounts 2>/dev/null | awk '{print $2}')
	used_mb=0
	if [ -n "$mount" ]; then
		used_mb=$(df -m "$mount" 2>/dev/null | awk 'NR==2{print $3}')
	fi
	STORAGE="$STORAGE{\"name\":\"$name\",\"size_mb\":$size_mb,\"used_mb\":${used_mb:-0},\"mount\":\"$(echo "$mount" | json_str)\",\"fs\":\"$fs\"},"
done
STORAGE=$(echo "$STORAGE" | sed 's/,$//')

# ---- 端口速率（只输出物理口 wan/lan1-4，过滤虚拟接口 br-lan*/wlan* 等）----
PORTS=""
for n in wan lan1 lan2 lan3 lan4; do
	[ -e "/sys/class/net/$n" ] || continue
	speed=$(cat "/sys/class/net/$n/speed" 2>/dev/null || echo 0)
	state=$(cat "/sys/class/net/$n/operstate" 2>/dev/null)
	PORTS="$PORTS{\"name\":\"$n\",\"speed\":${speed:-0},\"state\":\"$state\"},"
done
PORTS=$(echo "$PORTS" | sed 's/,$//')

# ---- 设备厂商识别（内置常见 OUI，前缀匹配）----
vendor_of() {
	mac=$(echo "$1" | tr 'a-f' 'A-F')
	case "$mac" in
		3C:22:FB:*|38:CA:DA:*|F0:18:98:*|8C:85:90:*|A4:83:E7:*) echo "Apple" ;;
		C0:EE:FB:*|D0:57:7B:*|E4:5F:01:*|70:B3:D5:*|AC:37:43:*|F0:1F:AF:*) echo "小米" ;;
		24:69:68:*|68:3E:34:*|28:6C:07:*|E0:19:1D:*|84:2B:2B:*|A0:91:A2:*) echo "华为" ;;
		00:1A:2B:*|E4:F4:C6:*|C8:3A:35:*|6C:70:9F:*|FC:D7:33:*|7C:76:35:*) echo "TP-Link" ;;
		14:DA:E9:*|E8:48:B8:*|DC:72:9B:*|F0:2F:74:*) echo "华硕" ;;
		04:D9:F5:*|48:4D:7E:*|A8:87:92:*|64:09:80:*|C0:25:2F:*) echo "三星" ;;
		00:25:9C:*|04:CF:8C:*|54:48:E6:*|B0:C5:54:*|F8:FF:C2:*) echo "索尼" ;;
		*) echo "未知设备" ;;
	esac
}

# ---- 客户端清单（dhcp leases + hostapd 关联 + ARP 在线判定）----
# 1) hostapd 关联表 → 无线在线 MAC + 频段映射（MAC 统一小写）
BAND_MAP=""       # " mac=band "
WIFI_ONLINE=""    # " mac "
for ap in /var/run/hostapd/*; do
	[ -e "$ap" ] || continue
	phyname=$(basename "$ap")
	band=$(iwinfo "$phyname" info 2>/dev/null | grep -oE '2\.4[0-9]* GHz|5\.[0-9]* GHz' | head -1)
	for client in $(grep -oE '^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}' "$ap" 2>/dev/null | sort -u); do
		c=$(echo "$client" | tr 'A-F' 'a-f')
		BAND_MAP="$BAND_MAP $c=$band"
		WIFI_ONLINE="$WIFI_ONLINE $c "
	done
done

# 2) ARP 表 → 活跃 MAC（有线设备/最近有通信；排除全 0 与 incomplete）
ARP_ONLINE=""
while read -r ip t flags mac rest; do
	[ -n "$mac" ] || continue
	[ "$mac" = "00:00:00:00:00:00" ] && continue
	[ "$flags" = "0x0" ] && continue
	ARP_ONLINE="$ARP_ONLINE $(echo "$mac" | tr 'A-F' 'a-f') "
done < /proc/net/arp 2>/dev/null

# 3) 在线时长 / 掉线时间戳（tmpfs 状态文件：设备在线起始与最后掉线时刻，重启自动清空，不磨损 flash）
# 状态文件行格式: <mac> <first_seen_epoch> <last_down_epoch>
#   - 首次在线 / 重新上线（曾有 last_down）：first_seen 重置为当前，连接时长重新累计
#   - 持续在线：沿用 first_seen，uptime_s = now - first_seen
#   - 离线：记录 last_down = now（前端显示"X 前掉线"）；last_down 为 0 表示从未在线/从未掉线
DEVSTATE=/tmp/athena-devs
NOW_EPOCH=$(date +%s 2>/dev/null)
: > "$DEVSTATE.new" 2>/dev/null
devstate() {  # $1=mac $2=online(1/0)；输出 "uptime_s last_down" 并写状态
	local mac="$1" on="$2"
	local FIRST=0 LAST_DOWN=0 ST="" UPT=0
	ST=$(grep "^$mac " "$DEVSTATE" 2>/dev/null | head -1)
	if [ -n "$ST" ]; then
		FIRST=$(echo "$ST" | awk '{print $2}')
		LAST_DOWN=$(echo "$ST" | awk '{print $3}')
	fi
	if [ "$on" = "1" ]; then
		if [ -z "$FIRST" ] || [ "$FIRST" -le 0 ] 2>/dev/null || { [ -n "$LAST_DOWN" ] && [ "$LAST_DOWN" -gt 0 ] 2>/dev/null; }; then
			FIRST="$NOW_EPOCH"
		fi
		LAST_DOWN=0
		UPT=$((NOW_EPOCH - FIRST))
	else
		if [ -n "$FIRST" ] && [ "$FIRST" -gt 0 ] 2>/dev/null; then
			LAST_DOWN="$NOW_EPOCH"
		fi
		UPT=0
	fi
	echo "$mac $FIRST $LAST_DOWN" >> "$DEVSTATE.new"
	echo "$UPT $LAST_DOWN"
}

CLIENTS=""
SEEN=""
while IFS= read -r line; do
	[ -n "$line" ] || continue
	# lease 格式: 剩余秒数 mac ip hostname clientid
	mac=$(echo "$line" | awk '{print $2}' | tr 'A-F' 'a-f')
	ip=$(echo "$line" | awk '{print $3}')
	host=$(echo "$line" | awk '{print $4}')
	[ "$host" = "*" ] && host=""
	[ -z "$mac" ] && continue
	# 在线判定：hostapd 关联（无线）或 ARP 活跃（有线）
	online=false
	case "$WIFI_ONLINE" in *" $mac "*) online=true ;; esac
	case "$ARP_ONLINE" in *" $mac "*) online=true ;; esac
	[ "$online" = "true" ] && ON=1 || ON=0
	DS=$(devstate "$mac" "$ON")
	UPT=$(echo "$DS" | awk '{print $1}')
	LD=$(echo "$DS" | awk '{print $2}')
	# 频段
	band=$(echo "$BAND_MAP" | tr ' ' '\n' | grep "^$mac=" | sed "s/^$mac=//" | head -1)
	[ -z "$band" ] && band="有线"
	vendor=$(vendor_of "$mac")
	CLIENTS="$CLIENTS{\"ip\":\"$ip\",\"mac\":\"$mac\",\"hostname\":\"$(echo "$host" | json_str)\",\"band\":\"$band\",\"online\":$online,\"uptime_s\":$UPT,\"last_down\":$LD,\"vendor\":\"$vendor\"},"
	SEEN="$SEEN $mac "
done < /tmp/dhcp.leases 2>/dev/null

# 补充：ARP 在线但未在 DHCP lease 中的设备（静态 IP / 光猫回传口设备）
while read -r ip t flags mac rest; do
	[ -n "$mac" ] || continue
	[ "$mac" = "00:00:00:00:00:00" ] && continue
	[ "$flags" = "0x0" ] && continue
	mac=$(echo "$mac" | tr 'A-F' 'a-f')
	case "$SEEN" in *" $mac "*) continue ;; esac
	DS=$(devstate "$mac" "1")
	UPT=$(echo "$DS" | awk '{print $1}')
	LD=$(echo "$DS" | awk '{print $2}')
	vendor=$(vendor_of "$mac")
	CLIENTS="$CLIENTS{\"ip\":\"$ip\",\"mac\":\"$mac\",\"hostname\":\"\",\"band\":\"有线\",\"online\":true,\"uptime_s\":$UPT,\"last_down\":$LD,\"vendor\":\"$vendor\"},"
	SEEN="$SEEN $mac "
done < /proc/net/arp 2>/dev/null
CLIENTS=$(echo "$CLIENTS" | sed 's/,$//')
# 状态文件替换（tmpfs 原子替换，避免读半行；空结果不覆盖，防止 dnsmasq/ARP 瞬时为空丢全部时长）
[ -s "$DEVSTATE.new" ] && mv "$DEVSTATE.new" "$DEVSTATE" 2>/dev/null

# ---- 点阵屏 / 模式 配置（读真实驱动 athena_led.general.*，与 athena-matrix.sh 对齐）----
g() { uci -q get "$1" 2>/dev/null; }
MT_ENABLED=$([ "$(g athena_led.general.enabled)" = "1" ] && echo true || echo false)
MT_LEVEL=$(g athena_led.general.light_level); [ -z "$MT_LEVEL" ] && MT_LEVEL=5
MT_NIGHT=$([ "$(g athena_led.general.night_light_enable)" = "1" ] && echo true || echo false)
MT_PROFILE=$(g athena_led.general.profile_mode); [ -z "$MT_PROFILE" ] && MT_PROFILE="multi"
MT_NS=$(g athena_led.general.night_start); [ -z "$MT_NS" ] && MT_NS="22:00"
MT_NE=$(g athena_led.general.night_end); [ -z "$MT_NE" ] && MT_NE="07:00"
MT_NL=$(g athena_led.general.night_light_level); [ -z "$MT_NL" ] && MT_NL=1
MT_CK=$([ "$(g athena_led.general.disable_led_clock)" = "1" ] && echo false || echo true)
MT_MD=$([ "$(g athena_led.general.disable_led_medal)" = "1" ] && echo false || echo true)
MT_UP=$([ "$(g athena_led.general.disable_led_up)" = "1" ] && echo false || echo true)
MT_DN=$([ "$(g athena_led.general.disable_led_down)" = "1" ] && echo false || echo true)
MODE=$(g athena.system.mode); [ -z "$MODE" ] && MODE="router"

# ---- WAN 配置回读（供前端组网/单臂表单回填，避免"已设账号密码又变默认"）----
# 判定顺序：
#   1) network.wan.username 有值 → 必为 PPPoE（static 用的是 ip/mask/gw，不用 username；避免 athena.single 残留 dhcp 覆盖）
#   2) network.wan.proto 有值 → 取实际生效值（dhcp/static/pppoe 均有效）
#   3) 兜底读 athena.single.wan_proto（老单臂配置），仍缺省则 pppoe
if [ -n "$(g network.wan.username)" ]; then
	WAN_PROTO="pppoe"
else
	NW_PROTO=$(g network.wan.proto)
	if [ -n "$NW_PROTO" ]; then
		WAN_PROTO="$NW_PROTO"
	else
		WAN_PROTO=$(g athena.single.wan_proto); [ -z "$WAN_PROTO" ] && WAN_PROTO="pppoe"
	fi
fi
WAN_USER=$(g network.wan.username); [ -z "$WAN_USER" ] && WAN_USER=""
WAN_PWD=$(g network.wan.password); [ -z "$WAN_PWD" ] && WAN_PWD=""
WAN_DEVICE=$(g network.wan.device); [ -z "$WAN_DEVICE" ] && WAN_DEVICE="wan"
# 直接查 WAN_DEVICE（单臂时为 br-lan.$wan_vlan，主路由时为 wan）
WAN_IP=$(ip -4 addr show dev "$WAN_DEVICE" 2>/dev/null | awk '/inet /{print $2; exit}')
# 静态 IP 配置回读（供前端主路由/单臂静态表单回填，避免"已设 IP 又变默认"）
WAN_SIP=$(g network.wan.ipaddr); WAN_SMASK=$(g network.wan.netmask); WAN_SGW=$(g network.wan.gateway)
WAN_SDNS=$(g network.wan.dns)
# 单臂 VLAN 回读：未配置默认 2044；显式配置为空（关闭回传）则保持空串，供前端精确回填
WAN_VLAN=$(g athena.single.wan_vlan); [ -z "$WAN_VLAN" ] && WAN_VLAN="2044"
# 单臂 VLAN 回读：config_single 写入 athena.single.inner_vlan（前端表单回填用 ret_vlan 字段，值同源）
if uci -q get athena.single.inner_vlan >/dev/null 2>&1; then RET_VLAN=$(uci -q get athena.single.inner_vlan); else RET_VLAN="1"; fi
IPTV_VLAN=$(g athena.single.iptv_vlan)
# 真机兼容：athena.single 无 iptv_vlan 字段但实际存在 IPTV（br-iptv 桥 + wan.X 子接口）时，
# 从 br-iptv 桥成员里的 wan.X 探测 VID（与 status_single 同源），避免前端误判"IPTV 未开启"而删配置
if [ -z "$IPTV_VLAN" ]; then
	IPTV_VLAN=$(uci -q show network 2>/dev/null | sed -n "s/^network\.\(@device\[[0-9]*\]\)\.ports='lan4' 'wan\.\([0-9]*\)'$/\2/p" | head -1)
fi
IPTV_PORT=$(g athena.single.iptv_port); [ -z "$IPTV_PORT" ] && IPTV_PORT="lan4"

# ---- 组装 JSON（写入缓存，供并发/多页面复用）----
cat <<EOF > "$SCACHE.tmp"
{"system":{"hostname":"$(echo "$HOSTNAME" | json_str)","model":"$(echo "$MODEL" | json_str)","uptime":$UPTIME,"firmware":"$(echo "$FIRMWARE" | json_str)","kernel":"$KERNEL","load":[$LOAD]},"cpu":{"temp":$TEMP,"total":$CPU_TOTAL},"memory":{"total_mb":$MEMTOTAL,"avail_mb":$MEMAVAIL,"used_mb":$MEMUSED,"pct":$MEMPCT},"network":{"rx_rate_mbps":$RX_RATE,"tx_rate_mbps":$TX_RATE},"wireless":$WIRELESS,"storage":[$STORAGE],"ports":[$PORTS],"clients":[$CLIENTS],"matrix":{"enabled":$MT_ENABLED,"light_level":$MT_LEVEL,"night":$MT_NIGHT,"night_start":"$MT_NS","night_end":"$MT_NE","night_level":$MT_NL,"profile":"$MT_PROFILE","clock":$MT_CK,"medal":$MT_MD,"up":$MT_UP,"down":$MT_DN},"mode":"$MODE","wan":{"proto":"$WAN_PROTO","username":"$(echo "$WAN_USER" | json_str)","password":"$(echo "$WAN_PWD" | json_str)","device":"$WAN_DEVICE","ip":"$WAN_IP","wan_vlan":"$WAN_VLAN","ret_vlan":"$RET_VLAN","iptv_vlan":"$(echo "${IPTV_VLAN:-}" | json_str)","iptv_port":"$IPTV_PORT","static_ip":"$(echo "${WAN_SIP:-}" | json_str)","static_mask":"$(echo "${WAN_SMASK:-}" | json_str)","static_gw":"$(echo "${WAN_SGW:-}" | json_str)","static_dns":"$(echo "${WAN_SDNS:-}" | json_str)"}}
EOF
mv "$SCACHE.tmp" "$SCACHE" 2>/dev/null
cut -d. -f1 /proc/uptime > "$SSTAMP" 2>/dev/null
cat "$SCACHE"

