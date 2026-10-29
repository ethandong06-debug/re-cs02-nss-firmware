import paramiko, io, sys, os, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\v17_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
sftp = c.open_sftp()
fw = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx"
lo = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
names = ["immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
         "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin", "sha256sums"]
lines = []
for n in names:
    sftp.get(fw + "/" + n, os.path.join(lo, n))
    lines.append("DL " + n + " " + str(os.path.getsize(os.path.join(lo, n))))
sftp.close()
# 解包验证
unpack = ("cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx && "
          "F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin && "
          "OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1) && "
          "dd if=$F of=/tmp/v17.sq bs=1 skip=$OFF 2>/dev/null && "
          "rm -rf /tmp/fwv17 && unsquashfs -d /tmp/fwv17 /tmp/v17.sq >/dev/null 2>&1; "
          "echo MARKER:; grep -c 'v1.2.17' /tmp/fwv17/www/luci-static/resources/view/athena/index.html; "
          "echo VLANPRE:; ls /tmp/fwv17/etc/init.d/athena-vlan-pre 2>/dev/null | wc -l; "
          "echo NETCHECK:; ls /tmp/fwv17/etc/init.d/athena-netcheck 2>/dev/null | wc -l; "
          "echo MODE_PROTECT:; grep -c '关键系统服务受保护' /tmp/fwv17/usr/libexec/athena-resources.sh; "
          "echo CORE_WPAD:; grep -c 'wpad hostapd' /tmp/fwv17/usr/libexec/athena-services.sh")
i, o, e = c.exec_command(unpack, timeout=300)
lines.append(o.read().decode("utf-8", "replace"))
c.close()
# 哈希
h = []
for n in names[:2]:
    h.append(hashlib.sha256(open(os.path.join(lo, n), "rb").read()).hexdigest())
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\nHASHES:\n" + "\n".join(h) + "\n")
print("done")
