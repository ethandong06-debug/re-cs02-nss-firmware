# -*- coding: utf-8 -*-
import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)

out = []
def run(cmd, name, t=60):
    i, o, e = c.exec_command(cmd, timeout=t)
    out.append("=== %s ===\n%s" % (name, (o.read().decode("utf-8", "replace").strip() or "(空)")[-1000:]))

run("pkill -9 -f 'filebrowser' ; pkill -9 -f 'pnpm' ; pkill -9 -f 'make -w -r' ; pkill -9 -f 'make -j6' ; sleep 2 ; ps aux | grep -E 'make|pnpm|filebrowser|node ' | grep -v grep | wc -l", "杀全部编译进程", 30)
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_killall13.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
