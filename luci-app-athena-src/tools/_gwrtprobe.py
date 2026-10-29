# -*- coding: utf-8 -*-
import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
cmds = [
    "ls ~/www | head; echo ===; ls ~/www/luci-static 2>/dev/null | head",
    "grep -rli 'realtime\\|speed\\|rx_bytes\\|net/dev' ~/www 2>/dev/null | head -20",
    "head -c 400 ~/menu-jdc-athena.js 2>/dev/null",
]
for cmd in cmds:
    _, o, e = c.exec_command(cmd, timeout=60)
    sys.stdout.write("$ " + cmd + "\n" + o.read().decode("utf-8", "replace") + "\n---\n")
c.close()
