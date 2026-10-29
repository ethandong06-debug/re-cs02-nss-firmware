#!/usr/bin/env python3
"""上传本地 tar.gz 并在远端解压。用法: vm_upload_tar.py <本地tar.gz> <远端目标目录>"""
import sys, os, paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"

def main(local_tar, remote_dir):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=20)
    sftp = c.open_sftp()

    # 确保目标目录存在（通过 SSH）
    c.exec_command(f"mkdir -p {remote_dir}")

    remote_tar = "/tmp/_upload.tar.gz"
    sftp.put(local_tar, remote_tar)
    sftp.close()

    # 远端解压到目标目录
    cmd = f"cd {remote_dir} && tar xzf {remote_tar} && rm -f {remote_tar} && echo UNPACK_OK && ls -la"
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    c.close()
    print(out)
    if err.strip():
        print("[stderr]", err)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
