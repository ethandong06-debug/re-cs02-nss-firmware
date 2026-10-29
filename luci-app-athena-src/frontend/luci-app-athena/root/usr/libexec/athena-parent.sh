#!/bin/sh
# ============================================================
#  AthenaWrt — 家长控制（按星期 / 时间段限制指定设备上网）
#  命令：
#    list                          输出规则列表（JSON）
#    set <mac> <days_csv> <start> <end>   添加/更新规则
#    clear <mac>                   删除规则
#  数据：uci athena.parent.<mac>.{days,start,end}
#  落地：/etc/nftables.d/10-athena-parent.nft（fw4 reload 自动 include）
#  规则：forward 链按 MAC + day_of_week + hour 匹配 drop（禁外网，内网互访不受影响）
#  说明：days 用 0-6（0=周日）；时间段跨午夜自动拆成两段
# ============================================================

RULE_FILE=/etc/nftables.d/10-athena-parent.nft
RULE_DIR=/etc/nftables.d

# 生成 nftables 规则文件（由所有规则重建，保证与 uci 一致）
gen_rules() {
	mkdir -p "$RULE_DIR"
	rm -f "$RULE_FILE"

	for mac in $(uci -q show athena.parent 2>/dev/null | sed -n 's/^athena\.parent\.\([0-9a-fA-F:]*\)\..*$/\1/p' | tr 'A-F' 'a-f' | sort -u); do
		days=$(uci -q get "athena.parent.$mac.days" 2>/dev/null)
		start=$(uci -q get "athena.parent.$mac.start" 2>/dev/null)
		end=$(uci -q get "athena.parent.$mac.end" 2>/dev/null)
		[ -z "$days" ] && continue
		[ -z "$start" ] || [ -z "$end" ] && continue

		# 组装 day_of_week 集合（0-6 白名单）
		dw=""
		for d in $(echo "$days" | tr ',' ' '); do
			case "$d" in
				0|1|2|3|4|5|6) ;;
				*) continue ;;
			esac
			[ -n "$dw" ] && dw="$dw,"
			dw="$dw$d"
		done
		[ -z "$dw" ] && continue

		# chain 名不能含冒号，MAC 冒号转 x
		chn=$(echo "$mac" | tr ':' 'x' | tr 'a-f' 'A-F')

		# 时间段跨午夜拆两段，避免 nft 范围语义歧义
		if [ "$start" \< "$end" ]; then
			cat >> "$RULE_FILE" <<EOF
chain athena_parent_$chn {
	type filter hook forward priority 0; policy accept;
	ether saddr $mac meta day_of_week {$dw} meta hour "$start"-"$end" drop
}
EOF
		else
			cat >> "$RULE_FILE" <<EOF
chain athena_parent_$chn {
	type filter hook forward priority 0; policy accept;
	ether saddr $mac meta day_of_week {$dw} meta hour "$start"-"23:59" drop
}
chain athena_parent_${chn}_b {
	type filter hook forward priority 0; policy accept;
	ether saddr $mac meta day_of_week {$dw} meta hour "00:00"-"$end" drop
}
EOF
		fi
	done

	return 0
}

json_escape() {
	# 简单转义（规则内容为受控输入，仅防御性处理引号）
	echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

case "$1" in
	list)
		echo '{'
		echo '  "rules": ['
		first=1
		for mac in $(uci -q show athena.parent 2>/dev/null | sed -n 's/^athena\.parent\.\([0-9a-fA-F:]*\)\..*$/\1/p' | tr 'A-F' 'a-f' | sort -u); do
			days=$(uci -q get "athena.parent.$mac.days" 2>/dev/null)
			start=$(uci -q get "athena.parent.$mac.start" 2>/dev/null)
			end=$(uci -q get "athena.parent.$mac.end" 2>/dev/null)
			[ -z "$days" ] && continue
			dayjson=$(echo "$days" | tr ',' ' ' | awk '{ s="["; for(i=1;i<=NF;i++){ if(i>1) s=s","; s=s$i } s=s"]"; printf "%s", s }')
			if [ "$first" -eq 1 ]; then
				first=0
				printf '    {"mac":"%s","days":%s,"start":"%s","end":"%s"}' "$mac" "$dayjson" "$start" "$end"
			else
				printf ',\n    {"mac":"%s","days":%s,"start":"%s","end":"%s"}' "$mac" "$dayjson" "$start" "$end"
			fi
		done
		echo ''
		echo '  ]'
		echo '}'
		;;

	set)
		if [ $# -lt 5 ]; then
			echo '{"ok":false,"msg":"set <mac> <days_csv> <start> <end>"}'
			exit 1
		fi
		MAC=$(echo "$2" | tr 'A-F' 'a-f')
		DAYS=$3
		START=$4
		END=$5

		# MAC 格式校验
		case "$MAC" in
			[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]) ;;
			*) echo '{"ok":false,"msg":"MAC 地址格式错误"}'; exit 1 ;;
		esac

		# 星期校验
		for d in $(echo "$DAYS" | tr ',' ' '); do
			case "$d" in
				0|1|2|3|4|5|6) ;;
				*) echo '{"ok":false,"msg":"星期值必须在 0-6（0=周日）"}'; exit 1 ;;
			esac
		done

		# 时间校验 HH:MM
		case "$START" in
			[0-2][0-9]:[0-5][0-9]) ;;
			*) echo '{"ok":false,"msg":"开始时间格式错误，应为 HH:MM"}'; exit 1 ;;
		esac
		case "$END" in
			[0-2][0-9]:[0-5][0-9]) ;;
			*) echo '{"ok":false,"msg":"结束时间格式错误，应为 HH:MM"}'; exit 1 ;;
		esac

		uci set "athena.parent.$MAC.days=$DAYS"
		uci set "athena.parent.$MAC.start=$START"
		uci set "athena.parent.$MAC.end=$END"
		uci commit athena
		gen_rules
		/etc/init.d/firewall reload >/dev/null 2>&1
		echo "{\"ok\":true,\"mac\":\"$MAC\"}"
		;;

	clear)
		if [ $# -lt 2 ]; then
			echo '{"ok":false,"msg":"clear <mac>"}'
			exit 1
		fi
		MAC=$(echo "$2" | tr 'A-F' 'a-f')
		uci -q delete "athena.parent.$MAC"
		uci commit athena
		gen_rules
		/etc/init.d/firewall reload >/dev/null 2>&1
		echo "{\"ok\":true}"
		;;

	*)
		echo '{"ok":false,"msg":"usage: list | set <mac> <days_csv> <start> <end> | clear <mac>"}'
		exit 1
		;;
esac

exit 0
