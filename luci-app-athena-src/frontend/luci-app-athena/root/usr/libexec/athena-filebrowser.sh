#!/bin/sh
# 仅供已登录 LuCI 管理员读取 filebrowser 首次生成的随机凭据。
DB=/etc/filebrowser.db
PASS_FILE=/etc/athena-filebrowser.pass
FB=/usr/bin/filebrowser
CMD="${1:-credentials}"

make_password() {
	od -An -N16 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n'
}
ensure_credentials() {
	[ -x "$FB" ] || return 1
	if [ ! -f "$DB" ]; then
		"$FB" -c "$DB" config init >/dev/null 2>&1 || return 1
	fi
	if [ ! -s "$PASS_FILE" ]; then
		PASS=$(make_password)
		[ "${#PASS}" -ge 32 ] || return 1
		if ! "$FB" -c "$DB" users update root --password "$PASS" >/dev/null 2>&1; then
			"$FB" -c "$DB" users add root "$PASS" --perm.admin >/dev/null 2>&1 || return 1
		fi
		umask 077
		printf '%s\n' "$PASS" > "$PASS_FILE.tmp" || return 1
		mv "$PASS_FILE.tmp" "$PASS_FILE" || return 1
		chmod 600 "$PASS_FILE" 2>/dev/null
	fi
	return 0
}
case "$CMD" in
	init|credentials)
		ensure_credentials || { echo '{"ok":false,"msg":"filebrowser 初始化或凭据准备失败，服务未启动"}'; exit 1; }
		PASS=$(cat "$PASS_FILE" 2>/dev/null)
		[ -n "$PASS" ] || { echo '{"ok":false,"msg":"未能读取 filebrowser 密码"}'; exit 1; }
		if [ "$CMD" = "credentials" ]; then
			# 用户主动打开文件共享面板时启动服务；默认不对外自启动，避免无意中长期开放文件入口。
			if ! pidof filebrowser >/dev/null 2>&1; then
				/etc/init.d/filebrowser start >/dev/null 2>&1 || { echo '{"ok":false,"msg":"文件共享启动失败，请确认 LAN 地址与服务状态"}'; exit 1; }
				sleep 1
			fi
			if pidof filebrowser >/dev/null 2>&1; then RUNNING=true; else echo '{"ok":false,"msg":"文件共享进程未能启动，请检查服务日志"}'; exit 1; fi
			printf '{"ok":true,"username":"root","password":"%s","running":%s,"root":"/mnt/usb"}\n' "$PASS" "$RUNNING"
		fi
		;;
	*) echo '{"ok":false,"msg":"未知命令"}'; exit 1 ;;
esac
