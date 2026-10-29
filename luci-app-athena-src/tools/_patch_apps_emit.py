# -*- coding: utf-8 -*-
"""athena-apps.sh：把 emit() 的 O(N×M) shell 循环改写成单次 awk 扫描。
真机现象：4 个实例长期存活、缓存写不出来，因为每行域名都 fork 一次 match_app，
而 match_app 要遍历整张 OAF 表（数千行）→ 单次执行几十秒到几分钟。
"""
import io

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-apps.sh"
s = io.open(P, encoding="utf-8").read()

# ---------- 1. 在 build_map 之后插入 build_rules ----------
ANCHOR = """# ---- 提取最近查询的 dnsmasq 域名日志（域名<TAB>来源IP） ----"""
RULES_FN = """# ---- 构建合并规则表 pattern<TAB>id<TAB>name（OAF 表 + DNS_RULES 兜底）----
# 只建一次，缺失才重建；之后 emit 只做一次 awk 扫描，不再每行 fork match_app
RULES=/tmp/athena-app-rules.tsv
build_rules() {
\t[ -s "$RULES" ] && return 0
\tbuild_map >/dev/null
\t{
\t\tprintf '%s\\n' "$DNS_RULES" | while IFS='|' read -r rnm rid rpats; do
\t\t\t[ -z "$rnm" ] && continue
\t\t\tprintf '%s\\n' "$rpats" | tr ',' '\\n' | while IFS= read -r pat; do
\t\t\t\t[ -z "$pat" ] && continue
\t\t\t\tprintf '%s\\t%s\\t%s\\n' "$pat" "$rid" "$rnm"
\t\t\tdone
\t\tdone
\t\t[ -s "$MAP_TMP" ] && cat "$MAP_TMP"
\t} > "$RULES.tmp" 2>/dev/null
\t[ -s "$RULES.tmp" ] && mv "$RULES.tmp" "$RULES"
\treturn 0
}

# ---- 提取最近查询的 dnsmasq 域名日志（域名<TAB>来源IP） ----"""

assert s.count(ANCHOR) == 1, "锚点未唯一命中"
s = s.replace(ANCHOR, RULES_FN)

# ---------- 2. 重写 emit ----------
OLD_EMIT = """emit() {
\tbuild_map >/dev/null
\tlocal lines aggr selfip
\tselfip=$(uci -q get network.lan.ipaddr 2>/dev/null); [ -z "$selfip" ] && selfip=192.168.10.1
\tlines=$(get_loglines)
\t[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"dnsmasq 查询日志为空（未开启 logqueries 或近期无查询）"}'; return; }
\t# 过滤：仅统计内网设备发起的查询（排除路由器自身 / 本机回环）
\tlines=$(printf '%s\\n' "$lines" | grep -v -E "(^| )$selfip$" | grep -v "127.0.0.1")
\t[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"近 %s 分钟无内网设备活跃应用"}' "$WINDOW"; return; }
\taggr=$(printf '%s\\n' "$lines" | while IFS=$TAB read -r dom ip; do
\t\t[ -z "$dom" ] && continue
\t\tr=$(match_app "$dom")
\t\t[ -z "$r" ] && continue
\t\tid=$(printf '%s' "$r" | cut -d'|' -f1)
\t\tname=$(printf '%s' "$r" | cut -d'|' -f2)
\t\tprintf '%s%s%s%s%s\\n' "$id" "$TAB" "$name" "$TAB" "$ip"
\tdone | sort -u | awk -F'\\t' '{cnt[$1 FS $2]++} END{for(k in cnt) print cnt[k] "\\t" k}')"""

NEW_EMIT = """emit() {
\tbuild_rules
\tlocal lines aggr selfip
\tselfip=$(uci -q get network.lan.ipaddr 2>/dev/null); [ -z "$selfip" ] && selfip=192.168.10.1
\tlines=$(get_loglines)
\t[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"dnsmasq 查询日志为空（未开启 logqueries 或近期无查询）"}'; return; }
\t# 过滤本机来源 + 域名去重（同一域名查很多次只需匹配一次）+ 上限 600 行
\tlines=$(printf '%s\\n' "$lines" | grep -v -E "(^| )$selfip$" | grep -v "127.0.0.1" \\
\t\t| awk -F'\\t' 'NF && $1!="" && !seen[$1]++' | head -n 600)
\t[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"近 %s 分钟无内网设备活跃应用"}' "$WINDOW"; return; }
\t# 单次 awk：规则表读入内存，逐行取最长命中，不再 per-line fork
\taggr=$(printf '%s\\n' "$lines" | awk -F'\\t' '
\t\tFNR==NR { if ($1 != "") { n++; k[n]=$1; id[n]=$2; nm[n]=$3 } next }
\t\t{
\t\t\td=$1; if (d == "") next
\t\t\tb=0; bl=0
\t\t\tfor (i=1; i<=n; i++) {
\t\t\t\tif (length(k[i]) > bl && index(d, k[i])) { bl=length(k[i]); b=i }
\t\t\t}
\t\t\tif (b == 0) next
\t\t\tprint id[b] "\\t" nm[b] "\\t" $2
\t\t}
\t' "$RULES" - | sort -u | awk -F'\\t' '{cnt[$1 FS $2]++} END{for(k in cnt) print cnt[k] "\\t" k}')"""

assert s.count(OLD_EMIT) == 1, "emit 原文未唯一命中: %d" % s.count(OLD_EMIT)
s = s.replace(OLD_EMIT, NEW_EMIT)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("emit rewritten, file bytes:", len(s.encode("utf-8")))
