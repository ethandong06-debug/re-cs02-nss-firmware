#!/bin/sh
# AthenaWrt 固件升级
# 用法:
#   athena-upgrade.sh check                检查是否有新固件（当前仅返回本地版本信息）
#   athena-upgrade.sh flash <文件路径>      刷写 sysupgrade 固件（保留配置或全新刷）
#   athena-upgrade.sh verify <文件路径>     校验固件文件（魔数/大小）
# 输出单行 JSON

CMD="${1:-check}"

case "$CMD" in
	check)
		VER=$(cat /etc/openwrt_release 2>/dev/null | sed -n 's/^DISTRIB_DESCRIPTION=//p' | tr -d '"')
		[ -z "$VER" ] && VER="AthenaWrt v1.0.0"
		echo "{\"ok\":true,\"current\":\"$VER\",\"latest\":null,\"msg\":\"已是最新（本机无在线源，需手动上传固件）\"}"
		;;
	verify)
		FILE="${2:-}"
		[ -z "$FILE" ] && { echo '{"ok":false,"msg":"缺少固件路径"}'; exit 1; }
		[ -f "$FILE" ] || { echo '{"ok":false,"msg":"文件不存在"}'; exit 1; }
		SIZE=$(wc -c < "$FILE" 2>/dev/null | tr -d ' ')
		SHA=$(sha256sum "$FILE" 2>/dev/null | awk '{print $1}')
		# sysupgrade -T 在本平台对任意数据都返回成功，不可作为判据，只作兜底
		if sysupgrade -T "$FILE" >/dev/null 2>&1; then STOP=true; else STOP=false; fi
		# 真实判据：固件是未压缩 tar，头部为 sysupgrade-<机型>/，内含 CONTROL / kernel / root
		HDR=$(dd if="$FILE" bs=1 count=12 2>/dev/null)
		LIST=$(tar -tf "$FILE" 2>/dev/null | head -n 40)
		DIR=$(printf '%s\n' "$LIST" | sed -n '1p' | sed 's#/*$##')
		COMP=false
		REASON="不是有效的 sysupgrade 固件包（缺少 sysupgrade-*/CONTROL、kernel、root 结构）"
		case "$HDR" in
			sysupgrade-*)
				if printf '%s\n' "$LIST" | grep -q '/CONTROL$' 2>/dev/null \
				   && printf '%s\n' "$LIST" | grep -q '/kernel$' 2>/dev/null \
				   && printf '%s\n' "$LIST" | grep -q '/root$' 2>/dev/null; then
					BOARD=$(cat /tmp/sysinfo/board_name 2>/dev/null | tr ',' '_')
					[ -z "$BOARD" ] && BOARD="jdcloud_re-cs-02"
					if [ "$DIR" = "sysupgrade-$BOARD" ]; then
						COMP=true; REASON=""
					else
						REASON="固件目标机型不匹配（固件：$DIR，本机：sysupgrade-$BOARD）"
					fi
				fi
				;;
		esac
		echo "{\"ok\":true,\"size\":${SIZE:-0},\"sha256\":\"$SHA\",\"compatible\":$COMP,\"stopper\":$STOP,\"pkg\":\"$DIR\",\"reason\":\"$REASON\"}"
		;;
	flash)
		FILE="${2:-}"
		KEEP="${3:-1}"
		[ -z "$FILE" ] && { echo '{"ok":false,"msg":"缺少固件路径"}'; exit 1; }
		[ -f "$FILE" ] || { echo '{"ok":false,"msg":"文件不存在"}'; exit 1; }
		# 若为 base64 上传文件（.b64）则先解码为 .bin
		FW="$FILE"
		case "$FILE" in
			*.b64)
				DEC="/tmp/athena-fw.bin"
				base64 -d "$FILE" > "$DEC" 2>/dev/null
				[ -s "$DEC" ] || { echo '{"ok":false,"msg":"固件解码失败（上传文件可能不完整）"}'; exit 1; }
				FW="$DEC"
				rm -f "$FILE" 2>/dev/null
				;;
		esac
		# 刷写前用 sysupgrade 自带完整性校验（平台/魔数/大小），失败则拒绝刷写，避免损坏固件导致变砖
		if ! sysupgrade -T "$FW" >/dev/null 2>&1; then
			echo '{"ok":false,"msg":"固件校验失败（不匹配本机平台或文件损坏），已取消刷写"}'
			rm -f "$FW" 2>/dev/null
			exit 1
		fi
		# 刷写：-n 不保留配置（全新刷）
		if [ "$KEEP" = "0" ]; then
			echo '{"ok":true,"msg":"开始刷写（不保留配置），设备即将重启"}'
			( sleep 1; sysupgrade -n "$FW" ) >/dev/null 2>&1 &
		else
			echo '{"ok":true,"msg":"开始刷写（保留配置），设备即将重启"}'
			( sleep 1; sysupgrade "$FW" ) >/dev/null 2>&1 &
		fi
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 check|verify|flash）"}'
		exit 1
		;;
esac
