#!/usr/bin/env python3
"""VM SSH 执行工具：连接编译 VM 执行命令。用法: vm_exec.py "命令" 或 vm_exec.py (从 stdin 读命令)"""
import sys, paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"

def run(cmd, timeout=120):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=20, banner_timeout=20, auth_timeout=20)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    c.close()
    return code, out, err

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
    else:
        cmd = sys.stdin.read()
    code, out, err = run(cmd)
    sys.stdout.write(out)
    if err.strip():
        sys.stderr.write("[stderr]\n" + err)
    sys.exit(code)
