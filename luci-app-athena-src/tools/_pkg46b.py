# -*- coding: utf-8 -*-
"""v1.2.46 包装 B/C 两态复测 + 本地/远端 sha256 对照。"""
import paramiko, io, hashlib, os

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
R = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax/usr/libexec"

BC = r'''#!/bin/sh
cd /tmp/svcw || exit 1
printf 'broken(\n' > bad.uc
sed 's#/tmp/svcw/new.uc#/tmp/svcw/bad.uc#' wrap.sh > wrap_bad.sh
chmod 755 wrap_bad.sh
sh wrap_bad.sh > out_b.json 2>err_b.txt
echo "B exit=$? bytes=$(wc -c < out_b.json) err=$(head -c 120 err_b.txt)"

sed 's#/tmp/svcw/new.uc#/tmp/svcw/none.uc#' wrap.sh > wrap_miss.sh
chmod 755 wrap_miss.sh
sh wrap_miss.sh > out_c.json 2>err_c.txt
echo "C exit=$? bytes=$(wc -c < out_c.json) err=$(head -c 120 err_c.txt)"

python3 - <<'PY'
import json
a=json.load(open('/tmp/svcw/out_a.json'))
b=json.load(open('/tmp/svcw/out_b.json'))
c=json.load(open('/tmp/svcw/out_c.json'))
print("A/B equal:", a==b, " A/C equal:", a==c)
print("counts:", len(a['services']), len(b['services']), len(c['services']))
PY
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
p = r"C:\Users\Administrator\AppData\Local\Temp\t_bc.sh"
io.open(p, "w", encoding="utf-8", newline="\n").write(BC)
s = c.open_sftp(); s.put(p, "/tmp/svcw/t_bc.sh"); s.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

out = []
out.append("== B/C 复测 ==")
out.append(run("PATH=/tmp/svcmock:/usr/sbin:/usr/bin:/sbin:/bin sh /tmp/svcw/t_bc.sh"))
out.append("== sha256 对照（本地 vs staging）==")
for f in ("athena-services.sh", "athena-services.uc", "athena-services-legacy.sh"):
    h = hashlib.sha256(io.open(os.path.join(LOCAL, f), "rb").read()).hexdigest()
    out.append("%s  本地 %d B  %s" % (f, os.path.getsize(os.path.join(LOCAL, f)), h))
out.append(run("sha256sum %s/athena-services.sh %s/athena-services.uc %s/athena-services-legacy.sh" % (R, R, R)))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg46b.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
