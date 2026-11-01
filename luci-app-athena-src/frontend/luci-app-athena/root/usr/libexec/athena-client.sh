#!/bin/sh
# AthenaWrt 设备操作脚本
# 用法:
#   athena-client.sh block  <mac>             拉黑设备（断网）
#   athena-client.sh unblock <mac>            解除拉黑
#   athena-client.sh rename <mac> <name>      重命名设备
#   athena-client.sh list                     列出已拉黑设备
#   athena-client.sh known                    列出已认识设备（自家设备标记，路由器级持久化）
#   athena-client.sh know <mac>               标记设备为自家设备（认识它）
#   athena-client.sh unlearn <mac>            取消认识标记
#   athena-client.sh restore                  开机恢复拉黑规则（读 athena.client.blocked）

CMD="${1:-list}"
MAC="${2:-}"

# MAC 规范化
norm_mac() { echo "$1" | tr 'A-F' 'a-f'; }
valid_mac() {
	case "$1" in
		[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]) return 0 ;;
		*) return 1 ;;
	esac
}
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

case "$CMD" in
	block)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		# 优先使用 fw4/nftables；规则已存在时视为成功，避免重复插入。
		if nft -a list chain inet fw4 forward 2>/dev/null | grep -F "ether saddr $M" | grep -q " drop"; then
			RULE_OK=1
		elif nft add rule inet fw4 forward ether saddr "$M" counter drop 2>/dev/null; then
			RULE_OK=1
		else
			RULE_OK=0
		fi
		# 旧版系统回退到 iptables；只有实际添加成功或规则已存在才确认拉黑。
		if [ "$RULE_OK" -ne 1 ]; then
			iptables -C FORWARD -m mac --mac-source "$M" -j DROP 2>/dev/null || iptables -I FORWARD -m mac --mac-source "$M" -j DROP 2>/dev/null
			[ $? -eq 0 ] && RULE_OK=1
		fi
		[ "$RULE_OK" -eq 1 ] || { echo '{"ok":false,"msg":"防火墙规则添加失败，设备未拉黑"}'; exit 1; }
		# 记录到 uci（持久化，首启脚本可恢复）
		uci -q add_list athena.client.blocked="$M"
		uci commit athena 2>/dev/null || { echo '{"ok":false,"msg":"已添加临时防火墙规则，但保存拉黑名单失败"}'; exit 1; }
		echo "{\"ok\":true,\"mac\":\"$M\"}"
		;;
	unblock)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		nft -a list chain inet fw4 forward 2>/dev/null | grep "saddr $M" | awk '{print $NF}' | while read h; do nft delete rule inet fw4 forward handle "$h" 2>/dev/null; done
		iptables -D FORWARD -m mac --mac-source "$M" -j DROP 2>/dev/null
		uci -q del_list athena.client.blocked="$M"
		uci commit athena 2>/dev/null || { echo '{"ok":false,"msg":"已解除当前规则，但保存名单失败"}'; exit 1; }
		echo "{\"ok\":true,\"mac\":\"$M\"}"
		;;
	rename)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		NAME="${3:-}"
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		NAME_BYTES=$(printf '%s' "$NAME" | wc -c | tr -d ' ')
		[ -n "$NAME" ] && [ "$NAME_BYTES" -le 32 ] || { echo '{"ok":false,"msg":"设备名称必须为 1-32 字节"}'; exit 1; }
		printf '%s' "$NAME" | LC_ALL=C grep -q '[[:cntrl:]]' && { echo '{"ok":false,"msg":"设备名称不能包含控制字符"}'; exit 1; }
		# 查找已存在该 MAC 的 host 段，有则更新名称，无则新增
		existing=$(uci show dhcp 2>/dev/null | grep "\.mac='$M'$" | cut -d. -f1-2 | head -n1)
		if [ -n "$existing" ]; then
			uci -q set "$existing.name=$NAME"
		else
			uci add dhcp host >/dev/null
			uci set dhcp.@host[-1].mac="$M"
			uci set dhcp.@host[-1].name="$NAME"
		fi
		uci commit dhcp 2>/dev/null || { echo '{"ok":false,"msg":"设备名称保存失败"}'; exit 1; }
		# 让 DHCP 主机名立即生效，否则改名只写配置、页面无变化（"无效果"）
		/etc/init.d/dnsmasq restart >/dev/null 2>&1 || { echo '{"ok":false,"saved":true,"msg":"名称已保存，但 DHCP 服务重载失败"}'; exit 1; }
		echo "{\"ok\":true,\"mac\":\"$M\",\"name\":\"$(printf '%s' "$NAME" | json_str)\"}"
		;;
	restore)
		# 开机/手动恢复持久化的拉黑规则（nft 规则重启后不保留）
		BLOCKED=$(uci -q get athena.client.blocked 2>/dev/null)
		for M in $BLOCKED; do
			M=$(norm_mac "$M")
			valid_mac "$M" || continue
			nft -a list chain inet fw4 forward 2>/dev/null | grep -F "$M" | grep -q " drop" || nft add rule inet fw4 forward ether saddr "$M" counter drop 2>/dev/null
		done
		echo '{"ok":true,"restored":true}'
		;;
	list)
		BLOCKED=$(uci -q get athena.client.blocked 2>/dev/null)
		if [ -z "$BLOCKED" ]; then
			echo '{"blocked":[]}'
		else
			echo "{\"blocked\":[$(echo "$BLOCKED" | sed 's/ /","/g; s/^/"/; s/$/"/')]}"
		fi
		;;
	known)
		# 列出已认识设备（自家设备标记，存 athena.client.known）
		KNOWN=$(uci -q get athena.client.known 2>/dev/null)
		if [ -z "$KNOWN" ]; then
			echo '{"known":[]}'
		else
			echo "{\"known\":[$(echo "$KNOWN" | sed 's/ /","/g; s/^/"/; s/$/"/')]}"
		fi
		;;
	know)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		# 已存在则不重复添加
		EXISTS=$(uci -q get athena.client.known 2>/dev/null | grep -o "$M" | head -n1)
		if [ -z "$EXISTS" ]; then
			uci -q add_list athena.client.known="$M"
			uci commit athena 2>/dev/null
		fi
		echo "{\"ok\":true,\"mac\":\"$M\"}"
		;;
	unlearn)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		uci -q del_list athena.client.known="$M"
		uci commit athena 2>/dev/null
		echo "{\"ok\":true,\"mac\":\"$M\"}"
		;;
	note)
		[ -z "$MAC" ] && { echo '{"ok":false,"msg":"缺少 MAC"}'; exit 1; }
		TEXT="${3:-}"
		M=$(norm_mac "$MAC")
		valid_mac "$M" || { echo '{"ok":false,"msg":"MAC 地址格式无效"}'; exit 1; }
		HEX=$(echo "$M" | tr -d ':')
		[ -n "$HEX" ] || { echo '{"ok":false,"msg":"MAC 无效"}'; exit 1; }
		# uci 选项名不能含冒号，用去掉冒号的 hex 作键，值即备注文本
		uci -q get athena.devnote >/dev/null 2>&1 || uci -q set athena.devnote=devnote
		if [ -n "$TEXT" ]; then
			uci -q set "athena.devnote.$HEX=$TEXT"
		else
			uci -q delete "athena.devnote.$HEX" 2>/dev/null
		fi
		uci commit athena 2>/dev/null
		echo "{\"ok\":true,\"mac\":\"$M\",\"note\":\"$(printf '%s' "$TEXT" | json_str)\"}"
		;;
	notes)
		printf '{"ok":true,"notes":{'
		uci -q show athena.devnote 2>/dev/null | awk -F"'" '
			/^athena\.devnote\./ {
				k=$1; sub(/^athena\.devnote\./,"",k); sub(/=.*$/,"",k);
				v=$2;
				gsub(/\\/,"\\\\",v); gsub(/"/,"\\\"",v);
				mac=k;
				if (length(k)==12) mac=substr(k,1,2)":"substr(k,3,2)":"substr(k,5,2)":"substr(k,7,2)":"substr(k,9,2)":"substr(k,11,2);
				printf "%s\"%s\":\"%s\"", (n++?",":""), mac, v;
			}'
		echo '}}'
		;;
	*)
		echo '{"ok":false,"msg":"未知命令"}'
		exit 1
		;;
esac
