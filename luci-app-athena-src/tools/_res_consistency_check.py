# -*- coding: utf-8 -*-
"""验证概览页(status) 与 高级页(resources) 的 CPU 口径一致（共用 /tmp/athena-cpu-cache）。"""
import paramiko, json

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=25)
sftp = c.open_sftp()
for f in ("athena-resources.sh", "athena-status.sh"):
    sftp.put(base + "\\" + f, "/tmp/rs/" + f)
sftp.close()

def run(cmd, t=90):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache /tmp/athena-res-cache.ticks")
run("nohup sh -c 'while :; do :; done' >/dev/null 2>&1 & echo $! > /tmp/rs/busy.pid; sleep 2", t=30)

def status_cpu():
    o, _ = run("cd /tmp/rs && sh athena-status.sh 2>/dev/null")
    d0 = json.loads(o[o.index("{"):o.rindex("}") + 1])
    return d0["cpu"], run("cat /tmp/athena-cpu-cache")[0].strip()

def res_cpu():
    o, _ = run("cd /tmp/rs && sh athena-resources.sh 2>/dev/null")
    return json.loads(o[o.index("{"):o.rindex("}") + 1])["cpu"]

print("S1:", status_cpu())
run("sleep 10", t=30)
s = status_cpu()
print("S2:", s)
print("R (紧跟 status):", res_cpu())
run("sleep 10", t=30)
print("R (隔10s，自己算):", res_cpu())
run("kill $(cat /tmp/rs/busy.pid) 2>/dev/null; true")
c.close()
