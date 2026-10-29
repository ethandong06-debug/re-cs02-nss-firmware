# -*- coding: utf-8 -*-
import paramiko, sys

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.put(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services.uc", "/tmp/svc.uc")
s.close()
for cmd in [
    "timeout 15 " + UC + " /tmp/svc.uc list > /tmp/svc.out 2>&1; echo rc=$?",
    "grep -o '\"id\":\"ddnsto\"[^}]*' /tmp/svc.out",
    "grep -o '\"id\":\"ddns\"[^}]*' /tmp/svc.out",
]:
    _, o, e = c.exec_command(cmd, timeout=60)
    sys.stdout.write(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace") + "\n---\n")
c.close()
