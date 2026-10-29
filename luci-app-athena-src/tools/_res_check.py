# -*- coding: utf-8 -*-
"""在编译 VM 内实跑 athena-resources.sh，检查采样口径、进程 CPU 归一、内存对账。"""
import os, paramiko, json

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-resources.sh"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20)
sftp = c.open_sftp()
c.exec_command("rm -rf /tmp/rs && mkdir -p /tmp/rs")[1].channel.recv_exit_status()
sftp.put(LOCAL, "/tmp/rs/athena-resources.sh")
sftp.close()

def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return o, e

print(run("sh -n /tmp/rs/athena-resources.sh && echo SYNTAX_OK")[0])

o, _ = run("cd /tmp/rs && /usr/bin/time -f 'elapsed=%e' sh athena-resources.sh", timeout=120)
print("RUN1", o[-1200:])
try:
    d = json.loads(o[o.index("{"):o.rindex("}") + 1])
    print("cpu", d["cpu"], "mem", d["memory"])
    print("procs", len(d.get("procs", [])), "top3", [(p["name"], p["cpu"], p["mem"], p.get("rss_mb")) for p in d.get("procs", [])[:3]])
    s = sum(float(p["rss_mb"]) for p in d["procs"])
    print("procs sum(MB) 前8 =", round(s, 1), " / 全部进程合计字段 =", d["memory"]["procs_mb"], " other =", d["memory"]["other_mb"])
    tot = d["memory"]["used_mb"]
    print("对账 used =", tot, " procs+other =", d["memory"]["procs_mb"] + d["memory"]["other_mb"])
except Exception as ex:
    print("JSON 解析失败:", ex)

run("sleep 6")
o2, _ = run("cd /tmp/rs && sh athena-resources.sh")
try:
    d2 = json.loads(o2[o2.index("{"):o2.rindex("}") + 1])
    print("RUN2 cpu", d2["cpu"], " window", d2["cpu"].get("window"))
    print("RUN2 top3", [(p["name"], p["cpu"]) for p in d2["procs"][:3]])
except Exception as ex:
    print("RUN2 解析失败:", ex, o2[:300])

print(run("awk --version 2>&1 | head -1")[0])
c.close()
