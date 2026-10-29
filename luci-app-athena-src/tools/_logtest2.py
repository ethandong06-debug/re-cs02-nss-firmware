# -*- coding: utf-8 -*-
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

# 直接写文件（避免 heredoc 转义问题）
lines_a = [
    "Fri Oct 28 20:12:00 2026 daemon.info dnsmasq[7466]: query[A] api.doubao.com from 192.168.10.23",
    "Fri Oct 28 20:12:01 2026 kern.warn kernel: [12345.678] ath11k c000000.wifi: peer aa:bb:cc deleted",
    "Fri Oct 28 20:12:05 2026 authpriv.err hostapd: wlan1: STA aa:bb:cc deauthenticated",
    "Fri Oct 28 20:12:09 2026 daemon.debug athena-status: collect done in 0.21s",
    "Oct 28 21:00:00 daemon.info dnsmasq[100]: forwarded api.doubao.com to 223.5.5.5",
    "Oct 28 21:00:02 kern.info kernel: [  88.123] br-lan: port 2 entered forwarding state",
]
payload = "\\n".join(lines_a)
run("mkdir -p /tmp/fl && rm -f /tmp/fl/logread")
run("printf '%b' \"" + payload + "\\n\" > /tmp/fl/logread && chmod 755 /tmp/fl/logread")
out = ["== fake logread file ==", run("cat -A /tmp/fl/logread | head -8")]
out.append("== 直接执行 ==")
out.append(run("PATH=/tmp/fl:$PATH sh /tmp/al54.sh list"))
out.append("== 中间层（awk 前 3 行）==")
out.append(run("PATH=/tmp/fl:$PATH logread | head -3"))
out.append("== awk 版本 ==")
out.append(run("awk --version 2>&1 | head -2; sh -c 'PATH=/tmp/fl:$PATH logread | awk \"{print NF}\"' | head -3"))
open(r"C:\Users\Administrator\AppData\Local\Temp\logtest2.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
