# -*- coding: utf-8 -*-
import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"

out = []
def run(cmd, name, t=60):
    i, o, e = c.exec_command(cmd, timeout=t)
    out.append("=== %s ===\n%s" % (name, (o.read().decode("utf-8", "replace").strip() or "(空)")[-1500:]))

run("ls -lt " + base + "/bin/targets/qualcommax/ipq60xx/*.bin | head -3", "固件文件")
run("cat " + base + "/bin/targets/qualcommax/ipq60xx/sha256sums | grep -E 'sysupgrade|factory' | head -4", "sha256sums")
run("date '+%H:%M:%S'", "当前时间")
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_fw_chk13.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
