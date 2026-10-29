#!/usr/bin/env python3
"""VM 增量重编译固件（make -j6），阻塞到完成并输出结果。"""
import paramiko, sys, time

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20, banner_timeout=20, auth_timeout=20)

cmd = 'cd ~/jdc-build/immortalwrt_ipq-main && make -j6 V=s 2>&1 | tail -120'
stdin, stdout, stderr = c.exec_command(cmd, timeout=None, get_pty=False)

# 持续读取直到 EOF
buf = b""
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        buf += stdout.channel.recv(65536)
    time.sleep(0.5)
# 收尾
while stdout.channel.recv_ready():
    buf += stdout.channel.recv(65536)

out = buf.decode("utf-8", "replace")
code = stdout.channel.recv_exit_status()
c.close()

# 只打印尾部关键信息
lines = out.splitlines()
print("\n".join(lines[-120:]) if lines else "(no output)")
print("\n=== EXIT CODE:", code, "===")
sys.exit(code)
