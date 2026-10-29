# -*- coding: utf-8 -*-
"""Turn off filebrowser, defconfig, rerun full make."""
import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=30)

out = []
def run(cmd, name, t=300):
    i, o, e = c.exec_command(cmd, timeout=t)
    out.append("=== %s ===\n%s" % (name, (o.read().decode("utf-8", "replace").strip() or "(空)")[-1200:]))

run("pkill -9 -f 'make -w -r' ; pkill -9 -f 'make -j6' ; pkill -9 -f 'filebrowser' ; sleep 2 ; ps aux | grep -E 'make|go ' | grep -v grep | wc -l", "杀残留", 30)
run("cd /home/vboxuser/jdc-build/immortalwrt_ipq-main && sed -i 's/^CONFIG_PACKAGE_filebrowser=y/# CONFIG_PACKAGE_filebrowser is not set/' .config && grep -n 'CONFIG_PACKAGE_filebrowser=' .config", "关 filebrowser", 30)
run("cd /home/vboxuser/jdc-build/immortalwrt_ipq-main && make defconfig 2>&1 | tail -2", "defconfig", 300)
run("cd /home/vboxuser/jdc-build/immortalwrt_ipq-main && grep -c 'CONFIG_PACKAGE_luci-app-athena=y' .config && grep -nE 'CONFIG_PACKAGE_(filebrowser|node|node-pnpm)=' .config", "确认", 30)
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_fb_off.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
