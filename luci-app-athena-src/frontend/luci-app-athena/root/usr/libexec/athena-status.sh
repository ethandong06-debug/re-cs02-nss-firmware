#!/bin/sh
# AthenaWrt 状态聚合入口 v1.2.45
# 采样逻辑已搬到 ucode：/usr/libexec/athena-status.uc
#   1) 所有 /proc、/sys、/etc 数据在 ucode 进程内直接读，不再 fork 上百个 sed/awk/cat
#      （编译机实测 execve 294 → 19，单次 0.19s → 0.01s；真机原为 1.41s）
#   2) 输出 JSON 的字段名、类型、顺序与 shell 版完全一致，前端不用改一行
#   3) ucode 不可用、或运行失败输出为空/不是 JSON 时，自动回退 athena-status-legacy.sh
#      回退版就是 v1.2.44 之前一直在用的 shell 实现，行为不变

# v1.2.57：`athena-status.sh rate` 是只读 /proc 的快速采样（约 10ms），供首页「实时网速」2 秒轮询；
#   走这个入口的好处是 rpcd 的 ACL 只认 /usr/libexec/athena-status.sh 这一条，不必新增放行项。
if [ "$1" = "rate" ]; then
	if [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-rate.uc ]; then
		exec /usr/bin/ucode /usr/libexec/athena-rate.uc
	fi
	printf '%s\n' '{"ok":false,"rx_mbps":0,"tx_mbps":0,"dt_ms":0}'
	exit 0
fi

if [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-status.uc ]; then
	_out=$(/usr/bin/ucode /usr/libexec/athena-status.uc 2>/dev/null)
	case "$_out" in
	'{"system"'*)
		printf '%s\n' "$_out"
		exit 0
		;;
	esac
fi

exec /usr/libexec/athena-status-legacy.sh
