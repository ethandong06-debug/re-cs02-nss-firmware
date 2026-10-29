# -*- coding: utf-8 -*-
import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
cmd = r'ls ~/ ; echo ===; find / -maxdepth 5 -iname "*gwrt*" 2>/dev/null | grep -v proc | head; echo ===; ls /tmp | head -30'
_, o, e = c.exec_command(cmd, timeout=60)
sys.stdout.write(o.read().decode("utf-8", "replace"))
sys.stdout.write("ERR:" + e.read().decode("utf-8", "replace"))
c.close()
