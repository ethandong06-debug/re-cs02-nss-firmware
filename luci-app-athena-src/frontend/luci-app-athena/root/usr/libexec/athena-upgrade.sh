#!/bin/sh
# AthenaWrt 固件升级：verify 与 flash 共用完整后端校验，flash 不信任前端结果。
# 仅允许 Athena 固件上传临时路径，拒绝任意路径和符号链接。
CMD="${1:-check}"
UPLOAD_BIN="/tmp/athena-fw-upload.bin"
UPLOAD_B64="/tmp/athena-fw.b64"
DECODED_BIN="/tmp/athena-fw.bin"
LOCK="/var/run/athena-upgrade.lock"
json_fail() { printf '{"ok":false,"msg":"%s"}\n' "$1"; exit 1; }
valid_sha() {
	case "$1" in ''|*[!0-9a-f]*) return 1 ;; esac
	[ "${#1}" -eq 64 ]
}
safe_input() {
	case "$1" in
		"$UPLOAD_BIN"|"$UPLOAD_B64"|"$DECODED_BIN") ;;
		/tmp/athena-fw-verified-*.bin)
			NAME=${1#/tmp/}
			printf '%s\n' "$NAME" | grep -Eq '^athena-fw-verified-[0-9]+\.bin$' || return 1
			;;
		*) return 1 ;;
	esac
	[ ! -L "$1" ] && [ -f "$1" ] || return 1
	REAL=$(readlink -f "$1" 2>/dev/null) || return 1
	[ "$REAL" = "$1" ]
}
validate_image() {
	FW="$1"; FW_SIZE=0; FW_SHA=""; FW_BOARD=""; FW_REASON="固件文件无效"
	safe_input "$FW" || { FW_REASON="固件路径非法、文件不存在或不允许符号链接"; return 1; }
	FW_SIZE=$(wc -c < "$FW" 2>/dev/null | tr -d ' ')
	case "$FW_SIZE" in ''|*[!0-9]*) FW_REASON="无法读取固件大小"; return 1 ;; esac
	[ "$FW_SIZE" -gt 0 ] 2>/dev/null || { FW_REASON="固件文件为空"; return 1; }
	FW_SHA=$(sha256sum "$FW" 2>/dev/null | awk '{print $1}')
	valid_sha "$FW_SHA" || { FW_REASON="SHA256 计算失败"; return 1; }
	BOARD=$(cat /tmp/sysinfo/board_name 2>/dev/null | tr ',' '_' | tr -cd 'A-Za-z0-9_.-')
	[ -n "$BOARD" ] || BOARD="jdcloud_re-cs-02"
	FW_BOARD="sysupgrade-$BOARD"
	LIST="/tmp/athena-fw-list-$$"; VERBOSE="/tmp/athena-fw-verbose-$$"
	( set -C; : > "$LIST" && : > "$VERBOSE" ) 2>/dev/null || { FW_REASON="无法创建固件校验临时文件"; return 1; }
	if ! tar -tf "$FW" > "$LIST" 2>/dev/null; then
		rm -f "$LIST" "$VERBOSE"; FW_REASON="固件不是可读取的 tar 归档"; return 1
	fi
	if [ ! -s "$LIST" ]; then
		rm -f "$LIST" "$VERBOSE"; FW_REASON="固件归档为空"; return 1
	fi
	if ! awk -v root="$FW_BOARD" '
	{
		name=$0; sub(/\/$/, "", name)
		if (name == "" || name ~ /^\// || name ~ /(^|\/)\.\.?($|\/)/) bad=1
		split(name, part, "/")
		if (part[1] != root) bad=1
		if (name == root) dir=1
		if (name == root "/CONTROL") control=1
		if (name == root "/kernel") kernel=1
		if (name == root "/root") image=1
	}
	END { if (bad || !dir || !control || !kernel || !image) exit 1 }
	' "$LIST"; then
		rm -f "$LIST" "$VERBOSE"; FW_REASON="固件结构或目标机型不匹配（必须包含本机目录、CONTROL、kernel、root）"; return 1
	fi
	if ! tar -tvf "$FW" > "$VERBOSE" 2>/dev/null; then
		rm -f "$LIST" "$VERBOSE"; FW_REASON="无法读取固件归档成员属性"; return 1
	fi
	if ! awk 'substr($0,1,1)!="-" && substr($0,1,1)!="d" { bad=1 } END { exit bad }' "$VERBOSE"; then
		rm -f "$LIST" "$VERBOSE"; FW_REASON="固件归档包含不允许的链接或特殊文件成员"; return 1
	fi
	rm -f "$LIST" "$VERBOSE"
	return 0
}
case "$CMD" in
	check)
		VER=$(cat /etc/openwrt_release 2>/dev/null | sed -n 's/^DISTRIB_DESCRIPTION=//p' | tr -d '"')
		[ -n "$VER" ] || VER="AthenaWrt v1.0.0"
		printf '{"ok":true,"current":"%s","latest":null,"msg":"已是最新（本机无在线源，需手动上传固件）"}\n' "$VER"
		;;
	verify)
		FILE="${2:-}"; [ -n "$FILE" ] || json_fail "缺少固件路径"
		if validate_image "$FILE"; then
			printf '{"ok":true,"size":%s,"sha256":"%s","compatible":true,"pkg":"%s","reason":""}\n' "$FW_SIZE" "$FW_SHA" "$FW_BOARD"
		else
			printf '{"ok":true,"size":%s,"sha256":"%s","compatible":false,"pkg":"%s","reason":"%s"}\n' "${FW_SIZE:-0}" "${FW_SHA:-}" "${FW_BOARD:-}" "$FW_REASON"
		fi
		;;
	flash)
		FILE="${2:-}"; KEEP="${3:-1}"; EXPECTED_SHA="${4:-}"
		[ "$KEEP" = "0" ] || [ "$KEEP" = "1" ] || json_fail "保留配置参数必须为 0 或 1"
		valid_sha "$EXPECTED_SHA" || json_fail "缺少有效的前端 SHA256 校验值"
		[ -n "$FILE" ] || json_fail "缺少固件路径"
		safe_input "$FILE" || json_fail "固件路径非法、文件不存在或不允许符号链接"
		FW="$FILE"; FROM_B64=0
		case "$FILE" in
			"$UPLOAD_B64")
				[ ! -L "$DECODED_BIN" ] || json_fail "解码目标不允许为符号链接"
				rm -f "$DECODED_BIN"
				umask 077
				( set -C; base64 -d "$FILE" > "$DECODED_BIN" ) 2>/dev/null || json_fail "固件解码失败"
				[ -s "$DECODED_BIN" ] || json_fail "固件解码结果为空"
				FW="$DECODED_BIN"; FROM_B64=1
				;;
		esac
		validate_image "$FW" || json_fail "$FW_REASON"
		[ "$FW_SHA" = "$EXPECTED_SHA" ] || json_fail "固件 SHA256 与上传时校验值不一致，已取消刷写"
		mkdir -p /var/run
		mkdir "$LOCK" 2>/dev/null || json_fail "已有固件刷写任务正在进行"
		STAGED="/tmp/athena-fw-verified-$$.bin"
		trap 'rm -f "$STAGED"; rmdir "$LOCK" 2>/dev/null' 0
		umask 077
		( set -C; cat "$FW" > "$STAGED" ) 2>/dev/null || json_fail "无法创建受保护的固件暂存文件"
		validate_image "$STAGED" || json_fail "固件暂存副本复验失败：$FW_REASON"
		[ "$FW_SHA" = "$EXPECTED_SHA" ] || json_fail "固件暂存副本哈希不一致"
		sysupgrade -T "$STAGED" >/dev/null 2>&1 || json_fail "sysupgrade 平台校验失败，已取消刷写"
		[ "$FROM_B64" = "0" ] || rm -f "$DECODED_BIN"
		if [ "$KEEP" = "0" ]; then
			printf '{"ok":true,"msg":"开始刷写（不保留配置），设备即将重启"}\n'
			( trap - 0; sleep 1; sysupgrade -n "$STAGED"; rc=$?; rm -f "$STAGED"; rmdir "$LOCK" 2>/dev/null; exit "$rc" ) >/dev/null 2>&1 &
		else
			printf '{"ok":true,"msg":"开始刷写（保留配置），设备即将重启"}\n'
			( trap - 0; sleep 1; sysupgrade "$STAGED"; rc=$?; rm -f "$STAGED"; rmdir "$LOCK" 2>/dev/null; exit "$rc" ) >/dev/null 2>&1 &
		fi
		trap - 0
		;;
	*) json_fail "未知命令（支持 check|verify|flash）" ;;
esac
