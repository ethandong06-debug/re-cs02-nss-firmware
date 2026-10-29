# -*- coding: utf-8 -*-
import paramiko, io, os
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
remote = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/package/luci-app-athena/root/usr/libexec/athena-services.sh"
local = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services-legacy.sh"
s.get(remote, local)
s.close()
c.close()
print("bytes:", os.path.getsize(local))
raw = io.open(local, "rb").read()
print("head:", raw[:60].decode("utf-8", "replace").replace("\n", "\\n"))
print("tail:", raw[-60:].decode("utf-8", "replace").replace("\n", "\\n"))
