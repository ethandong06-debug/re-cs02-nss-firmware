#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)

content = """#!/bin/sh
cd ~/athena-build/nss/openwrt
setsid sh -c 'make -j$(nproc) V=s > ~/athena-build/nss/logs/athena-final.log 2>&1 < /dev/null' &
echo "BUILD_STARTED"
exit 0
"""

sftp = c.open_sftp()
with sftp.file("/home/vboxuser/start_build.sh", "w") as f:
    f.write(content)
sftp.close()

c.exec_command("chmod +x /home/vboxuser/start_build.sh")
c.close()
print("start_build.sh 已上传")
