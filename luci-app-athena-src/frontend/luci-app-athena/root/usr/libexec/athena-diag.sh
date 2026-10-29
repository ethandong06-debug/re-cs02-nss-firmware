#!/bin/sh
# AthenaWrt 网络诊断脚本
# 用法:
#   athena-diag.sh nodes                      列出内置测速节点
#   athena-diag.sh ping <host> [count]        ping 测试
#   athena-diag.sh dns <domain> [dns]         DNS 解析测试
#   athena-diag.sh check                      一键连通性体检（网关/DNS/外网）
# 输出均为单行 JSON

CMD="${1:-check}"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# 内置测速节点（信通院等公共节点，域名形式，真机按需替换为 IP）
NODES='[
  {"id":"cata1","name":"中国信通院 · 北京","host":"speedtest.cata.net","type":"iperf3"},
  {"id":"cata2","name":"中国信通院 · 广州","host":"speedtest2.cata.net","type":"iperf3"},
  {"id":"ali","name":"阿里云 · 华东","host":"mirrors.aliyun.com","type":"curl"},
  {"id":"qq","name":"腾讯云 · 华南","host":"mirrors.tencent.com","type":"curl"},
  {"id":"netease","name":"网易 · 浙江","host":"mirrors.163.com","type":"curl"}
]'

case "$CMD" in
	nodes)
		echo "{\"ok\":true,\"nodes\":$NODES}"
		;;
	ping)
		HOST="${2:-114.114.114.114}"; CNT="${3:-4}"
		raw=$(ping -c "$CNT" -W 2 "$HOST" 2>/dev/null)
		[ -z "$raw" ] && { echo "{\"ok\":false,\"msg\":\"ping 失败或无响应\"}"; exit 1; }
	# 提取丢包率 / 平均时延 / 抖动（mdev）
	loss=$(echo "$raw" | awk '/packet loss/{for(i=1;i<=NF;i++)if($i~/%/)print $i}' | tr -d '%')
	rtt_line=$(echo "$raw" | grep -E 'min/avg/max' | tail -1)
	avg=$(echo "$rtt_line" | sed -n 's/.*= \([0-9.]*\)\/\([0-9.]*\)\/.*/\2/p')
	mdev=$(echo "$rtt_line" | sed -n 's/.*\/\([0-9.]*\) ms.*/\1/p')
	[ -z "$loss" ] && loss=100
	echo "{\"ok\":true,\"host\":\"$(echo "$HOST" | json_str)\",\"loss_pct\":$loss,\"avg_ms\":\"${avg:-0}\",\"jitter_ms\":\"${mdev:-0}\"}"
		;;
	dns)
		DOMAIN="${2:-www.qq.com}"; DNS="${3:-}"
		if [ -n "$DNS" ]; then
			out=$(nslookup "$DOMAIN" "$DNS" 2>/dev/null)
		else
			out=$(nslookup "$DOMAIN" 2>/dev/null)
		fi
		ip=$(echo "$out" | awk '/^Address/{print $2}' | grep -v ':' | tail -1)
		if [ -n "$ip" ]; then
			echo "{\"ok\":true,\"domain\":\"$(echo "$DOMAIN" | json_str)\",\"ip\":\"$ip\",\"dns\":\"${DNS:-系统默认}\"}"
		else
			echo "{\"ok\":false,\"msg\":\"DNS 解析失败\"}"
		fi
		;;
	check)
		# 网关
		gw=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')
		gw_ok=false; gw_ms="无默认网关"
		if [ -n "$gw" ]; then
			r=$(ping -c 1 -W 1 "$gw" 2>/dev/null | sed -n 's/.*time=\([0-9.]*\) ms.*/\1/p' | head -1)
			[ -n "$r" ] && { gw_ok=true; gw_ms="$r ms"; }
		fi
		# 外网连通：以 HTTP 为准（v1.2.52）
		# 真机实测：重庆联通线路 ping 114.114.114.114 100% 丢包、ping 223.5.5.5 正常，
		# 也就是说 ICMP 会被个别目标拦截，用它判"能不能上网"会误报。这里改用 HTTP 200/30x。
		wan_ok=false; wan_msg="无法访问公网"
		for h in www.qq.com www.baidu.com mirrors.aliyun.com; do
			code=$(curl -s -o /dev/null -m 4 -w '%{http_code}' "http://$h/" 2>/dev/null)
			case "$code" in
				2*|3*) wan_ok=true; wan_msg="公网可达（HTTP $code · $h）"; break ;;
			esac
		done
		if [ "$wan_ok" = false ]; then
			if ping -c 1 -W 2 223.5.5.5 >/dev/null 2>&1; then
				wan_ok=true; wan_msg="公网可达（ICMP · 223.5.5.5）"
			fi
		fi
		# DNS
		dns_ok=false; dns_msg="域名解析失败"
		if nslookup www.qq.com >/dev/null 2>&1; then dns_ok=true; dns_msg="www.qq.com 解析正常"; fi
		# ICMP 探测（参考项，不参与判定）
		icmp_ok=false; icmp_msg="223.5.5.5 无响应（可能被运营商拦截，不代表断网）"
		r=$(ping -c 2 -W 2 223.5.5.5 2>/dev/null | sed -n 's/.*min\/avg\/max = [0-9.]*\/\([0-9.]*\).*/\1/p')
		[ -n "$r" ] && { icmp_ok=true; icmp_msg="223.5.5.5 · ${r} ms"; }
		cat <<EOF
{"ok":true,"items":[
{"key":"gateway","name":"网关连通","ok":$gw_ok,"msg":"${gw:-未检测到默认网关} · ${gw_ms}"},
{"key":"wan","name":"外网连通","ok":$wan_ok,"msg":"$wan_msg"},
{"key":"dns","name":"DNS 解析","ok":$dns_ok,"msg":"$dns_msg"},
{"key":"icmp","name":"ICMP 探测","ok":$icmp_ok,"msg":"$icmp_msg","info":true}
]}
EOF
		;;
	*)
		echo "{\"ok\":false,\"msg\":\"未知命令（支持 nodes|ping|dns|check）\"}"
		exit 1
		;;
esac
