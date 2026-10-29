# -*- coding: utf-8 -*-
import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
cmds = [
    "wc -l ~/www/luci-static/resources/view/jdc/dashboard.js",
    "grep -n -i 'rx_bytes\\|tx_bytes\\|net/dev\\|statistics\\|pppoe\\|br-lan\\|ifname\\|wan' ~/www/luci-static/resources/view/jdc/dashboard.js | head -40",
]
for cmd in cmds:
    _, o, e = c.exec_command(cmd, timeout=60)
    sys.stdout.write("$ " + cmd + "\n" + o.read().decode("utf-8", "replace") + "\n---\n")
c.close()
