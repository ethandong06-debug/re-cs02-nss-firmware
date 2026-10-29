# -*- coding: utf-8 -*-
"""v1.2.45：全量同步到编译机 -> 编译 -> 校验 staging 落地文件；再验证入口包装的透传与回退。"""
import paramiko, os, io

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
PKG = B + "/package/luci-app-athena"
R = B + "/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"
U = B + "/staging_dir/hostpkg/bin/ucode"

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

def run(cmd, t=1200):
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
out.append(run("cd %s && make package/luci-app-athena/compile V=s -j4 2>&1 | tail -6" % B))
out.append("== apk 产物 ==")
out.append(run("ls -l %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.4*.apk" % B))
out.append("== staging rootfs 落地文件 ==")
out.append(run("ls -l %s/usr/libexec/athena-status* %s/usr/libexec/athena-version" % (R, R)))
out.append(run("echo -n 'athena-version='; cat %s/usr/libexec/athena-version" % R))
out.append("== sha256 ==")
out.append(run("sha256sum %s/usr/libexec/athena-status.sh %s/usr/libexec/athena-status.uc %s/usr/libexec/athena-status-legacy.sh" % (R, R, R)))

# --- 入口包装功能测试：透传 + 回退 ---
out.append("== 入口包装：正常透传 ==")
out.append(run("mkdir -p /tmp/wt && sed 's#/usr/bin/ucode#%s#; s#/usr/libexec/athena-status.uc#/tmp/st_new.uc#; s#/usr/libexec/athena-status-legacy.sh#/tmp/st_old.sh#' /tmp/athena-status.sh > /tmp/wt/wrap.sh && chmod 755 /tmp/wt/wrap.sh && PATH=/tmp/mockbin:/usr/sbin:/usr/bin:/sbin:/bin sh -c 'rm -f /tmp/athena-status.json /tmp/athena-status.stamp; /tmp/wt/wrap.sh | head -c 120; echo; echo exit=$?'" % U))
out.append("== 入口包装：ucode 坏掉 -> 应回退 legacy ==")
out.append(run("printf 'this is broken ucode(\\n' > /tmp/bad.uc; sed 's#/tmp/st_new.uc#/tmp/bad.uc#' /tmp/wt/wrap.sh > /tmp/wt/wrap_bad.sh; chmod 755 /tmp/wt/wrap_bad.sh; PATH=/tmp/mockbin:/usr/sbin:/usr/bin:/sbin:/bin sh -c 'rm -f /tmp/athena-status.json /tmp/athena-status.stamp; /tmp/wt/wrap_bad.sh | head -c 120; echo; echo exit=$?'"))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg45.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
