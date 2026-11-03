#!/bin/sh
# AthenaWrt 软件包管理（apk 版）—— 兜底实现 v1.2.51
# ImmortalWrt SNAPSHOT r1-20261017 起，opkg 已被 apk 取代（/usr/bin/apk，无 opkg）。
# 用法:
#   athena-packages.sh list [installed|available] [keyword]
#   athena-packages.sh install <pkg>
#   athena-packages.sh remove <pkg>
#   athena-packages.sh update
#   athena-packages.sh upgrade <pkg>   注：apk 全量 upgrade 有变砖风险，仅允许单包升级
#
# `list installed`（无关键字）已由 athena-packages.uc 直读数据库接管，本文件保留其余分支。
#
# v1.2.51 的核心改动：available 改成"读缓存 + 后台预热"，页面永不等待。
#   真机实测 `apk list`（全仓库，一万多个包）要 36.34s，而且这 36 秒是纯 CPU。
#   原因不是索引加载慢（`apk list -I` 只要 1.41s），而是它把每个包的依赖/provides/体积
#   全格式化一遍。/var/cache/apk/APKINDEX.*.tar.gz 也不能自己解析：那是 apk 3.0 的
#   ADBd 二进制格式（魔数 41 44 42 64），既不是 gzip 也不是 tar，解析它没有性价比。
#   所以：缓存照用（TTL 内直接返回），过期了就在后台悄悄重算——请求本身立刻返回旧数据，
#   绝不让用户在页面上等 36 秒。
#
# v1.2.48 保留的两处修补：
#   1) 死锁自愈：锁里写持有者 PID，进程没了或超过 180 秒自动清理（真机曾因 09:17 的死锁
#      让 available 一直静默返回空列表）。
#   2) installed 已不走这里；available 的缓存 TTL 见下方 AV_KEEP / AV_STALE。

CMD="${1:-list}"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# Package-name validation prevents option injection and path-like arguments.
valid_pkg_name() {
	case "$1" in ''|-*|*/*|*[!A-Za-z0-9+._@-]*) return 1 ;; esac
	return 0
}

# Protect OpenClash, NSS/ECM, kernel, network and essential LuCI components.
protected_pkg() {
	case "$1" in
		luci-app-openclash|luci-i18n-openclash-*|openclash|mihomo*|clash*|sing-box*|singbox*| \
		qca-nss*|kmod-qca-nss*|qca-ssdk*|kmod-qca-ssdk*|ecm*|kmod-ecm*|nss-*|kmod-nss-*| \
		base-files|busybox|apk-tools|openwrt-keyring|immortalwrt-keyring|kernel|kernel-*|kmod-*| \
		libc|libc-*|musl|musl-*|libgcc|libgcc-*|libubox*|libubus*|libnl*|libopenssl*|libustream*|libqca-nss*|libecm*|libqca-ssdk*|ath11k-firmware*| \
		rpcd|rpcd-mod-*|ubus|uhttpd|netifd|firewall4|nftables|dnsmasq*|odhcpd*|dropbear|procd|fstools|block-mount| \
		wpad*|hostapd*|ppp|ppp-*|luci-base|luci-mod-*|luci-app-firewall|luci-app-athena|luci-theme-jdc-athena|luci-i18n-athena-zh-cn)
			return 0 ;;
	esac
	return 1
}

# 预演 APK 事务：禁止 Athena 页面间接升级、降级或移除关键组件。
transaction_safe() {
	local plan rc changed name
	plan=$("$@" 2>&1); rc=$?
	if [ "$rc" -ne 0 ]; then
		echo '{"ok":false,"msg":"无法完成软件包事务预演，已拒绝执行"}'
		return 1
	fi
	changed=$(printf '%s\n' "$plan" | awk '
		$1 ~ /^\([0-9]+\/[0-9]+\)$/ && ($2 == "Upgrading" || $2 == "Downgrading" || $2 == "Removing") { print $3 }
	')
	for name in $changed; do
		if protected_pkg "$name"; then
			printf '{"ok":false,"msg":"事务将变更受保护组件 %s，已拒绝执行"}\n' "$name"
			return 1
		fi
	done
	return 0
}

# apk list 输出 name-version（version 以数字开头），拆成 name|version
split_pv() {
	awk '{
		line=$1;
		if (match(line, /-[0-9][^[:space:]]*$/)) {
			print substr(line,1,RSTART-1) "|" substr(line,RSTART+1);
		} else {
			print line "|";
		}
	}'
}

installed_pkgs() { apk list -I 2>/dev/null | split_pv | sort; }
available_pkgs() { apk list 2>/dev/null | split_pv | sort; }

emit_list() {
	local src="$1" kw="$2" installed="$3"
	local first=1
	printf '{"ok":true,"packages":['
	$src | while IFS='|' read -r name ver; do
		[ -z "$name" ] && continue
		if [ -n "$kw" ]; then echo "$name" | grep -qi "$kw" || continue; fi
		[ "$first" = "1" ] || printf ','
		first=0
		printf '{"name":"%s","version":"%s","installed":%s}' \
			"$(printf '%s' "$name" | json_str)" "$ver" "$installed"
	done
	printf ']}'
}

AV_CACHE="/tmp/athena-pkg-available.tmp"
AV_STAMP="/tmp/athena-pkg-available.stamp"
AV_LOCK="/var/run/athena-pkg-available.lock"
AV_KEEP=86400     # 列表本身放 24 小时（它是"仓库里有什么"，不会分钟级变化）
AV_STALE=21600    # 超过 6 小时就在后台悄悄重算一遍

now_up() { cut -d. -f1 /proc/uptime; }

# 后台预热：抢锁 -> 后台子进程跑 apk list -> 落盘 -> 放锁
# 绝不阻塞调用方：调用方拿到的是"现在缓存里有什么"
warm_background() {
	mkdir "$AV_LOCK" 2>/dev/null || return 0
	echo $$ > "$AV_LOCK/pid"
	now_up > "$AV_LOCK/since"
	(
		emit_list available_pkgs "" false > "$AV_CACHE.new" 2>/dev/null
		if [ -s "$AV_CACHE.new" ]; then
			mv "$AV_CACHE.new" "$AV_CACHE"
			now_up > "$AV_STAMP"
		else
			rm -f "$AV_CACHE.new"
		fi
		rm -rf "$AV_LOCK"
	) >/dev/null 2>&1 &
}

case "$CMD" in
	list)
		SUB="${2:-installed}"; KW="${3:-}"

		# 带关键字：直接真查（用户明确在搜东西，慢一点可以接受）
		if [ -n "$KW" ]; then
			case "$SUB" in
				installed) emit_list installed_pkgs "$KW" true ;;
				available) emit_list available_pkgs "$KW" false ;;
				*) echo '{"ok":false,"msg":"未知列表类型"}'; exit 1 ;;
			esac
			exit 0
		fi

		if [ "$SUB" = "available" ]; then
			NOWUP=$(now_up)
			# 死锁自愈：持有者进程没了、或锁存在超过 180 秒，就清锁并清掉写了一半的 .new
			if [ -d "$AV_LOCK" ]; then
				LPID=$(cat "$AV_LOCK/pid" 2>/dev/null)
				LSINCE=$(cat "$AV_LOCK/since" 2>/dev/null)
				STALE=0
				[ -z "$LPID" ] && STALE=1
				[ -n "$LPID" ] && [ ! -d "/proc/$LPID" ] && STALE=1
				[ -n "$LSINCE" ] && [ $((NOWUP - LSINCE)) -gt 300 ] 2>/dev/null && STALE=1
				[ "$STALE" = "1" ] && { rm -rf "$AV_LOCK"; rm -f "$AV_CACHE.new"; }
			fi

			OLDUP=$(cat "$AV_STAMP" 2>/dev/null)
			AGE=""
			[ -n "$OLDUP" ] && AGE=$((NOWUP - OLDUP))

			# 没缓存、或缓存太旧 -> 起后台任务；无论哪种，都先把手里的数据返回
			if [ ! -s "$AV_CACHE" ]; then
				warm_background
				echo '{"ok":true,"packages":[],"note":"正在后台读取软件包列表，约一分钟后刷新即可"}'
				exit 0
			fi
			if [ -n "$AGE" ] && [ "$AGE" -ge "$AV_STALE" ]; then
				warm_background
			fi
			cat "$AV_CACHE"
			exit 0
		fi

		# installed 的兜底路径（正常情况由 athena-packages.uc 接管，走不到这里）
		if [ -s "/tmp/athena-pkg-installed.tmp" ]; then
			cat "/tmp/athena-pkg-installed.tmp"; exit 0
		fi
		emit_list installed_pkgs "" true > "/tmp/athena-pkg-installed.tmp" 2>/dev/null
		if [ -s "/tmp/athena-pkg-installed.tmp" ]; then
			cat "/tmp/athena-pkg-installed.tmp"
		else
			echo '{"ok":true,"packages":[]}'
		fi
		;;
	install)
		PKG="${2:-}"; valid_pkg_name "$PKG" || { echo '{"ok":false,"msg":"软件包名称无效"}'; exit 1; }
		if protected_pkg "$PKG"; then
			if installed_pkgs | awk -F'|' -v p="$PKG" '$1 == p { found=1 } END { exit !found }'; then
				echo '{"ok":false,"msg":"该关键软件包已安装，禁止通过安装入口变相升级"}'; exit 1
			fi
		fi
		transaction_safe apk add --simulate "$PKG" || exit 1
		apk add "$PKG" >/dev/null 2>&1 && echo "{\"ok\":true,\"msg\":\"$PKG 安装成功\"}" || echo "{\"ok\":false,\"msg\":\"$PKG 安装失败\"}"
		;;
	remove)
		PKG="${2:-}"; valid_pkg_name "$PKG" || { echo '{"ok":false,"msg":"软件包名称无效"}'; exit 1; }
		protected_pkg "$PKG" && { echo '{"ok":false,"msg":"该软件包属于 OpenClash、NSS/ECM 或关键系统组件，已禁止卸载"}'; exit 1; }
		transaction_safe apk del --simulate "$PKG" || exit 1
		apk del "$PKG" >/dev/null 2>&1 && echo "{\"ok\":true,\"msg\":\"$PKG 已卸载\"}" || echo "{\"ok\":false,\"msg\":\"$PKG 卸载失败\"}"
		;;
	update)
		# 索引刷新后旧列表必须作废，否则页面还显示老仓库内容
		rm -f "$AV_CACHE" "$AV_STAMP" "$AV_CACHE.new" /tmp/athena-pkg-installed.tmp 2>/dev/null
		rm -f /tmp/athena-pkg-available.json /tmp/athena-pkg-av.stamp 2>/dev/null
		apk update >/dev/null 2>&1 && echo '{"ok":true,"msg":"软件列表已更新"}' || echo '{"ok":false,"msg":"更新列表失败（可能无网络）"}'
		;;
	upgrade)
		PKG="${2:-}"
		valid_pkg_name "$PKG" || { echo '{"ok":false,"msg":"软件包名称无效"}'; exit 1; }
		protected_pkg "$PKG" && { echo '{"ok":false,"msg":"该软件包属于 OpenClash、NSS/ECM 或关键系统组件，已禁止升级"}'; exit 1; }
		if [ -z "$PKG" ]; then echo '{"ok":false,"msg":"为安全起见不支持全量升级，请指定单个包"}'; exit 1; fi
		transaction_safe apk upgrade --simulate "$PKG" || exit 1
		apk upgrade "$PKG" >/dev/null 2>&1 && echo "{\"ok\":true,\"msg\":\"$PKG 已更新\"}" || echo "{\"ok\":false,\"msg\":\"$PKG 更新失败\"}"
		;;
	*)
		echo '{"ok":false,"msg":"未知命令"}'
		exit 1
		;;
esac
