# -*- coding: utf-8 -*-
"""把 athena-resources.sh 从 v1.2.41 回退到 v1.2.40（本轮改动前的原文）。"""
import io, sys

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-resources.sh"
t = io.open(P, encoding="utf-8").read()

OLD_HEAD = """#!/bin/sh
# AthenaWrt 资源监控聚合脚本
# 输出单行 JSON：
#   {"cpu":{"total":0-100,"temp":c},"memory":{"total_mb":n,"used_mb":n,"pct":0-100},
#    "procs":[{"pid":p,"name":"x","cpu":x.x,"mem":x.x}]}
# - cpu.total / memory.pct：真实采样计算
# - procs：按内存占用取前 8，进程 CPU% 通过两次 /proc 采样（间隔 1s）计算
# 注意：首次运行时无上次采样，进程 CPU% 会偏高，第二次起恢复准确。

CACHE=/tmp/athena-res-cache
HZ=$(getconf CLK_TCK 2>/dev/null)
[ -z "$HZ" ] || [ "$HZ" -le 0 ] 2>/dev/null && HZ=100
NCPU=$(grep -c '^processor' /proc/cpuinfo 2>/dev/null)
[ -z "$NCPU" ] || [ "$NCPU" -le 0 ] 2>/dev/null && NCPU=4
"""

OLD_LIST = """# ---- 遍历进程：输出 "pid|name|ticks|rss_kb" ----
# stat 字段：去掉 "pid (comm) " 后 utime/stime 为第 12/13 字段（累计 CPU tick）
list_procs() {
	for p in /proc/[0-9]*; do
		[ -d "$p" ] || continue
		pid=${p##*/}
		name=$(tr -d '\\0' < "$p/comm" 2>/dev/null)
		[ -n "$name" ] || continue
		ticks=$(sed 's/.*) //' "$p/stat" 2>/dev/null | awk '{print $12+$13}')
		[ -n "$ticks" ] || continue
		rss=$(awk '/^VmRSS:/{print $2}' "$p/status" 2>/dev/null)
		[ -z "$rss" ] && rss=0
		echo "$pid|$name|$ticks|$rss"
	done
}

"""

OLD_CPU = """set -- $(read_cpu)
T1_TOTAL=$1; T1_IDLE=$2

list_procs > "$CACHE.now"

sleep 1

set -- $(read_cpu)
T2_TOTAL=$1; T2_IDLE=$2

# ---- CPU 总占用 ----
CPU_TOTAL=0
DT=$((T2_TOTAL - T1_TOTAL))
DI=$((T2_IDLE - T1_IDLE))
[ "$DT" -gt 0 ] 2>/dev/null && CPU_TOTAL=$(awk -v d="$DT" -v i="$DI" 'BEGIN{printf "%.0f", (d-i)/d*100}')
[ "$CPU_TOTAL" -gt 100 ] 2>/dev/null && CPU_TOTAL=100

"""

OLD_PROCS = """# ---- 进程 CPU%（对比上次 ticks 缓存）+ 内存排序取前 8 ----
# 首次运行无历史 ticks 时用当前快照顶替，否则 awk 单文件模式下 NR==FNR 恒真、
# 所有行都被当 prev 吞掉、无任何输出，导致进程排行永远为空
[ -f "$CACHE.ticks" ] || cp "$CACHE.now" "$CACHE.ticks" 2>/dev/null
PROCS=$(awk -F'|' -v hz="$HZ" -v ncpu="$NCPU" -v mtotal="$MEMTOTAL_KB" '
	NR==FNR { prev[$1]=$2+0; next }
	{
		pid=$1; name=$2; ticks=$3+0; rss=$4+0;
		d=ticks - prev[pid];
		cpu=0; if(d>0) cpu=d/hz/ncpu*100; if(cpu>100) cpu=100;
		mem=0; if(mtotal>0) mem=rss/mtotal*100;
		printf "%d|%s|%.1f|%.1f\\n", pid, name, cpu, mem;
	}
' "$CACHE.ticks" "$CACHE.now" 2>/dev/null | sort -t'|' -k4 -rn)

# 更新 ticks 缓存供下次
cut -d'|' -f1,3 "$CACHE.now" > "$CACHE.ticks" 2>/dev/null
rm -f "$CACHE.now" 2>/dev/null

"""

OLD_JSON = """# ---- 组装 JSON ----
printf '{"cpu":{"total":%s,"temp":%s},"memory":{"total_mb":%s,"used_mb":%s,"pct":%s},"procs":[' \\
	"$CPU_TOTAL" "$TEMP" "$((MEMTOTAL_KB/1024))" "$((MEMUSED_KB/1024))" "$MEMPCT"
first=1
printf '%s\\n' "$PROCS" | while IFS='|' read -r pid name cpu mem; do
	[ -z "$pid" ] && continue
	[ "$first" = "1" ] || printf ','
	first=0
	label=$(proc_label "$name")
	desc=$(proc_desc "$name")
	prot=false
	case "|$name|" in
		*"|wpad|"*|*"|hostapd|"*|*"|hostapd_cli|"*|*"|netifd|"*|*"|dnsmasq|"*|*"|odhcpd|"*|*"|odhcp6c|"*|*"|ubusd|"*|*"|rpcd|"*|*"|uhttpd|"*|*"|lighttpd|"*|*"|dropbear|"*|*"|logd|"*|*"|syslogd|"*|*"|pppd|"*|*"|pppoe|"*)
			prot=true ;;
	esac
	printf '{"pid":%s,"name":"%s","label":"%s","desc":"%s","cpu":%s,"mem":%s,"prot":%s}' \\
		"$pid" "$(printf '%s' "$name" | json_str)" "$(printf '%s' "$label" | json_str)" \\
		"$(printf '%s' "$desc" | json_str)" "$cpu" "$mem" "$prot"
done
echo ']}'
"""

def cut_between(s, start_marker, end_marker, repl, name):
    i = s.find(start_marker)
    j = s.find(end_marker, i + 1) if end_marker else len(s)
    if i < 0 or j < 0:
        print("FAIL locate", name, i, j); sys.exit(1)
    if s.count(start_marker) != 1:
        print("WARN marker repeated", name, s.count(start_marker))
    return s[:i] + repl + s[j:]

# 1) 头部
i = t.find("json_str() {")
assert i > 0
t = OLD_HEAD + "\n" + t[i:]

# 2) list_procs
t = cut_between(t, "# ---- 遍历进程：输出", "# ---- CPU 总占用：", OLD_LIST, "list_procs")

# 3) CPU 采样块
t = cut_between(t, "set -- $(read_cpu)", "# ---- 温度（取所有 thermal zone 最高值）----", OLD_CPU, "cpu")

# 4) 内存对账 + ticks 块
t = cut_between(t, "# 所有进程 RSS 合计", "# ---- 进程名 → 友好中文名 / 用途（小白可读） ----", OLD_PROCS, "procs")

# 5) JSON 组装
i = t.find("# ---- 组装 JSON ----")
assert i > 0
t = t[:i] + OLD_JSON

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("reverted bytes:", len(t.encode("utf-8")))
for kw in ("window", "procs_mb", "other_mb", "rss_mb", "TICKS_UP_RAW", "sleep 1"):
    print(kw, t.count(kw))
