# -*- coding: utf-8 -*-
import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"

out = []
def run(cmd, name, t=60):
    i, o, e = c.exec_command(cmd, timeout=t)
    out.append("=== %s ===\n%s" % (name, (o.read().decode("utf-8", "replace").strip() or "(空)")[-1000:]))

run("ps aux | grep -E 'make|go |node ' | grep -v grep | head -8", "残留进程", 20)
run("ls -la " + base + "/tmp/.config-check* 2>/dev/null; ls " + base + "/tmp/ 2>/dev/null | head -8", "tmp config 状态", 20)
run("rm -f " + base + "/tmp/.config-check* " + base + "/tmp/config-check* ; echo cleaned", "清理 config-check", 20)
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_cfgchk.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
