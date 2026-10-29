# -*- coding: utf-8 -*-
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.put(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-log.sh", "/tmp/al54.sh")

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

lines = [
    "Fri Oct 28 20:12:00 2026 daemon.info dnsmasq[7466]: query[A] api.doubao.com from 192.168.10.23",
    "Fri Oct 28 20:12:01 2026 kern.warn kernel: [12345.678] ath11k c000000.wifi: peer aa:bb:cc deleted",
    "Fri Oct 28 20:12:05 2026 authpriv.err hostapd: wlan1: STA aa:bb:cc deauthenticated",
    "Fri Oct 28 20:12:09 2026 daemon.debug athena-status: collect done in 0.21s",
    "Oct 28 21:00:00 daemon.info dnsmasq[100]: forwarded api.doubao.com to 223.5.5.5",
    "Oct 28 21:00:02 kern.info kernel: [  88.123] br-lan: port 2 entered forwarding state",
    "kern.err kernel: [  99.001] phy0: 内核错误但不是 logread 标准行",
]
script = "#!/bin/sh\ncat <<'EOX'\n" + "\n".join(lines) + "\nEOX\n"
f = s.open("/tmp/fl/logread", "w")
f.write(script)
f.close()
run("chmod 755 /tmp/fl/logread")
s.close()

out = ["== logread 输出 ==", run("PATH=/tmp/fl:$PATH logread | head -3")]
out.append("== athena-log.sh list ==")
out.append(run("PATH=/tmp/fl:$PATH sh /tmp/al54.sh list"))
out.append("== level=err 过滤 ==")
out.append(run("PATH=/tmp/fl:$PATH sh /tmp/al54.sh list err"))
out.append("== keyword=dnsmasq ==")
out.append(run("PATH=/tmp/fl:$PATH sh /tmp/al54.sh list all dnsmasq"))
open(r"C:\Users\Administrator\AppData\Local\Temp\logtest3.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
