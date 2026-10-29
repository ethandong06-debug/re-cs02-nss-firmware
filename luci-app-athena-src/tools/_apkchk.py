# -*- coding: utf-8 -*-
import paramiko, io
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
apk = B + "/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.44-r1.apk"
out = []
out.append("== apk 是否含 ucode 采集器（按文件名搜 tar 列表）==")
out.append(run("cd /tmp && rm -rf apkz && mkdir apkz && cd apkz && tar xzf %s 2>/dev/null; find . | grep -E 'athena-resources|athena-version' | head -10" % apk))
out.append("== 直接看 apk 原始列表 ==")
out.append(run("tar tzf %s 2>/dev/null | head -20" % apk))
out.append("== staging rootfs 里落地的三个文件 ==")
out.append(run("ls -l %s/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax/usr/libexec/ | grep -E 'athena-resources|athena-version'" % B))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\apkchk.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
