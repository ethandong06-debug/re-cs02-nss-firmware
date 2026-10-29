# -*- coding: utf-8 -*-
"""同步 luci-app-athena 到编译机并只编译这个包，确认 .uc 进了 ipk。"""
import paramiko, io, os

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
FILES = [
    ("Makefile", "Makefile"),
    (r"root\usr\libexec\athena-resources.sh", "root/usr/libexec/athena-resources.sh"),
    (r"root\usr\libexec\athena-resources-legacy.sh", "root/usr/libexec/athena-resources-legacy.sh"),
    (r"root\usr\libexec\athena-resources.uc", "root/usr/libexec/athena-resources.uc"),
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

def run(cmd, t=600):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
out = []
where = run("ls -d %s/feeds/base/luci-app-athena %s/package/feeds/base/luci-app-athena 2>/dev/null" % (B, B)).strip()
out.append("包目录: " + where)
pkgdir = (where.split("\n")[0] if where else B + "/feeds/base/luci-app-athena").strip()

s = c.open_sftp()
for local_rel, remote_rel in FILES:
    lp = os.path.join(LOCAL, local_rel)
    rp = pkgdir + "/" + remote_rel
    s.put(lp, rp)
    out.append("上传 %s -> %s (%d B)" % (local_rel, rp, os.path.getsize(lp)))
s.close()

out.append("== 编译 ==")
r = run("cd %s && make package/feeds/base/luci-app-athena/compile V=s -j4 2>&1 | tail -25" % B, t=900)
out.append(r)

out.append("== ipk 内容检查 ==")
r2 = run("ls -t %s/bin/packages/*/base/luci-app-athena_1.2.44*.ipk 2>/dev/null | head -2" % B)
out.append("ipk: " + r2.strip())
if r2.strip():
    ipk = r2.strip().split("\n")[0]
    out.append(run("cd /tmp && rm -rf ipkx && mkdir ipkx && cd ipkx && tar xzf %s 2>/dev/null; ls; tar xzf data.tar.gz 2>/dev/null; ls -l usr/libexec/ 2>/dev/null | head -30; echo '--- version file ---'; cat usr/libexec/athena-version 2>/dev/null" % ipk))

io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg44.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
