#!/bin/sh
# ============================================================
#  AthenaWrt — 活跃应用识别数据源：开启 dnsmasq 查询日志
#  开启 logqueries 并把日志写到 /tmp/dnsmasq.log
#  （athena-apps.sh 读取该文件做 OAF/DNS 指纹识别）
#  注意：仅开启查询日志，不影响 DNS 解析行为；
#        /tmp 为 tmpfs，重启自动清空，无持久化负担。
# ============================================================

# dnsmasq 配置段（首个 @dnsmasq[0]）
if uci -q get dhcp.@dnsmasq[0] >/dev/null 2>&1; then
	# 开启查询日志 + 写文件（logread 也可见，但文件读取更高效稳定）
	uci -q set dhcp.@dnsmasq[0].logqueries='1'
	uci -q set dhcp.@dnsmasq[0].logfacility='/tmp/dnsmasq.log'
	uci -q commit dhcp
fi

exit 0
