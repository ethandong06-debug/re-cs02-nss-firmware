# -*- coding: utf-8 -*-
"""v1.2.54 日志四列解析实测：用假 logread 喂两种真实 logread 输出格式。"""
import paramiko, io

LOG = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-log.sh"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

s.put(LOG, "/tmp/al54.sh")
s.close()

# 假 logread：格式 A（带星期与年份，OpenWrt ubox 常见）、格式 B（无星期无年份）
fmtA = r"""Fri Oct 28 20:12:00 2026 daemon.info dnsmasq[7466]: query[A] api.doubao.com from 192.168.10.23
Fri Oct 28 20:12:01 2026 kern.warn kernel: [12345.678] ath11k c000000.wifi: peer aa:bb:cc deleted
Fri Oct 28 20:12:05 2026 authpriv.err hostapd: wlan1: STA aa:bb:cc deauthenticated
Fri Oct 28 20:12:09 2026 daemon.debug athena-status: collect done in 0.21s
Fri Oct 28 20:12:11 2026 user.notice root: 这条没有标准时间戳的兜底测试
"""
fmtB = r"""Oct 28 21:00:00 daemon.info dnsmasq[100]: forwarded api.doubao.com to 223.5.5.5
Oct 28 21:00:02 kern.info kernel: [  88.123] br-lan: port 2 entered forwarding state
"""
io.open(r"C:\Users\Administrator\AppData\Local\Temp\logtest.txt", "w", encoding="utf-8").write(
    run("mkdir -p /tmp/fl; printf '%s' \"$(cat <<'EOT'\n" + fmtA + "EOT\n)\" > /tmp/fl/logread; chmod 755 /tmp/fl/logread; PATH=/tmp/fl:$PATH sh /tmp/al54.sh list") + "\n--- fmtB ---\n" +
    run("printf '%s' \"$(cat <<'EOT'\n" + fmtB + "EOT\n)\" > /tmp/fl/logread; chmod 755 /tmp/fl/logread; PATH=/tmp/fl:$PATH sh /tmp/al54.sh list")
)
c.close()
print("done")
