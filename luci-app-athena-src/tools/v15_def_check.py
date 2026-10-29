import paramiko, io, sys, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\v15_def_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(12):
    try:
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        break
    except Exception:
        time.sleep(3)
sftp = c.open_sftp()
v15 = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\AthenaWrt-v1.2.15-jdcloud_re-cs-02-sysupgrade.bin"
sftp.put(v15, "/tmp/v15.bin")
sftp.close()
cmd = ("cd /tmp && "
       "OFF=$(grep -abo 'hsqs' /tmp/v15.bin | head -1 | cut -d: -f1) && "
       "dd if=/tmp/v15.bin of=/tmp/v15.sq bs=1 skip=$OFF 2>/dev/null && "
       "rm -rf /tmp/fwv15 && unsquashfs -d /tmp/fwv15 /tmp/v15.sq >/dev/null 2>&1; "
       "echo '===V1.2.15 UCI-DEFAULTS==='; ls /tmp/fwv15/etc/uci-defaults/ 2>/dev/null | grep -E 'migrate|network|jdc|athena'; "
       "echo '===MIGRATE-BRIDGES in v1.2.15?==='; ls -la /tmp/fwv15/etc/uci-defaults/11_network-migrate-bridges 2>&1; "
       "echo '===99-zz-athena-redirect==='; cat /tmp/fwv15/etc/uci-defaults/99-zz-athena-redirect 2>/dev/null; "
       "echo '===99-athena-custom==='; cat /tmp/fwv15/etc/uci-defaults/99-athena-custom.sh 2>/dev/null")
i, o, e = c.exec_command(cmd, timeout=180)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
