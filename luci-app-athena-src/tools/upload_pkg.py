#!/usr/bin/env python3
"""递归上传本地 luci-app-athena 目录到编译 VM 的 package/ 目录（paramiko SFTP）"""
import os, sys, paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"

LOCAL = r"C:/Users/Administrator/WorkBuddy/2026-10-22-23-23-11/athena-openwrt/frontend/luci-app-athena"
REMOTE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/package/luci-app-athena"

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=20, banner_timeout=20, auth_timeout=20)
    sftp = c.open_sftp()

    # 确保远程根目录存在
    def mkdir_p(remote_path):
        parts = remote_path.split("/")
        cur = ""
        for p in parts:
            if not p:
                continue
            cur += "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                sftp.mkdir(cur)

    mkdir_p(REMOTE)

    uploaded = 0
    for dirpath, dirnames, filenames in os.walk(LOCAL):
        rel = os.path.relpath(dirpath, LOCAL)
        remote_dir = REMOTE if rel == "." else REMOTE + "/" + rel.replace("\\", "/")
        mkdir_p(remote_dir)
        for fn in filenames:
            local_fp = os.path.join(dirpath, fn)
            remote_fp = remote_dir + "/" + fn
            sftp.put(local_fp, remote_fp)
            uploaded += 1
            print("  +", remote_fp)

    sftp.close()
    c.close()
    print("上传完成，共", uploaded, "个文件")

if __name__ == "__main__":
    main()
