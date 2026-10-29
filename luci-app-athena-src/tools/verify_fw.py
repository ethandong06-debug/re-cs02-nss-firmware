import paramiko, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\verify_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
cmd = [
    "cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx",
    "F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
    "OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1)",
    "dd if=$F of=/tmp/r3.sq bs=1 skip=$OFF 2>/dev/null",
    "rm -rf /tmp/fwroot3",
    "unsquashfs -d /tmp/fwroot3 /tmp/r3.sq >/dev/null 2>&1",
    "S=/tmp/fwroot3/usr/libexec/athena-services.sh",
    "echo MARKER:; grep -c 'v1.2.16' /tmp/fwroot3/www/luci-static/resources/view/athena/index.html",
    "echo INSTALLED_SHOW:; grep -c '已安装即显示' $S",
    "echo CORE_INIT_ATHENA:; grep -c 'athena-boot athena-ui' $S",
    "echo ENABLED_ON:; grep -c 'enabled >/dev/null 2>&1; then on=true' $S",
]
i, o, e = c.exec_command(" && ".join(cmd), timeout=120)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
