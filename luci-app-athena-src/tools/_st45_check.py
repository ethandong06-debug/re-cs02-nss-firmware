# -*- coding: utf-8 -*-
"""v1.2.45 编译机验证：athena-status.uc vs athena-status.sh（v1.2.40）逐字段对比。"""
import paramiko, io

LOCAL_UC = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-status.uc"
LOCAL_SH = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-status.sh"

CMP = r'''
import json

def walk(a, b, path, out):
    if type(a) != type(b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a != b: out.append("%s  value: old=%r new=%r" % (path, a, b))
            return
        out.append("%s  type: old=%s(%r) new=%s(%r)" % (path, type(a).__name__, a, type(b).__name__, b))
        return
    if isinstance(a, dict):
        ka, kb = set(a.keys()), set(b.keys())
        for k in sorted(ka - kb): out.append("%s.%s  MISSING in new" % (path, k))
        for k in sorted(kb - ka): out.append("%s.%s  EXTRA in new" % (path, k))
        for k in sorted(ka & kb): walk(a[k], b[k], path + "." + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append("%s  len: old=%d new=%d" % (path, len(a), len(b)))
            return
        for i in range(len(a)): walk(a[i], b[i], "%s[%d]" % (path, i), out)
    else:
        if a != b: out.append("%s  value: old=%r new=%r" % (path, a, b))

old = json.load(open('/tmp/old.json'))
new = json.load(open('/tmp/new.json'))
out = []
walk(old, new, '', out)
print("diff count:", len(out))
for line in out[:80]: print("  ", line)
print("---- top keys ----")
print(" old:", sorted(old.keys()))
print(" new:", sorted(new.keys()))
print("---- new output ----")
print(json.dumps(new, ensure_ascii=False)[:1400])
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.put(LOCAL_UC, "/tmp/athena-status.uc")
s.put(LOCAL_SH, "/tmp/athena-status-legacy.sh")
io.open(r"C:\Users\Administrator\AppData\Local\Temp\st45_cmp.py", "w", encoding="utf-8").write(CMP)
s.put(r"C:\Users\Administrator\AppData\Local\Temp\st45_cmp.py", "/tmp/st45_cmp.py")
s.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
CLEAN = "rm -f /tmp/athena-status.json /tmp/athena-status.stamp /tmp/athena-cpu-cache /tmp/athena-net-cache /tmp/athena-devs"

out = []
out.append("== 1) 旧版 shell 跑两次（第二次为对比基准）==")
out.append(run(CLEAN + "; sh /tmp/athena-status-legacy.sh > /tmp/old1.json 2>/tmp/old1.err; sh /tmp/athena-status-legacy.sh > /tmp/old.json 2>/tmp/old2.err; echo old_bytes=$(wc -c < /tmp/old.json)").strip())
out.append("[old stderr] " + run("head -c 400 /tmp/old1.err").strip())
out.append("== 2) 新版 ucode 跑一次（捕获 stderr）==")
out.append(run(CLEAN + "; " + U + " /tmp/athena-status.uc > /tmp/new.json 2>/tmp/new.err; echo new_bytes=$(wc -c < /tmp/new.json)").strip())
out.append("[new stderr]\n" + run("head -30 /tmp/new.err").strip())
out.append("[new first bytes]\n" + run("head -c 300 /tmp/new.json").strip())
out.append("== 3) 逐字段对比 ==")
out.append(run("python3 /tmp/st45_cmp.py 2>&1").strip())
out.append("== 4) 耗时 ==")
tmpl = "for i in 1 2 3; do " + CLEAN + "; /usr/bin/time -f 'REAL %e USER %U SYS %S' CMD >/dev/null; done 2>&1"
out.append(run(tmpl.replace("CMD", "sh /tmp/athena-status-legacy.sh")).strip())
out.append(run(tmpl.replace("CMD", U + " /tmp/athena-status.uc")).strip())
out.append("== 5) execve 计数 ==")
out.append(run("cd /tmp && " + CLEAN + " && strace -f -c -e trace=execve sh /tmp/athena-status-legacy.sh >/dev/null 2>/tmp/trace_old.txt; grep -E 'execve|total' /tmp/trace_old.txt | head -5").strip())
out.append(run("cd /tmp && " + CLEAN + " && strace -f -c -e trace=execve " + U + " /tmp/athena-status.uc >/dev/null 2>/tmp/trace_new.txt; grep -E 'execve|total' /tmp/trace_new.txt | head -5").strip())

io.open(r"C:\Users\Administrator\AppData\Local\Temp\st45.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
