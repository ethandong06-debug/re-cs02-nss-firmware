#!/bin/sh
# AthenaWrt — dnsmasq 查询日志限额（v1.2.56）
#
# 背景：/etc/config/dhcp 里 log-facility=/tmp/dnsmasq.log 开着 log-queries，
#       这台机器 /tmp 是 tmpfs（直吃内存），真机实测日志已长到 31MB → 44.8MB。
#       日志同时是「当前活跃应用」的数据源，不能简单关掉。
#
# 做法：超过 2MB 时原地裁剪，只保留最后 20000 行（约 1.6-1.8MB）。
#       原位截断（cat > 文件）而不是 mv，为的是不破坏 dnsmasq 已打开的 FD；
#       dnsmasq 以 O_APPEND 写日志，截断后会自动从新文件尾继续写。
#
# 触发：/etc/crontabs/root 每分钟一次（见 README 安装步骤），
#       另外 athena-apps.sh 每次被调用时也会顺手调一次（双保险）。
#
# v1.2.55 修正：本机 BusyBox 的 `stat -c '%s'` 返回空（真机 sh -x 实测 `+ sz=`），
#   导致 v1.2.53 版脚本读到空尺寸后直接 exit 0，一次都没裁过。改用 `wc -c` 取字节数。

LOG=/tmp/dnsmasq.log
CAP=4194304          # 4 MB（v1.2.56：真机 20000 行实测 2.27MB，比 2MB 还大，会每分钟裁一次空转）
KEEP=20000           # 保留行数（约 1.6-2.3MB，够「最近 15 分钟」用；apps.sh 只读最后 3000 行）
TMP=/tmp/.dnsmasq.log.trim

fsize() {
	# wc -c 在这种 BusyBox 上可用；先 wc，失败再退回 stat（个别版本 stat 才支持 %s）
	_n=$(wc -c < "$1" 2>/dev/null | tr -d ' \t')
	case "$_n" in ''|*[!0-9]*) _n=$(stat -c %s "$1" 2>/dev/null) ;; esac
	printf '%s' "$_n"
}

[ -f "$LOG" ] || exit 0

sz=$(fsize "$LOG")
case "$sz" in ''|*[!0-9]*) exit 0 ;; esac
[ "$sz" -gt "$CAP" ] || exit 0

# 同一时刻只允许一个实例裁剪（cron 与页面请求可能撞车）
if ! mkdir /tmp/.athena-logcap.lock 2>/dev/null; then
	exit 0
fi
trap 'rmdir /tmp/.athena-logcap.lock 2>/dev/null' EXIT INT TERM

tail -n "$KEEP" "$LOG" > "$TMP" 2>/dev/null || { rm -f "$TMP"; exit 1; }
cat "$TMP" > "$LOG"
rm -f "$TMP"

nw=$(fsize "$LOG")
echo "$(date '+%F %T') trim $sz -> ${nw:-0} bytes" >> /tmp/athena-logcap.log 2>/dev/null
# 只留最近 50 条裁剪记录，避免它自己也长成负担
if [ "$(wc -l < /tmp/athena-logcap.log 2>/dev/null || echo 0)" -gt 50 ]; then
	tail -n 50 /tmp/athena-logcap.log > "$TMP" 2>/dev/null && cat "$TMP" > /tmp/athena-logcap.log && rm -f "$TMP"
fi

exit 0
