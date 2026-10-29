# -*- coding: utf-8 -*-
import paramiko, io, json
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
for n in ("athena-resources.sh", "athena-resources-legacy.sh", "athena-resources.uc"):
    s.put(base + "\\" + n, "/tmp/rs3/" + n)
s.close()

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

U = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
out = []
out.append("== sh 语法（入口/legacy）==")
out.append(run("sh -n /tmp/rs3/athena-resources.sh && echo ENTRY_OK; sh -n /tmp/rs3/athena-resources-legacy.sh && echo LEGACY_OK"))
out.append("== legacy 仍能出合法 JSON ==")
out.append(run("rm -f /tmp/athena-cpu-cache /tmp/athena-res-cache.ticks; sh /tmp/rs3/athena-resources-legacy.sh | head -c 150"))
out.append("== stop 分支：受保护进程应被拒 ==")
out.append(run("sh /tmp/rs3/athena-resources.sh stop 1"))
out.append(run("sh /tmp/rs3/athena-resources.sh stop 999999"))
out.append("== 入口在 ucode 缺失时的行为（用 PATH 模拟不影响绝对路径，直接看分支逻辑）==")
out.append(run("grep -n 'exec /usr/bin/ucode\\|exec /usr/libexec/athena-resources-legacy.sh' /tmp/rs3/athena-resources.sh"))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\\sh44.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
