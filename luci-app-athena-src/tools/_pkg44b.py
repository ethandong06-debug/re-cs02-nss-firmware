# -*- coding: utf-8 -*-
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
def run(cmd, t=900):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
out = []
out.append("== package/luci-app-athena 是什么 ==")
out.append(run("ls -ld %s/package/luci-app-athena" % B).strip())
out.append(run("ls -l %s/package/luci-app-athena/root/usr/libexec/athena-resources.sh 2>/dev/null" % B).strip())

pkgdir = B + "/package/luci-app-athena"
s = c.open_sftp()
for local_rel, remote_rel in FILES:
    s.put(os.path.join(LOCAL, local_rel), pkgdir + "/" + remote_rel)
s.close()
out.append("== 已上传到 package/luci-app-athena ==")

r = run("cd %s && make package/luci-app-athena/compile V=s -j4 2>&1 | tail -20" % B, t=900)
out.append(r.strip())

r2 = run("ls -t %s/bin/packages/*/base/luci-app-athena_*.ipk 2>/dev/null | head -3" % B)
out.append("ipk 候选:\n" + r2.strip())
if r2.strip():
    ipk = r2.strip().split("\n")[0]
    out.append("== %s 内容 ==" % ipk)
    out.append(run("rm -rf /tmp/ipkx && mkdir -p /tmp/ipkx && cd /tmp/ipkx && tar xzf %s && tar xzf data.tar.gz && ls -l usr/libexec/ | grep athena-resources; echo '--- version ---'; cat usr/libexec/athena-version" % ipk).strip())
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg44b.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
