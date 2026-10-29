#!/bin/sh
# ============================================================
#  AthenaWrt — 活跃应用识别脚本（OAF 分类 + DNS 指纹）
#  通过 dnsmasq 查询日志中的域名，匹配 OAF 应用映射表，
#  聚合出"最近 15 分钟每设备正在使用的 App"。
#  数据源：/tmp/dnsmasq.log（dnsmasq logqueries 开启时）或 logread 兜底
#  依赖：/usr/share/athena/oaf-app-map.json（随固件内置）
#  用法：
#    athena-apps.sh list                输出活跃应用列表 JSON
#    athena-apps.sh window <min>        指定统计窗口（默认 15 分钟）
#  输出：{"apps":[{"id":"3001","name":"抖音短视频","deviceCount":2},...],"source":"dns"}
#  兼容性：纯 POSIX sh + grep/awk/sed，BusyBox 与 GNU 均可用（不用 $'\t'、不用 sed \t）
# ============================================================

JSON=/usr/share/athena/oaf-app-map.json
MAP_TMP=/tmp/athena-oaf-map.tsv
WINDOW=${2:-15}
[ "$WINDOW" -gt 0 ] 2>/dev/null || WINDOW=15
NOW=$(date +%s)
TAB=$(printf '\t')

# v1.2.53：日志在 tmpfs（直吃内存），超过 2MB 先原地裁剪；cron 每分钟也会调一次，这里做双保险。
[ -x /usr/libexec/athena-logcap.sh ] && /usr/libexec/athena-logcap.sh >/dev/null 2>&1

# ---- DNS 指纹兜底规则（OAF 表未覆盖的海外/高频应用）app|OAF id（可空）|域名片段1,片段2 ----
DNS_RULES="
YouTube|3049|youtube,googlevideo,ytimg,youtu.be
Netflix|3043|netflix,nflxvideo,nflximg
TikTok|3001|tiktok,douyin,byteimg,bytecdn,ibyteimg,pstatp,douyinvod
哔哩哔哩|3014|bilibili,hdslb,bilivideo,biliapi,acgvideo
Spotify||spotify,scdn.co,spotifycdn
Twitch||twitch,ttvnw,jtvnw
腾讯视频|3003|v.qq.com,qqvideo
微信|1002|weixin,wechat,wx.qq,wxs.qq
QQ|1001|qpic.cn,gtimg,qlogo,qqmail
Telegram||telegram,t.me,tdesktop,telesco.pe
WhatsApp||whatsapp
Instagram|1012|instagram,cdninstagram
Facebook||facebook,fbcdn,fb.com,fbsbx
Twitter||twitter,twimg,t.co
Reddit||reddit,redd.it,redditmedia
Discord||discord,discordapp
快手|3009|kuaishou,gifshow
知乎|10005|zhihu,zhimg
美团|10035|meituan,dpfile,sankuai,dianping
网易|8004|163.com,126.net,netease,music.126,ntes
Amazon||amazon,media-amazon,ssl-images-amazon,amazonaws
Apple|7002|apple.com,icloud,mzstatic,cdn-apple,aaplimg
Microsoft||microsoft,windows.com,live.com,msftncsi,windowsupdate
Google|8079|google,gstatic,googleapis,googleusercontent
GitHub|8087|github,githubusercontent,githubassets
Steam||steampowered,steamcommunity,steamstatic,steamcontent
百度|8001|baidu,bdstatic,bdimg,bcebos,bdydns
Disney+||disneyplus,disney-plus,dssott,bamgrid
Cloudflare||cloudflare,cf-ipfs,workers.dev
"

# ---- 构建行式映射表 key<TAB>id<TAB>name（一次性；grep -o + awk，busybox/GNU 通吃） ----
build_map() {
	[ -f "$JSON" ] || { echo ""; return; }
	grep -o '"\([^"]*\)":{"id":"\([^"]*\)","name":"\([^"]*\)"}' "$JSON" \
	| awk -F'"' '{print $2 "\t" $6 "\t" $10}' > "$MAP_TMP" 2>/dev/null
	wc -l < "$MAP_TMP" 2>/dev/null
}

# ---- 构建合并规则表 pattern<TAB>id<TAB>name<TAB>prio（OAF 表 + DNS_RULES 兜底）----
# prio 1 = DNS 指纹规则（人工维护，优先）；prio 2 = OAF 表。
# 只建一次，缺失才重建；之后 emit 只做一次 awk 扫描，不再每行 fork match_app
RULES=/tmp/athena-app-rules-v2.tsv
build_rules() {
	[ -s "$RULES" ] && return 0
	build_map >/dev/null
	{
		printf '%s\n' "$DNS_RULES" | while IFS='|' read -r rnm rid rpats; do
			[ -z "$rnm" ] && continue
			printf '%s\n' "$rpats" | tr ',' '\n' | while IFS= read -r pat; do
				[ -z "$pat" ] && continue
				printf '%s\t%s\t%s\t1\n' "$pat" "$rid" "$rnm"
			done
		done
		[ -s "$MAP_TMP" ] && awk -F'\t' 'NF>=3 { print $1 "\t" $2 "\t" $3 "\t2" }' "$MAP_TMP"
	} > "$RULES.tmp" 2>/dev/null
	[ -s "$RULES.tmp" ] && mv "$RULES.tmp" "$RULES"
	return 0
}

# ---- 提取最近查询的 dnsmasq 域名日志（域名<TAB>来源IP） ----
# dnsmasq 格式: "Oct 26 10:00:00 dnsmasq[1234]: query[A] example.com from 192.168.10.5"
get_loglines() {
	local lines=""
	if [ -f /tmp/dnsmasq.log ]; then
		lines=$(grep -E 'query\[' /tmp/dnsmasq.log 2>/dev/null | tail -n 3000 \
			| awk '{ dom=""; ip=""; for(i=1;i<=NF;i++){ if($i ~ /^query\[/){ dom=$(i+1); for(j=i+2;j<=NF;j++){ if($j=="from" && j+1<=NF){ ip=$(j+1); break } } } } if(dom!="") print dom "\t" ip }')
	else
		lines=$(logread 2>/dev/null | grep -E 'dnsmasq.*query\[' | tail -n 3000 \
			| awk '{ dom=""; ip=""; for(i=1;i<=NF;i++){ if($i ~ /^query\[/){ dom=$(i+1); for(j=i+2;j<=NF;j++){ if($j=="from" && j+1<=NF){ ip=$(j+1); break } } } } if(dom!="") print dom "\t" ip }')
	fi
	printf '%s\n' "$lines" | grep -v '^[[:space:]]*$'
}

# ---- 域名 → 应用（先 DNS 指纹规则，再 OAF 表子串匹配取最长） ----
match_app() {
	local dom="$1" nm oaf pats pat OLDIFS
	# 1) DNS 指纹规则（逐条规则、逐片段精确命中；规则顺序即优先级）
	while IFS='|' read -r nm oaf pats; do
		[ -z "$nm" ] && continue
		[ -z "$oaf" ] && oaf="$nm"
		OLDIFS=$IFS; IFS=','
		for pat in $pats; do
			[ -z "$pat" ] && continue
			case "$dom" in
				*"$pat"*)
					IFS=$OLDIFS
					printf '%s|%s' "$oaf" "$nm"
					return 0
					;;
			esac
		done
		IFS=$OLDIFS
	done <<EOF
$DNS_RULES
EOF
	# 2) OAF 表（子串匹配，取最长命中 key）
	[ -s "$MAP_TMP" ] || return 1
	local best="" bid="" bname="" blen=0 key id name
	while IFS=$TAB read -r key id name; do
		[ -z "$key" ] && continue
		case "$dom" in
			*"$key"*)
				if [ ${#key} -gt $blen ]; then blen=${#key}; best="$key"; bid="$id"; bname="$name"; fi
				;;
		esac
	done < "$MAP_TMP"
	[ -n "$bid" ] || return 1
	printf '%s|%s' "$bid" "$bname"
}

emit() {
	build_rules
	local lines aggr selfip
	selfip=$(uci -q get network.lan.ipaddr 2>/dev/null); [ -z "$selfip" ] && selfip=192.168.10.1
	lines=$(get_loglines)
	[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"dnsmasq 查询日志为空（未开启 logqueries 或近期无查询）"}'; return; }
	# 过滤本机来源 + 域名去重（同一域名查很多次只需匹配一次）+ 上限 600 行
	lines=$(printf '%s\n' "$lines" | grep -v -E "(^| )$selfip$" | grep -v "127.0.0.1" \
		| awk -F'\t' 'NF && $1!="" && !seen[$1]++' | head -n 600)
	[ -z "$lines" ] && { printf '{"apps":[],"source":"dns","note":"近 %s 分钟无内网设备活跃应用"}' "$WINDOW"; return; }
	# 单次 awk：规则表读入内存，选优顺序为「带 id 的规则 > 命中 key 更长 > prio 更小」，
	# 不再 per-line fork。带 id 优先是为了让 DNS 指纹（有正式 OAF id）压过 OAF 表里
	# 被置空 id 的同名条目；key 更长优先保证 music.163.com 命中网易云音乐而不是“网易”。
	aggr=$(printf '%s\n' "$lines" | awk -F'\t' '
		FNR==NR { if ($1 != "") { n++; k[n]=$1; id[n]=$2; nm[n]=$3; pr[n]=$4+0 } next }
		{
			d=$1; if (d == "") next
			b=0; be=2; bl=-1; bp=99
			for (i=1; i<=n; i++) {
				if (!index(d, k[i])) continue
				e = (id[i] == "" ? 1 : 0)
				if (e < be || (e == be && (length(k[i]) > bl || (length(k[i]) == bl && pr[i] < bp)))) {
					be=e; bl=length(k[i]); bp=pr[i]; b=i
				}
			}
			if (b == 0) next
			print id[b] "\t" nm[b] "\t" $2
		}
	' "$RULES" - | sort -u | awk -F'\t' '{cnt[$1 FS $2]++} END{for(k in cnt) print cnt[k] "\t" k}')
	[ -z "$aggr" ] && { printf '{"apps":[],"source":"dns","note":"近 %s 分钟未识别到活跃应用"}' "$WINDOW"; return; }
	printf '{"apps":['
	printf '%s\n' "$aggr" | sort -rn | awk -F'\t' '{a[NR]=$0} END{
		first=1
		for(i=1;i<=NR;i++){
			split(a[i],f,"\t"); cnt=f[1]; id=f[2]; name=f[3]
			if(!first) printf ","
			first=0
			gsub(/\\/,"\\\\",name); gsub(/"/,"\\\"",name)
			gsub(/\\/,"\\\\",id); gsub(/"/,"\\\"",id)
			printf "{\"id\":\"%s\",\"name\":\"%s\",\"deviceCount\":%s}",id,name,cnt
		}
	}'
	printf '],"source":"dns"}'
}

# ---- 并发保护 + 结果缓存 ----
# 前端多个入口会同时触发 list；单次执行要扫 dnsmasq 日志并匹配 OAF 表，
# 不加锁会叠出十几个进程（真机实测同时存在 12 个实例），直接把 CPU 吃满。
APP_CACHE=/tmp/athena-apps.json
APP_WIN=/tmp/athena-apps.win
APP_STAMP=/tmp/athena-apps.stamp
APP_LOCK=/var/run/athena-apps.lock

case "$1" in
	list|window)
		if [ "$1" = "window" ]; then WINDOW=${2:-15}; [ "$WINDOW" -gt 0 ] 2>/dev/null || WINDOW=15; fi
		NOWUP=$(cut -d. -f1 /proc/uptime)
		OLDUP=$(cat "$APP_STAMP" 2>/dev/null)
		# 缓存 60 秒有效，且统计窗口一致才复用
		if [ -s "$APP_CACHE" ] && [ -n "$OLDUP" ] && [ $((NOWUP - OLDUP)) -lt 60 ] 2>/dev/null \
		   && [ "$WINDOW" = "$(cat "$APP_WIN" 2>/dev/null)" ]; then
			cat "$APP_CACHE"; exit 0
		fi
		if mkdir "$APP_LOCK" 2>/dev/null; then
			OWN=1
			trap 'rmdir "$APP_LOCK" 2>/dev/null' EXIT INT TERM HUP
			emit > "$APP_CACHE.tmp" 2>/dev/null
			if [ -s "$APP_CACHE.tmp" ]; then
				mv "$APP_CACHE.tmp" "$APP_CACHE"
				printf '%s' "$WINDOW" > "$APP_WIN"
				cut -d. -f1 /proc/uptime > "$APP_STAMP"
				cat "$APP_CACHE"
			else
				rm -f "$APP_CACHE.tmp"
				cat "$APP_CACHE" 2>/dev/null || echo '{"apps":[],"source":"dns","note":"暂无数据"}'
			fi
		else
			# 已有实例在跑：直接返回缓存，绝不并发重算
			if [ -s "$APP_CACHE" ]; then cat "$APP_CACHE"
			else echo '{"apps":[],"source":"dns","note":"正在统计"}'; fi
		fi
		;;
	*) echo '{"ok":false,"msg":"usage: list|window <min>"}'; exit 1 ;;
esac
