# -*- coding: utf-8 -*-
"""v1.2.48：全量同步 -> 编译 -> 校验 staging 三个 packages 文件 sha256。"""
import paramiko, os, io, hashlib

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
PKG = B + "/package/luci-app-athena"
R = B + "/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax/usr/libexec"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()

def ensure(rd):
    cur = ""
    for p in rd.strip("/").split("/"):
        cur += "/" + p
        try: s.stat(cur)
        except IOError: s.mkdir(cur)

def run(cmd, t=1500):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

n = 0
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d != "_backup"]
    rel = os.path.relpath(root, LOCAL).replace("\\", "/")
    rdir = PKG if rel == "." else PKG + "/" + rel
    ensure(rdir)
    for f in files:
        s.put(os.path.join(root, f), rdir + "/" + f)
        n += 1
s.close()

out = ["上传 %d 个文件" % n]
out.append("== 编译 ==")
out.append(run("cd %s && make package/luci-app-athena/compile V=s -j4 2>&1 | tail -5" % B))
out.append(run("ls -l %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.4*.apk" % B))
out.append("== staging 落地 ==")
out.append(run("ls -l %s/athena-packages*" % R))
out.append("== sha256 本地 vs staging ==")
for f in ("athena-packages.sh", "athena-packages.uc", "athena-packages-legacy.sh"):
    lp = os.path.join(LOCAL, "root/usr/libexec", f)
    h = hashlib.sha256(io.open(lp, "rb").read()).hexdigest()
    out.append("%s  本地 %d B  %s" % (f, os.path.getsize(lp), h))
out.append(run("sha256sum %s/athena-packages.sh %s/athena-packages.uc %s/athena-packages-legacy.sh" % (R, R, R)))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg52c.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
