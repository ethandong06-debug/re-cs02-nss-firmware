#!/bin/sh
# AthenaWrt 资源监控入口（v1.2.44）
#
# 采样逻辑已搬到 ucode：/usr/libexec/athena-resources.uc
#   旧实现一次采样触发 459 次 execve（146 进程 × 3 个外部命令），真机 1.80 秒；
#   ucode 版一次采样只 1 次 execve，编译器实测 0.02 秒。
# 本脚本只保留：
#   1) 进程启停（stop/restart —— 这一步要 kill，本来就要起进程，频率极低）
#   2) 入口：exec 到 ucode；ucode 不可用时回退到 legacy shell 实现
#
# rpcd ACL 仍只认这个路径，所以前端/ACL 都不用改。

# ---- 进程操作：stop <pid> / restart <pid>（供资源排行启停按钮）----
if [ "$1" = "stop" ] || [ "$1" = "restart" ]; then
	PID="${2:-}"
	{ [ -n "$PID" ] && [ "$PID" -gt 1 ]; } 2>/dev/null || { echo '{"ok":false,"msg":"无效的 PID"}'; exit 1; }
	[ -d "/proc/$PID" ] || { echo '{"ok":false,"msg":"进程不存在"}'; exit 1; }
	NAME=$(tr -d '\0' < "/proc/$PID/comm" 2>/dev/null)
	[ -n "$NAME" ] || NAME="unknown"
	# 内核线程（comm 形如 [kworker/x]）与核心进程保护
	case "$NAME" in *"["*) echo '{"ok":false,"msg":"内核线程受保护，不允许操作"}'; exit 1 ;; esac
	[ "$PID" -le 2 ] && { echo '{"ok":false,"msg":"系统核心进程受保护"}'; exit 1; }
	# 关键系统服务进程保护：误停会断网/丢 WiFi/失联（网络、无线、管理、拨号、DNS 等）
	case "|$NAME|" in
		*"|wpad|"*|*"|hostapd|"*|*"|hostapd_cli|"*|*"|netifd|"*|*"|dnsmasq|"*|*"|odhcpd|"*|*"|odhcp6c|"*|*"|ubusd|"*|*"|rpcd|"*|*"|uhttpd|"*|*"|lighttpd|"*|*"|dropbear|"*|*"|logd|"*|*"|syslogd|"*|*"|pppd|"*|*"|pppoe|"*)
			echo '{"ok":false,"msg":"关键系统服务受保护，不允许停止/重启（会导致断网或失联）"}'; exit 1 ;;
	esac
	kill -9 "$PID" 2>/dev/null
	if [ "$1" = "restart" ]; then
		sleep 1
		if [ -x "/etc/init.d/$NAME" ]; then
			/etc/init.d/$NAME restart >/dev/null 2>&1
		fi
	fi
	echo "{\"ok\":true,\"pid\":$PID,\"name\":\"$NAME\",\"action\":\"$1\"}"
	exit 0
fi

# ---- 采样 ----
if [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-resources.uc ]; then
	exec /usr/bin/ucode /usr/libexec/athena-resources.uc
fi

# 兜底：ucode 缺失（理论不会发生，ucode 是 LuCI 的运行时）时走旧 shell 实现
exec /usr/libexec/athena-resources-legacy.sh
