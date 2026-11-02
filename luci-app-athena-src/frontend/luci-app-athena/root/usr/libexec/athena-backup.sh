#!/bin/sh
# AthenaWrt 备份与恢复
# 用法:
#   athena-backup.sh create                 生成配置备份（sysupgrade -b）
#   athena-backup.sh list                   列出已有备份
#   athena-backup.sh restore <file>         从备份恢复（sysupgrade -r，随后重启）
#   athena-backup.sh download <file>        导出备份内容（base64，前端转文件）
# 输出单行 JSON

CMD="${1:-list}"
BACKUP_DIR="/etc/athena-backup"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }
# Accept legacy backup naming styles but never path separators or traversal.
resolve_backup() {
	local name="$1" base
	case "$name" in config-*.tar.gz) ;; *) return 1 ;; esac
	case "$name" in *[!A-Za-z0-9._-]*|*..*) return 1 ;; esac
	base=$(readlink -f "$BACKUP_DIR" 2>/dev/null) || return 1
	FP=$(readlink -f "$BACKUP_DIR/$name" 2>/dev/null) || return 1
	[ -f "$FP" ] || return 1
	case "$FP" in "$base"/config-*.tar.gz) return 0 ;; esac
	return 1
}

mkdir -p "$BACKUP_DIR" 2>/dev/null
mkdir -p /etc/crontabs 2>/dev/null

# 自动备份执行体：创建备份 + 只保留最近 keep 份
autobackup() {
	local keep="${1:-3}"
	case "$keep" in ''|*[!0-9]*) keep=3 ;; esac
	[ "$keep" -ge 1 ] 2>/dev/null && [ "$keep" -le 30 ] 2>/dev/null || keep=3
	local TS=$(date +%Y%m%d-%H%M%S)
	local FILE="$BACKUP_DIR/config-$TS.tar.gz"
	sysupgrade -b "$FILE" >/dev/null 2>&1
	[ "$keep" -gt 0 ] 2>/dev/null && ls -1t "$BACKUP_DIR"/config-*.tar.gz 2>/dev/null | tail -n +$((keep+1)) | while read -r f; do rm -f "$f"; done
}

# 自动备份定时：schedule get / set <freq> <time> <keep> / disable
schedule_get() {
	local freq=$(uci -q get athena.backup.freq 2>/dev/null); [ -z "$freq" ] && freq="daily"
	local time=$(uci -q get athena.backup.time 2>/dev/null); [ -z "$time" ] && time="02:00"
	local keep=$(uci -q get athena.backup.keep 2>/dev/null); [ -z "$keep" ] && keep="3"
	local enabled=false
	grep -q "athena-backup.sh autobackup" /etc/crontabs/root 2>/dev/null && enabled=true
	printf '{"ok":true,"enabled":%s,"freq":"%s","time":"%s","keep":%s}' "$enabled" "$freq" "$time" "$keep"
}

schedule_set() {
	local freq="${1:-daily}" time="${2:-02:00}" keep="${3:-3}"
	local hh="${time%%:*}" mm="${time#*:}"
	case "$freq" in
		daily) cron="$mm $hh * * *" ;;
		weekly) cron="$mm $hh * * 0" ;;
		monthly) cron="$mm $hh 1 * *" ;;
		*) { echo '{"ok":false,"msg":"未知频率（daily|weekly|monthly）"}'; exit 1; } ;;
	esac
	case "$time" in
		[0-9][0-9]:[0-9][0-9]) ;;
		*) echo '{"ok":false,"msg":"时间格式必须为 HH:MM"}'; exit 1 ;;
	esac
	[ "$hh" -ge 0 ] 2>/dev/null && [ "$hh" -le 23 ] 2>/dev/null || { echo '{"ok":false,"msg":"小时必须为 00-23"}'; exit 1; }
	[ "$mm" -ge 0 ] 2>/dev/null && [ "$mm" -le 59 ] 2>/dev/null || { echo '{"ok":false,"msg":"分钟必须为 00-59"}'; exit 1; }
	case "$keep" in ''|*[!0-9]*) echo '{"ok":false,"msg":"保留份数必须为正整数"}'; exit 1 ;; esac
	[ "$keep" -ge 1 ] 2>/dev/null && [ "$keep" -le 30 ] 2>/dev/null || { echo '{"ok":false,"msg":"保留份数范围为 1-30"}'; exit 1; }
	sed -i '/athena-backup.sh autobackup/d' /etc/crontabs/root 2>/dev/null
	echo "$cron /usr/libexec/athena-backup.sh autobackup $keep" >> /etc/crontabs/root
	/etc/init.d/cron enable >/dev/null 2>&1
	/etc/init.d/cron restart >/dev/null 2>&1
	uci set athena.backup.freq="$freq" 2>/dev/null
	uci set athena.backup.time="$time" 2>/dev/null
	uci set athena.backup.keep="$keep" 2>/dev/null
	uci commit athena 2>/dev/null
	echo '{"ok":true,"msg":"自动备份已设置"}'
}

schedule_disable() {
	sed -i '/athena-backup.sh autobackup/d' /etc/crontabs/root 2>/dev/null
	/etc/init.d/cron restart >/dev/null 2>&1
	uci -q delete athena.backup 2>/dev/null
	uci commit athena 2>/dev/null
	echo '{"ok":true,"msg":"自动备份已关闭"}'
}

case "$CMD" in
	create)
		TS=$(date +%Y%m%d-%H%M%S)
		FILE="$BACKUP_DIR/config-$TS.tar.gz"
		sysupgrade -b "$FILE" >/dev/null 2>&1
		if [ -f "$FILE" ]; then
			SIZE=$(du -k "$FILE" 2>/dev/null | awk '{print $1}')
			echo "{\"ok\":true,\"file\":\"$(basename "$FILE")\",\"size_kb\":${SIZE:-0},\"time\":\"$TS\"}"
		else
			echo '{"ok":false,"msg":"备份失败"}'
		fi
		;;
	list)
		# 收集文件名后统一输出单行 JSON（不能用管道 sort：会拆行破坏 JSON，导致前端解析失败）
		first=1
		printf '{"ok":true,"backups":['
		for name in $(ls -1t "$BACKUP_DIR"/config-*.tar.gz 2>/dev/null | sed 's#.*/##'); do
			size=$(du -k "$BACKUP_DIR/$name" 2>/dev/null | awk '{print $1}')
			[ "$first" = "1" ] || printf ','
			first=0
			printf '{"file":"%s","size_kb":%s}' "$name" "${size:-0}"
		done
		printf ']}'
		;;
	restore)
		FILE="${2:-}"
		[ -z "$FILE" ] && { echo '{"ok":false,"msg":"缺少备份文件名"}'; exit 1; }
		resolve_backup "$FILE" || { echo '{"ok":false,"msg":"备份文件名无效或文件不存在"}'; exit 1; }
		tar -tzf "$FP" >/dev/null 2>&1 || { echo '{"ok":false,"msg":"备份文件不是有效的 tar.gz 配置归档"}'; exit 1; }
		if sysupgrade -r "$FP" >/dev/null 2>&1; then
			echo '{"ok":true,"msg":"配置已恢复，设备即将重启"}'
		else
			rc=$?
			echo '{"ok":false,"msg":"sysupgrade 拒绝恢复该配置备份"}'
			exit "$rc"
		fi
		;;
	download)
		FILE="${2:-}"
		[ -z "$FILE" ] && { echo '{"ok":false,"msg":"缺少备份文件名"}'; exit 1; }
		resolve_backup "$FILE" || { echo '{"ok":false,"msg":"备份文件名无效或文件不存在"}'; exit 1; }
		B64=$(base64 "$FP" 2>/dev/null | tr -d '\n')
		echo "{\"ok\":true,\"file\":\"$FILE\",\"base64\":\"$B64\"}"
		;;
	export)
		# 已废弃：历史上把备份复制到 /www/athena-bk 返 http 直链，因 www 目录权限与
		# ACL 限制会 403/404。前端已改走 download（base64 + Blob），此分支保留只为
		# 兼容旧页面调用，直接回落到 base64 通道，不再写 /www。
		FILE="${2:-}"
		[ -z "$FILE" ] && { echo '{"ok":false,"msg":"缺少备份文件名"}'; exit 1; }
		resolve_backup "$FILE" || { echo '{"ok":false,"msg":"备份文件名无效或文件不存在"}'; exit 1; }
		B64=$(base64 "$FP" 2>/dev/null | tr -d '\n')
		echo "{\"ok\":true,\"file\":\"$FILE\",\"base64\":\"$B64\"}"
		;;
	restore-upload)
		# 前端先经 rpcd file.write 把备份内容（base64）写入 /tmp/athena-restore.b64，
		# 再调用本命令（无参）：大文件不能走 exec 命令行参数（rpcd 限制 1024B），避免恢复上传必失败
		TMP="/tmp/athena-restore.b64"
		[ -s "$TMP" ] || { echo '{"ok":false,"msg":"未找到上传的备份内容（请重新选择备份文件）"}'; exit 1; }
		OUT="/tmp/athena-restore.tar.gz"
		base64 -d "$TMP" > "$OUT" 2>/dev/null
		[ -s "$OUT" ] || { rm -f "$TMP" "$OUT" 2>/dev/null; echo '{"ok":false,"msg":"备份内容解码失败"}'; exit 1; }
		tar -tzf "$OUT" >/dev/null 2>&1 || { rm -f "$TMP" "$OUT" 2>/dev/null; echo '{"ok":false,"msg":"文件不是有效的 OpenWrt 配置备份（tar.gz）"}'; exit 1; }
		if sysupgrade -r "$OUT" >/dev/null 2>&1; then
			rm -f "$TMP" "$OUT" 2>/dev/null
			echo '{"ok":true,"msg":"配置已恢复，设备即将重启"}'
		else
			rc=$?
			rm -f "$TMP" "$OUT" 2>/dev/null
			echo '{"ok":false,"msg":"sysupgrade 拒绝恢复该配置备份"}'
			exit "$rc"
		fi
		;;
	schedule)
		case "${2:-get}" in
			get) schedule_get ;;
			set) schedule_set "$3" "$4" "$5" ;;
			disable) schedule_disable ;;
			*) echo '{"ok":false,"msg":"未知 schedule 子命令（get|set|disable）"}'; exit 1 ;;
		esac
		;;
	autobackup) autobackup "${2:-3}" ;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 create|list|restore|download|restore-upload|schedule）"}'
		exit 1
		;;
esac
