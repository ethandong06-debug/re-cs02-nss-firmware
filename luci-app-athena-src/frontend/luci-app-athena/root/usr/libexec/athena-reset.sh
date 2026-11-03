#!/bin/sh
# AthenaWrt 恢复出厂：短时、一次性随机挑战，避免固定确认参数被重放。
umask 077
CHALLENGE="/tmp/athena-reset.challenge"
LOCK="/var/run/athena-reset.lock"
TTL=60
fail() { printf '{"ok":false,"msg":"%s"}\n' "$1"; exit 1; }
valid_token() {
	case "$1" in ''|*[!0-9a-f]*) return 1 ;; esac
	[ "${#1}" -eq 64 ]
}
case "${1:-}" in
	prepare)
		[ ! -d "$LOCK" ] || fail "恢复出厂操作正在进行"
		TOKEN=$(openssl rand -hex 32 2>/dev/null)
		valid_token "$TOKEN" || fail "无法生成安全确认码"
		NOW=$(date +%s); [ -n "$NOW" ] || fail "无法读取系统时间"
		TMP="$CHALLENGE.$$"
		( set -C; printf '%s %s\n' "$TOKEN" "$NOW" > "$TMP" ) 2>/dev/null || fail "无法安全创建确认状态"
		mv "$TMP" "$CHALLENGE" || { rm -f "$TMP"; fail "无法保存确认状态"; }
		printf '{"ok":true,"token":"%s","expires_in":%s}\n' "$TOKEN" "$TTL"
		;;
	confirm)
		TOKEN="${2:-}"
		valid_token "$TOKEN" || fail "确认码无效"
		mkdir "$LOCK" 2>/dev/null || fail "恢复出厂操作正在进行"
		trap 'rmdir "$LOCK" 2>/dev/null' 0
		SAVED=$(cat "$CHALLENGE" 2>/dev/null)
		SAVED_TOKEN=${SAVED%% *}; SAVED_TIME=${SAVED#* }
		case "$SAVED_TIME" in ''|*[!0-9]*) rm -f "$CHALLENGE"; fail "确认码不存在或已过期" ;; esac
		NOW=$(date +%s); AGE=$((NOW - SAVED_TIME))
		[ "$SAVED_TOKEN" = "$TOKEN" ] && [ "$AGE" -ge 0 ] && [ "$AGE" -le "$TTL" ] || {
			rm -f "$CHALLENGE"; fail "确认码无效或已过期，请重新发起恢复出厂";
		}
		# 先消费确认码，再执行不可逆操作，防止并发重放。
		rm -f "$CHALLENGE"
		firstboot -y >/dev/null 2>&1 || fail "firstboot 执行失败，未安排重启"
		printf '{"ok":true,"msg":"已标记恢复出厂，设备即将重启"}\n'
		( sleep 2; reboot ) >/dev/null 2>&1 &
		;;
	*) printf '{"ok":false,"need_confirm":true,"msg":"请先请求一次性确认码，再由用户确认执行"}\n'; exit 1 ;;
esac
