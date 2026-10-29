# -*- coding: utf-8 -*-
"""v1.2.43 验证：单 awk 组装后的 execve 次数、耗时、JSON 与 v1.2.42 逐字段对比。"""
import paramiko, json, io

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=25)
sftp = c.open_sftp()
try:
    sftp.mkdir("/tmp/rs2")
except IOError:
    pass
sftp.put(base + r"\athena-resources.sh", "/tmp/rs2/athena-resources.sh")
sftp.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

def jload(s):
    return json.loads(s[s.index("{"):s.rindex("}") + 1])

print("syntax:", run("sh -n /tmp/rs2/athena-resources.sh && echo OK")[0].strip())
run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache /tmp/athena-res-cache.ticks")

# 新脚本跑两轮（第一轮无快照，第二轮有 CPU%）
o1, e1 = run("cd /tmp/rs2 && time sh athena-resources.sh", t=120)
run("sleep 10", t=40)
o2, e2 = run("cd /tmp/rs2 && time sh athena-resources.sh", t=120)
print("耗时(第2轮):", [l for l in e2.splitlines() if l.startswith(("real", "user", "sys"))])
d = jload(o2)
print("字段:", sorted(d["cpu"].keys()), sorted(d["memory"].keys()), sorted(d["procs"][0].keys()))
print("cpu:", d["cpu"], "mem:", d["memory"])
print("进程数(过滤内核线程后):", len(d["procs"]), " 首个:", d["procs"][0])
print("对账:", d["memory"]["procs_mb"] + d["memory"]["other_mb"], "vs used", d["memory"]["used_mb"])
missing = [p for p in d["procs"] if not p.get("label") or not p.get("desc")]
print("label/desc 为空的进程:", len(missing), [p["name"] for p in missing][:5])
kth = [p for p in d["procs"] if p["name"].startswith(("kworker", "napi/", "irq/"))]
print("仍在列表里的内核线程:", len(kth))

# execve 次数
print("== execve 计数（新） ==")
o, e = run("cd /tmp/rs2 && strace -f -c -e trace=execve sh athena-resources.sh >/dev/null 2>/tmp/rs2/se.txt; tail -4 /tmp/rs2/se.txt", t=180)
print(o.strip() or e.strip()[:300])
c.close()
