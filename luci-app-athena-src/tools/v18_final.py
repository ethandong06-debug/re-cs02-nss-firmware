import paramiko, io, sys, hashlib, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
sftp = c.open_sftp()
r = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx/"
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
pairs = [
    ("immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin", "AthenaWrt-v1.2.18-jdcloud_re-cs-02-sysupgrade.bin"),
    ("immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin", "AthenaWrt-v1.2.18-jdcloud_re-cs-02-factory.bin"),
]
for remote, local in pairs:
    dst = os.path.join(out, local)
    sftp.get(r + remote, dst)
    print("DL", local, os.path.getsize(dst))
sftp.close()

# 解包验证：可更新已移除 + 标记
cmd = r'''
cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx
F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin
OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1)
dd if=$F of=/tmp/v18b.sq bs=1 skip=$OFF 2>/dev/null
rm -rf /tmp/fwv18b && unsquashfs -d /tmp/fwv18b /tmp/v18b.sq >/dev/null 2>&1
B=/tmp/fwv18b
echo MARKER18:; grep -c 'v1.2.18' $B/www/luci-static/resources/view/athena/index.html
echo PKG_NOUPDATE_LINE:; grep -c '可更新' $B/www/luci-static/resources/view/athena/index.html
echo PKG_INSTALLED_LINE:; grep -c '个软件包' $B/www/luci-static/resources/view/athena/index.html
'''
i, o, e = c.exec_command(cmd, timeout=300)
print(o.read().decode("utf-8", "replace"))
c.close()

for n in ["AthenaWrt-v1.2.18-jdcloud_re-cs-02-sysupgrade.bin", "AthenaWrt-v1.2.18-jdcloud_re-cs-02-factory.bin"]:
    h = hashlib.sha256(open(os.path.join(out, n), "rb").read()).hexdigest()
    print("HASH", n, h)
