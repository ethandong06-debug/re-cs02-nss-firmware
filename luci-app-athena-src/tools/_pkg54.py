# -*- coding: utf-8 -*-
"""v1.2.54：全量同步 -> clean+编译 -> 校验 apk 与 staging 的 6 个文件 sha256。"""
import paramiko, os, io, hashlib

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
PKG = B + "/package/luci-app-athena"
R = B + "/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()

def ensure(rd):
    cur = ""
    for p in rd.strip("/").split("/"):
        cur += "/" + p
        try:
            s.stat(cur)
        except IOError:
            s.mkdir(cur)

def run(cmd, t=2400):
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
out.append("== 版本 ==")
out.append(run("grep '^PKG_VERSION' %s/Makefile" % PKG))
out.append("== clean + 编译 ==")
out.append(run("cd %s && make package/luci-app-athena/clean >/dev/null 2>&1; make package/luci-app-athena/compile V=s -j4 2>&1 | tail -6" % B))
out.append("== apk 产物 ==")
out.append(run("ls -l %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.5*.apk" % B))
out.append("== staging 落地 ==")
out.append(run("ls -l %s/usr/libexec/athena-disk.sh %s/usr/libexec/athena-log.sh %s/usr/libexec/athena-resources.uc %s/usr/libexec/athena-services.uc %s/usr/libexec/athena-logcap.sh %s/usr/libexec/athena-apps.sh %s/www/luci-static/resources/view/athena/index.html" % (R, R, R, R, R, R, R)))
out.append("== athena-version ==")
out.append(run("cat %s/usr/libexec/athena-version" % R))
out.append("== sha256 本地 ==")
pairs = [
    ("root/usr/libexec/athena-disk.sh", "athena-disk.sh"),
    ("root/usr/libexec/athena-log.sh", "athena-log.sh"),
    ("root/usr/libexec/athena-resources.uc", "athena-resources.uc"),
    ("root/usr/libexec/athena-services.uc", "athena-services.uc"),
    ("root/usr/libexec/athena-logcap.sh", "athena-logcap.sh"),
    ("root/usr/libexec/athena-apps.sh", "athena-apps.sh"),
]
lh = {}
for rel, name in pairs:
    lp = os.path.join(LOCAL, rel)
    h = hashlib.sha256(io.open(lp, "rb").read()).hexdigest()
    lh[name] = h
    out.append("%s  %d B  %s" % (name, os.path.getsize(lp), h))
pi = os.path.join(LOCAL, r"htdocs/luci-static/resources/view/athena/index.html")
ih = hashlib.sha256(io.open(pi, "rb").read()).hexdigest()
out.append("index.html  %d B  %s" % (os.path.getsize(pi), ih))
out.append("== sha256 staging ==")
cmd = "sha256sum"
for rel, name in pairs:
    cmd += " %s/usr/libexec/%s" % (R, name)
cmd += " %s/www/luci-static/resources/view/athena/index.html" % R
out.append(run(cmd))
out.append("== 逐项比对 ==")
sm = run("for f in athena-disk.sh athena-log.sh athena-resources.uc athena-services.uc athena-logcap.sh athena-apps.sh; do sha256sum %s/usr/libexec/$f; done" % R)
for line in sm.splitlines():
    parts = line.split()
    if len(parts) == 2:
        nm = parts[1].split("/")[-1]
        out.append("%s staging=%s local=%s match=%s" % (nm, parts[0][:16], lh.get(nm, "?")[:16], parts[0] == lh.get(nm)))
isl = run("sha256sum %s/www/luci-static/resources/view/athena/index.html" % R).split()
if isl:
    out.append("index.html staging=%s local=%s match=%s" % (isl[0][:16], ih[:16], isl[0] == ih))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg54.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
