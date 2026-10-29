# -*- coding: utf-8 -*-
"""下载 v1.2.20 产物并校验哈希。"""
import paramiko, hashlib, os, sys

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
REMOTE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\athenawrt-v1.2.22"
FILES = [
    "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
    "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin",
]

os.makedirs(LOCAL, exist_ok=True)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20)

def sha256file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

sftp = c.open_sftp()
for f in FILES:
    rp = REMOTE + "/" + f
    lp = os.path.join(LOCAL, f)
    # VM 侧大小与哈希
    st = sftp.stat(rp)
    # 下载
    sftp.get(rp, lp)
    lh = sha256file(lp)
    print("FILE: %s" % f)
    print("  size: %d bytes (VM stat)" % st.st_size)
    print("  local sha256: %s" % lh)
sftp.close()
c.close()
print("DONE ->", LOCAL)
