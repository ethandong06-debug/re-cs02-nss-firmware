# -*- coding: utf-8 -*-
"""把本地 luci-app-athena 全量同步到编译机 package/luci-app-athena（跳过 _backup），再编译。"""
import paramiko, os, io

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
PKG = B + "/package/luci-app-athena"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()

def ensure(remote_dir):
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            s.stat(cur)
        except IOError:
            s.mkdir(cur)

def run(cmd, t=900):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))

n = 0
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d != "_backup"]
    rel = os.path.relpath(root, LOCAL).replace("\\", "/")
    rdir = PKG if rel == "." else PKG + "/" + rel
    ensure(rdir)
    for f in files:
        lp = os.path.join(root, f)
        s.put(lp, rdir + "/" + f)
        n += 1
s.close()
out = ["上传 %d 个文件到 %s" % (n, PKG)]

r = run("cd %s && make package/luci-app-athena/compile V=s -j4 2>&1 | tail -12" % B)
out.append(r.strip())

r2 = run("ls -t %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-*.apk %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-*.ipk 2>/dev/null | head -3" % (B, B))
out.append("产物:\n" + r2.strip())
if r2.strip():
    p = r2.strip().split("\n")[0]
    out.append("== 包内 athena-resources* ==")
    if p.endswith(".apk"):
        out.append(run("cd /tmp && rm -rf apkx && mkdir apkx && cd apkx && tar xzf %s 2>/dev/null; find . -name 'athena-resources*' -o -name 'athena-version' | head" % p).strip())
    else:
        out.append(run("cd /tmp && rm -rf ipkx && mkdir ipkx && cd ipkx && tar xzf %s && tar xzf data.tar.gz && ls -l usr/libexec/ | grep -E 'athena-resources|athena-version'" % p).strip())
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg44c.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
