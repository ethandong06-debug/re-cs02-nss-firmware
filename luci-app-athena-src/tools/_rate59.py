# -*- coding: utf-8 -*-
import paramiko, sys, traceback
try:
    UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
    s = c.open_sftp()
    s.put(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-rate.uc", "/tmp/rate2.uc")
    s.close()
    print("uploaded")
    for cmd in [
        "rm -f /tmp/.athena-rate /tmp/.athena-rate.log",
        "timeout 15 " + UC + " /tmp/rate2.uc",
        "sleep 2; timeout 15 " + UC + " /tmp/rate2.uc",
        "sleep 2; timeout 15 " + UC + " /tmp/rate2.uc",
        "echo ===LOG===; cat /tmp/.athena-rate.log",
    ]:
        _, o, e = c.exec_command(cmd, timeout=30)
        out = o.read().decode("utf-8", "replace")
        err = e.read().decode("utf-8", "replace")
        print("$ " + cmd)
        print(out)
        if err.strip():
            print("ERR:", err)
    c.close()
except Exception:
    traceback.print_exc()
