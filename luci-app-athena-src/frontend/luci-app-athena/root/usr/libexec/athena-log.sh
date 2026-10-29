#!/bin/sh
# AthenaWrt 系统日志脚本（v1.2.54：四列结构化输出）
# 用法:
#   athena-log.sh list [level] [keyword]      读取系统日志（level: debug/info/warn/err/all）
#   athena-log.sh clear                       清空日志（logread -c + dmesg -c）
#   athena-log.sh export                      导出全部日志为纯文本
# 输出单行 JSON：{"ok":true,"logs":[{"time":"10-28 20:12:00","level":"info","module":"dnsmasq","msg":"..."}]}
#
# 四列口径（前端按固定列宽渲染）：
#   time   logread 行的月-日 时:分:秒（去掉星期与年份，省横向空间）
#   level  facility.level 里的级别，emerg/alert/crit/err→err，warn→warn，debug→debug，其余 info
#   module 发日志的进程名（dnsmasq[7466] → dnsmasq）
#   msg    进程名之后正文；内核行把 [12345.678] 时间前缀去掉

CMD="${1:-list}"
LEVEL="${2:-all}"
KEYWORD="${3:-}"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g; s/\r//g'; }

parse_lines() {
	logread 2>/dev/null | awk '
	BEGIN{ split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", mn, " "); for (i = 1; i <= 12; i++) mon[mn[i]] = sprintf("%02d", i) }
	function lvof(f,   l) {
		l = f
		sub(/^.*\./, "", l)                 # daemon.info → info
		if (l == "emerg" || l == "alert" || l == "crit" || l == "err" || l == "error") return "err"
		if (l == "warn" || l == "warning") return "warn"
		if (l == "debug") return "debug"
		return "info"
	}
	{
		n = split($0, a, " ")
		idx = 0
		for (i = 1; i <= n; i++) {
			# logread 的 facility.level 字段，如 daemon.info / kern.warn / authpriv.err
			if (i < n && a[i] ~ /^(kern|user|daemon|auth|authpriv|syslog|lpr|news|uucp|cron|ftp|local[0-7])\.(emerg|alert|crit|err|error|warn|warning|notice|info|debug)$/) { idx = i; break }
		}
		# 时间列：在 facility.level 之前找 HH:MM:SS，再往前找月名 + 日
		# 兼容 "Oct 28 20:12:00 daemon.info" 与 "Fri Oct 28 20:12:00 2026 daemon.info" 两种 logread 输出
		tm = ""
		if (idx == 0) { lv = "info"; mod = ""; body = $0 }
		else {
			lv = lvof(a[idx])
			mod = (idx < n) ? a[idx+1] : ""
			sub(/\[[0-9]+\]:?$/, "", mod)     # dnsmasq[7466]: → dnsmasq
			sub(/:$/, "", mod)
			body = ""
			for (i = idx + 2; i <= n; i++) body = (body == "" ? a[i] : body " " a[i])
			tpos = 0
			for (i = 1; i < idx; i++) { if (a[i] ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$/) { tpos = i; break } }
			if (tpos >= 3 && (a[tpos-2] in mon)) tm = mon[a[tpos-2]] "-" sprintf("%02d", a[tpos-1]) " " a[tpos]
			else if (tpos >= 2 && a[tpos-1] ~ /^[0-9][0-9]-[0-9][0-9]$/) tm = a[tpos-1] " " a[tpos]
		}
		sub(/^\[[ 0-9.]+\][ \t]*/, "", body)   # 内核行 [12345.678] / [  88.123] 前缀
		if (tm == "") {
			# 拿不到标准时间戳时退回原始行，保证信息不丢
			body = $0; mod = ""
		}
		gsub(/[|]/, "/", tm); gsub(/[|]/, "/", mod); gsub(/[|]/, "/", body)
		if (body == "") next
		printf "%s|%s|%s|%s\n", tm, lv, mod, body
	}' | head -300
}

emit_list() {
	local flt_level="$1" kw="$2" first=1
	printf '{"ok":true,"logs":['
	parse_lines | while IFS='|' read -r tm lv mod msg; do
		[ -z "$msg" ] && continue
		if [ "$flt_level" != "all" ] && [ "$flt_level" != "$lv" ]; then continue; fi
		if [ -n "$kw" ]; then echo "$tm $mod $msg" | grep -qi "$kw" || continue; fi
		[ "$first" = "1" ] || printf ','
		first=0
		printf '{"time":"%s","level":"%s","module":"%s","msg":"%s"}' \
			"$(printf '%s' "$tm" | json_str)" "$lv" "$(printf '%s' "$mod" | json_str)" "$(printf '%s' "$msg" | json_str)"
	done
	printf ']}'
}

case "$CMD" in
	list) emit_list "$LEVEL" "$KEYWORD" ;;
	clear)
		logread -c 2>/dev/null || true
		dmesg -c >/dev/null 2>&1 || true
		echo '{"ok":true,"msg":"日志已清空"}'
		;;
	export)
		DIR="/www/athena-log"
		mkdir -p "$DIR" 2>/dev/null
		RAND=$(head -c6 /dev/urandom 2>/dev/null | hexdump -v -e '6/1 "%02x"' 2>/dev/null)
		[ -z "$RAND" ] && RAND=$$
		DST="$DIR/syslog.$RAND.log"
		logread 2>/dev/null > "$DST"
		[ -s "$DST" ] || { echo '{"ok":false,"msg":"日志为空或读取失败"}'; exit 1; }
		( sleep 300; rm -f "$DST" ) >/dev/null 2>&1 &
		echo "{\"ok\":true,\"url\":\"/athena-log/syslog.$RAND.log\"}"
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 list|clear|export）"}'
		exit 1
		;;
esac
