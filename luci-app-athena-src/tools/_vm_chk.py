#!/usr/bin/env python3
"""临时检查 VM 编译状态 v2"""
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('127.0.0.1', 2222, 'vboxuser', 'vboxuser', timeout=15)
cmd = "pgrep -af make | head -20; echo '--- bin ---'; ls bin/targets/qualcommax/ipq60xx/ 2>/dev/null | head -20"
stdin, stdout, stderr = c.exec_command(cmd, timeout=20)
out = stdout.read().decode('utf-8', 'replace')
err = stderr.read().decode('utf-8', 'replace')
print('STDOUT:\n' + out)
print('STDERR:\n' + err)
c.close()
