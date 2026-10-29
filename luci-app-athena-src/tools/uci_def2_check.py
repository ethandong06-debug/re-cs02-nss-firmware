import paramiko, io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\uci_def2_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(12):
    try:
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        break
    except Exception:
        time.sleep(3)
cmd = ("cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx && "
       "F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin && "
       "OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1) && "
       "dd if=$F of=/tmp/v17.sq bs=1 skip=$OFF 2>/dev/null && "
       "rm -rf /tmp/fwv17u && unsquashfs -d /tmp/fwv17u /tmp/v17.sq >/dev/null 2>&1; "
       "echo '===UCI-DEFAULTS FILES==='; ls -la /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null; "
       "echo '===GREP network/wireless in uci-defaults==='; "
       "grep -rln -E 'network|wireless|lan|wlan' /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null | while read f; do echo \"--- $f ---\"; cat \"$f\"; echo; done")
i, o, e = c.exec_command(cmd, timeout=300)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
