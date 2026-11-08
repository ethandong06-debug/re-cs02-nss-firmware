#!/bin/sh
# AthenaWrt V1.0 least-privilege RPC gateway.
# No mode switching, PPPoE/VLAN/IPv6 writes, firmware flashing, factory reset or restore.
set -eu
BASE=/usr/libexec
fail() { msg=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\r//g; s/\n/\\n/g'); printf '{"ok":false,"msg":"%s"}\n' "$msg"; exit 1; }
need() { [ "$#" -ge "$1" ] || fail "参数不足"; }
valid_mac() { printf '%s\n' "$1" | grep -Eiq '^([0-9a-f]{2}:){5}[0-9a-f]{2}$'; }
valid_host() { [ -n "$1" ] && [ "${#1}" -le 253 ] && printf '%s' "$1" | grep -Eq '^[A-Za-z0-9._:-]+$'; }
cmd="${1:-help}"; [ "$#" -gt 0 ] && shift || true
case "$cmd" in
  status) exec "$BASE/athena-status.sh" "$@" ;;
  resources) exec "$BASE/athena-resources.sh" "$@" ;;
  accel) exec "$BASE/athena-accel.sh" ;;
  wifi-get) exec "$BASE/athena-wireless.sh" get ;;
  wifi-enable|wifi-disable) need 1 "$#"; case "$1" in all|b24|b52|b58) ;; *) fail "无线频段参数无效";; esac; exec "$BASE/athena-wireless.sh" "${cmd#wifi-}" "$1" ;;
  wifi-set) need 7 "$#"; case "$1" in b24|b52|b58) ;; *) fail "无线频段参数无效";; esac; exec "$BASE/athena-wireless.sh" set "$@" ;;
  wifi-guest-get) exec "$BASE/athena-wireless.sh" guest get ;;
  wifi-guest-enable) need 2 "$#"; exec "$BASE/athena-wireless.sh" guest enable "$1" "$2" ;;
  wifi-guest-disable) exec "$BASE/athena-wireless.sh" guest disable ;;
  wifi-schedule-status) exec "$BASE/athena-wifi-schedule.sh" status ;;
  wifi-schedule-set) need 5 "$#"; exec "$BASE/athena-wifi-schedule.sh" set "$@" ;;
  wifi-schedule-disable) exec "$BASE/athena-wifi-schedule.sh" disable ;;
  clients-list) exec "$BASE/athena-client.sh" list ;;
  clients-block|clients-unblock|clients-know|clients-unlearn) need 1 "$#"; valid_mac "$1" || fail "MAC 地址格式无效"; case "$cmd" in clients-block) exec "$BASE/athena-client.sh" block "$1";; clients-unblock) exec "$BASE/athena-client.sh" unblock "$1";; clients-know) exec "$BASE/athena-client.sh" know "$1";; clients-unlearn) exec "$BASE/athena-client.sh" unlearn "$1";; esac ;;
  clients-known) exec "$BASE/athena-client.sh" known ;;
  clients-notes) exec "$BASE/athena-client.sh" notes ;;
  clients-note) need 2 "$#"; valid_mac "$1" || fail "MAC 地址格式无效"; exec "$BASE/athena-client.sh" note "$1" "$2" ;;
  clients-rename) need 2 "$#"; valid_mac "$1" || fail "MAC 地址格式无效"; exec "$BASE/athena-client.sh" rename "$1" "$2" ;;
  parent-list) exec "$BASE/athena-parent.sh" list ;;
  parent-set) need 4 "$#"; valid_mac "$1" || fail "MAC 地址格式无效"; exec "$BASE/athena-parent.sh" set "$@" ;;
  parent-clear) need 1 "$#"; valid_mac "$1" || fail "MAC 地址格式无效"; exec "$BASE/athena-parent.sh" clear "$1" ;;
  disk-list) exec "$BASE/athena-disk.sh" list ;;
  disk-mount) need 2 "$#"; [ "$2" = /mnt/usb ] || fail "USB 分区只能挂载到 /mnt/usb"; exec "$BASE/athena-disk.sh" mount "$1" "$2" "${3:-auto}" ;;
  disk-umount) need 1 "$#"; exec "$BASE/athena-disk.sh" umount "$1" ;;
  disk-format) need 3 "$#"; [ "$3" = CONFIRM_FORMAT ] || fail "格式化必须经过二次确认"; exec "$BASE/athena-disk.sh" format "$1" "$2" ;;
  nas-status) exec "$BASE/athena-nas.sh" status ;;
  nas-install) need 1 "$#"; case "$1" in ksmbd|samba4) ;; *) fail "NAS 实现仅支持 KSMBD 或 Samba4";; esac; exec "$BASE/athena-nas.sh" install "$1" ;;
  nas-start) exec "$BASE/athena-nas.sh" start ;;
  nas-stop) exec "$BASE/athena-nas.sh" stop ;;
  nas-remove) need 1 "$#"; [ "$1" = CONFIRM_REMOVE ] || fail "卸载 NAS 必须经过二次确认"; exec "$BASE/athena-nas.sh" remove ;;
  nas-credentials) exec "$BASE/athena-nas.sh" credentials ;;
  matrix-get) exec "$BASE/athena-matrix.sh" get ;;
  matrix-set) need 2 "$#"; case "$1" in enabled|light_level|night|night_start|night_end|night_level|profile|clock|medal|up|down) ;; *) fail "点阵屏配置项无效";; esac; exec "$BASE/athena-matrix.sh" set "$1" "$2" ;;
  led-get) exec "$BASE/athena-led.sh" get ;;
  led-breath) need 1 "$#"; case "$1" in 0|1) ;; *) fail "呼吸灯参数只能为 0 或 1";; esac; exec "$BASE/athena-led.sh" set breath "$1" ;;
  diag-check) exec "$BASE/athena-diag.sh" check ;;
  diag-ping) need 1 "$#"; valid_host "$1" || fail "目标主机格式无效"; exec "$BASE/athena-diag.sh" ping "$1" 4 ;;
  diag-dns) need 1 "$#"; valid_host "$1" || fail "域名格式无效"; exec "$BASE/athena-diag.sh" dns "$1" ;;
  backup-list) exec "$BASE/athena-backup.sh" list ;;
  backup-create) exec "$BASE/athena-backup.sh" create ;;
  backup-download) need 1 "$#"; exec "$BASE/athena-backup.sh" download "$1" ;;
  backup-delete)
    need 1 "$#"
    case "$1" in config-*.tar.gz) ;; *) fail "备份文件名无效";; esac
    case "$1" in *[!A-Za-z0-9._-]*|*..*) fail "备份文件名无效";; esac
    base=$(readlink -f /etc/athena-backup 2>/dev/null) || fail "备份目录不存在"
    file=$(readlink -f "/etc/athena-backup/$1" 2>/dev/null) || fail "备份文件不存在"
    case "$file" in "$base"/config-*.tar.gz) ;; *) fail "拒绝删除备份目录之外的文件";; esac
    [ -f "$file" ] || fail "备份文件不存在"
    rm -f "$file" || fail "删除备份失败"
    printf '{"ok":true,"msg":"备份已删除"}\n'
    ;;
  backup-schedule-get) exec "$BASE/athena-backup.sh" schedule get ;;
  backup-schedule-set) need 3 "$#"; exec "$BASE/athena-backup.sh" schedule set "$@" ;;
  backup-schedule-disable) exec "$BASE/athena-backup.sh" schedule disable ;;

  backup-download) need 1 "$#"; exec "$BASE/athena-backup.sh" download "$1" ;;

  reboot-status) exec "$BASE/athena-reboot.sh" status ;;
  reboot-enable) need 2 "$#"; exec "$BASE/athena-reboot.sh" enable "$1" "$2" ;;
  reboot-disable) exec "$BASE/athena-reboot.sh" disable ;;
  reboot-now) need 1 "$#"; [ "$1" = CONFIRM_REBOOT ] || fail "立即重启必须经过二次确认"; exec "$BASE/athena-reboot.sh" now ;;
  logs-read) exec "$BASE/athena-log.sh" list "${1:-all}" "${2:-}" ;;
  logs-export) exec "$BASE/athena-log.sh" export ;;
  packages-installed) exec "$BASE/athena-packages.sh" list installed ;;
  packages-available) exec "$BASE/athena-packages.sh" list available ;;
  packages-install) need 1 "$#"; exec "$BASE/athena-packages.sh" install "$1" ;;
  packages-remove) need 1 "$#"; exec "$BASE/athena-packages.sh" remove "$1" ;;
  packages-upgrade) need 1 "$#"; exec "$BASE/athena-packages.sh" upgrade "$1" ;;
  packages-update) exec "$BASE/athena-packages.sh" update ;;
  apps-list) exec "$BASE/athena-apps.sh" list ;;
  services-list) exec "$BASE/athena-services.sh" list ;;
  filebrowser-status) exec "$BASE/athena-services.sh" filebrowser-status ;;
  *) fail "此操作未开放真实后端接口。网络模式切换、PPPoE/VLAN/IPv6 写入、固件刷写、恢复出厂和备份恢复均被 V1.0 网关阻断。" ;;
esac
