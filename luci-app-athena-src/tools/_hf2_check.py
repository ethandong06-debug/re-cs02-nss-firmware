#!/usr/bin/env python3
"""把三个后端脚本上传到编译 VM 的 /tmp/hf2 并做 sh -n 语法校验。"""
import paramiko, os

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
FILES = ["athena-status.sh", "athena-apps.sh", "athena-packages.sh", "athena-services.sh", "athena-upgrade.sh"]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20)
c.exec_command("mkdir -p /tmp/hf2")[1].channel.recv_exit_status()
sftp = c.open_sftp()
for f in FILES:
    sftp.put(os.path.join(BASE, f), "/tmp/hf2/" + f)
sftp.close()

cmd = "cd /tmp/hf2 && for f in *.sh; do sh -n \"$f\" && echo \"OK $f\" || echo \"FAIL $f\"; done"
stdin, stdout, stderr = c.exec_command(cmd)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()
