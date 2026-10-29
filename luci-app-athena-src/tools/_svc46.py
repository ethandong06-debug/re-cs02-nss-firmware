# -*- coding: utf-8 -*-
"""v1.2.46 等价性验证：athena-services.uc vs athena-services-legacy.sh（mock init.d / rc.d / menu.d）。"""
import paramiko, io

UC = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services.uc"
LEG = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services-legacy.sh"

UCI = r'''#!/bin/sh
if [ "$1" = "-q" ]; then shift; fi
case "$1" in
show)
	case "$2" in
	ddns) printf "ddns.@service[0]=service\nddns.@service[0].enabled='1'\n" ;;
	ttyd) printf "ttyd.@ttyd[0]=ttyd\nttyd.@ttyd[0].enabled='0'\n" ;;
	athena_led) printf "athena_led.general=general\nathena_led.general.enabled='1'\n" ;;
	esac
	;;
get)
	key="$2"; pkg=${key%%.*}; rest=${key#*.}
	line=$(uci -q show "$pkg" | grep -F "$pkg.$rest=" | head -1)
	[ -z "$line" ] && exit 1
	v=${line#*=}
	case "$v" in \'*\') v=${v#\'}; v=${v%\'} ;; esac
	printf '%s\n' "$v"
	;;
esac
'''

INIT = r'''#!/bin/sh
b=$(basename "$0")
case "$1" in
enabled)
	if ls /tmp/svc/etc/rc.d/ 2>/dev/null | grep -q "^S[0-9]*${b}$"; then exit 0; else exit 1; fi
	;;
esac
exit 0
'''

OVR = r'''#!/bin/sh
enabled() { return 0; }
if [ "$1" = "enabled" ]; then enabled; exit $?; fi
exit 0
'''

MENU = {
    "luci-app-openclash.json": '{\n\t"admin/services/openclash": {\n\t\t"title": "OpenClash",\n\t\t"order": 60\n\t}\n}\n',
    "luci-app-passwall.json": '{\n\t"admin/services/passwall": {\n\t\t"title": "PassWall"\n\t},\n\t"admin/services/passwall/app": {\n\t\t"title": "App"\n\t}\n}\n',
    "luci-app-mosdns.json": '{\n\t"admin/services/mosdns": {\n\t\t"title": "MosDNS"\n\t}\n}\n',
    "luci-app-other.json": '{\n\t"admin/services/ddnsto": {\n\t\t"title": "DDNSTO"\n\t}\n}\n',
    "luci-app-nomenu.json": '{\n\t"admin/status/overview": {\n\t\t"title": "Overview"\n\t}\n}\n',
}

CMP = r'''
import json
a = json.load(open('/tmp/svc_old.json'))
b = json.load(open('/tmp/svc_new.json'))
sa = a['services']; sb = b['services']
print("old count:", len(sa), " new count:", len(sb))
ida = [x['id'] for x in sa]; idb = [x['id'] for x in sb]
print("old ids:", ida)
print("new ids:", idb)
diff = 0
if ida != idb:
    print("!! id 顺序/集合不同"); diff += 1
for x, y in zip(sa, sb):
    for k in sorted(set(x) | set(y)):
        if x.get(k) != y.get(k):
            print("!! diff", x.get('id'), k, repr(x.get(k)), "->", repr(y.get(k))); diff += 1
print("total diff:", diff)
print("---- new ----")
print(json.dumps(b, ensure_ascii=False, indent=1))
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

def run(cmd, t=240):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))

run("rm -rf /tmp/svc /tmp/svcmock && mkdir -p /tmp/svc/etc/init.d /tmp/svc/etc/rc.d /tmp/svc/usr/share/luci/menu.d /tmp/svcmock")

s = c.open_sftp()
P = r"C:\Users\Administrator\AppData\Local\Temp\\"
def put(path, body):
    p = P + "svc_" + path.replace("/", "_")
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    s.put(p, path)

put("/tmp/svcmock/uci", UCI)

for name in ("ddns", "ttyd", "athena_led", "openclash", "passwall", "mosdns", "ddnsto", "extraapp", "ovr", "rcS"):
    put("/tmp/svc/etc/init.d/" + name, OVR if name == "ovr" else INIT)
for menu, body in MENU.items():
    put("/tmp/svc/usr/share/luci/menu.d/" + menu, body)
put("/tmp/svc_old.sh", "")  # 占位，稍后 sed
put("/tmp/svc_new.uc", "")
s.put(UC, "/tmp/svc_new_raw.uc")
s.put(LEG, "/tmp/svc_old_raw.sh")
put("/tmp/svc_cmp.py", CMP)
s.close()

out = []
out.append(run("chmod 755 /tmp/svcmock/uci /tmp/svc/etc/init.d/*; "
               "cd /tmp/svc/etc/rc.d && ln -sf ../init.d/ddns S95ddns && ln -sf ../init.d/ttyd S96ttyd && "
               "ln -sf ../init.d/openclash S99openclash && ln -sf ../init.d/mosdns K10mosdns; ls -l /tmp/svc/etc/rc.d").strip())

# 把两个实现的路径指到 mock
out.append(run("sed 's#/etc/init.d#/tmp/svc/etc/init.d#g; s#/usr/share/luci/menu.d#/tmp/svc/usr/share/luci/menu.d#g' /tmp/svc_old_raw.sh > /tmp/svc_old.sh; "
               "sed \"s#/etc/init.d#/tmp/svc/etc/init.d#g; s#'/etc/rc.d'#'/tmp/svc/etc/rc.d'#g; s#/usr/share/luci/menu.d#/tmp/svc/usr/share/luci/menu.d#g\" /tmp/svc_new_raw.uc > /tmp/svc_new.uc; "
               "grep -n \"INITD\\|RCD\\|MENUD\" /tmp/svc_new.uc | head -4; chmod 755 /tmp/svc_old.sh").strip())

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
ENV = "PATH=/tmp/svcmock:/usr/sbin:/usr/bin:/sbin:/bin"

out.append("== 旧版输出 ==")
out.append(run(ENV + " sh /tmp/svc_old.sh > /tmp/svc_old.json 2>/tmp/svc_old.err; echo bytes=$(wc -c < /tmp/svc_old.json); head -c 400 /tmp/svc_old.err").strip())
out.append("== 新版输出 ==")
out.append(run(ENV + " " + U + " /tmp/svc_new.uc > /tmp/svc_new.json 2>/tmp/svc_new.err; echo bytes=$(wc -c < /tmp/svc_new.json); head -c 400 /tmp/svc_new.err").strip())
out.append("== 逐字段对比 ==")
out.append(run("python3 /tmp/svc_cmp.py 2>&1").strip())
out.append("== 耗时（各 3 次）==")
out.append(run(ENV + " sh -c 'for i in 1 2 3; do /usr/bin/time -f \"OLD %e %U %S\" sh /tmp/svc_old.sh >/dev/null; done' 2>&1").strip())
out.append(run(ENV + " sh -c 'for i in 1 2 3; do /usr/bin/time -f \"NEW %e %U %S\" " + U + " /tmp/svc_new.uc >/dev/null; done' 2>&1").strip())
out.append("== execve ==")
out.append(run(ENV + " sh -c 'strace -f -c -e trace=execve sh /tmp/svc_old.sh >/dev/null 2>/tmp/tro.txt; grep -E \"execve|total\" /tmp/tro.txt|head -2; strace -f -c -e trace=execve " + U + " /tmp/svc_new.uc >/dev/null 2>/tmp/trn.txt; grep -E \"execve|total\" /tmp/trn.txt|head -2'").strip())

io.open(r"C:\Users\Administrator\AppData\Local\Temp\svc46.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
