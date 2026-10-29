# -*- coding: utf-8 -*-
"""v1.2.42 后端验证：老字段不变 + 新字段自洽 + 采样耗时 + 进程 CPU 归一 + 与 status 一致。"""
import paramiko, json

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=25)
sftp = c.open_sftp()
for f in ("athena-resources.sh", "athena-status.sh"):
    sftp.put(base + "\\" + f, "/tmp/rs/" + f)
sftp.close()

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

def jload(s):
    return json.loads(s[s.index("{"):s.rindex("}") + 1])

print("syntax:", run("sh -n /tmp/rs/athena-resources.sh && echo OK")[0].strip())
run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache /tmp/athena-res-cache.ticks /tmp/athena-status.json /tmp/athena-status.stamp")

o, e = run("cd /tmp/rs && time sh athena-resources.sh")
print("elapsed:", [l for l in e.splitlines() if l.startswith("real")])
d = jload(o)
print("cpu keys:", sorted(d["cpu"].keys()), "| memory keys:", sorted(d["memory"].keys()))
print("proc[0] keys:", sorted(d["procs"][0].keys()))
m = d["memory"]
print("对账 procs_mb+other_mb=%d  used_mb=%d" % (m["procs_mb"] + m["other_mb"], m["used_mb"]))
print("cpu:", d["cpu"], "procs:", len(d["procs"]))

# 与概览页口径一致性
run("sleep 8", t=40)
o2, _ = run("rm -f /tmp/athena-status.json /tmp/athena-status.stamp; cd /tmp/rs && sh athena-status.sh")
s = jload(o2)
o3, _ = run("cd /tmp/rs && sh athena-resources.sh")
r = jload(o3)
print("status cpu=%s  resources cpu=%s window=%s  -> %s" % (s["cpu"]["total"], r["cpu"]["total"], r["cpu"]["window"], "一致" if abs(s["cpu"]["total"] - r["cpu"]["total"]) <= 1 else "不一致"))

# 进程 CPU 归一精度
run("nohup sh -c 'while :; do :; done' >/dev/null 2>&1 & echo $! > /tmp/rs/busy.pid; sleep 1", t=30)
pid = run("cat /tmp/rs/busy.pid")[0].strip()
ncpu = int(run("grep -c '^processor' /proc/cpuinfo")[0].strip())
hz = int(run("getconf CLK_TCK")[0].strip())
run("cd /tmp/rs && sh athena-resources.sh >/dev/null", t=60)
tk = lambda: int(run("awk '{sub(/^.*\\) /,\"\"); print $12+$13}' /proc/%s/stat" % pid)[0].strip())
up = lambda: float(run("cut -d' ' -f1 /proc/uptime")[0].strip())
t1, u1 = tk(), up()
run("sleep 9", t=30)
o4, _ = run("cd /tmp/rs && sh athena-resources.sh", t=60)
t2, u2 = tk(), up()
d4 = jload(o4)
mine = [p for p in d4["procs"] if str(p["pid"]) == pid]
exp = (t2 - t1) / hz / ncpu / (u2 - u1) * 100
got = mine[0]["cpu"] if mine else None
print("busy pid=%s 脚本=%s%%  独立计算=%.1f%%  窗口=%.1fs" % (pid, got, exp, u2 - u1))
run("kill %s 2>/dev/null; true" % pid)
c.close()
