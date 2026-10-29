#!/usr/bin/env python3
"""递归上传本地目录到编译 VM。用法: vm_upload.py <本地目录> <远端绝对路径>"""
import sys, os, paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"

def upload(local_dir, remote_dir):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=20)
    sftp = c.open_sftp()

    def ensure_remote(path):
        try:
            sftp.stat(path)
        except IOError:
            sftp.mkdir(path)

    # 递归创建远端目录
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        rdir = remote_dir if rel == "." else os.path.join(remote_dir, rel).replace("\\", "/")
        try:
            sftp.stat(rdir)
        except IOError:
            # 逐级创建
            parts = rdir.strip("/").split("/")
            cur = ""
            for p in parts:
                cur = cur + "/" + p
                try:
                    sftp.stat(cur)
                except IOError:
                    sftp.mkdir(cur)

    # 上传文件
    n = 0
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        rdir = remote_dir if rel == "." else os.path.join(remote_dir, rel).replace("\\", "/")
        for f in files:
            lp = os.path.join(root, f)
            rp = rdir + "/" + f
            sftp.put(lp, rp)
            n += 1
    sftp.close()
    c.close()
    print(f"上传完成：{n} 个文件 -> {remote_dir}")

if __name__ == "__main__":
    upload(sys.argv[1], sys.argv[2])
