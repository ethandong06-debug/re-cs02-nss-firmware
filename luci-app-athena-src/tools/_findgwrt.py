# -*- coding: utf-8 -*-
import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
cmd = r'ls -d ~/gwrt* ~/GWRT* /tmp/gwrt* 2>/dev/null; find /home/vboxuser -maxdepth 4 -iname "*gwrt*" 2>/dev/null | head -20'
_, o, e = c.exec_command(cmd, timeout=40)
sys.stdout.write(o.read().decode("utf-8", "replace"))
sys.stdout.write("ERR:" + e.read().decode("utf-8", "replace"))
c.close()
