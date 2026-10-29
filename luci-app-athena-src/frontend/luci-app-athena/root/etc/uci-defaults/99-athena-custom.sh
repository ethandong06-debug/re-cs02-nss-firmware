#!/bin/sh
# ============================================================
#  AthenaWrt 定制 — 首启配置 (uci-defaults，仅执行一次)
#  主机名 / 时区 / NTP / root 密码 / SSH
#  无线品牌 SSID 见 99-zz-athena-wifi.sh（排序在 99-jdc-wifi 之后覆盖）
# ============================================================

# ---------- 1. 主机名 & 时区 (中国标准时间) ----------
uci set system.@system[0].hostname='Athena'
uci set system.@system[0].timezone='CST-8'
uci set system.@system[0].zonename='Asia/Shanghai'
uci set system.@system[0].log_size='128'
uci set system.@system[0].log_type='file'
uci set system.@system[0].conloglevel='8'

# ---------- 2. NTP 时间同步 (国内源) ----------
uci -q delete system.ntp
uci set system.ntp=timeserver
uci add_list system.ntp.server='ntp.aliyun.com'
uci add_list system.ntp.server='ntp.tencent.com'
uci add_list system.ntp.server='cn.pool.ntp.org'
uci set system.ntp.enabled='1'
uci set system.ntp.enable_server='0'

# ---------- 3. root 默认密码 = password (首次登录后请务必修改) ----------
( echo "password"; echo "password" ) | passwd root 2>/dev/null

# ---------- 4. 启用 SSH (dropbear) ----------
if uci -q get dropbear.@dropbear[0] >/dev/null 2>&1; then
  uci set dropbear.@dropbear[0].RootPasswordAuth='on'
  uci set dropbear.@dropbear[0].PasswordAuth='on'
  uci set dropbear.@dropbear[0].Port='22'
fi

uci commit system
uci commit dropbear 2>/dev/null

exit 0
