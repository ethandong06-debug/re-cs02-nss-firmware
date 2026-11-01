#!/bin/sh
# AthenaWrt 固件升级。verify 与 flash 共用同一套机型/归档结构校验。
CMD="${1:-check}"
FW_ALLOWED="/tmp/athena-fw-upload.bin"

verify_file() {
	FILE="$1"
	[ "$FILE" = "$FW_ALLOWED" ] || { REASON="固件路径不在允许范围内"; return 1; }
	COMP=false
	REASON="固件包结构无效"
	DIR=""
	SIZE=0
	SHA=""
	[ -f "$FILE" ] && [ ! -L "$FILE" ] || { REASON="固件文件不存在或不是普通文件"; return 1; }
	SIZE=$(wc -c < "$FILE" 2>/dev/null | tr -d ' ')
	case "$SIZE" in ''|*[!0-9]*) REASON="无法读取固件大小"; return 1 ;; esac
	[ "$SIZE" -ge 1048576 ] || { REASON="固件文件过小（不足 1 MiB）"; return 1; }
	[ "$SIZE" -le 134217728 ] || { REASON="固件文件过大（超过 128 MiB）"; return 1; }
	SHA=$(sha256sum "$FILE" 2>/dev/null | awk '{print $1}')
	[ -n "$SHA" ] || { REASON="无法计算 SHA256"; return 1; }
	HDR=$(dd if="$FILE" bs=1 count=12 2>/dev/null)
	case "$HDR" in sysupgrade-*) ;; *) REASON="文件头不是 OpenWrt sysupgrade 固件"; return 1 ;; esac
	LIST=$(tar -tf "$FILE" 2>/dev/null) || { REASON="固件不是有效的 sysupgrade tar 归档"; return 1; }
	FIRST=$(printf '%s\n' "$LIST" | sed -n '1p')
	[ -n "$FIRST" ] || { REASON="固件归档为空"; return 1; }
	DIR="${FIRST%%/*}"
	case "$DIR" in sysupgrade-[A-Za-z0-9._+-]*) ;; *) REASON="固件归档目录名无效"; return 1 ;; esac
	# 拒绝绝对路径和目录穿越项，且必须在同一机型目录下包含 CONTROL/kernel/root。
	while IFS= read -r ENTRY; do
		case "$ENTRY" in /*|../*|*/../*|*/..) REASON="固件归档包含不安全路径"; return 1 ;; esac
		case "$ENTRY" in "$DIR"|"$DIR"/*) ;; *) REASON="固件归档包含异常顶层路径"; return 1 ;; esac
	done <<EOF
$LIST
EOF
	printf '%s\n' "$LIST" | grep -Fxq "$DIR/CONTROL" || { REASON="固件缺少 CONTROL"; return 1; }
	printf '%s\n' "$LIST" | grep -Fxq "$DIR/kernel" || { REASON="固件缺少 kernel"; return 1; }
	printf '%s\n' "$LIST" | grep -Fxq "$DIR/root" || { REASON="固件缺少 root"; return 1; }
	BOARD=$(cat /tmp/sysinfo/board_name 2>/dev/null | tr ',' '_' | tr -cd 'A-Za-z0-9._+-')
	[ -n "$BOARD" ] || BOARD="jdcloud_re-cs-02"
	if [ "$DIR" != "sysupgrade-$BOARD" ]; then
		REASON="目标机型不匹配（固件：$DIR；本机：sysupgrade-$BOARD）"
		return 1
	fi
	COMP=true
	REASON=""
	return 0
}

case "$CMD" in
	check)
		VER=$(sed -n 's/^DISTRIB_DESCRIPTION=//p' /etc/openwrt_release 2>/dev/null | tr -d '"')
		[ -n "$VER" ] || VER="AthenaWrt"
		printf '{"ok":true,"current":"%s","latest":null,"msg":"本机未配置在线升级源，请手动上传固件"}\n' "$VER"
		;;
	verify)
		FILE="${2:-}"
		[ "$FILE" = "$FW_ALLOWED" ] || { echo '{"ok":false,"compatible":false,"msg":"固件路径不在允许范围"}'; exit 1; }
		# 每次预校验先清理旧凭据；只有本次完整校验成功才生成一次性 SHA-256 凭据。
		rm -f /tmp/athena-fw-upload.sha256 /tmp/athena-fw-upload.sha256.tmp.*
		if verify_file "$FILE"; then
			umask 077
			MARKER_TMP="/tmp/athena-fw-upload.sha256.tmp.$$"
			if ! printf '%s\\n' "$SHA" > "$MARKER_TMP" || ! chmod 600 "$MARKER_TMP" || ! mv -f "$MARKER_TMP" /tmp/athena-fw-upload.sha256; then
				rm -f "$MARKER_TMP" /tmp/athena-fw-upload.sha256
				echo '{"ok":false,"compatible":false,"msg":"无法保存固件预校验凭据"}'
				exit 1
			fi
			printf '{"ok":true,"size":%s,"sha256":"%s","compatible":true,"pkg":"%s","reason":""}\\n' "$SIZE" "$SHA" "$DIR"
		else
			rm -f /tmp/athena-fw-upload.sha256
			SAFE_REASON=$(printf '%s' "$REASON" | sed 's/\\\\/\\\\\\\\/g; s/"/\\\\"/g')
			printf '{"ok":true,"size":%s,"sha256":"%s","compatible":false,"pkg":"%s","reason":"%s"}\\n' "${SIZE:-0}" "$SHA" "$DIR" "$SAFE_REASON"
		fi
		;;
	flash)
		FILE="${2:-}"
		KEEP="${3:-1}"
		[ "$FILE" = "$FW_ALLOWED" ] || { echo '{"ok":false,"msg":"固件路径不在允许范围"}'; exit 1; }
		case "$KEEP" in 0|1) ;; *) echo '{"ok":false,"msg":"保留配置参数必须为 0 或 1"}'; exit 1 ;; esac
		if ! verify_file "$FILE"; then
			rm -f /tmp/athena-fw-upload.sha256
			SAFE_REASON=$(printf '%s' "$REASON" | sed 's/\\/\\\\/g; s/"/\\"/g')
			printf '{"ok":false,"msg":"刷写前校验失败：%s"}\n' "$SAFE_REASON"
			exit 1
		fi
		VERIFIED_SHA=$(cat /tmp/athena-fw-upload.sha256 2>/dev/null)
		[ -n "$VERIFIED_SHA" ] && [ "$VERIFIED_SHA" = "$SHA" ] || { echo '{"ok":false,"msg":"固件未完成预校验或文件在校验后发生变化，请重新验证"}'; exit 1; }
		rm -f /tmp/athena-fw-upload.sha256
		if [ "$KEEP" = "0" ]; then
			echo '{"ok":true,"msg":"固件已通过机型与结构校验，开始全新刷写，设备即将重启"}'
			( sleep 1; sysupgrade -n "$FILE" ) >/dev/null 2>&1 &
		else
			echo '{"ok":true,"msg":"固件已通过机型与结构校验，开始保留配置刷写，设备即将重启"}'
			( sleep 1; sysupgrade "$FILE" ) >/dev/null 2>&1 &
		fi
		;;
	*) echo '{"ok":false,"msg":"未知命令（支持 check|verify|flash）"}'; exit 1 ;;
esac
