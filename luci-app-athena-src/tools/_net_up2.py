# -*- coding: utf-8 -*-
"""Retry upload x/net v0.40.0 with mkdir -p."""
import paramiko, os, sys

HOST, PORT, USER, PASS = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
LOCAL_BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download"
REMOTE_BASE = BASE + "/dl/go-mod-cache/cache/download"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)

# check remote base
i, o, e = c.exec_command("ls -d " + REMOTE_BASE + " 2>/dev/null || echo MISSING; ls -d " + BASE + "/dl/go-mod-cache 2>/dev/null || echo MISSING2")
print(o.read().decode("utf-8", "replace").strip())

em = "golang.org/x/net"
i, o, e = c.exec_command("mkdir -p " + REMOTE_BASE + "/" + em + "/@v && echo mkdir-ok")
print(o.read().decode("utf-8", "replace").strip())

sftp = c.open_sftp()
vdir = os.path.join(LOCAL_BASE, em, "@v")
for f in os.listdir(vdir):
    rp = os.path.join(REMOTE_BASE, em, "@v", f)
    sftp.put(os.path.join(vdir, f), rp)
    print("uploaded", f)
sftp.close()
i, o, e = c.exec_command("ls -la " + REMOTE_BASE + "/" + em + "/@v/")
print(o.read().decode("utf-8", "replace").strip())
c.close()
