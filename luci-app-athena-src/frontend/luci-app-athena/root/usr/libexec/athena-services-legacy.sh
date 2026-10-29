#!/bin/sh
# AthenaWrt 运行服务聚合脚本
# 无参：输出可安全启停的应用服务清单 JSON（按功能分类，隐藏核心网络服务）
# set <id> <0|1>：启停指定服务（写 uci enable 字段 + /etc/init.d enable|disable + start|stop）
#
# 字段说明（以 | 分隔）：id|功能名|说明|uci 启停字段|init 名|是否第三方插件(1/0)|插件原生 LuCI 路径
# 注意：path 为不带 /cgi-bin/luci 前缀的相对路径，前端拼接完整地址；ttyd 页面路由为 /admin/system/ttyd（勿加多余后缀）
# 注意：以下 uci 字段 / init 名已按真机校准（点阵屏 init 名为 athena_led 下划线；无 fullconenat 包，NSS/ECM 已提供全锥形 NAT）。

SERVICES="
ddns|动态 DNS|DDNS · 阿里云域名实时解析到家宽动态 IP|ddns.@service[0].enabled|ddns|0|/admin/services/ddns
ttyd|网页终端|ttyd · 浏览器内直接操作路由器终端|ttyd.@ttyd[0].enabled|ttyd|0|/admin/system/ttyd
matrix|点阵屏显示|athena_led · 正面点阵屏信息展示|athena_led.general.enabled|athena_led|0|
"

# 核心系统服务：不展示、不允许一键启停（误停会断网/失联），仅作运行状态展示
CORE_INIT="network firewall rpcd uhttpd dnsmasq odhcpd dropbear sysctl boot done led system logd ubusd netifd fstab urandom_seed rssileds athena-boot athena-ui athena-vlan-pre athena-netcheck wpad hostapd hostapd_cli"

json_esc() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# 判断服务是否启用：uci 字段优先，其次 init.d enabled
svc_on() {
	local uci_key="$1" init="$2" v=""
	if [ -n "$uci_key" ] && [ "$uci_key" != "none" ]; then
		v=$(uci -q get "$uci_key" 2>/dev/null)
		case "$v" in
			1|on|enabled|yes|true) echo true; return ;;
			0|off|disabled|no|false) echo false; return ;;
		esac
	fi
	if [ -n "$init" ] && [ "$init" != "none" ] && [ -x "/etc/init.d/$init" ]; then
		if /etc/init.d/$init enabled >/dev/null 2>&1; then echo true; else echo false; fi
		return
	fi
	echo false
}

# 是否支持一键启停（uci 字段或 init 至少其一可用，且非核心服务）
svc_toggle() {
	local uci_key="$1" init="$2"
	case " $CORE_INIT " in *" $init "*) echo false; return ;; esac
	if { [ -n "$uci_key" ] && [ "$uci_key" != "none" ]; } || { [ -n "$init" ] && [ "$init" != "none" ]; }; then
		echo true
	else
		echo false
	fi
}

emit_list() {
	printf '{"services":['
	local first=""
	local line id name desc uci_key init plugin path on toggle
	while IFS='|' read -r id name desc uci_key init plugin path; do
		[ -z "$id" ] && continue
		on=$(svc_on "$uci_key" "$init")
		toggle=$(svc_toggle "$uci_key" "$init")
		[ -n "$first" ] && printf ','
		first=1
		printf '{"id":"%s","name":"%s","desc":"%s","on":%s,"toggle":%s' \
			"$(printf '%s' "$id" | json_esc)" \
			"$(printf '%s' "$name" | json_esc)" \
			"$(printf '%s' "$desc" | json_esc)" \
			"$on" "$toggle"
		if [ "$plugin" = "1" ]; then
			printf ',"plugin":true'
		fi
		if [ -n "$path" ]; then
			printf ',"path":"%s"' "$(printf '%s' "$path" | json_esc)"
		fi
		printf '}'
	done <<EOF
$SERVICES
EOF
	# 动态追加：所有已安装的第三方 init.d 服务（系统底层核心服务不展示；
	# 已安装即显示，未启用时 on=false，可直接一键启停）
	# path 探测：从 LuCI menu.d 中匹配同名应用的菜单路径，作为"打开"入口（无则前端折叠展示）
	local init base core on toggle dpath
	for init in /etc/init.d/*; do
		[ -f "$init" ] && [ -x "$init" ] || continue
		base=$(basename "$init")
		case "$base" in *.*|rcS) continue ;; esac
		# 跳过静态表已列出的（ddns/ttyd/athena_led）
		printf '%s\n' "$SERVICES" | cut -d'|' -f5 | grep -qx "$base" && continue
		core=false
		case " $CORE_INIT " in *" $base "*) core=true ;; esac
		# 系统底层（核心服务）不展示，只显示第三方服务
		if $core; then continue; fi
		# 已安装即显示；enabled（开机自启）视为"运行中"，未启用显示为关闭
		if /etc/init.d/$base enabled >/dev/null 2>&1; then on=true; else on=false; fi
		toggle=true
		dpath=""
		# 在 LuCI 菜单注册文件里找同名应用的菜单路径（menu.d 的 key 行带 TAB 缩进，
		# 必须容忍前导空白，否则永远探不到 → 服务只能显示"无独立界面"、无法打开）
		for md in /usr/share/luci/menu.d/luci-app-$base.json /usr/share/luci/menu.d/*$base*.json; do
			[ -f "$md" ] || continue
			dpath=$(sed -n 's/^[[:space:]]*"\(admin\/[^"]*\)".*/\1/p' "$md" 2>/dev/null | grep '^admin/' | grep -m1 "$base")
			[ -z "$dpath" ] && dpath=$(sed -n 's/^[[:space:]]*"\(admin\/[^"]*\)".*/\1/p' "$md" 2>/dev/null | grep '^admin/' | head -n1)
			[ -n "$dpath" ] && break
		done
		# 兜底：插件菜单文件名与 init 名不一致时（如 ddnsto → luci-app-ddnsto.json），
		# 全量扫 menu.d，找注册了 admin/services/<init 名> 的文件
		if [ -z "$dpath" ]; then
			for md in /usr/share/luci/menu.d/*.json; do
				[ -f "$md" ] || continue
				grep -q "admin/services/$base\"" "$md" 2>/dev/null || continue
				dpath="admin/services/$base"
				break
			done
		fi
		[ -n "$first" ] && printf ','
		first=1
		printf '{"id":"%s","name":"%s","desc":"%s","on":%s,"toggle":%s' \
			"$(printf '%s' "$base" | json_esc)" \
			"$(printf '%s' "$base" | json_esc)" \
			"$(if $core; then echo '系统核心服务（受保护，不建议启停）'; else echo '第三方服务'; fi | json_esc)" \
			"$on" "$toggle"
		if [ -n "$dpath" ]; then
			printf ',"path":"%s"' "$(printf '%s' "$dpath" | json_esc)"
		fi
		printf '}'
	done
	printf ']}'
}

set_svc() {
	local id="$1" en="$2" line uci_key init val=0
	line=$(printf '%s\n' "$SERVICES" | grep "^$id|" | head -n1)
	if [ -z "$line" ]; then
		# 动态 init.d 服务：id 即 init 名
		init="$id"
		uci_key="none"
		if [ ! -x "/etc/init.d/$init" ]; then
			echo '{"ok":false,"error":"unknown service"}'; return
		fi
		# 核心服务保护：不允许一键启停（防误操作断网/失联）
		case " $CORE_INIT " in *" $init "*) echo '{"ok":false,"msg":"核心系统服务受保护，不允许在此启停"}'; return ;; esac
	else
		uci_key=$(printf '%s' "$line" | cut -d'|' -f4)
		init=$(printf '%s' "$line" | cut -d'|' -f5)
	fi
	[ "$en" = "1" ] && val=1

	if [ -n "$uci_key" ] && [ "$uci_key" != "none" ]; then
		uci set "$uci_key=$val" 2>/dev/null
		uci commit 2>/dev/null
	fi
	if [ -n "$init" ] && [ "$init" != "none" ] && [ -x "/etc/init.d/$init" ]; then
		if [ "$en" = "1" ]; then
			/etc/init.d/$init enable >/dev/null 2>&1
			/etc/init.d/$init start >/dev/null 2>&1
		else
			/etc/init.d/$init stop >/dev/null 2>&1
			/etc/init.d/$init disable >/dev/null 2>&1
		fi
	fi

	if [ "$en" = "1" ]; then on=true; else on=false; fi
	echo "{\"ok\":true,\"id\":\"$id\",\"on\":$on}"
}

case "$1" in
	set) set_svc "$2" "$3" ;;
	*) emit_list ;;
esac
