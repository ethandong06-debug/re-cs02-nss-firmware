# -*- coding: utf-8 -*-
"""v1.2.45 mock 验证（无 sudo 版）：两个脚本的锁目录/hostapd 目录改到 /tmp 后，逐字段对比 + 计时 + execve。"""
import paramiko, io

LOCAL_UC = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-status.uc"
LOCAL_SH = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-status.sh"

UCI = r'''#!/bin/sh
if [ "$1" = "-q" ]; then shift; fi
case "$1" in
show)
	case "$2" in
	athena)
		cat <<'X'
athena.system=system
athena.system.mode='single'
athena.single=single
athena.single.wan_proto='pppoe'
athena.single.wan_vlan='2044'
athena.single.inner_vlan='1'
athena.single.iptv_port='lan4'
X
		;;
	athena_led)
		cat <<'X'
athena_led.general=general
athena_led.general.enabled='1'
athena_led.general.light_level='4'
athena_led.general.night_light_enable='1'
athena_led.general.profile_mode='single'
athena_led.general.night_start='23:00'
athena_led.general.night_end='06:30'
athena_led.general.night_light_level='2'
athena_led.general.disable_led_clock='1'
athena_led.general.disable_led_medal='0'
athena_led.general.disable_led_up='1'
athena_led.general.disable_led_down='0'
X
		;;
	network)
		cat <<'X'
network.wan=interface
network.wan.proto='pppoe'
network.wan.device='wan.2044'
network.wan.username='clan2210158893'
network.wan.password='abc"def'
network.wan.ipaddr='192.168.1.2'
network.wan.netmask='255.255.255.0'
network.wan.gateway='192.168.1.1'
network.wan.dns='223.5.5.5 119.29.29.29'
network.@device[0]=device
network.@device[0].ports='lan4' 'wan.3066'
X
		;;
	esac
	;;
get)
	key="$2"
	pkg=${key%%.*}
	rest=${key#*.}
	line=$(uci -q show "$pkg" | grep "^$pkg\.$rest=" | head -1)
	[ -z "$line" ] && exit 1
	v=${line#*=}
	case "$v" in
	\'*\') v=${v#\'}; v=${v%\'} ;;
	esac
	printf '%s\n' "$v"
	;;
esac
'''

IWINFO = r'''#!/bin/sh
case "$2" in
info)
	case "$1" in
	*phy0*) echo "phy0     ESSID: \"Athena\""; echo "          Channel: 6 (2.4 GHz)" ;;
	*phy1*) echo "phy1     ESSID: \"Athena-5G\""; echo "          Channel: 149 (5 GHz)" ;;
	*) echo "" ;;
	esac
	;;
esac
'''

UBUS = r'''#!/bin/sh
cat <<'X'
{"radio0":{"up":true,"pending":false,"autostart":true,"disabled":false,"config":{"path":"platform\/soc\/18000000.wifi","channel":"6","band":"2g","htmode":"HE40"},"interfaces":[{"section":"default_radio0","ifname":"phy0-ap0","config":{"mode":"ap","ssid":"Athena","encryption":"sae-mixed","key":"12345678"},"stations":[{"mac":"3c:22:fb:aa:bb:cc","rx":{"bytes":123456},"tx":{"bytes":234567},"inactive":120}]}]},"radio1":{"up":true,"pending":false,"autostart":true,"disabled":false,"config":{"path":"platform\/soc\/18000000.wifi+1","channel":"149","band":"5g","htmode":"HE80"},"interfaces":[{"section":"default_radio1","ifname":"phy1-ap0","config":{"mode":"ap","ssid":"Athena-5G","encryption":"sae-mixed","key":"12345678"},"stations":[]}]}}
X
'''

IP = r'''#!/bin/sh
echo "5: wan.2044: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1492 qdisc fq_codel state UNKNOWN group default qlen 3"
echo "    link/ppp"
echo "    inet 100.64.12.34/32 scope global wan.2044"
echo "       valid_lft forever preferred_lft forever"
'''

LEASES = """1761234567 3c:22:fb:aa:bb:cc 192.168.10.100 iPhone *
1761234567 68:3e:34:11:22:33 192.168.10.101 PC-Huawei 01:68:3e:34:11:22:33
1761234567 70:b3:d5:44:55:66 192.168.10.102 Camera 01:70:b3:d5:44:55:66
1761234567 aa:bb:cc:dd:ee:01 192.168.10.7 off-dev *
"""

HOSTAPD0 = """3c:22:fb:aa:bb:cc
70:b3:d5:44:55:66
"""

CMP = r'''
import json

def walk(a, b, path, out):
    if type(a) != type(b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a != b: out.append("%s  value: old=%r new=%r" % (path, a, b))
            return
        out.append("%s  TYPE: old=%s(%r) new=%s(%r)" % (path, type(a).__name__, a, type(b).__name__, b))
        return
    if isinstance(a, dict):
        ka, kb = set(a.keys()), set(b.keys())
        for k in sorted(ka - kb): out.append("%s.%s  MISSING in new" % (path, k))
        for k in sorted(kb - ka): out.append("%s.%s  EXTRA in new" % (path, k))
        for k in sorted(ka & kb): walk(a[k], b[k], path + "." + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append("%s  LEN: old=%d new=%d" % (path, len(a), len(b)))
            return
        for i in range(len(a)): walk(a[i], b[i], "%s[%d]" % (path, i), out)
    else:
        if a != b: out.append("%s  value: old=%r new=%r" % (path, a, b))

old = json.load(open('/tmp/old.json'))
new = json.load(open('/tmp/new.json'))
out = []
walk(old, new, '', out)
print("diff count:", len(out))
for line in out[:100]: print("  ", line)
print("---- OLD clients/storage ----")
print(" old clients:", json.dumps(old.get("clients"), ensure_ascii=False))
print(" old storage:", json.dumps(old.get("storage"), ensure_ascii=False))
print("---- NEW FULL ----")
print(json.dumps(new, ensure_ascii=False, indent=1))
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=240):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))

run("mkdir -p /tmp/mockbin /tmp/hostapd")
s = c.open_sftp()
TMP = r"C:\Users\Administrator\AppData\Local\Temp\\"
for name, body in (("uci", UCI), ("iwinfo", IWINFO), ("ubus", UBUS), ("ip", IP), ("leases", LEASES), ("hostapd0", HOSTAPD0), ("cmp", CMP)):
    p = TMP + "m_" + name
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    s.put(p, "/tmp/mockbin/_" + name if name in ("uci", "iwinfo", "ubus", "ip") else "/tmp/m_" + name)
s.put(LOCAL_UC, "/tmp/athena-status.uc")
s.put(LOCAL_SH, "/tmp/athena-status-legacy.sh")
s.close()

out = []
# 把 mock 装到 mockbin（可执行），并把两个脚本的 /var/run 路径改到 /tmp
out.append(run("cd /tmp/mockbin && for n in uci iwinfo ubus ip; do mv _\"$n\" \"$n\"; chmod 755 \"$n\"; done; ls -l /tmp/mockbin").strip())
out.append(run("cp /tmp/athena-status-legacy.sh /tmp/st_old.sh; cp /tmp/athena-status.uc /tmp/st_new.uc; "
               "sed -i 's#/var/run/athena-status.lock#/tmp/athena-status.lock#; s#/var/run/hostapd#/tmp/hostapd#' /tmp/st_old.sh /tmp/st_new.uc; "
               "grep -n 'athena-status.lock\\|hostapd' /tmp/st_old.sh /tmp/st_new.uc | head -8").strip())
out.append(run("cp /tmp/m_leases /tmp/dhcp.leases; cp /tmp/m_hostapd0 /tmp/hostapd/phy0-ap0; cp /tmp/m_hostapd0 /tmp/hostapd/phy1-ap0; ls -l /tmp/hostapd").strip())

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
ENV = "PATH=/tmp/mockbin:/usr/sbin:/usr/bin:/sbin:/bin"
CLEAN = "rm -rf /tmp/athena-status.json /tmp/athena-status.stamp /tmp/athena-cpu-cache /tmp/athena-net-cache /tmp/athena-devs /tmp/athena-status.lock.lock; rm -rf /tmp/athena-status.lock"

out.append("== 旧版（跑两次，第二次为基准）==")
out.append(run(ENV + " sh -c '" + CLEAN + "; sh /tmp/st_old.sh > /tmp/old1.json 2>/tmp/old1.err; sh /tmp/st_old.sh > /tmp/old.json 2>/tmp/old2.err; echo bytes=$(wc -c < /tmp/old.json)'").strip())
out.append("[old stderr] " + run("head -c 400 /tmp/old1.err").strip())
out.append("== 新版 ==")
out.append(run(ENV + " sh -c '" + CLEAN + "; " + U + " /tmp/st_new.uc > /tmp/new.json 2>/tmp/new.err; echo bytes=$(wc -c < /tmp/new.json)'").strip())
out.append("[new stderr]\n" + run("head -20 /tmp/new.err").strip())
out.append("== 逐字段对比 ==")
out.append(run("python3 /tmp/m_cmp").strip())
out.append("== 耗时（各 3 次，锁目录可写，不再 sleep）==")
out.append(run(ENV + " sh -c 'for i in 1 2 3; do " + CLEAN + "; /usr/bin/time -f \"OLD %e real %U user %S sys\" sh /tmp/st_old.sh >/dev/null; done' 2>&1").strip())
out.append(run(ENV + " sh -c 'for i in 1 2 3; do " + CLEAN + "; /usr/bin/time -f \"NEW %e real %U user %S sys\" " + U + " /tmp/st_new.uc >/dev/null; done' 2>&1").strip())
out.append("== execve 计数 ==")
out.append(run(ENV + " sh -c 'cd /tmp; " + CLEAN + "; strace -f -c -e trace=execve sh /tmp/st_old.sh >/dev/null 2>/tmp/tr_old.txt; grep -E \"execve|total\" /tmp/tr_old.txt | head -3'").strip())
out.append(run(ENV + " sh -c 'cd /tmp; " + CLEAN + "; strace -f -c -e trace=execve " + U + " /tmp/st_new.uc >/dev/null 2>/tmp/tr_new.txt; grep -E \"execve|total\" /tmp/tr_new.txt | head -3'").strip())

io.open(r"C:\Users\Administrator\AppData\Local\Temp\st45mock.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
