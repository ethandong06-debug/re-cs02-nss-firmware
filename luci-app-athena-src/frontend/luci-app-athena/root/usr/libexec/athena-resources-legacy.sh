#!/bin/sh
# AthenaWrt 资源监控 —— 旧 shell 实现（v1.2.43 逻辑，原样保留做兜底）
# 只在 /usr/bin/ucode 缺失时被 athena-resources.sh exec 调用；
# 正常路径走 athena-resources.uc（1 次 execve）。
#
CACHE=/tmp/athena-res-cache
CPU_CACHE=/tmp/athena-cpu-cache
HZ=$(getconf CLK_TCK 2>/dev/null)
[ -z "$HZ" ] || [ "$HZ" -le 0 ] 2>/dev/null && HZ=100
NCPU=$(grep -c '^processor' /proc/cpuinfo 2>/dev/null)
[ -z "$NCPU" ] || [ "$NCPU" -le 0 ] 2>/dev/null && NCPU=4
PAGESIZE=$(getconf PAGESIZE 2>/dev/null)
[ -z "$PAGESIZE" ] || [ "$PAGESIZE" -le 0 ] 2>/dev/null && PAGESIZE=4096

json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# ---- CPU 总量（/proc/stat 的 cpu 行）----
# idle 取 idle+iowait，total 取 user..softirq（不含 steal/guest，guest 已含在 user 内）
read_cpu() {
	awk '/^cpu /{printf "%d %d", $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat
}

# ---- 遍历进程：输出 "pid|name|ticks|rss_kb" ----
# 一次 cat 全部 stat + 单个 awk。旧版每个 PID fork 三次（tr/sed/awk），150+ 进程 = 400+ 次
# fork，采样本身就把 CPU 顶上去，测到的是「测量行为本身」。
# stat 去掉 "pid (comm) " 后：utime/stime 为第 12/13 字段；rss 为第 22 字段（单位：页）
list_procs() {
	cat /proc/[0-9]*/stat 2>/dev/null | awk -v ps="$PAGESIZE" '
	{
		pid=$1
		b=$0
		sub(/^.*\) /, "", b)      # 贪婪匹配到最右的 ") "，comm 里带括号也不会错位
		n=split(b, f, " ")
		if (n < 22) next
		nm=$0
		sub(/^[0-9]+ \(/, "", nm)
		sub(/\) .*/, "", nm)
		printf "%s|%s|%d|%d\n", pid, nm, f[12]+f[13], f[22]*ps/1024
	}'
}

# ---- CPU 总占用 ----
# ---- CPU 总占用：与概览页共用 /tmp/athena-cpu-cache（4 列整数，格式不变）----
# 口径：上次采样 → 本次 的真实时间窗。窗口 <2 秒或 tick 增量 <80 时沿用上次结果，
# 避免 1 秒窗口下整数除法把噪声放大（旧版这里 sleep 1 双采样，是 30% 与 63% 打架的根源）。
# athena-status.sh 不做任何修改，仍按原格式读这个文件。
NOW_UP=$(cut -d. -f1 /proc/uptime 2>/dev/null)
UP_RAW=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)
[ -z "$NOW_UP" ] && NOW_UP=0
[ -z "$UP_RAW" ] && UP_RAW=$NOW_UP
set -- $(read_cpu)
CUR_TOTAL=$1; CUR_IDLE=$2

list_procs > "$CACHE.now"

CPU_TOTAL=0
CPU_WIN=0
if [ -f "$CPU_CACHE" ]; then
	read -r OLD_IDLE OLD_TOTAL OLD_UP OLD_PCT < "$CPU_CACHE" 2>/dev/null
	# 老版 status.sh 写的是带小数的 uptime，这里必须剥掉小数，否则 shell 算术会报错
	OLD_UP=${OLD_UP%%.*}
	[ -z "$OLD_UP" ] && OLD_UP=0
	DT=$((CUR_TOTAL - ${OLD_TOTAL:-0}))
	DI=$((CUR_IDLE - ${OLD_IDLE:-0}))
	CPU_WIN=$((NOW_UP - OLD_UP))
	if [ "$DT" -ge 80 ] 2>/dev/null && [ "$CPU_WIN" -ge 2 ] 2>/dev/null; then
		CPU_TOTAL=$(( (DT - DI) * 100 / DT ))
	elif [ -n "$OLD_PCT" ] 2>/dev/null; then
		CPU_TOTAL=${OLD_PCT:-0}
	fi
else
	LOAD1=$(cut -d' ' -f1 /proc/loadavg 2>/dev/null)
	CPU_TOTAL=$(awk -v l="${LOAD1:-0}" -v n="$NCPU" 'BEGIN{printf "%.0f", l/n*100}')
fi
[ "$CPU_TOTAL" -gt 100 ] 2>/dev/null && CPU_TOTAL=100
[ "$CPU_TOTAL" -lt 0 ] 2>/dev/null && CPU_TOTAL=0
echo "$CUR_IDLE $CUR_TOTAL $NOW_UP $CPU_TOTAL" > "$CPU_CACHE" 2>/dev/null

# ---- 温度（取所有 thermal zone 最高值）----
TEMP=0
for f in /sys/class/thermal/thermal_zone*/temp; do
	[ -r "$f" ] || continue
	t=$(cat "$f" 2>/dev/null)
	[ -n "$t" ] && [ "$t" -gt "$TEMP" ] 2>/dev/null && TEMP=$t
done
TEMP=$((TEMP/1000))

# ---- 内存 ----
MEMTOTAL_KB=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
MEMAVAIL_KB=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
[ -z "$MEMTOTAL_KB" ] || [ "$MEMTOTAL_KB" -le 0 ] 2>/dev/null && MEMTOTAL_KB=1
[ -z "$MEMAVAIL_KB" ] && MEMAVAIL_KB=0
MEMUSED_KB=$((MEMTOTAL_KB - MEMAVAIL_KB))
MEMPCT=$((MEMUSED_KB * 100 / MEMTOTAL_KB))

# 内存对账（追加字段）：所有进程 RSS 合计 + 其余部分（内核 slab / 页缓存 / 共享内存），
# 用来解释「为什么进程明细加起来不等于总占用」
PROCS_KB=$(awk -F'|' '{s+=$4} END{printf "%d", s}' "$CACHE.now" 2>/dev/null)
[ -z "$PROCS_KB" ] && PROCS_KB=0
OTHER_KB=$((MEMUSED_KB - PROCS_KB))
[ "$OTHER_KB" -lt 0 ] 2>/dev/null && OTHER_KB=0

# ---- 进程 CPU%（对比上次 ticks 缓存）+ 内存排序取前 8 ----
# 关键：除以「实际经过的秒数」。旧版只除 HZ 和核数，前端 10 秒一刷就会放大 10 倍。
# ticks 缓存首行记录采样时刻（UP|秒），时间与数据放同一文件，避免两份缓存不同步。
if [ -f "$CACHE.ticks" ]; then
	OLD_TICK_UP=$(awk -F'|' '$1=="UP"{print $2; exit}' "$CACHE.ticks" 2>/dev/null)
else
	cp "$CACHE.now" "$CACHE.ticks" 2>/dev/null
	OLD_TICK_UP=""
fi
ELAPSED=0
if [ -n "$OLD_TICK_UP" ]; then
	ELAPSED=$(awk -v a="$UP_RAW" -v b="$OLD_TICK_UP" 'BEGIN{d=a-b; if(d<1||d>300) d=0; printf "%.2f", d}')
fi
PROCS=$(awk -F'|' -v hz="$HZ" -v ncpu="$NCPU" -v mtotal="$MEMTOTAL_KB" -v el="$ELAPSED" '
	NR==FNR { if($1=="UP") next; prev[$1]=$2+0; next }
	{
		pid=$1; name=$2; ticks=$3+0; rss=$4+0;
		d=ticks - prev[pid];
		cpu=0; if(el>0 && d>0) cpu=d/hz/ncpu/el*100;
		if(cpu>100) cpu=100;
		mem=0; if(mtotal>0) mem=rss/mtotal*100;
		printf "%d|%s|%.1f|%.1f|%.1f\n", pid, name, cpu, mem, rss/1024;
	}
' "$CACHE.ticks" "$CACHE.now" 2>/dev/null | sort -t'|' -k4 -rn)

# 更新 ticks 缓存供下次
{ echo "UP|$UP_RAW"; cut -d'|' -f1,3 "$CACHE.now"; } > "$CACHE.ticks" 2>/dev/null
rm -f "$CACHE.now" 2>/dev/null

# ---- 组装 JSON（单个 awk 完成）----
# v1.2.42 这里是「146 个进程 × 3 次 fork」：proc_label / proc_desc / json_str 各调一次外部命令，
# 实测 459 次 execve，占整脚本 1.8 秒里的 1.6 秒。现在全部搬进一个 awk，整脚本 execve 降到个位数。
# 内核线程（kworker/napi/irq/...，RSS 恒为 0 且不允许操作）不进列表，输出行数从 146 降到约 45。
printf '%s\n' "$PROCS" | awk -F'|' \
	-v ct="$CPU_TOTAL" -v tp="$TEMP" -v cw="$CPU_WIN" \
	-v mt="$((MEMTOTAL_KB/1024))" -v mu="$((MEMUSED_KB/1024))" -v mp="$MEMPCT" \
	-v pm="$((PROCS_KB/1024))" -v om="$((OTHER_KB/1024))" '
function esc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
function kth(n) { return (n ~ /^(kworker|ksoftirqd|napi\/|irq\/|migration\/|cpuhp\/|kthreadd|kswapd|oom_reaper|watchdogd|pool_workqueue|rcu_|kcompactd|spi0|askfirst)/) }
function lab(n) {
	if (n ~ /^athena-/) return "雅典娜后台服务"
	if (kth(n)) return (n ~ /^(kthreadd|ksoftirqd)/) ? "内核调度线程" : "内核后台任务"
	if (n == "netifd") return "网络服务"
	if (n == "odhcpd") return "地址分配服务"
	if (n == "dnsmasq") return "DNS 与地址分配"
	if (n == "ubusd") return "系统消息中心"
	if (n ~ /^(uhttpd|lighttpd|luci)/) return "Web 管理界面"
	if (n == "rpcd") return "后台管理接口"
	if (n == "logd") return "系统日志服务"
	if (n == "dropbear") return "远程登录服务"
	if (n ~ /^ppp/) return "宽带拨号服务"
	if (n == "hostapd") return "WiFi 服务"
	if (n == "wpa_supplicant") return "WiFi 客户端"
	if (n ~ /^(crond|busybox-cron)$/) return "定时任务服务"
	if (n ~ /^(ntpd|chronyd|systemd-timesyncd)$/) return "时间同步服务"
	if (n == "odhcp6c") return "IPv6 获取服务"
	if (n ~ /^(ash|sh|bash)$/) return "命令脚本"
	if (n ~ /^(curl|wget)$/) return "网络工具"
	if (n == "busybox") return "系统基础工具"
	return "后台进程"
}
function dsc(n) {
	if (n ~ /^athena-/) return "AthenaWrt 管理功能"
	if (kth(n)) return (n ~ /^(kthreadd|ksoftirqd)/) ? "内核调度（可忽略）" : "系统底层任务（可忽略）"
	if (n == "netifd") return "管理网口与上网连接"
	if (n == "odhcpd") return "给手机/电脑分配 IP"
	if (n == "dnsmasq") return "上网域名解析 + IP 分配"
	if (n == "ubusd") return "系统内部通信（可忽略）"
	if (n ~ /^(uhttpd|lighttpd|luci)/) return "运行后台管理页面"
	if (n == "rpcd") return "向管理界面提供数据"
	if (n == "logd") return "记录系统运行日志"
	if (n == "dropbear") return "允许 SSH 远程登录"
	if (n ~ /^ppp/) return "宽带账号拨号连接"
	if (n == "hostapd") return "管理无线网络（WiFi）"
	if (n == "wpa_supplicant") return "连接外部无线网络"
	if (n ~ /^(crond|busybox-cron)$/) return "按计划执行定时任务"
	if (n ~ /^(ntpd|chronyd|systemd-timesyncd)$/) return "自动校准系统时间"
	if (n == "odhcp6c") return "自动获取 IPv6 地址"
	if (n ~ /^(ash|sh|bash)$/) return "执行系统脚本"
	if (n ~ /^(curl|wget)$/) return "下载与测速工具"
	if (n == "busybox") return "系统常用命令集合"
	return "系统或应用进程"
}
function prot(n) {
	return (n ~ /^(wpad|hostapd|hostapd_cli|netifd|dnsmasq|odhcpd|odhcp6c|ubusd|rpcd|uhttpd|lighttpd|dropbear|logd|syslogd|pppd|pppoe.*)$/)
}
BEGIN {
	printf "{\"cpu\":{\"total\":%d,\"temp\":%d,\"window\":%d},\"memory\":{\"total_mb\":%d,\"used_mb\":%d,\"pct\":%d,\"procs_mb\":%d,\"other_mb\":%d},\"procs\":[", ct, tp, cw, mt, mu, mp, pm, om
	first = 1
}
{
	if (NF < 3) next
	pid = $1; nm = $2; cpu = $3 + 0; mem = $4 + 0; rs = $5 + 0
	if (nm == "" || kth(nm)) next
	if (!first) printf ","
	first = 0
	printf "{\"pid\":%d,\"name\":\"%s\",\"label\":\"%s\",\"desc\":\"%s\",\"cpu\":%.1f,\"mem\":%.1f,\"rss_mb\":%.1f,\"prot\":%s}", pid, esc(nm), esc(lab(nm)), esc(dsc(nm)), cpu, mem, rs, (prot(nm) ? "true" : "false")
}
END { print "]}" }
'
