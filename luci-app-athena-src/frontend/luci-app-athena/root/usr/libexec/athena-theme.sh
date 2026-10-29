#!/bin/sh
# AthenaWrt 液态玻璃主题持久化
# 用法:
#   athena-theme.sh get                                     读取主题（JSON）
#   athena-theme.sh set <palette> <blob> <glass> <blur> <iri> <hi> [dark]  一次性保存全部
#   athena-theme.sh reset                                   恢复默认
# 字段模型与前端 GLASS_THEME 一致：
#   palette: aurora|ocean|emerald|sunset|plain（颜色渲染在前端 GLASS_PALETTES）
#   blob/glass/blur/iri/hi: 0-100 整数
#   dark: light|dark|auto（明暗模式，路由器级持久化，换浏览器不丢失）

CMD="${1:-get}"

D_PALETTE="aurora"; D_BLOB="100"; D_GLASS="58"; D_BLUR="20"; D_IRI="55"; D_HI="70"

get_val() { uci -q get "athena.theme.$1" 2>/dev/null; }
num() { echo "$1" | grep -oE '^[0-9]+$' | head -1; }

emit_json() {
	local p=$(get_val palette); [ -z "$p" ] && p="$D_PALETTE"
	local blob=$(num "$(get_val blob)"); [ -z "$blob" ] && blob="$D_BLOB"
	local glass=$(num "$(get_val glass)"); [ -z "$glass" ] && glass="$D_GLASS"
	local blur=$(num "$(get_val blur)"); [ -z "$blur" ] && blur="$D_BLUR"
	local iri=$(num "$(get_val iri)"); [ -z "$iri" ] && iri="$D_IRI"
	local hi=$(num "$(get_val hi)"); [ -z "$hi" ] && hi="$D_HI"
	local dark=$(get_val dark); [ -z "$dark" ] && dark="auto"
	printf '{"ok":true,"palette":"%s","blob":%s,"glass":%s,"blur":%s,"iri":%s,"hi":%s,"dark":"%s"}' \
		"$p" "$blob" "$glass" "$blur" "$iri" "$hi" "$dark"
}

case "$CMD" in
	get) emit_json ;;
	set)
		P="${2:-$D_PALETTE}"
		case "$P" in aurora|ocean|emerald|sunset|plain) ;; *) P="$D_PALETTE" ;; esac
		B=$(num "${3:-$D_BLOB}"); [ -z "$B" ] && B="$D_BLOB"
		G=$(num "${4:-$D_GLASS}"); [ -z "$G" ] && G="$D_GLASS"
		L=$(num "${5:-$D_BLUR}"); [ -z "$L" ] && L="$D_BLUR"
		I=$(num "${6:-$D_IRI}"); [ -z "$I" ] && I="$D_IRI"
		H=$(num "${7:-$D_HI}"); [ -z "$H" ] && H="$D_HI"
		D="${8:-}"
		# dark 白名单：light|dark|auto；传空则不修改（兼容旧调用只传 6 参）
		if [ -n "$D" ]; then
			case "$D" in light|dark|auto) ;; *) D="" ;; esac
		fi
		[ "$B" -gt 100 ] 2>/dev/null && B=100; [ "$G" -gt 100 ] 2>/dev/null && G=100
		[ "$L" -gt 100 ] 2>/dev/null && L=100; [ "$I" -gt 100 ] 2>/dev/null && I=100; [ "$H" -gt 100 ] 2>/dev/null && H=100
		uci -q set "athena.theme.palette=$P"
		uci -q set "athena.theme.blob=$B"
		uci -q set "athena.theme.glass=$G"
		uci -q set "athena.theme.blur=$L"
		uci -q set "athena.theme.iri=$I"
		uci -q set "athena.theme.hi=$H"
		[ -n "$D" ] && uci -q set "athena.theme.dark=$D"
		uci commit athena 2>/dev/null
		emit_json
		;;
	reset)
		uci -q delete athena.theme 2>/dev/null
		uci -q set athena.theme=theme
		uci commit athena 2>/dev/null
		echo '{"ok":true,"msg":"主题已恢复默认"}'
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 get|set|reset）"}'
		exit 1
		;;
esac
