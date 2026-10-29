# -*- coding: utf-8 -*-
"""VM 内实测 athena-resources.sh：采样口径、进程 CPU 归一、内存对账、执行耗时。"""
import paramiko, json

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
sftp = c.open_sftp()
sftp.put(base + r"\athena-resources.sh", "/tmp/rs/athena-resources.sh")
sftp.put(base + r"\athena-status.sh", "/tmp/rs/athena-status.sh")
sftp.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

def jload(s):
    return json.loads(s[s.index("{"):s.rindex("}") + 1])

print(run("sh -n /tmp/rs/athena-resources.sh && sh -n /tmp/rs/athena-status.sh && echo SYNTAX_OK")[0].strip())
run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-now /tmp/athena-res-ticks /tmp/athena-res-cache.up")

o, e = run("cd /tmp/rs && time sh athena-resources.sh")
print("RUN1 elapsed:", e.strip().splitlines()[-3] if e.strip() else "-")
d = jload(o)
print("cpu:", d["cpu"])
print("mem:", d["memory"])
print("procs:", len(d["procs"]))
print("top5:", [(p["name"], p["cpu"], p["mem"], p["rss_mb"]) for p in d["procs"][:5]])
m = d["memory"]
print("对账 procs_mb+other_mb =", m["procs_mb"] + m["other_mb"], " used_mb =", m["used_mb"])
bad = [p for p in d["procs"] if p["rss_mb"] > m["procs_mb"]]
print("异常进程(单进程 RSS 超过总和):", [(p['name'], p['rss_mb']) for p in bad])

run("sleep 8")
o2, e2 = run("cd /tmp/rs && sh athena-resources.sh")
d2 = jload(o2)
print("RUN2 cpu:", d2["cpu"], "top5:", [(p["name"], p["cpu"]) for p in d2["procs"][:5]])
print("RUN2 mem procs_mb/other_mb:", d2["memory"]["procs_mb"], d2["memory"]["other_mb"], "used:", d2["memory"]["used_mb"])

# 与 status.sh 共用缓存的口径一致性：status 里 CPU 计算块单独验证
o3, _ = run("cd /tmp/rs && sh athena-status.sh 2>/dev/null | head -c 400")
print("status head:", o3[:200])
c.close()
