# -*- coding: utf-8 -*-
"""v1.2.44 ucode 采集器验证：JSON 结构 + 与 shell 版逐字段对比 + execve/耗时。"""
import paramiko, json, io, time

UC = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-resources.uc"
SH = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-resources.sh"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
try:
    s.mkdir("/tmp/rs3")
except IOError:
    pass
s.put(UC, "/tmp/rs3/athena-resources.uc")
s.put(SH, "/tmp/rs3/athena-resources.sh")
s.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

UCODE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
lines = []
def say(x):
    lines.append(x)

say("== 1. 语法检查 ==")
o, e = run("%s -s /tmp/rs3/athena-resources.uc 2>&1 | head -5" % UCODE)
say("ucode -s: " + (o.strip() or e.strip() or "(no output, ok)"))

say("== 2. 冷启动（清缓存）第一轮 ==")
run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache /tmp/athena-res-cache.ticks")
o1, e1 = run("%s /tmp/rs3/athena-resources.uc" % UCODE)
say("first run stderr: " + (e1.strip()[:300] or "(none)"))
say("first run len: %d" % len(o1))

say("== 3. 等 10 秒后第二轮（应有 CPU% 与 window） ==")
run("sleep 10", t=40)
o2, e2 = run("%s /tmp/rs3/athena-resources.uc" % UCODE)
say("second run stderr: " + (e2.strip()[:300] or "(none)"))

try:
    d = json.loads(o2.strip())
    say("JSON 合法 ✔")
    say("cpu: " + json.dumps(d["cpu"], ensure_ascii=False))
    say("memory: " + json.dumps(d["memory"], ensure_ascii=False))
    say("procs: %d 条，首个 %s" % (len(d["procs"]), json.dumps(d["procs"][0], ensure_ascii=False)))
    missing = [p["name"] for p in d["procs"] if not p.get("label") or not p.get("desc")]
    say("label/desc 为空: %d %s" % (len(missing), missing[:5]))
    kth = [p["name"] for p in d["procs"] if p["name"].startswith(("kworker", "napi/", "irq/"))]
    say("列表里内核线程: %d" % len(kth))
    say("内存对账: procs %d + other %d = %d vs used %d" % (
        d["memory"]["procs_mb"], d["memory"]["other_mb"],
        d["memory"]["procs_mb"] + d["memory"]["other_mb"], d["memory"]["used_mb"]))
    keys = sorted(d["procs"][0].keys())
    say("procs 字段: " + ",".join(keys))
except Exception as ex:
    say("JSON 解析失败: %s" % ex)
    say("原始输出前 400: " + o2[:400])

say("== 4. 与 shell 版（v1.2.43）同机对比 ==")
run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache /tmp/athena-res-cache.ticks")
o, e = run("/bin/sh /tmp/rs3/athena-resources.sh")
os_, es_ = run("sleep 10; /bin/sh /tmp/rs3/athena-resources.sh", t=60)
try:
    ds = json.loads(os_.strip())
    say("shell cpu=%s mem=%s procs=%d" % (
        json.dumps(ds["cpu"], ensure_ascii=False), json.dumps(ds["memory"], ensure_ascii=False), len(ds["procs"])))
    say("ucode cpu=%s mem=%s procs=%d" % (
        json.dumps(d["cpu"], ensure_ascii=False), json.dumps(d["memory"], ensure_ascii=False), len(d["procs"])))
    sn = set(p["name"] for p in ds["procs"])
    un = set(p["name"] for p in d["procs"])
    say("shell 独有: %s" % sorted(sn - un)[:10])
    say("ucode 独有: %s" % sorted(un - sn)[:10])
    srss = {p["name"]: p["rss_mb"] for p in ds["procs"]}
    diff = [(n, srss[n], p["rss_mb"]) for p in d["procs"] for n in [p["name"]]
            if n in srss and abs(srss[n] - p["rss_mb"]) > 1.0]
    say("rss_mb 差 >1MB 的进程: %d %s" % (len(diff), diff[:5]))
except Exception as ex:
    say("shell 对比失败: %s" % ex)

say("== 5. execve 次数（ucode 版） ==")
o, e = run("cd /tmp/rs3 && strace -f -c -e trace=execve %s ./athena-resources.uc >/dev/null 2>/tmp/rs3/se_uc.txt; tail -4 /tmp/rs3/se_uc.txt" % UCODE, t=120)
say(o.strip() or e.strip()[:200])

say("== 6. 耗时（time，两轮平均） ==")
o, e = run("cd /tmp/rs3 && for k in 1 2 3; do /usr/bin/time -f 'ELAPSED %e USER %U SYS %S' " + UCODE + " ./athena-resources.uc >/dev/null; done 2>&1 | tail -3", t=120)
say(o.strip())

io.open(r"C:\Users\Administrator\AppData\Local\Temp\uc44.txt", "w", encoding="utf-8").write("\n".join(lines))
c.close()
