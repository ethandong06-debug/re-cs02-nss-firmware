# -*- coding: utf-8 -*-
"""v1.2.55 logcap 实测：造 3.1MB/40000 行 → 断言裁到 ~1.56MB/20000 行并写记录。"""
import paramiko, io

LC = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-logcap.sh"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.put(LC, "/tmp/lc55.sh")
s.close()

def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

out = []
out.append("== sh -n ==")
out.append(run("sh -n /tmp/lc55.sh && echo SYNTAX-OK"))
out.append("== 造 40000 行样本 ==")
out.append(run("rm -f /tmp/dnsmasq.log /tmp/athena-logcap.log /tmp/.athena-logcap.lock;"
               "awk 'BEGIN{for(i=1;i<=40000;i++) printf \"Oct 28 22:00:%02d dnsmasq[7466]: query[A] test%d.doubao.com from 192.168.10.23\\n\", i%60, i}' > /tmp/dnsmasq.log;"
               "wc -c < /tmp/dnsmasq.log; wc -l < /tmp/dnsmasq.log"))
out.append("== 跑 ==")
out.append(run("sh -x /tmp/lc55.sh 2>&1 | tail -12"))
out.append("== 结果 ==")
out.append(run("wc -c < /tmp/dnsmasq.log; wc -l < /tmp/dnsmasq.log; head -1 /tmp/dnsmasq.log; tail -1 /tmp/dnsmasq.log; cat /tmp/athena-logcap.log"))
out.append("== 第二次跑（应无动作）==")
out.append(run("sh /tmp/lc55.sh; echo rc=$?; wc -c < /tmp/dnsmasq.log"))
out.append("== 记录自我限额（造假 60 行记录）==")
out.append(run("awk 'BEGIN{for(i=1;i<=60;i++) print \"2026-10-28 22:00:00 trim 1 -> 2 bytes\"}' > /tmp/athena-logcap.log;"
               "awk 'BEGIN{for(i=1;i<=40000;i++) printf \"x\\n\"}' > /tmp/dnsmasq.log; sh /tmp/lc55.sh; wc -l < /tmp/athena-logcap.log"))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\lc55.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
