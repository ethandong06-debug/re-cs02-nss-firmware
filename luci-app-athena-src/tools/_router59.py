# -*- coding: utf-8 -*-
import paramiko, sys, time
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.10.1", 22, "root", timeout=15)
cmds = [
    "sha256sum /usr/libexec/athena-rate.uc /www/luci-static/resources/view/athena/index.html",
    "tail -15 /tmp/.athena-rate.log",
    "echo ===; sh /usr/libexec/athena-status.sh rate; sleep 2; sh /usr/libexec/athena-status.sh rate; sleep 2; sh /usr/libexec/athena-status.sh rate",
]
for cmd in cmds:
    _, o, e = c.exec_command(cmd, timeout=30)
    sys.stdout.write("$ " + cmd + "\n" + o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace") + "\n---\n")
c.close()
