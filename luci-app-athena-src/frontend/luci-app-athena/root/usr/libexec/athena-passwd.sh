#!/bin/sh
# AthenaWrt 修改管理账号/密码
# 用法: athena-passwd.sh <当前密码> <新密码> <同步SSH:0|1>
# 输出单行 JSON；当前密码校验通过 sha256 对比 shadow，或比对 /etc/config/athena 暂存明文
# 说明：管理与 SSH 共用 root shadow 密码；不设置或展示任何默认密码。

CUR="${1:-}"; NEW="${2:-}"; SYNC="${3:-1}"

[ -z "$CUR" ] && { echo '{"ok":false,"msg":"缺少当前密码"}'; exit 1; }
[ -z "$NEW" ] && { echo '{"ok":false,"msg":"缺少新密码"}'; exit 1; }
[ ${#NEW} -lt 8 ] && { echo '{"ok":false,"msg":"新密码至少 8 位"}'; exit 1; }
[ ${#NEW} -gt 128 ] && { echo '{"ok":false,"msg":"新密码不能超过 128 位"}'; exit 1; }
case "$NEW" in *:*) echo '{"ok":false,"msg":"新密码不能包含冒号"}'; exit 1 ;; esac
NL=$(printf '\\nX'); NL=${NL%X}
CR=$(printf '\\r')
case "$NEW" in *"$NL"*|*"$CR"*) echo '{"ok":false,"msg":"新密码不能包含换行符"}'; exit 1 ;; esac
case "$SYNC" in 0|1) ;; *) echo '{"ok":false,"msg":"SSH 同步参数无效"}'; exit 1 ;; esac

# ---- 校验当前密码 ----
check_cur() {
	# 比对 /etc/shadow 里的 root hash（真机多为 $1$ md5crypt / $5$ sha256crypt / $6$ sha512crypt）
	local sh_line hash id salt test_hash
	sh_line=$(grep '^root:' /etc/shadow 2>/dev/null)
	hash=$(echo "$sh_line" | cut -d: -f2)
	# 无密码 / 锁定：直接放行（首次未设密码时允许修改）
	[ -z "$hash" ] && return 0
	[ "$hash" = "!" ] && return 0
	[ "$hash" = "*" ] && return 0
	id=$(echo "$hash" | cut -d'$' -f2)
	salt=$(echo "$hash" | cut -d'$' -f3)
	[ -z "$id" ] || [ -z "$salt" ] && return 1
	if command -v openssl >/dev/null 2>&1; then
		case "$id" in
			1) test_hash=$(openssl passwd -1 -salt "$salt" "$CUR" 2>/dev/null) ;;
			5) test_hash=$(openssl passwd -5 -salt "$salt" "$CUR" 2>/dev/null) ;;
			6) test_hash=$(openssl passwd -6 -salt "$salt" "$CUR" 2>/dev/null) ;;
			*) return 1 ;;
		esac
		[ -n "$test_hash" ] && [ "$test_hash" = "$hash" ] && return 0
		return 1
	fi
	# 无 openssl 或 shadow 哈希算法不支持时，拒绝绕过当前密码校验。
	return 1
}

if ! check_cur; then
	echo '{"ok":false,"msg":"当前密码错误"}'
	exit 1
fi

# ---- 修改 root 密码 ----
# chpasswd 优先（无 TTY 更可靠）；busybox 无 chpasswd 时回退 passwd 管道
if command -v chpasswd >/dev/null 2>&1; then
	echo "root:$NEW" | chpasswd >/dev/null 2>&1
	rc=$?
else
	( echo "$NEW"; echo "$NEW" ) | passwd root >/dev/null 2>&1
	rc=$?
fi
if [ "$rc" -ne 0 ]; then
	echo '{"ok":false,"msg":"修改失败，请稍后重试"}'
	exit 1
fi

# ---- SSH 与管理界面共用 root shadow，无需单独同步 ----
if [ "$SYNC" = "1" ]; then
	MSG="管理密码已更新，SSH 登录密码已同步"
else
	MSG="管理密码已更新"
fi
echo "{\"ok\":true,\"msg\":\"$MSG\"}"
exit 0
