#!/usr/bin/env python3
"""从编译 VM 下载定制固件产物到本地。用法: python vm_download.py"""
import paramiko, os, sys

HOST = "127.0.0.1"
PORT = 2222
USER = "vboxuser"
PASS = "vboxuser"

REMOTE_DIR = "/home/vboxuser/athena-build/nss/openwrt/bin/targets/qualcommax/ipq60xx"
LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "athenawrt-v1.0.0")

FILES = [
    "athenawrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
    "athenawrt-qualcommax-ipq60xx.manifest",
    "sha256sums",
    "config.buildinfo",
    "feeds.buildinfo",
    "version.buildinfo",
]

def main():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PASS, timeout=30)
    sftp = c.open_sftp()
    for f in FILES:
        remote = REMOTE_DIR + "/" + f
        local = os.path.join(LOCAL_DIR, f)
        try:
            sftp.get(remote, local)
            size = os.path.getsize(local)
            print(f"OK  {f}  ({size} bytes)")
        except Exception as e:
            print(f"SKIP {f}: {e}")
    sftp.close()
    c.close()
    print("下载完成 ->", LOCAL_DIR)

if __name__ == "__main__":
    main()
