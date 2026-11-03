#!/bin/sh
# AthenaWrt NAS lifecycle manager: choose exactly one SMB provider, KSMBD or Samba4.
# Share root is constrained to a verified USB filesystem at /mnt/usb/AthenaShare.
# Stop/uninstall never deletes user data.
set -u
CONF=/etc/athena/nas.conf
OWNER=/etc/athena/nas.owner
PASSFILE=/etc/athena/nas.password
SHARE=/mnt/usb/AthenaShare
NAS_USER=athena-nas

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\r//g; s/\n/\\n/g'; }
fail() { printf '{"ok":false,"msg":"%s"}\n' "$(json_escape "$1")"; exit 1; }
method_pkg() { case "$1" in ksmbd) echo ksmbd-server;; samba4) echo samba4-server;; *) return 1;; esac; }
method_init() { case "$1" in ksmbd) echo ksmbd;; samba4) echo samba4;; *) return 1;; esac; }
read_method() { [ -r "$CONF" ] && sed -n 's/^method=\(ksmbd\|samba4\)$/\1/p' "$CONF" | head -1; }
owned_pkg() { [ -r "$OWNER" ] && sed -n '1p' "$OWNER" | grep -E '^(ksmbd-server|samba4-server)$'; }
pkg_installed() { apk info -e "$1" >/dev/null 2>&1; }
is_usb_mounted() {
  local dev name part
  dev=$(awk '$2=="/mnt/usb" && $1 ~ /^\/dev\/sd[a-z][0-9]+$/ {print $1; exit}' /proc/mounts)
  [ -n "$dev" ] || return 1
  name=$(basename "$dev")
  part=$(cat "/sys/class/block/$name/partition" 2>/dev/null)
  [ -n "$part" ] && [ -e "/sys/class/block/$name" ] || return 1
  [ -d /mnt/usb ] || return 1
  return 0
}
lan_ip() {
  local dev ip
  dev=$(uci -q get network.lan.device 2>/dev/null); [ -z "$dev" ] && dev=br-lan
  ip=$(ip -4 -o addr show dev "$dev" 2>/dev/null | awk '{split($4,a,"/"); if(a[1] !~ /^169\.254\./ && a[1]!="127.0.0.1"){print a[1];exit}}')
  [ -n "$ip" ] || ip=$(uci -q get network.lan.ipaddr 2>/dev/null)
  printf '%s' "$ip"
}
provider_running() {
  case "$1" in ksmbd) pidof ksmbd.mountd >/dev/null 2>&1;; samba4) pidof smbd >/dev/null 2>&1;; *) return 1;; esac
}
supervisor_enabled() { [ -e /etc/rc.d/S99athena-nas ]; }
port_445_busy() { awk 'NR>1 && $2 ~ /:01BD$/ && $4=="0A" {found=1} END {exit !found}' /proc/net/tcp /proc/net/tcp6 2>/dev/null; }
protected_plan() {
  printf '%s\n' "$1" | grep -Eiq 'openclash|mihomo|sing[-_]?box|qca[-_]nss|qca[-_]ssdk|(^|[^[:alnum:]_])(ecm|kernel|netifd|firewall4|nftables|ppp|odhcpd|base-files|busybox|apk-tools|rpcd|ubus)([^[:alnum:]_]|$)'
}
simulate_add() {
  local package="$1" plan
  plan=$(apk add --simulate "$package" 2>&1) || fail "APK 依赖事务模拟失败，已拒绝安装"
  [ -n "$plan" ] || fail "APK 没有返回事务计划，无法判断安装影响"
  printf '%s\n' "$plan" | grep -F "$package" >/dev/null 2>&1 || fail "APK 事务计划未明确列出目标包，已拒绝安装"
  printf '%s\n' "$plan" | grep -Eiq 'upgrad|downgrad|remov|purge|replac' && fail "APK 事务包含升级、降级、删除或替换操作，已拒绝"
  protected_plan "$plan" && fail "APK 事务涉及 OpenClash、NSS/ECM、内核或网络关键组件，已拒绝"
}
simulate_remove() {
  local package="$1" plan installed
  plan=$(apk del --simulate "$package" 2>&1) || fail "NAS 卸载事务模拟失败，已保留软件包"
  [ -n "$plan" ] || fail "APK 没有返回卸载计划，已拒绝"
  protected_plan "$plan" && fail "卸载事务涉及受保护系统组件，已拒绝"
  printf '%s\n' "$plan" | grep -F "$package" >/dev/null 2>&1 || fail "卸载计划未明确列出 NAS 软件包，已拒绝"
  # Any additional installed package named in the solver output makes removal unsafe.
  for installed in $(apk info 2>/dev/null); do
    [ "$installed" = "$package" ] && continue
    printf '%s\n' "$plan" | grep -F "$installed" >/dev/null 2>&1 && fail "卸载事务可能影响其他软件包（$installed），为保护依赖已拒绝"
  done
}
create_unix_user() {
  id "$NAS_USER" >/dev/null 2>&1 && return 0
  command -v adduser >/dev/null 2>&1 || fail "系统缺少 adduser，无法创建 NAS 用户"
  adduser -D -H -s /bin/false "$NAS_USER" >/dev/null 2>&1 || fail "创建 NAS 专用系统用户失败"
  id "$NAS_USER" >/dev/null 2>&1 || fail "无法验证 NAS 系统用户"
}
generate_password() {
  local p
  p=$(openssl rand -hex 16 2>/dev/null)
  [ "${#p}" -eq 32 ] || fail "无法生成 NAS 随机密码"
  printf '%s' "$p"
}
prepare_share() {
  local real
  is_usb_mounted || fail "请先将真实 USB 分区挂载到 /mnt/usb"
  mkdir -p "$SHARE" || fail "创建 NAS 共享目录失败"
  real=$(readlink -f "$SHARE" 2>/dev/null)
  case "$real" in /mnt/usb/*) ;; *) fail "共享目录解析后超出 USB 挂载目录，已拒绝" ;; esac
  chmod 0770 "$real" 2>/dev/null || fail "设置共享目录权限失败"
  chown "$NAS_USER" "$real" 2>/dev/null || fail "当前文件系统不支持 NAS 用户所有权；请使用支持 Unix 权限的文件系统"
}
configure_ksmbd() {
  local pass="$1" sec
  command -v ksmbd.adduser >/dev/null 2>&1 || fail "KSMBD 用户管理工具缺失"
  sec=$(uci -q show ksmbd 2>/dev/null | sed -n 's/^ksmbd\.\([^.=]*\)=globals$/\1/p' | head -1)
  [ -n "$sec" ] || sec=$(uci add ksmbd globals 2>/dev/null)
  [ -n "$sec" ] || fail "创建 KSMBD 全局配置失败"
  uci set "ksmbd.$sec.interface=lan"
  uci set "ksmbd.$sec.workgroup=WORKGROUP"
  uci set ksmbd.athena_share=share
  uci set ksmbd.athena_share.name=AthenaShare
  uci set "ksmbd.athena_share.path=$SHARE"
  uci set "ksmbd.athena_share.users=$NAS_USER"
  uci set ksmbd.athena_share.read_only=no
  uci set ksmbd.athena_share.guest_ok=no
  uci set ksmbd.athena_share.create_mask=0660
  uci set ksmbd.athena_share.dir_mask=0770
  uci commit ksmbd || fail "写入 KSMBD 配置失败"
  ksmbd.adduser -a -p "$pass" "$NAS_USER" >/dev/null 2>&1 || fail "创建 KSMBD SMB 账号失败"
}
configure_samba4() {
  local pass="$1" sec
  command -v smbpasswd >/dev/null 2>&1 || fail "Samba4 用户管理工具缺失"
  sec=$(uci -q show samba4 2>/dev/null | sed -n 's/^samba4\.\([^.=]*\)=samba$/\1/p' | head -1)
  [ -n "$sec" ] || sec=$(uci add samba4 samba 2>/dev/null)
  [ -n "$sec" ] || fail "创建 Samba4 全局配置失败"
  uci set "samba4.$sec.interface=lan"
  uci set "samba4.$sec.workgroup=WORKGROUP"
  uci set samba4.athena_share=sambashare
  uci set samba4.athena_share.name=AthenaShare
  uci set "samba4.athena_share.path=$SHARE"
  uci set "samba4.athena_share.users=$NAS_USER"
  uci set samba4.athena_share.read_only=no
  uci set samba4.athena_share.guest_ok=no
  uci set samba4.athena_share.create_mask=0660
  uci set samba4.athena_share.dir_mask=0770
  uci commit samba4 || fail "写入 Samba4 配置失败"
  printf '%s\n%s\n' "$pass" "$pass" | smbpasswd -s -a "$NAS_USER" >/dev/null 2>&1 || fail "创建 Samba4 SMB 账号失败"
}
start_provider() {
  local method="$1" init
  is_usb_mounted || fail "USB 数据分区未真实挂载到 /mnt/usb，NAS 未启动"
  init=$(method_init "$method") || fail "NAS 实现方案无效"
  [ -x "/etc/init.d/$init" ] || fail "NAS 服务初始化脚本不存在"
  "/etc/init.d/$init" restart >/dev/null 2>&1 || fail "NAS 服务启动失败，请检查日志和内核 ABI"
}
stop_provider() {
  local init
  init=$(method_init "$1") || return 0
  [ -x "/etc/init.d/$init" ] && "/etc/init.d/$init" stop >/dev/null 2>&1 || true
}
write_status() {
  local method package installed=false running=false enabled=false unmanaged=false ip address
  method=$(read_method); package=$(owned_pkg)
  if [ -n "$package" ] && pkg_installed "$package"; then installed=true; fi
  if [ -z "$method" ]; then
    if pkg_installed ksmbd-server || pkg_installed samba4-server; then unmanaged=true; fi
    method=none
  fi
  if [ "$method" != none ] && [ "$installed" = true ] && provider_running "$method"; then running=true; fi
  supervisor_enabled && enabled=true
  ip=$(lan_ip); address=''
  [ -n "$ip" ] && address="smb://$ip/AthenaShare"
  printf '{"ok":true,"installed":%s,"running":%s,"enabled":%s,"unmanaged":%s,"method":"%s","username":"%s","share":"%s","address":"%s"}\n' "$installed" "$running" "$enabled" "$unmanaged" "$method" "$NAS_USER" "$SHARE" "$address"
}
install_method() {
  local method="$1" package other pass
  package=$(method_pkg "$method") || fail "NAS 方案仅支持 KSMBD 或 Samba4"
  other=$([ "$method" = ksmbd ] && echo samba4-server || echo ksmbd-server)
  [ -z "$(owned_pkg)" ] || fail "NAS 已由 Athena 管理；请先停止或卸载"
  pkg_installed "$package" && fail "目标 NAS 软件包已由其他方式安装；Athena 不会擅自接管"
  pkg_installed "$other" && fail "检测到另一种 SMB 服务已安装；Athena 不会自动接管"
  is_usb_mounted || fail "请先将真实 USB 分区挂载到 /mnt/usb"
  port_445_busy && fail "TCP 445 端口已被占用，无法安全安装 NAS"
  simulate_add "$package"
  apk add "$package" >/dev/null 2>&1 || fail "NAS 安装失败；请检查软件源签名、内核 ABI 和依赖"
  umask 077
  printf 'method=%s\n' "$method" > "$CONF"
  printf '%s\n' "$package" > "$OWNER"
  chmod 600 "$CONF" "$OWNER"
  create_unix_user
  prepare_share
  pass=$( [ -s "$PASSFILE" ] && cat "$PASSFILE" || generate_password )
  case "$method" in ksmbd) configure_ksmbd "$pass";; samba4) configure_samba4 "$pass";; esac
  umask 077; printf '%s\n' "$pass" > "$PASSFILE"; chmod 600 "$PASSFILE"
  /etc/init.d/athena-nas enable >/dev/null 2>&1 || fail "NAS 已安装，但无法启用开机服务"
  /etc/init.d/athena-nas start >/dev/null 2>&1 || fail "NAS 已安装但启动失败；请检查状态和日志"
  printf '{"ok":true,"msg":"NAS 已安装；共享仅绑定 LAN，文件与磁盘数据不会被删除"}\n'
}
remove_managed() {
  local method package
  method=$(read_method); package=$(owned_pkg)
  [ -n "$method" ] && [ -n "$package" ] && pkg_installed "$package" || fail "没有可确认归 Athena 所有的 NAS 服务包"
  simulate_remove "$package"
  stop_provider "$method"
  /etc/init.d/athena-nas disable >/dev/null 2>&1 || true
  apk del "$package" >/dev/null 2>&1 || fail "卸载 NAS 服务包失败；配置和数据均已保留"
  rm -f "$OWNER"
}
case "${1:-status}" in
  status) write_status ;;
  install) install_method "${2:-}" ;;
  start)
    method=$(read_method); [ -n "$method" ] && [ "$method" != none ] || fail "NAS 尚未安装"
    /etc/init.d/athena-nas enable >/dev/null 2>&1 || fail "启用 NAS 自启动失败"
    /etc/init.d/athena-nas start >/dev/null 2>&1 || fail "NAS 启动失败"
    printf '{"ok":true,"msg":"NAS 已启动"}\n'
    ;;
  stop)
    method=$(read_method); [ -n "$method" ] && stop_provider "$method"
    /etc/init.d/athena-nas disable >/dev/null 2>&1 || true
    printf '{"ok":true,"msg":"NAS 已停止并禁用自启动；软件包、账号、配置和数据保留"}\n'
    ;;
  service-start)
    method=$(read_method); package=$(owned_pkg)
    [ -n "$method" ] && [ -n "$package" ] && pkg_installed "$package" || exit 0
    start_provider "$method"
    ;;
  service-stop)
    method=$(read_method); [ -n "$method" ] && stop_provider "$method"
    ;;
  remove)
    remove_managed
    printf '{"ok":true,"msg":"NAS 软件包已卸载；配置、账号、凭据和共享文件均保留"}\n'
    ;;
  credentials)
    method=$(read_method); package=$(owned_pkg)
    [ -n "$method" ] && [ -n "$package" ] && pkg_installed "$package" || fail "NAS 尚未安装或不由 Athena 管理"
    [ -s "$PASSFILE" ] || fail "NAS 凭据文件不存在"
    ip=$(lan_ip); pass=$(cat "$PASSFILE")
    printf '{"ok":true,"username":"%s","password":"%s","address":"%s"}\n' "$NAS_USER" "$pass" "$([ -n "$ip" ] && printf 'smb://%s/AthenaShare' "$ip" || printf '')"
    ;;
  *) fail "未知命令" ;;
esac
