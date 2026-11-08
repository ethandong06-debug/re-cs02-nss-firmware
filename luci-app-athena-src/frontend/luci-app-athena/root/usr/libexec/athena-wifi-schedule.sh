#!/bin/sh
# AthenaWrt Wi-Fi schedule. Owns only lines marked ATHENA_WIFI_SCHEDULE.
set -eu
CONF=/etc/athena/wifi-schedule.conf
CRON=/etc/crontabs/root
fail(){ printf '{"ok":false,"msg":"%s"}\n' "$1"; exit 1; }
valid_time(){
  case "$1" in [0-9][0-9]:[0-9][0-9]) ;; *) return 1;; esac
  h=\${1%:*}; m=\${1#*:}
  [ "$h" -le 23 ] 2>/dev/null && [ "$m" -le 59 ] 2>/dev/null
}
remove_owned(){
  [ -f "$CRON" ] || return 0
  tmp="$CRON.athena.$$"
  grep -v '# ATHENA_WIFI_SCHEDULE$' "$CRON" > "$tmp" || true
  cat "$tmp" > "$CRON"; rm -f "$tmp"
}
write_line(){
  time="$1"; action="$2"; band="$3"
  h=\${time%:*}; m=\${time#*:}
  printf '%s %s * * * /usr/libexec/athena-wireless.sh %s %s >/dev/null 2>&1 # ATHENA_WIFI_SCHEDULE\n' "$m" "$h" "$action" "$band" >> "$CRON"
}
case "\${1:-status}" in
  status)
    if [ -r "$CONF" ]; then
      . "$CONF"
      printf '{"ok":true,"enabled":true,"off":"%s","on":"%s","b24":%s,"b52":%s,"b58":%s}\n' "$OFF" "$ON" "$B24" "$B52" "$B58"
    else
      printf '{"ok":true,"enabled":false}\n'
    fi
    ;;
  set)
    OFF="\${2:-}"; ON="\${3:-}"; B24="\${4:-0}"; B52="\${5:-0}"; B58="\${6:-0}"
    valid_time "$OFF" && valid_time "$ON" || fail "时间格式必须为 HH:MM"
    for v in "$B24" "$B52" "$B58"; do case "$v" in 0|1) ;; *) fail "频段开关只能为 0 或 1";; esac; done
    [ "$B24$B52$B58" != "000" ] || fail "至少选择一个需要定时控制的频段"
    mkdir -p /etc/athena /etc/crontabs
    umask 077
    printf 'OFF=%s\nON=%s\nB24=%s\nB52=%s\nB58=%s\n' "$OFF" "$ON" "$B24" "$B52" "$B58" > "$CONF"
    touch "$CRON"
    remove_owned
    for pair in "b24:$B24" "b52:$B52" "b58:$B58"; do
      band=\${pair%%:*}; enabled=\${pair#*:}
      [ "$enabled" = 1 ] || continue
      write_line "$OFF" disable "$band"
      write_line "$ON" enable "$band"
    done
    /etc/init.d/cron restart >/dev/null 2>&1 || /etc/init.d/crond restart >/dev/null 2>&1 || fail "cron 重载失败"
    printf '{"ok":true,"msg":"Wi-Fi 定时任务已保存","off":"%s","on":"%s"}\n' "$OFF" "$ON"
    ;;
  disable)
    remove_owned
    rm -f "$CONF"
    /etc/init.d/cron restart >/dev/null 2>&1 || /etc/init.d/crond restart >/dev/null 2>&1 || fail "cron 重载失败"
    printf '{"ok":true,"msg":"Wi-Fi 定时已关闭；其他 crontab 项未修改"}\n'
    ;;
  *) fail "仅支持 status|set|disable" ;;
esac
