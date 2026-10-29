#!/usr/bin/env python3
"""从编译 VM 下载 v1.2.39 固件镜像到本地 output 目录，并校验 sha256。"""
import paramiko, hashlib, os

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
REMOTE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx"
OUT = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
PAIRS = [
    ("immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin", "AthenaWrt-v1.2.39-factory.bin"),
    ("immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin", "AthenaWrt-v1.2.39-sysupgrade.bin"),
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20)
sftp = c.open_sftp()
os.makedirs(OUT, exist_ok=True)
for rn, ln in PAIRS:
    lp = os.path.join(OUT, ln)
    sftp.get(f"{REMOTE}/{rn}", lp)
    h = hashlib.sha256(open(lp, "rb").read()).hexdigest()
    print(f"{ln}  {os.path.getsize(lp)} bytes  sha256={h}")
sftp.close()
c.close()
