#!/bin/sh
# ============================================================
#  AthenaWrt 定制固件 — 首次启动配置脚本 (uci-defaults, 仅执行一次)
#  京东云雅典娜 AX6600 (JDCloud RE-CS-02 / IPQ6010)
# ============================================================

. /lib/functions.sh

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

# ---------- 3. 设置 root 默认密码 (password, 首次登录后请务必修改) ----------
( echo "password"; echo "password" ) | passwd root 2>/dev/null

# ---------- 4. 启用 SSH (dropbear) ----------
if uci -q get dropbear.@dropbear[0] >/dev/null 2>&1; then
  uci set dropbear.@dropbear[0].RootPasswordAuth='on'
  uci set dropbear.@dropbear[0].PasswordAuth='on'
  uci set dropbear.@dropbear[0].Port='22'
fi

# ---------- 5. 无线网络：品牌 SSID 由 99-zz-athena-wifi.sh 统一设置 ----------
# 注：本脚本按字母序先于 99-jdc-wifi 执行，会被其覆盖；
#     因此 SSID/密码/国家码的最终覆盖统一放到 99-zz-athena-wifi.sh（排序在 jdc 之后）。

# ---------- 6. 提交并清理 ----------
uci commit system
uci commit dropbear 2>/dev/null

exit 0
