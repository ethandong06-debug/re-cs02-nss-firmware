# -*- coding: utf-8 -*-
"""v1.2.46：全量同步 -> 编译 -> staging 校验 -> 入口包装四态测试（透传/set 转 legacy/坏 ucode 回退/ucode 缺失回退）。"""
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

# 三个文件传到 /tmp/svcw 供包装测试
run("mkdir -p /tmp/svcw && rm -f /tmp/svcw/*")
for name, dst in (("athena-services.sh", "/tmp/svcw/wrap_raw.sh"),
                  ("athena-services-legacy.sh", "/tmp/svcw/legacy_raw.sh"),
                  ("athena-services.uc", "/tmp/svcw/new_raw.uc")):
    s.put(os.path.join(LOCAL, "root/usr/libexec", name), dst)
s.close()

out = ["上传 %d 个文件" % n]
out.append("== 编译 ==")
out.append(run("cd %s && make package/luci-app-athena/compile V=s -j4 2>&1 | tail -8" % B))
out.append("== apk 产物 ==")
out.append(run("ls -l %s/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.4*.apk" % B))
out.append("== staging 落地 ==")
out.append(run("ls -l %s/usr/libexec/athena-services*" % R))
out.append("== sha256（staging vs 本地真值）==")
out.append(run("sha256sum %s/usr/libexec/athena-services.sh %s/usr/libexec/athena-services.uc %s/usr/libexec/athena-services-legacy.sh" % (R, R, R)))

# ---- 包装测试（复用 /tmp/svc mock 环境）----
P = r"C:\Users\Administrator\AppData\Local\Temp\\"
ENVM = "PATH=/tmp/svcmock:/usr/sbin:/usr/bin:/sbin:/bin"

out.append("== 准备测试副本 ==")
out.append(run(
    "mkdir -p /tmp/svcw && chmod -R u+w /tmp/svcw 2>/dev/null; "
    "sed \"s#/usr/libexec/athena-services.uc#/tmp/svcw/new.uc#; s#/usr/libexec/athena-services-legacy.sh#/tmp/svcw/legacy.sh#; s#/usr/bin/ucode#%s#\" /tmp/svcw/wrap_raw.sh > /tmp/svcw/wrap.sh; "
    "sed \"s#/etc/init.d#/tmp/svc/etc/init.d#g; s#'/etc/rc.d'#'/tmp/svc/etc/rc.d'#g; s#/usr/share/luci/menu.d#/tmp/svc/usr/share/luci/menu.d#g\" /tmp/svcw/new_raw.uc > /tmp/svcw/new.uc; "
    "sed 's#/etc/init.d#/tmp/svc/etc/init.d#g; s#/usr/share/luci/menu.d#/tmp/svc/usr/share/luci/menu.d#g' /tmp/svcw/legacy_raw.sh > /tmp/svcw/legacy.sh; "
    "chmod 755 /tmp/svcw/wrap.sh /tmp/svcw/legacy.sh /tmp/svcw/new.uc; "
    "ls -l /tmp/svcw" % U))

def case(name, cmd):
    out.append("== %s ==" % name)
    out.append(run(ENVM + " sh -c " + repr(cmd).replace("'", "'\"'\"'") if False else ENVM + " sh -c '%s'" % cmd))

case("A 正常透传（ucode 版）", "sh /tmp/svcw/wrap.sh > /tmp/svcw/out_a.json; echo bytes=$(wc -c < /tmp/svcw/out_a.json); head -c 100 /tmp/svcw/out_a.json; echo; "
                             "python3 -c \"import json;d=json.load(open('/tmp/svcw/out_a.json'));print('count',len(d['services']),[x['id'] for x in d['services']])\"")
case("B ucode 坏了 -> 应回退 legacy", "printf 'broken(\\n' > /tmp/svcw/bad.uc; sed 's#/tmp/svcw/new.uc#/tmp/svcw/bad.uc#' /tmp/svcw/wrap.sh > /tmp/svcw/wrap_bad.sh; chmod 755 /tmp/svcw/wrap_bad.sh; "
                                    "sh /tmp/svcw/wrap_bad.sh > /tmp/svcw/out_b.json; echo bytes=$(wc -c < /tmp/svcw/out_b.json); "
                                    "python3 -c \"import json;a=json.load(open('/tmp/svcw/out_a.json'));b=json.load(open('/tmp/svcw/out_b.json'));print('equal', a==b)\"")
case("C ucode 文件缺失 -> 应回退 legacy", "sed 's#/tmp/svcw/new.uc#/tmp/svcw/none.uc#' /tmp/svcw/wrap.sh > /tmp/svcw/wrap_miss.sh; chmod 755 /tmp/svcw/wrap_miss.sh; "
                                    "sh /tmp/svcw/wrap_miss.sh > /tmp/svcw/out_c.json; python3 -c \"import json;a=json.load(open('/tmp/svcw/out_a.json'));b=json.load(open('/tmp/svcw/out_c.json'));print('equal', a==b)\"")
case("D set 分支应转 legacy 并真执行", "sh /tmp/svcw/wrap.sh set extraapp 1; echo; sh /tmp/svcw/wrap.sh")

io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkg46.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
