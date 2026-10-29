# -*- coding: utf-8 -*-
import paramiko, sys

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

for cmd in [
    "timeout 15 " + UC + " /tmp/svc.uc list > /tmp/svc.out 2>/tmp/svc.err; echo rc=$?",
    "grep -o '\"id\":\"ddnsto\"[^}]*' /tmp/svc.out",
    "wc -c /tmp/svc.out; head -c 200 /tmp/svc.err",
]:
    _, o, e = c.exec_command(cmd, timeout=60)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    sys.stdout.write("$ " + cmd + "\n" + out + "\n---\n")
c.close()
