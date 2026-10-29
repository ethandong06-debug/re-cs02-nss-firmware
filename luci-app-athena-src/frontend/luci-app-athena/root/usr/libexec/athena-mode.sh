#!/bin/sh
# AthenaWrt 组网模式一键切换
# 用法:
#   athena-mode.sh router [pppoe|dhcp|static] [username] [password]  主路由
#   athena-mode.sh ap                                     AP 桥接
#   athena-mode.sh single <inner_vlan> <wan_vlan> <iptv_vlan> [proto] [username] [password] [nss] [iptv_port]  单臂路由
#   athena-mode.sh bypass <ip> <gateway> <dns>           旁路由
# 单臂路由参数：<内网 VLAN(默认1)> <拨号 VLAN(默认2044)> <IPTV VLAN(默认3066, off=关闭)> [proto] [账号] [密码] [nss: on|off] [iptv_port: lan1-lan4]
# 进度上报：single-bg 后台模式写进度到 /tmp/athena-mode-progress（前端弹窗轮询），
#           athena-mode.sh progress 读取当前进度文本（含步骤：备份→VLAN创建→网桥重建→拨号挂接→IPTV透传→回写→提交重启）
# 单臂路由（三层 VLAN 子接口方案，保 NSS）：
#   内网回传 VLAN1 → wan.1 → 直接桥接入 br-lan（VLAN1 内网设备与 LAN/WiFi 同二层域，
#                      dhcp.lan 统一分配，无需独立 DHCP 段；IPTV 关闭时 lan4 一并回桥）
#   拨号 VLAN2044 → wan.2044 → 原 network.wan 接口直接改造拨号（PPPoE/静态/DHCP），
#                      防火墙 wan 区域 / NAT / 默认路由 / IPv6 全部保留不重建
#   IPTV VLAN3066 → wan.3066 → br-iptv 网桥（wan.3066 + 功能口 lan4）二层透传，lan4 不入 br-lan
#   交换机接雅典娜 wan 的口：Trunk（Tagged 1/2044/3066，PVID 保持 1 默认）
#   交换机普通口（光猫LAN/电脑/AP）：Access PVID=1 Untagged（默认即 VLAN1）
#   不开 br-lan 的 vlan_filtering（保住 NSS 硬件加速）
# 切换前自动备份可回滚；默认 LAN 管理 IP = 192.168.10.1
#
# 真机 DSA 端口（已按 board.d 02_network / DTS 校准）：
#   lan1 lan2 lan3 lan4 = 4×1G 内网口   wan = 2.5G 口（QCA8081）

MODE="${1:-router}"
BACKUP_DIR="/etc/athena-backup"
TS=$(date +%Y%m%d%H%M%S)

# log 必须输出到 stderr：脚本 stdout 只用于最终 JSON，否则会污染 rpcd 返回值导致前端解析失败
log() { echo "[athena-mode] $*" >&2; }

# ---- 单臂配置进度上报（前端弹窗轮询读取）----
# 前台同步执行时直接透传进度；single-bg 后台模式把进度写入文件供前端轮询
PROG_FILE=/tmp/athena-mode-progress
pstep() { echo "$*" >> "$PROG_FILE"; }
prog_reset() { : > "$PROG_FILE"; }
prog_show() { cat "$PROG_FILE" 2>/dev/null; }

# ---- 备份当前网络配置 ----
backup() {
	mkdir -p "$BACKUP_DIR"
	uci export network > "$BACKUP_DIR/network.$TS.uci" 2>/dev/null
	uci export wireless > "$BACKUP_DIR/wireless.$TS.uci" 2>/dev/null
	log "已备份网络配置到 $BACKUP_DIR/network.$TS.uci"
}

# ---- 定位 br-lan 的 device 段（config_generate 生成的匿名段，name='br-lan'）----
br_dev() {
	uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)\.name='br-lan'$/\1/p" | head -1
}

# ---- 确保 br-lan device 段显式存在（默认固件 br-lan 是 netifd 运行时生成的，
#      不出现在 /etc/config/network 里，必须显式定义才能设置 vlan_filtering，
#      否则 DSA bridge-vlan 全部失效、VLAN 子接口无法创建，导致 LAN/WiFi 断网）----
ensure_br_device() {
	local name="${1:-br-lan}"
	local sec=$(uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)\.name='$name'$/\1/p" | head -1)
	if [ -z "$sec" ]; then
		uci -q add network device >/dev/null || return 1
		sec="network.@device[-1]"
		uci set "$sec.name=$name"
		uci set "$sec.type=bridge"
	fi
	echo "$sec"
}

# ---- 确保命名 device 段存在（通用，可选指定类型，如 br-iptv bridge）----
ensure_device() {
	local name="$1" type="$2"
	local sec=$(uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)\.name='$name'$/\1/p" | head -1)
	if [ -z "$sec" ]; then
		uci add network device >/dev/null || return 1
		sec="network.@device[-1]"
		uci set "$sec.name=$name"
		[ -n "$type" ] && uci set "$sec.type=$type"
	fi
	echo "$sec"
}

# ---- 按名称删除 device 段（如 wan.10 / br-iptv）----
del_device_by_name() {
	local name="$1"
	local sec=$(uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)\.name='$name'$/\1/p" | head -1)
	[ -n "$sec" ] && uci -q delete "$sec" 2>/dev/null
}

# ---- 删除所有 wan.X 8021q VLAN 设备（清理单臂残留）----
del_wan_vlan_devs() {
	for d in $(uci -q show network 2>/dev/null | sed -n "s/^network\.\(@device\[[0-9]*\]\)\.name='\(wan\.[0-9]*\)'$/\2/p"); do
		del_device_by_name "$d"
	done
}

# ---- 创建 802.1Q VLAN 子接口设备（如 wan.20，LuCI「设备」页同款）----
add_vlan_dev() {
	local name="$1" base="$2" vid="$3"
	uci add network device >/dev/null
	uci set network.@device[-1].name="$name"
	uci set network.@device[-1].type='8021q'
	uci set network.@device[-1].ifname="$base"
	uci set network.@device[-1].vid="$vid"
}

# ---- 按 name 查找 firewall zone 段（如 lan/wan）----
find_zone() {
	uci -q show firewall 2>/dev/null | sed -n "s/^firewall\.\(@zone\[[0-9]*\]\)\.name='$1'$/\1/p" | head -1
}

# ---- 删除所有 bridge-vlan 段（匿名 + 命名都覆盖）----
clear_bridge_vlan() {
	for s in $(uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)=bridge-vlan$/\1/p"); do
		uci -q delete "$s"
	done
}

# ---- 重建 br-lan 桥成员（保留无线接口，防止全量替换踢掉 wlan 导致 WiFi 断网）----
set_bridge_ports() {
	local br="$1"; shift
	[ -n "$br" ] || return 1
	# 当前成员中保留无线接口（wlan* 等），排除有线口 lan1-4/wan 及全部 wan.X VLAN 子接口
	# （VLAN 子接口是单臂模式专属，切换模式时其 device 段已删，若保留引用会导致桥含已删设备）
	local keep=""
	for p in $(uci -q get "$br.ports" 2>/dev/null); do
		case "$p" in lan1|lan2|lan3|lan4|wan|wan.*) ;; *) keep="$keep $p" ;; esac
	done
	uci -q delete "$br.ports" 2>/dev/null
	for p in $keep "$@"; do
		[ -n "$p" ] && uci add_list "$br.ports=$p"
	done
}

# ---- 确保 br-lan 桥开启 VLAN filtering（DSA bridge-vlan 生效前提）----
enable_vlan_filtering() {
	local br="$1"; [ -n "$br" ] || return 1
	uci -q set "$br.vlan_filtering=1"
}

# ---- VLAN ID 校验（1-4094 纯数字；空串=关闭该功能）----
valid_vlan() {
	case "$1" in
		'') return 0 ;;
		*[!0-9]*) return 1 ;;
	esac
	[ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 4094 ] 2>/dev/null
}

# ---- 移除 br-lan 里非内网口（wan），恢复纯内网桥 ----
detach_wan_from_bridge() {
	local br="$1"; [ -n "$br" ] || return 0
	uci -q del_list "$br.ports=wan" 2>/dev/null
}

# ---- NSS 开关 ----
nss_off() {
	log "关闭软件 flow offload（旁路由/AP 用）"
	uci -q set firewall.@defaults[0].flow_offloading='0'
	uci -q delete firewall.@defaults[0].flow_offloading_hw 2>/dev/null
	[ -x /etc/init.d/qca-nss-ecm ] && /etc/init.d/qca-nss-ecm stop 2>/dev/null
}

nss_on() {
	log "开启 NSS 硬件加速（ECM offload）"
	[ -x /etc/init.d/qca-nss-ecm ] && /etc/init.d/qca-nss-ecm start 2>/dev/null
	uci -q set firewall.@defaults[0].flow_offloading='0'
}

# ---- 各模式配置 ----
config_router() {
	local proto="${2:-pppoe}" user="${3:-}" pass="${4:-}" ip="${5:-}" mask="${6:-}" gw="${7:-}" dns="${8:-}"
	log "配置为 主路由模式（WAN=$proto）"

	# 清理单臂残留：bridge-vlan、wan.X 子接口、br-iptv、单臂专用接口、防火墙还原
	clear_bridge_vlan
	del_wan_vlan_devs
	del_device_by_name br-iptv
	uci -q delete network.lan_remote 2>/dev/null
	uci -q delete network.wan_pppoe 2>/dev/null
	uci -q delete network.iptv 2>/dev/null
	uci -q delete dhcp.lan_remote 2>/dev/null
	LANZ=$(find_zone lan)
	[ -n "$LANZ" ] && uci -q del_list "$LANZ.network=lan_remote" 2>/dev/null
	WANZ=$(find_zone wan)
	[ -n "$WANZ" ] && { uci -q del_list "$WANZ.network=wan_pppoe" 2>/dev/null; uci -q del_list "$WANZ.network=wan" 2>/dev/null; uci -q add_list "$WANZ.network=wan"; }

	BR=$(ensure_br_device br-lan)
	[ -n "$BR" ] && set_bridge_ports "$BR" lan1 lan2 lan3 lan4

	uci set network.lan.proto='static'
	uci set network.lan.ipaddr='192.168.10.1'
	uci set network.lan.netmask='255.255.255.0'
	uci -q set network.lan.device='br-lan'
	uci -q delete network.lan.gateway 2>/dev/null
	uci -q delete network.lan.dns 2>/dev/null

	uci set network.wan.device='wan'
	uci set network.wan.proto="$proto"
	if [ "$proto" = "pppoe" ]; then
		[ -n "$user" ] && uci set network.wan.username="$user"
		[ -n "$pass" ] && uci set network.wan.password="$pass"
	elif [ "$proto" = "static" ]; then
		# 静态 IP：IP/掩码/网关/DNS 完整写入，避免 wan.proto=static 却无地址导致断网
		[ -n "$ip" ] && uci set network.wan.ipaddr="$ip"
		[ -n "$mask" ] && uci set network.wan.netmask="$mask"
		[ -n "$gw" ] && uci set network.wan.gateway="$gw"
		[ -n "$dns" ] && uci -q add_list network.wan.dns="$dns"
	else
		uci -q delete network.wan.username 2>/dev/null
		uci -q delete network.wan.password 2>/dev/null
	fi
	uci -q set network.wan6.device='wan'
	uci -q set network.wan6.proto='dhcpv6'

	uci -q set dhcp.lan.ignore='0'
	uci -q set dhcp.lan.dhcpv4='server'
	nss_on
}

config_ap() {
	log "配置为 AP 桥接模式"
	# 清理单臂残留（同 router）
	clear_bridge_vlan
	del_wan_vlan_devs
	del_device_by_name br-iptv
	uci -q delete network.lan_remote 2>/dev/null
	uci -q delete network.wan_pppoe 2>/dev/null
	uci -q delete network.iptv 2>/dev/null
	uci -q delete dhcp.lan_remote 2>/dev/null
	LANZ=$(find_zone lan)
	[ -n "$LANZ" ] && uci -q del_list "$LANZ.network=lan_remote" 2>/dev/null
	WANZ=$(find_zone wan)
	[ -n "$WANZ" ] && { uci -q del_list "$WANZ.network=wan_pppoe" 2>/dev/null; uci -q del_list "$WANZ.network=wan" 2>/dev/null; uci -q add_list "$WANZ.network=wan"; }

	BR=$(ensure_br_device br-lan)
	[ -n "$BR" ] && set_bridge_ports "$BR" lan1 lan2 lan3 lan4

	uci set network.lan.proto='dhcp'
	uci -q set network.lan.device='br-lan'
	uci -q delete network.lan.ipaddr 2>/dev/null
	uci -q delete network.lan.netmask 2>/dev/null
	uci -q delete network.lan.gateway 2>/dev/null
	uci -q set dhcp.lan.ignore='1'
	uci -q delete network.wan 2>/dev/null
	uci -q delete network.wan6 2>/dev/null
	# AP/旁路由无 wan 接口：同步清理防火墙 wan 区域对 network=wan 的引用，避免 fw4 reload 告警
	[ -n "$WANZ" ] && uci -q del_list "$WANZ.network=wan" 2>/dev/null
	nss_off
}

config_single() {
	local vlan_inner="${2:-1}" vlan_wan="${3:-2044}" vlan_iptv="${4:-3066}"
	local proto="${5:-pppoe}" user="${6:-}" pass="${7:-}"
	local nss="${8:-on}" iptv_port="${9:-lan4}"
	# 归一化 IPTV 参数：off/none/关闭/留空 一律视为不开启（前端旧版曾传 'off' 字符串）
	case "$vlan_iptv" in off|none|OFF|NONE|"关闭"|"无") vlan_iptv='' ;; esac
	log "配置为 单臂路由（内网VLAN=$vlan_inner, 拨号VLAN=$vlan_wan, IPTV=${vlan_iptv:-无}, proto=$proto, NSS=$nss, IPTV口=$iptv_port）"

	# ---- 参数校验（误配会直接打断网络，先拦）----
	for v in "$vlan_inner" "$vlan_wan" "$vlan_iptv"; do
		if [ -n "$v" ] && ! valid_vlan "$v"; then
			echo '{"ok":false,"msg":"VLAN ID 必须为 1-4094 的纯数字（IPTV 可留空关闭）"}'
			exit 1
		fi
	done
	case "$iptv_port" in lan1|lan2|lan3|lan4) ;; *) echo '{"ok":false,"msg":"IPTV 透传端口必须是 lan1-lan4"}'; exit 1 ;; esac
	case "$nss" in on|off) ;; *) echo '{"ok":false,"msg":"NSS 参数必须是 on|off"}'; exit 1 ;; esac

	# ---- 清理旧方案残留：bridge-vlan filtering 段、旧 wan.X 子接口、单臂专用接口 ----
	clear_bridge_vlan
	del_wan_vlan_devs
	del_device_by_name br-iptv
	uci -q delete network.lan_remote 2>/dev/null
	uci -q delete network.wan_pppoe 2>/dev/null
	uci -q delete network.iptv 2>/dev/null
	uci -q delete dhcp.lan_remote 2>/dev/null
	pstep "旧方案残留已清理"

	# ---- 网桥与 lan/wan 接口重置为默认形态：删除旧段，由下方生成逻辑重建干净配置 ----
	# 删 br-lan 段前先捕获现有无线桥成员（wlan*），重建后显式写回，防止 WiFi 断网
	# lan/wan 接口段删除后由下方 uci set 自动重建（防火墙 zone 按名引用 lan/wan，重建即归位）；
	# wan6 保留不删（IPv6 配置随模式保留，仅下方覆盖承载口）
	local LBX WK=""
	LBX=$(br_dev)
	if [ -n "$LBX" ]; then
		for p in $(uci -q get "$LBX.ports" 2>/dev/null); do
			case "$p" in wlan*) WK="$WK $p" ;; esac
		done
		uci -q delete "$LBX" 2>/dev/null
	fi
	uci -q delete network.lan 2>/dev/null
	uci -q delete network.wan 2>/dev/null

	# ---- 创建 802.1Q VLAN 子接口设备（LuCI「设备」页同款：wan.1 / wan.2044 / wan.3066）----
	add_vlan_dev "wan.${vlan_inner}" wan "$vlan_inner"
	add_vlan_dev "wan.${vlan_wan}" wan "$vlan_wan"
	if [ -n "$vlan_iptv" ]; then add_vlan_dev "wan.${vlan_iptv}" wan "$vlan_iptv"; fi
	pstep "VLAN 子接口已创建（wan.${vlan_inner} / wan.${vlan_wan}$([ -n "$vlan_iptv" ] && echo " / wan.${vlan_iptv}")）"

	# ---- br-lan：lan1 lan2 lan3 + WiFi + 内网回传 VLAN 子接口（wan.$vlan_inner 桥接入，
	#      VLAN 内网设备与 LAN/WiFi 同二层域，dhcp.lan 自动覆盖，无需额外 DHCP 段）；
	#      不开 vlan_filtering（保住 NSS 硬件加速）。
	#      注意：IPTV 开启时 lan4 留给 br-iptv，不入 br-lan；IPTV 关闭时 lan4 回到 br-lan（防孤儿口）----
	BR=$(ensure_br_device br-lan)
	if [ -n "$vlan_iptv" ]; then
		[ -n "$BR" ] && set_bridge_ports "$BR" $WK lan1 lan2 lan3 "wan.${vlan_inner}"
	else
		[ -n "$BR" ] && set_bridge_ports "$BR" $WK lan1 lan2 lan3 lan4 "wan.${vlan_inner}"
	fi
	uci set network.lan=interface
	uci set network.lan.proto='static'
	uci set network.lan.ipaddr='192.168.10.1'
	uci set network.lan.netmask='255.255.255.0'
	uci set network.lan.device='br-lan'
	uci -q delete network.lan.gateway 2>/dev/null
	uci -q delete network.lan.dns 2>/dev/null
	uci -q set dhcp.lan.ignore='0'
	uci -q set dhcp.lan.dhcpv4='server'
	pstep "br-lan 网桥已重建（内网回传 VLAN${vlan_inner} 已桥接）"

	# ---- 原 wan 接口直接改造为拨号接口（挂 wan.拨号VLAN；防火墙 wan 区域、NAT/默认路由保留不动）----
	uci set network.wan=interface
	uci set network.wan.device="wan.${vlan_wan}"
	uci set network.wan.proto="$proto"
	if [ "$proto" = "pppoe" ]; then
		[ -n "$user" ] && uci set network.wan.username="$user"
		[ -n "$pass" ] && uci set network.wan.password="$pass"
	elif [ "$proto" = "static" ]; then
		# 前端传参格式：user="ip/mask/gw/dns"，逐项回写（缺省留空由 netifd 兜底）
		local sip smask sgw sdns
		sip=$(echo "$user" | cut -d/ -f1); smask=$(echo "$user" | cut -d/ -f2); sgw=$(echo "$user" | cut -d/ -f3); sdns=$(echo "$user" | cut -d/ -f4)
		[ -n "$sip" ] && uci set network.wan.ipaddr="$sip"
		[ -n "$smask" ] && uci set network.wan.netmask="$smask"
		[ -n "$sgw" ] && uci set network.wan.gateway="$sgw"
		[ -n "$sdns" ] && uci set network.wan.dns="$sdns"
	else
		uci -q delete network.wan.username 2>/dev/null
		uci -q delete network.wan.password 2>/dev/null
		uci -q delete network.wan.ipaddr 2>/dev/null
		uci -q delete network.wan.netmask 2>/dev/null
		uci -q delete network.wan.gateway 2>/dev/null
		uci -q delete network.wan.dns 2>/dev/null
	fi
	# IPv6 保留现有正常配置（不关闭），仅把 wan6 承载口指向拨号 VLAN 子接口，随模式恢复
	if [ -n "$(uci -q get network.wan6 2>/dev/null)" ]; then
		uci set network.wan6.device="wan.${vlan_wan}"
		[ -z "$(uci -q get network.wan6.proto 2>/dev/null)" ] && uci set network.wan6.proto='dhcpv6'
	fi
	pstep "WAN 拨号接口已挂接 wan.${vlan_wan}（${proto}）"

	# ---- IPTV：VLAN3066 → br-iptv 网桥（wan.3066 + 功能口 lan4）二层透传 ----
	if [ -n "$vlan_iptv" ]; then
		local IBR
		IBR=$(ensure_device br-iptv bridge)
		if [ -n "$IBR" ]; then
			uci -q delete "$IBR.ports" 2>/dev/null
			uci add_list "$IBR.ports=wan.${vlan_iptv}"
			uci add_list "$IBR.ports=$iptv_port"
		fi
		uci set network.iptv=interface
		uci set network.iptv.device='br-iptv'
		uci set network.iptv.proto='none'
		pstep "IPTV 透传已配置（${iptv_port} + wan.${vlan_iptv}）"
	else
		uci -q delete network.iptv 2>/dev/null
		pstep "IPTV 未开启（lan4 已回归 br-lan）"
	fi

	# ---- 防火墙：区域不动（wan 区域未改，原 wan 接口改造后仍在区域内）----

	# ---- 参数回写（供前端/状态页读取与真机校准；兼容新旧字段）----
	uci -q set athena.single.wan_vlan="$vlan_wan"
	uci -q set athena.single.inner_vlan="$vlan_inner"
	uci -q set athena.single.ret_vlan="$vlan_inner"
	uci -q set athena.single.wan_proto="$proto"
	if [ -n "$vlan_iptv" ]; then uci -q set athena.single.iptv_vlan="$vlan_iptv"; else uci -q delete athena.single.iptv_vlan 2>/dev/null; fi
	uci -q set athena.single.iptv_port="$iptv_port"
	pstep "参数已回写 athena.single（wan_vlan/ret_vlan/iptv_vlan/iptv_port）"

	if [ "$nss" = "off" ]; then
		nss_off
		log "单臂兼容模式：已关闭 ECM offload（hairpin 走 CPU 软转）"
	else
		nss_on
	fi
	pstep "NSS 硬件加速状态已设置"
}

# ---- 单臂配置检测（提交后核对是否真正写入后台；参数缺省读 athena.single 回写值）----
status_single() {
	local inner="${2:-}" wan="${3:-}" iptv="${4:-}"
	[ -z "$inner" ] && inner=$(uci -q get athena.single.inner_vlan 2>/dev/null)
	# 兼容真机旧字段：早期脚本写 ret_vlan，无 inner_vlan
	[ -z "$inner" ] && inner=$(uci -q get athena.single.ret_vlan 2>/dev/null)
	[ -z "$wan" ] && wan=$(uci -q get athena.single.wan_vlan 2>/dev/null)
	[ -z "$iptv" ] && iptv=$(uci -q get athena.single.iptv_vlan 2>/dev/null)
	# IPTV VLAN 字段缺失时，从 br-iptv 桥成员里的 wan.X 子接口探测 VID（真机现场无 iptv_vlan 字段场景）
	if [ -z "$iptv" ]; then
		local IPTVDEV WSV
		IPTVDEV=$(uci -q show network 2>/dev/null | sed -n "s/^network\.\([^.]*\)\.name='br-iptv'$/\1/p" | head -1)
		if [ -n "$IPTVDEV" ]; then
			for p in $(uci -q get "$IPTVDEV.ports" 2>/dev/null); do
				case "$p" in
					wan.*)
						WSV=$(uci -q show network 2>/dev/null | sed -n "s/^network\.\([^.]*\)\.name='$p'$/\1/p" | head -1)
						[ -n "$WSV" ] && iptv=$(uci -q get "$WSV.vid" 2>/dev/null)
						[ -n "$iptv" ] && break
						;;
				esac
			done
		fi
	fi

	dev_named() { uci -q show network 2>/dev/null | sed -n "s/^network\.\(@device\[[0-9]*\]\)\.name='$1'$/\1/p" | head -1; }

	local n=0 ok=0 bad=0
	local list=""
	add_item() { # $1=name $2=ok(1/0) $3=detail
		[ $n -gt 0 ] && list="$list,"
		list="$list{\"name\":\"$1\",\"ok\":$([ "$2" = 1 ] && echo true || echo false),\"detail\":\"$3\"}"
		n=$((n+1)); [ "$2" = 1 ] && ok=$((ok+1)) || bad=$((bad+1))
	}

	# 1-2. VLAN 子接口设备
	local D
	D=$(dev_named "wan.$inner"); add_item "VLAN 设备 wan.$inner" $([ -n "$D" ] && echo 1 || echo 0) "$([ -n "$D" ] && echo 已创建 || echo 缺失)"
	D=$(dev_named "wan.$wan"); add_item "VLAN 设备 wan.$wan" $([ -n "$D" ] && echo 1 || echo 0) "$([ -n "$D" ] && echo 已创建 || echo 缺失)"
	if [ -n "$iptv" ]; then
		D=$(dev_named "wan.$iptv"); add_item "VLAN 设备 wan.$iptv（IPTV）" $([ -n "$D" ] && echo 1 || echo 0) "$([ -n "$D" ] && echo 已创建 || echo 缺失)"
	fi

	# 3. 原 wan 接口改造为拨号接口（挂 wan.$wan，防火墙域无需改动）
	local WP
	WP=$(uci -q get network.wan.device 2>/dev/null)
	local WPR
	WPR=$(uci -q get network.wan.proto 2>/dev/null)
	add_item "WAN 拨号接口（原 wan 改造）" $([ "$WP" = "wan.$wan" ] && [ "$WPR" != "none" ] && echo 1 || echo 0) "$([ "$WP" = "wan.$wan" ] && [ "$WPR" != "none" ] && echo "已挂 wan.$wan（$WPR）" || echo "当前 wan.$WP / $WPR")"

	# 4. br-lan 桥接内网 VLAN（wan.$inner 已加入 br-lan 桥，VLAN10 内网设备同二层域）
	local BRD BRP
	BRD=$(uci -q show network 2>/dev/null | sed -n "s/^network\.\(@device\[[0-9]*\]\)\.name='br-lan'$/\1/p" | head -1)
	BRP=$(uci -q get "$BRD.ports" 2>/dev/null)
	case "$BRP" in
		*"wan.$inner"*) add_item "br-lan 桥接 wan.$inner（内网 VLAN）" 1 "已桥接，VLAN10 设备与 LAN/WiFi 同网段" ;;
		*) add_item "br-lan 桥接 wan.$inner（内网 VLAN）" 0 "桥成员中未找到 wan.$inner" ;;
	esac

	# 4b. lan 接口承载：device 必须指向 br-lan 且静态 IP 已配置（缺失 device 会导致管理地址不落桥、后台失联）
	local LDEV LIP
	LDEV=$(uci -q get network.lan.device 2>/dev/null)
	LIP=$(uci -q get network.lan.ipaddr 2>/dev/null)
	add_item "LAN 管理接口（192.168.10.1 @ br-lan）" $([ "$LDEV" = "br-lan" ] && [ -n "$LIP" ] && echo 1 || echo 0) "$([ "$LDEV" = "br-lan" ] && [ -n "$LIP" ] && echo "已绑定 $LDEV（$LIP）" || echo "当前 device=$LDEV ipaddr=$LIP，需 device=br-lan")"

	# 5. br-iptv 网桥（IPTV 开启时）
	if [ -n "$iptv" ]; then
		local BP
		BP=$(uci -q get network.iptv.device 2>/dev/null)
		add_item "网桥 br-iptv / iptv 接口" $([ "$BP" = "br-iptv" ] && echo 1 || echo 0) "$([ "$BP" = "br-iptv" ] && echo 已挂 br-iptv || echo 未挂 br-iptv)"
		# lan4 归属：IPTV 开启时应只在 br-iptv，不在 br-lan
		case "$BRP" in
			*lan4*) add_item "lan4 归属（IPTV 透传口）" 0 "lan4 仍在 br-lan，应只在 br-iptv（当前桥成员：$BRP）" ;;
			*) add_item "lan4 归属（IPTV 透传口）" 1 "已从 br-lan 移出，专用于 br-iptv" ;;
		esac
	else
		# lan4 归属：IPTV 关闭时应回到 br-lan（防孤儿口）
		case "$BRP" in
			*lan4*) add_item "lan4 归属（无 IPTV）" 1 "已留在 br-lan，LAN4 可正常使用" ;;
			*) add_item "lan4 归属（无 IPTV）" 0 "lan4 不在 br-lan（孤儿口），需重跑单臂配置或改回主路由" ;;
		esac
	fi

	# 6. IPv6 保留：wan6 存在且 proto 未被关闭，承载口指向拨号 VLAN
	local W6D W6P
	W6D=$(uci -q get network.wan6.device 2>/dev/null)
	W6P=$(uci -q get network.wan6.proto 2>/dev/null)
	if [ -n "$(uci -q get network.wan6 2>/dev/null)" ]; then
		add_item "IPv6 保留（wan6）" $([ "$W6P" != "none" ] && [ "$W6D" = "wan.$wan" ] && echo 1 || echo 0) "$([ "$W6P" != "none" ] && [ "$W6D" = "wan.$wan" ] && echo "已保留（$W6P @ $W6D）" || echo "当前 proto=$W6P device=$W6D")"
	else
		add_item "IPv6 保留（wan6）" 0 "wan6 接口不存在（若曾手动删除则跳过）"
	fi

	echo "{\"mode\":\"single\",\"ok\":$ok,\"bad\":$bad,\"items\":[$list]}"
}

config_bypass() {
	local ip="${2:-192.168.10.2}" gw="${3:-192.168.10.1}" dns="${4:-192.168.10.1}"
	log "配置为 旁路由模式（IP=$ip, GW=$gw, DNS=$dns）"
	# 清理单臂残留（同 router）
	clear_bridge_vlan
	del_wan_vlan_devs
	del_device_by_name br-iptv
	uci -q delete network.lan_remote 2>/dev/null
	uci -q delete network.wan_pppoe 2>/dev/null
	uci -q delete network.iptv 2>/dev/null
	uci -q delete dhcp.lan_remote 2>/dev/null
	LANZ=$(find_zone lan)
	[ -n "$LANZ" ] && uci -q del_list "$LANZ.network=lan_remote" 2>/dev/null
	WANZ=$(find_zone wan)
	[ -n "$WANZ" ] && { uci -q del_list "$WANZ.network=wan_pppoe" 2>/dev/null; uci -q del_list "$WANZ.network=wan" 2>/dev/null; uci -q add_list "$WANZ.network=wan"; }

	BR=$(ensure_br_device br-lan)
	[ -n "$BR" ] && set_bridge_ports "$BR" lan1 lan2 lan3 lan4

	uci set network.lan.proto='static'
	uci set network.lan.ipaddr="$ip"
	uci set network.lan.netmask='255.255.255.0'
	uci -q set network.lan.device='br-lan'
	uci -q set network.lan.gateway="$gw"
	uci -q delete network.lan.dns 2>/dev/null
	uci -q add_list network.lan.dns="$dns"
	uci -q set dhcp.lan.ignore='1'
	uci -q delete network.wan 2>/dev/null
	uci -q delete network.wan6 2>/dev/null
	# AP/旁路由无 wan 接口：同步清理防火墙 wan 区域对 network=wan 的引用，避免 fw4 reload 告警
	[ -n "$WANZ" ] && uci -q del_list "$WANZ.network=wan" 2>/dev/null
	nss_off
}

# ---- 主流程 ----
# 单臂配置检测（只读）必须先于 backup：backup 会向 stdout 输出日志，污染 JSON，前端将解析失败
case "$MODE" in
	single-status) status_single "$@"; exit 0 ;;
	progress) prog_show; exit 0 ;;
	# 单臂后台模式：前端弹窗轮询进度文件（single-bg 与原 single 同参数，内部先清空进度文件再后台执行）
	single-bg)
		prog_reset
		pstep "单臂路由配置开始…"
		# 参数校验前移到前台，错误立即返回（避免后台失败无反馈）
		for v in "${2:-1}" "${3:-2044}" "${4:-3066}"; do
			if [ -n "$v" ] && ! valid_vlan "$v"; then
				echo '{"ok":false,"msg":"VLAN ID 必须为 1-4094 的纯数字"}'
				exit 1
			fi
		done
		(
			# 后台执行完整配置：备份 → 配置 → 提交 → 重启
			backup
			pstep "网络配置已备份（可回滚）"
			# 去掉 single-bg 前缀，让 config_single 的 $2..$9 对齐 <inner> <wan> <iptv> [proto] [user] [pass] [nss] [port]
			shift 1
			config_single single "$@"
			rc=$?
			if [ $rc -ne 0 ]; then
				pstep "配置失败，已中止（网络未变更）"
				exit $rc
			fi
			uci commit network
			uci commit wireless 2>/dev/null
			uci commit dhcp 2>/dev/null
			uci commit firewall 2>/dev/null
			uci -q set athena.system.mode='single'
			uci commit athena 2>/dev/null
			pstep "配置已提交，网络重启生效中…"
			# 应用后自检 + 失败自动回滚：8 秒后检查 br-lan 管理 IP，未恢复则从备份回滚并重启网络，
			# 防止"WiFi 在但后台进不去"的锁死状态（hostapd 独立于 netifd，network 失败 WiFi 仍广播）
			( sleep 8
			  if ! ip -4 addr show dev br-lan 2>/dev/null | grep -q '192.168.10.1'; then
			    echo "自检失败：br-lan 未获得管理 IP（192.168.10.1），自动回滚…" >> "$PROG_FILE"
			    latest=$(ls -t "$BACKUP_DIR"/network.*.uci 2>/dev/null | head -1)
			    if [ -n "$latest" ]; then
			      uci import network < "$latest" 2>/dev/null
			      uci commit network 2>/dev/null
			      uci -q set athena.system.mode='router'
			      uci commit athena 2>/dev/null
			      /etc/init.d/network restart >/dev/null 2>&1
			      echo "已自动回滚至备份：$(basename "$latest")" >> "$PROG_FILE"
			    else
			      echo "无备份可回滚！请手动检查网络配置或恢复出厂" >> "$PROG_FILE"
			    fi
			  else
			    echo "自检通过：br-lan 管理 IP 正常" >> "$PROG_FILE"
			  fi ) &
			pstep "完成：单臂路由已生效"
		) &
		echo '{"ok":true,"async":true,"progress":"'$PROG_FILE'"}'
		exit 0
		;;
esac

backup

case "$MODE" in
	router)  config_router "$@" ;;
	ap)      config_ap ;;
	single)  config_single "$@" ;;
	single-status) status_single "$@" ;;
	bypass)  config_bypass "$@" ;;
	*) log "未知模式: $MODE（支持 router|ap|single|single-bg|single-status|bypass|progress）"; exit 1 ;;
esac

uci commit network
uci commit wireless 2>/dev/null
uci commit dhcp 2>/dev/null
uci commit firewall 2>/dev/null

uci -q set athena.system.mode="$MODE"
uci commit athena 2>/dev/null

# 应用网络配置：延迟后台重启网络栈。
# 关键：network restart 会短暂断开 LAN/WAN，若同步执行会中断 rpcd 响应，
# 导致前端 fetch 超时误判"后端失败"。故先返回成功，再后台重启。
( sleep 1; /etc/init.d/network restart >/dev/null 2>&1 || wifi reload >/dev/null 2>&1 ) &
# 自检 + 失败自动回滚（仅单臂模式需要：管理 IP 丢失会锁死后台）
if [ "$MODE" = "single" ]; then
	( sleep 8
	  if ! ip -4 addr show dev br-lan 2>/dev/null | grep -q '192.168.10.1'; then
	    latest=$(ls -t "$BACKUP_DIR"/network.*.uci 2>/dev/null | head -1)
	    if [ -n "$latest" ]; then
	      uci import network < "$latest" 2>/dev/null
	      uci commit network 2>/dev/null
	      uci -q set athena.system.mode='router'
	      uci commit athena 2>/dev/null
	      /etc/init.d/network restart >/dev/null 2>&1
	      log "单臂应用自检失败，已自动回滚至备份：$(basename "$latest")"
	    else
	      log "单臂应用自检失败，无备份可回滚！"
	    fi
	  else
	    log "单臂应用自检通过：br-lan 管理 IP 正常"
	  fi ) &
fi

log "配置完成，模式=$MODE"
echo "{\"ok\":true,\"msg\":\"组网模式已切换为 $MODE，网络正在重启生效\"}"
