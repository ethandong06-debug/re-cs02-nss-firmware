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
out.append(run("ls -l %s; file %s 2>/dev/null" % (apk, apk)))
out.append("== 包内文件列表（apk = tar.gz）==")
out.append(run("tar tzf %s 2>/dev/null | head -40; echo ...; tar tzf %s 2>/dev/null | wc -l" % (apk, apk)))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\apkinfo.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
