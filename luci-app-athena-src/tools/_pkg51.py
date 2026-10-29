# -*- coding: utf-8 -*-
"""v1.2.51：available 读缓存 + 后台预热，验证"请求永不阻塞"。"""
import paramiko, os, io, time

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
TMP = os.environ.get("TEMP", ".")

APK_MOCK = """#!/bin/sh
case "$1" in
list)
	if [ "$2" = "-I" ]; then
		printf 'libc-1.2.5-r4\\nbusybox-1.38.0-r1\\n'
	else
		sleep 2
		printf 'libc-1.2.5-r4\\nfoo-1.0-r1\\nbar-2.1-r3\\n'
	fi
	;;
*) exit 1 ;;
esac
"""

DB = "\n".join([
    "C:Q1", "P:busybox", "V:1.38.0-r1", "A:all", "S:1", "",
    "C:Q2", "P:libc", "V:1.2.5-r4", "A:all", "S:1", "",
    "C:Q3", "P:libusb-1.0-0", "V:1.0.29-r2", "A:all", "S:1", "",
    "C:Q4", "P:kmod-nls-iso8859-1", "V:6.18.55-r1", "A:all", "S:1", "",
    "",
])

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


run("rm -rf /tmp/pkw51 /tmp/pk; mkdir -p /tmp/pkw51/bin /tmp/pkw51/run /tmp/pk/db")
s = c.open_sftp()
p = os.path.join(TMP, "apk51")
io.open(p, "w", encoding="utf-8", newline="\n").write(APK_MOCK)
s.put(p, "/tmp/pkw51/bin/apk")
p = os.path.join(TMP, "db51")
io.open(p, "w", encoding="utf-8", newline="\n").write(DB)
s.put(p, "/tmp/pk/db/installed")
s.put(os.path.join(LOCAL, "athena-packages.uc"), "/tmp/pkw51/uc_raw.uc")
s.put(os.path.join(LOCAL, "athena-packages.sh"), "/tmp/pkw51/wrap_raw.sh")
s.put(os.path.join(LOCAL, "athena-packages-legacy.sh"), "/tmp/pkw51/leg_raw.sh")
s.close()

run("chmod 755 /tmp/pkw51/bin/apk")
# 替换路径：数据库、缓存/锁、ucode 绝对路径
run("sed 's#/lib/apk/db/installed#/tmp/pk/db/installed#' /tmp/pkw51/uc_raw.uc > /tmp/pkw51/uc.uc")
run("sed 's#^AV_CACHE=.*#AV_CACHE=\"/tmp/pkw51/av.tmp\"#; s#^AV_STAMP=.*#AV_STAMP=\"/tmp/pkw51/av.stamp\"#; s#^AV_LOCK=.*#AV_LOCK=\"/tmp/pkw51/run/av.lock\"#' /tmp/pkw51/leg_raw.sh > /tmp/pkw51/leg.sh")
run("sed \"s#/usr/libexec/athena-packages.uc#/tmp/pkw51/uc.uc#; s#/usr/libexec/athena-packages-legacy.sh#/tmp/pkw51/leg.sh#; s#/usr/bin/ucode#%s#\" /tmp/pkw51/wrap_raw.sh > /tmp/pkw51/wrap.sh" % U)
run("chmod 755 /tmp/pkw51/wrap.sh /tmp/pkw51/leg.sh")
run("grep -n 'AV_CACHE=\\|AV_STAMP=\\|AV_LOCK=\\|AV_KEEP=\\|AV_STALE=' /tmp/pkw51/leg.sh")

ENV = "export PATH=/tmp/pkw51/bin:$PATH; "
out = []
out.append("== 场景1 installed（ucode 路径）==")
out.append(run(ENV + "sh /tmp/pkw51/wrap.sh list installed"))

out.append("== 场景2 available 首次（无缓存，应立即返回）==")
out.append(run(ENV + "cd /tmp/pkw51; S=$(date +%s%N); sh wrap.sh list available; E=$(date +%s%N); echo \"耗时=$(( (E-S)/1000000 ))ms\""))

out.append("== 等后台完成（mock apk sleep 2）==")
run("sleep 4")
out.append("== 场景3 available 二次（应命中缓存，含 foo/bar）==")
out.append(run(ENV + "cd /tmp/pkw51; S=$(date +%s%N); sh wrap.sh list available; E=$(date +%s%N); echo \"耗时=$(( (E-S)/1000000 ))ms\"; ls -l /tmp/pkw51/av.tmp /tmp/pkw51/run/av.lock 2>&1"))

out.append("== 场景4 缓存过期（把 stamp 改成很久以前）==")
out.append(run(ENV + "printf '1' > /tmp/pkw51/av.stamp; cd /tmp/pkw51; S=$(date +%s%N); sh wrap.sh list available | head -c 100; E=$(date +%s%N); echo; echo \"耗时=$(( (E-S)/1000000 ))ms（应仍为旧数据、且立即返回）\"; ls -ld /tmp/pkw51/run/av.lock 2>&1"))
run("sleep 4")
out.append(run(ENV + "ls -l /tmp/pkw51/av.stamp /tmp/pkw51/run/av.lock 2>&1; cat /tmp/pkw51/av.stamp"))

out.append("== 场景5 死锁自愈（造一个 pid 不存在的锁）==")
out.append(run(ENV + "mkdir -p /tmp/pkw51/run/av.lock; echo 999999 > /tmp/pkw51/run/av.lock/pid; printf '5' > /tmp/pkw51/run/av.lock/since; cd /tmp/pkw51; sh wrap.sh list available | head -c 60; echo; sleep 1; ls -ld /tmp/pkw51/run/av.lock 2>&1"))

out.append("== 场景6 带关键字（走真查）==")
out.append(run(ENV + "cd /tmp/pkw51; sh wrap.sh list available foo"))

io.open(os.path.join(TMP, "pkg51.txt"), "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
