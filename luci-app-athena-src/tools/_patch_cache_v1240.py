# -*- coding: utf-8 -*-
"""为 AthenaWrt 三个后端脚本加入并发保护与结果缓存（v1.2.40 前置）。
现场证据：真机同时存在 12 个 athena-apps.sh、3 个 athena-packages.sh，
athena-status.sh 单次 real 1.66s / user 1.27s，导致 CPU 长期 74%~96%。
"""
import io, sys

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"

# ---------- 1. athena-apps.sh：加锁 + 60 秒缓存 ----------
p = BASE + r"\athena-apps.sh"
s = io.open(p, encoding="utf-8").read()

OLD = """case "$1" in
\tlist) emit ;;
\twindow) WINDOW=${2:-15}; [ "$WINDOW" -gt 0 ] 2>/dev/null || WINDOW=15; emit ;;
\t*) echo '{"ok":false,"msg":"usage: list|window <min>"}'; exit 1 ;;
esac"""

NEW = """# ---- 并发保护 + 结果缓存 ----
# 前端多个入口会同时触发 list；单次执行要扫 dnsmasq 日志并匹配 OAF 表，
# 不加锁会叠出十几个进程（真机实测同时存在 12 个实例），直接把 CPU 吃满。
APP_CACHE=/tmp/athena-apps.json
APP_WIN=/tmp/athena-apps.win
APP_STAMP=/tmp/athena-apps.stamp
APP_LOCK=/var/run/athena-apps.lock

case "$1" in
\tlist|window)
\t\tif [ "$1" = "window" ]; then WINDOW=${2:-15}; [ "$WINDOW" -gt 0 ] 2>/dev/null || WINDOW=15; fi
\t\tNOWUP=$(cut -d. -f1 /proc/uptime)
\t\tOLDUP=$(cat "$APP_STAMP" 2>/dev/null)
\t\t# 缓存 60 秒有效，且统计窗口一致才复用
\t\tif [ -s "$APP_CACHE" ] && [ -n "$OLDUP" ] && [ $((NOWUP - OLDUP)) -lt 60 ] 2>/dev/null \\
\t\t   && [ "$WINDOW" = "$(cat "$APP_WIN" 2>/dev/null)" ]; then
\t\t\tcat "$APP_CACHE"; exit 0
\t\tfi
\t\tif mkdir "$APP_LOCK" 2>/dev/null; then
\t\t\tOWN=1
\t\t\ttrap 'rmdir "$APP_LOCK" 2>/dev/null' EXIT INT TERM HUP
\t\t\temit > "$APP_CACHE.tmp" 2>/dev/null
\t\t\tif [ -s "$APP_CACHE.tmp" ]; then
\t\t\t\tmv "$APP_CACHE.tmp" "$APP_CACHE"
\t\t\t\tprintf '%s' "$WINDOW" > "$APP_WIN"
\t\t\t\tcut -d. -f1 /proc/uptime > "$APP_STAMP"
\t\t\t\tcat "$APP_CACHE"
\t\t\telse
\t\t\t\trm -f "$APP_CACHE.tmp"
\t\t\t\tcat "$APP_CACHE" 2>/dev/null || echo '{"apps":[],"source":"dns","note":"暂无数据"}'
\t\t\tfi
\t\telse
\t\t\t# 已有实例在跑：直接返回缓存，绝不并发重算
\t\t\tif [ -s "$APP_CACHE" ]; then cat "$APP_CACHE"
\t\t\telse echo '{"apps":[],"source":"dns","note":"正在统计"}'; fi
\t\tfi
\t\t;;
\t*) echo '{"ok":false,"msg":"usage: list|window <min>"}'; exit 1 ;;
esac"""

assert s.count(OLD) == 1, "apps.sh case 块未唯一命中: %d" % s.count(OLD)
s = s.replace(OLD, NEW)
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("apps.sh patched")

# ---------- 2. athena-packages.sh：list 分支加锁 + 120 秒缓存 ----------
p = BASE + r"\athena-packages.sh"
s = io.open(p, encoding="utf-8").read()

OLD = """case "$CMD" in
\tlist)
\t\tSUB="${2:-installed}"; KW="${3:-}"
\t\tcase "$SUB" in
\t\t\tinstalled) emit_list installed_pkgs "$KW" true ;;
\t\t\tavailable) emit_list available_pkgs "$KW" false ;;
\t\t\t*) echo '{"ok":false,"msg":"未知列表类型"}'; exit 1 ;;
\t\tesac
\t\t;;"""

NEW = """case "$CMD" in
\tlist)
\t\tSUB="${2:-installed}"; KW="${3:-}"
\t\t# 并发保护 + 120 秒缓存：apk list 要遍历全部索引，前端多入口并发时
\t\t# 会同时跑好几份（真机实测 3 个实例并存）
\t\tPKG_CACHE="/tmp/athena-pkg-$SUB.tmp"
\t\tPKG_STAMP="/tmp/athena-pkg-$SUB.stamp"
\t\tPKG_LOCK="/var/run/athena-pkg-$SUB.lock"
\t\tNOWUP=$(cut -d. -f1 /proc/uptime)
\t\tOLDUP=$(cat "$PKG_STAMP" 2>/dev/null)
\t\tif [ -s "$PKG_CACHE" ] && [ -z "$KW" ] && [ -n "$OLDUP" ] && [ $((NOWUP - OLDUP)) -lt 120 ] 2>/dev/null; then
\t\t\tcat "$PKG_CACHE"; exit 0
\t\tfi
\t\tif [ -n "$KW" ]; then
\t\t\tcase "$SUB" in
\t\t\t\tinstalled) emit_list installed_pkgs "$KW" true ;;
\t\t\t\tavailable) emit_list available_pkgs "$KW" false ;;
\t\t\t\t*) echo '{"ok":false,"msg":"未知列表类型"}'; exit 1 ;;
\t\t\tesac
\t\t\texit 0
\t\tfi
\t\tif mkdir "$PKG_LOCK" 2>/dev/null; then
\t\t\ttrap 'rmdir "$PKG_LOCK" 2>/dev/null' EXIT INT TERM HUP
\t\t\tcase "$SUB" in
\t\t\t\tinstalled) emit_list installed_pkgs "" true > "$PKG_CACHE.new" ;;
\t\t\t\tavailable) emit_list available_pkgs "" false > "$PKG_CACHE.new" ;;
\t\t\t\t*) echo '{"ok":false,"msg":"未知列表类型"}'; rmdir "$PKG_LOCK" 2>/dev/null; exit 1 ;;
\t\t\tesac
\t\t\tif [ -s "$PKG_CACHE.new" ]; then
\t\t\t\tmv "$PKG_CACHE.new" "$PKG_CACHE"
\t\t\t\tcut -d. -f1 /proc/uptime > "$PKG_STAMP"
\t\t\t\tcat "$PKG_CACHE"
\t\t\telse
\t\t\t\trm -f "$PKG_CACHE.new"
\t\t\t\tcat "$PKG_CACHE" 2>/dev/null || echo '{"ok":true,"packages":[]}'
\t\t\tfi
\t\telse
\t\t\tif [ -s "$PKG_CACHE" ]; then cat "$PKG_CACHE"
\t\t\telse echo '{"ok":true,"packages":[],"note":"正在读取软件包列表"}'; fi
\t\tfi
\t\t;;"""

assert s.count(OLD) == 1, "packages.sh list 分支未唯一命中: %d" % s.count(OLD)
s = s.replace(OLD, NEW)
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("packages.sh patched")

# ---------- 3. athena-status.sh：3 秒缓存 + 锁 ----------
p = BASE + r"\athena-status.sh"
s = io.open(p, encoding="utf-8").read()

HDR_OLD = """# ---- JSON 字符串转义 ----"""
HDR_NEW = """# ---- 结果缓存（3 秒）+ 并发合并 ----
# 单次执行实测 real 1.66s / user 1.27s（要 fork 几十个进程），而前端多页面
# 轮询会并发调用，不合并就会把 CPU 吃掉。3 秒内重复请求直接复用上次结果。
SCACHE=/tmp/athena-status.json
SSTAMP=/tmp/athena-status.stamp
SLOCK=/var/run/athena-status.lock
if [ -s "$SCACHE" ]; then
\t_oup=$(cat "$SSTAMP" 2>/dev/null)
\t_now=$(cut -d. -f1 /proc/uptime)
\tif [ -n "$_oup" ] && [ $((_now - _oup)) -lt 3 ] 2>/dev/null; then
\t\tcat "$SCACHE"
\t\texit 0
\tfi
fi
if mkdir "$SLOCK" 2>/dev/null; then
\tSOWN=1
\ttrap 'rmdir "$SLOCK" 2>/dev/null' EXIT INT TERM HUP
else
\t# 已有实例在算：等 1 秒读它的结果，避免重叠执行
\tsleep 1
\tif [ -s "$SCACHE" ]; then cat "$SCACHE"; exit 0; fi
\tSOWN=0
fi

# ---- JSON 字符串转义 ----"""

assert s.count(HDR_OLD) == 1, "status.sh 头锚点未唯一命中: %d" % s.count(HDR_OLD)
s = s.replace(HDR_OLD, HDR_NEW)

TAIL_OLD = """# ---- 组装 JSON ----
cat <<EOF"""
TAIL_NEW = """# ---- 组装 JSON（写入缓存，供并发/多页面复用）----
cat <<EOF > "$SCACHE.tmp\""""

assert s.count(TAIL_OLD) == 1, "status.sh 尾部锚点未唯一命中: %d" % s.count(TAIL_OLD)
s = s.replace(TAIL_OLD, TAIL_NEW)

# 在最后一个 EOF 之后追加落盘逻辑
idx = s.rstrip().rfind("\nEOF")
assert idx > 0, "未找到结尾 EOF"
tail_add = """
mv "$SCACHE.tmp" "$SCACHE" 2>/dev/null
cut -d. -f1 /proc/uptime > "$SSTAMP" 2>/dev/null
cat "$SCACHE"
"""
s = s[:idx + 4] + tail_add + s[idx + 4:]
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("status.sh patched")
print("done")
