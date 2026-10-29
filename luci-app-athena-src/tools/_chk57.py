# -*- coding: utf-8 -*-
"""确认新文件真的进了 rootfs（rate.uc 首次安装、status.sh 的 rate 分支、status.uc 的正则修正）。"""
import paramiko

R = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"
UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


print("== rootfs 里的五个文件 ==")
print(run("ls -l %s/usr/libexec/athena-rate.uc %s/usr/libexec/athena-status.sh %s/usr/libexec/athena-status.uc %s/usr/libexec/athena-services.uc %s/www/luci-static/resources/view/athena/index.html" % (R, R, R, R, R)))
print(run("sha256sum %s/usr/libexec/athena-rate.uc %s/usr/libexec/athena-status.sh %s/usr/libexec/athena-status.uc %s/usr/libexec/athena-services.uc %s/www/luci-static/resources/view/athena/index.html" % (R, R, R, R, R)))

print("== status.sh 的 rate 分支 ==")
print(run("grep -n 'rate' %s/usr/libexec/athena-status.sh" % R))

print("== status.uc 正则是否还有字符类 \\s ==")
print(run("grep -n '\\[\\^\\?\\\\s' %s/usr/libexec/athena-status.uc | head -5; grep -c 'rate' %s/usr/libexec/athena-status.uc" % (R, R)))

print("== 用 rootfs 里的 ucode 对三个 .uc 做语法/装载检查 ==")
print(run("%s -e 'import * as fs from \"fs\"; print(fs.stat(\"%s/usr/libexec/athena-rate.uc\").size)' 2>&1" % (UC, R)))
print(run("cd /tmp && cp %s/usr/libexec/athena-rate.uc /tmp/r_chk.uc && %s /tmp/r_chk.uc 2>&1 | head -5" % (R, UC)))
c.close()
