# -*- coding: utf-8 -*-
"""精确对账：造一个吃满单核的进程，比较脚本给出的 CPU% 与独立计算值。"""
import paramiko, json

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=25)
sftp = c.open_sftp()
sftp.put(base + r"\athena-resources.sh", "/tmp/rs/athena-resources.sh")
sftp.close()

def run(cmd, t=90):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

print(run("sh -n /tmp/rs/athena-resources.sh && echo SYNTAX_OK")[0].strip())
run("rm -f /tmp/athena-res-cache /tmp/athena-res-cache.ticks /tmp/athena-cpu-cache")
ncpu = int(run("grep -c '^processor' /proc/cpuinfo")[0].strip())
hz = int(run("getconf CLK_TCK")[0].strip())
print("ncpu=%d hz=%d" % (ncpu, hz))

run("nohup sh -c 'while :; do :; done' >/dev/null 2>&1 & echo $! > /tmp/rs/busy.pid; sleep 1", t=30)
pid = run("cat /tmp/rs/busy.pid")[0].strip()
run("cd /tmp/rs && sh athena-resources.sh >/dev/null", t=60)
print("ticks head:", run("head -1 /tmp/athena-res-cache.ticks")[0].strip())

def ticks():
    return int(run("awk '{sub(/^.*\\) /,\"\"); print $12+$13}' /proc/%s/stat" % pid)[0].strip())
def up():
    return float(run("cut -d' ' -f1 /proc/uptime")[0].strip())

t1, u1 = ticks(), up()
run("sleep 9", t=30)
o, _ = run("cd /tmp/rs && sh athena-resources.sh", t=60)
t2, u2 = ticks(), up()
d = json.loads(o[o.index("{"):o.rindex("}") + 1])
got = [p for p in d["procs"] if str(p["pid"]) == pid]
stamp = run("head -1 /tmp/athena-res-cache.ticks")[0].strip().split("|")[-1]
print("新时间戳:", stamp)
exp = (t2 - t1) / hz / ncpu / (u2 - u1) * 100
print("ticks %d->%d  up %.2f->%.2f" % (t1, t2, u1, u2))
print("脚本: %s" % (got[0] if got else "(不在前8)"))
print("独立计算: %.1f%%  (窗口 %.1fs)" % (exp, u2 - u1))
run("kill %s 2>/dev/null; true" % pid)
c.close()
