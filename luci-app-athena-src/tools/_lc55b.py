# -*- coding: utf-8 -*-
"""补测：记录文件超过 50 行时是否自我裁剪（需日志本身超 CAP 才会走到那段）。"""
import paramiko, io

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

cmd = (
    "awk 'BEGIN{for(i=1;i<=60;i++) print \"2026-10-28 22:00:00 trim 1 -> 2 bytes\"}' > /tmp/athena-logcap.log;"
    "awk 'BEGIN{for(i=1;i<=40000;i++) printf \"y\\n\"}' > /tmp/dnsmasq.log;"
    "echo before=$(wc -l < /tmp/athena-logcap.log);"
    "sh /tmp/lc55.sh;"
    "echo after_log=$(wc -c < /tmp/dnsmasq.log) after_rec=$(wc -l < /tmp/athena-logcap.log);"
    "tail -2 /tmp/athena-logcap.log"
)
out = run(cmd)
io.open(r"C:\Users\Administrator\AppData\Local\Temp\lc55b.txt", "w", encoding="utf-8").write(out)
print("done")
