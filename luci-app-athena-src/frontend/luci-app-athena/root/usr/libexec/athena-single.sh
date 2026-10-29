#!/bin/sh
# ============================================================
#  AthenaWrt 单臂路由脚本（按真机配置生成）
#  ============================================================
#  设备：京东云雅典娜 AX6600（JDCloud RE-CS-02 / IPQ6010 / 2.5G wan）
#  场景：交换机接雅典娜 wan（Trunk：Tagged 1/2044/3066，PVID=1）
#  真实参数（来自真机 uci show network / athena）：
#    内网回传 VLAN = 1      → wan.1  → 桥入 br-lan（LAN/WiFi 同二层域）
#    拨号   VLAN   = 2044   → wan.2044 → network.wan（PPPoE 拨号）
#    IPTV  VLAN   = 3066   → wan.3066 → br-iptv（+ lan4 二层透传）
#    IPTV 透传口   = lan4
#  ============================================================
#  用法（参数与 athena-mode.sh single 完全一致，供前端/SSH 按需传参）：
#    sh athena-single.sh <inner_vlan> <wan_vlan> <iptv_vlan> [iptv_port] [proto] [user] [pass]
#       <inner_vlan>  内网回传 VLAN（默认 1）
#       <wan_vlan>    拨号 VLAN（默认 2044）
#       <iptv_vlan>   IPTV VLAN；传 off / none / 留空 表示关闭 IPTV（不创建任何 IPTV 相关）
#       [iptv_port]   IPTV 透传口（lan1-lan4，默认 lan4）
#       [proto]       拨号方式（pppoe|dhcp|static，默认 pppoe）
#       [user] [pass] 宽带账号密码（缺省时读现有 network.wan，不硬编码）
#       例：sh athena-single.sh 1 2044 3066 lan4 pppoe user pass
#           sh athena-single.sh 1 2044 off lan4 dhcp        # 关闭 IPTV、DHCP 上网
#  ============================================================
#  特性：
#   - 完全按传入参数创建：VLAN 子接口 / lan 口归属 / 拨号账号密码
#   - IPTV VLAN 留空则：不创建 wan.$iptv、不建 br-iptv、lan4 回归 br-lan
#   - 切换前自动备份 /etc/athena-backup/network.<时间戳>.uci
#   - 修正 athena.system.mode=single（保证冷启动预建 VLAN + 自检生效）
#   - 保 NSS 硬件加速（不开 br-lan vlan_filtering）
#   - 应用后延迟后台重启网络栈，避免中断 rpcd 响应
#  ============================================================

INNER="${1:-1}"
WAN_VLAN="${2:-2044}"
IPTV_VLAN="${3:-3066}"
IPTV_PORT="${4:-lan4}"
WAN_PROTO="${5:-pppoe}"
PPPOE_USER="${6:-}"
PPPOE_PASS="${7:-}"
# IPTV 归一化：off/none/留空一律视为不开启
case "$IPTV_VLAN" in off|none|OFF|NONE|"关闭"|"无") IPTV_VLAN='' ;; esac

BACKUP_DIR="/etc/athena-backup"
TS=$(date +%Y%m%d%H%M%S)

# log 到 stderr，stdout 只输出最终 JSON
log() { echo "[athena-single] $*" >&2; }

# ---- 进度上报（与 athena-mode.sh 共用 /tmp/athena-mode-progress，前端弹窗轮询）----
PROG_FILE=/tmp/athena-mode-progress
pstep() { echo "$*" >> "$PROG_FILE"; }
prog_reset() { : > "$PROG_FILE"; }
prog_show() { cat "$PROG_FILE" 2>/dev/null; }

# ---- VLAN 校验 ----
valid_vlan() {
	case "$1" in
		''|off|none|OFF|NONE) return 0 ;;
		*[!0-9]*) return 1 ;;
	esac
	[ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 4094 ] 2>/dev/null
}

# ---- 按名称定位 device 段 ----
dev_named() {
	uci -q show network 2>/dev/null | sed -n "s/^\(network\.[^.]*\)\.name='$1'$/\1/p" | head -1
}
br_dev() { dev_named br-lan; }

# ---- 按名称删除 device 段 ----
del_dev() {
	local sec
	sec=$(dev_named "$1")
	[ -n "$sec" ] && uci -q delete "$sec" 2>/dev/null
}

# ---- 删除所有 wan.X 8021q 残留 ----
del_wan_vlans() {
	local sec
	for sec in $(uci -q show network 2>/dev/null | sed -n "s/^network\.\(@device\[[0-9]*\]\)\.name='\(wan\.[0-9]*\)'$/\1/p"); do
		uci -q delete "$sec" 2>/dev/null
	done
}

# ---- 确保命名 device 段存在 ----
ensure_dev() {
	local name="$1" type="$2" sec
	sec=$(dev_named "$name")
	if [ -z "$sec" ]; then
		uci add network device >/dev/null || return 1
		sec="network.@device[-1]"
		uci set "$sec.name=$name"
		[ -n "$type" ] && uci set "$sec.type=$type"
	fi
	echo "$sec"
}

# ---- 创建 8021q 子接口设备 ----
add_vlan_dev() {
	uci add network device >/dev/null
	uci set network.@device[-1].name="$1"
	uci set network.@device[-1].type='8021q'
	uci set network.@device[-1].ifname='wan'
	uci set network.@device[-1].vid="$2"
}

# ---- 重建 br-lan 桥成员（保留无线接口）----
set_bridge_ports() {
	local br="$1"; shift
	[ -n "$br" ] || return 1
	local keep="" p
	for p in $(uci -q get "$br.ports" 2>/dev/null); do
		case "$p" in lan1|lan2|lan3|lan4|wan|wan.*) ;; *) keep="$keep $p" ;; esac
	done
	uci -q delete "$br.ports" 2>/dev/null
	for p in $keep "$@"; do
		[ -n "$p" ] && uci add_list "$br.ports=$p"
	done
}

# ---- 主流程 ----
# 参数校验
for v in "$INNER" "$WAN_VLAN" "$IPTV_VLAN"; do
	if ! valid_vlan "$v"; then
		echo '{"ok":false,"msg":"VLAN ID 必须为 1-4094 纯数字（IPTV 可传 off 关闭）"}'
		exit 1
	fi
done
case "$IPTV_PORT" in lan1|lan2|lan3|lan4) ;; *) echo '{"ok":false,"msg":"IPTV 透传端口必须是 lan1-lan4"}'; exit 1 ;; esac

# 清空进度文件，开始上报
prog_reset
pstep "单臂路由配置开始（内网VLAN=$INNER 拨号VLAN=$WAN_VLAN IPTV=${IPTV_VLAN:-关闭}）"

# 备份
mkdir -p "$BACKUP_DIR"
uci export network > "$BACKUP_DIR/network.$TS.uci" 2>/dev/null
uci export wireless > "$BACKUP_DIR/wireless.$TS.uci" 2>/dev/null
log "已备份到 $BACKUP_DIR/network.$TS.uci"
pstep "网络配置已备份（可回滚）"

# 读取现有 PPPoE 账号密码（仅当未显式传入参数时兜底，不硬编码）
if [ "$WAN_PROTO" = "pppoe" ]; then
	if [ -z "$PPPOE_USER" ]; then PPPOE_USER=$(uci -q get network.wan.username 2>/dev/null); fi
	if [ -z "$PPPOE_PASS" ]; then PPPOE_PASS=$(uci -q get network.wan.password 2>/dev/null); fi
fi

# ---- 清理旧方案残留 ----
del_wan_vlans
del_dev br-iptv
uci -q delete network.iptv 2>/dev/null
uci -q delete network.lan_remote 2>/dev/null
uci -q delete network.wan_pppoe 2>/dev/null
uci -q delete dhcp.lan_remote 2>/dev/null
pstep "旧方案残留已清理"

# ---- 重建干净配置 ----
# 捕获现有无线桥成员，重建后写回（防 WiFi 断网）
WK=""
LBX=$(br_dev)
if [ -n "$LBX" ]; then
	for p in $(uci -q get "$LBX.ports" 2>/dev/null); do
		case "$p" in wlan*) WK="$WK $p" ;; esac
	done
	uci -q delete "$LBX" 2>/dev/null
fi
uci -q delete network.lan 2>/dev/null
uci -q delete network.wan 2>/dev/null

# VLAN 子接口
add_vlan_dev "wan.$INNER" "$INNER"
add_vlan_dev "wan.$WAN_VLAN" "$WAN_VLAN"
if [ -n "$IPTV_VLAN" ]; then
	add_vlan_dev "wan.$IPTV_VLAN" "$IPTV_VLAN"
fi
pstep "VLAN 子接口已创建（wan.$INNER / wan.$WAN_VLAN$([ -n "$IPTV_VLAN" ] && echo " / wan.$IPTV_VLAN")）"

# br-lan：lan1-3 + WiFi + 内网回传 VLAN 子接口；IPTV 开时 lan4 留给 br-iptv
BR=$(ensure_dev br-lan bridge)
if [ -n "$IPTV_VLAN" ]; then
	set_bridge_ports "$BR" $WK lan1 lan2 lan3 "wan.$INNER"
else
	set_bridge_ports "$BR" $WK lan1 lan2 lan3 lan4 "wan.$INNER"
fi
pstep "br-lan 网桥已重建（内网回传 VLAN$INNER 已桥接）"

# lan 接口
uci set network.lan=interface
uci set network.lan.device='br-lan'
uci set network.lan.proto='static'
uci set network.lan.ipaddr='192.168.10.1'
uci set network.lan.netmask='255.255.255.0'
uci -q delete network.lan.gateway 2>/dev/null
uci -q delete network.lan.dns 2>/dev/null
uci -q set dhcp.lan.ignore='0'
uci -q set dhcp.lan.dhcpv4='server'

# wan 接口：挂拨号 VLAN
uci set network.wan=interface
uci set network.wan.device="wan.$WAN_VLAN"
uci set network.wan.proto="$WAN_PROTO"
if [ "$WAN_PROTO" = "pppoe" ]; then
	[ -n "$PPPOE_USER" ] && uci set network.wan.username="$PPPOE_USER"
	[ -n "$PPPOE_PASS" ] && uci set network.wan.password="$PPPOE_PASS"
	uci -q set network.wan.norelease='1'
else
	uci -q delete network.wan.username 2>/dev/null
	uci -q delete network.wan.password 2>/dev/null
fi
# wan6 承载口指向拨号 VLAN
if [ -n "$(uci -q get network.wan6 2>/dev/null)" ]; then
	uci set network.wan6.device="wan.$WAN_VLAN"
	[ -z "$(uci -q get network.wan6.proto 2>/dev/null)" ] && uci set network.wan6.proto='dhcpv6'
fi
pstep "WAN 拨号接口已挂接 wan.$WAN_VLAN（$WAN_PROTO）"

# IPTV：br-iptv = wan.$IPTV_VLAN + 透传口
if [ -n "$IPTV_VLAN" ]; then
	IBR=$(ensure_dev br-iptv bridge)
	if [ -n "$IBR" ]; then
		uci -q delete "$IBR.ports" 2>/dev/null
		uci add_list "$IBR.ports=wan.$IPTV_VLAN"
		uci add_list "$IBR.ports=$IPTV_PORT"
	fi
	uci set network.iptv=interface
	uci set network.iptv.device='br-iptv'
	uci set network.iptv.proto='none'
	pstep "IPTV 透传已配置（$IPTV_PORT + wan.$IPTV_VLAN）"
else
	uci -q delete network.iptv 2>/dev/null
	pstep "IPTV 未开启（lan4 已回归 br-lan）"
fi

# ---- 参数回写（前端/状态页读取；兼容新旧字段）----
uci -q set athena.single.wan_vlan="$WAN_VLAN"
uci -q set athena.single.inner_vlan="$INNER"
uci -q set athena.single.ret_vlan="$INNER"
uci -q set athena.single.wan_proto="$WAN_PROTO"
if [ -n "$IPTV_VLAN" ]; then
	uci -q set athena.single.iptv_vlan="$IPTV_VLAN"
else
	uci -q delete athena.single.iptv_vlan 2>/dev/null
fi
uci -q set athena.single.iptv_port="$IPTV_PORT"
pstep "参数已回写 athena.single（wan_vlan/ret_vlan/iptv_vlan/iptv_port）"

# 模式标记修正为 single（冷启动预建 VLAN + 自检回退依赖此标记）
uci -q set athena.system.mode='single'

uci commit network 2>/dev/null
uci commit dhcp 2>/dev/null
uci commit athena 2>/dev/null
pstep "配置已提交，网络重启生效中…"

# 应用：延迟后台重启网络栈（避免中断 rpcd 响应），并带自检 + 失败自动回滚
( sleep 1; /etc/init.d/network restart >/dev/null 2>&1 || wifi reload >/dev/null 2>&1 ) &
( sleep 8
  if ! ip -4 addr show dev br-lan 2>/dev/null | grep -q '192.168.10.1'; then
    pstep "自检失败：br-lan 未获得管理 IP（192.168.10.1），自动回滚…"
    latest=$(ls -t "$BACKUP_DIR"/network.*.uci 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
      uci import network < "$latest" 2>/dev/null
      uci commit network 2>/dev/null
      uci -q set athena.system.mode='router'
      uci commit athena 2>/dev/null
      /etc/init.d/network restart >/dev/null 2>&1
      pstep "已自动回滚至备份：$(basename "$latest")"
    else
      pstep "无备份可回滚！请手动检查网络配置或恢复出厂"
    fi
  else
    pstep "自检通过：br-lan 管理 IP 正常"
  fi ) &

log "单臂路由配置完成（inner=$INNER wan=$WAN_VLAN iptv=${IPTV_VLAN:-off} port=$IPTV_PORT proto=$WAN_PROTO）"
pstep "完成：单臂路由已生效"
echo '{"ok":true,"msg":"单臂路由已配置，网络正在重启生效"}'
exit 0
