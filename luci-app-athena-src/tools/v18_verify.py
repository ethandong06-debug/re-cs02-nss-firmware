import paramiko, io, sys, hashlib, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)

cmd = r'''
cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx
F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin
OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1)
dd if=$F of=/tmp/v18.sq bs=1 skip=$OFF 2>/dev/null
rm -rf /tmp/fwv18 && unsquashfs -d /tmp/fwv18 /tmp/v18.sq >/dev/null 2>&1
B=/tmp/fwv18
echo MARKER18:; grep -c 'v1.2.18' $B/www/luci-static/resources/view/athena/index.html
echo BK_SORT_FIX:; grep -c 'ls -1t' $B/usr/libexec/athena-backup.sh
echo MODE_STDERR:; grep -c '>&2' $B/usr/libexec/athena-mode.sh
echo BR_GUEST:; grep -c 'br-guest' $B/usr/libexec/athena-wireless.sh
echo SCAN_RADIO:; grep -c 'local dis' $B/usr/libexec/athena-scan.sh
echo UPGRADE_T:; grep -c 'sysupgrade -T' $B/usr/libexec/athena-upgrade.sh
echo SPEED_NULL:; grep -c 'UP_MBPS:-null' $B/usr/libexec/athena-speedtest.sh
echo SVC_CORE:; grep -c 'athena-vlan-pre athena-netcheck' $B/usr/libexec/athena-services.sh
echo STATUS_INNER:; grep -c 'athena.single.inner_vlan' $B/usr/libexec/athena-status.sh
echo LOG_URL:; grep -c 'athena-log/' $B/usr/libexec/athena-log.sh
echo VLANPRE_TYPECHK:; grep -c 'stype' $B/etc/init.d/athena-vlan-pre
echo NETCHECK_DYN:; grep -c 'network.lan.ipaddr' $B/etc/init.d/athena-netcheck
echo FE_RT_BACKFILL:; grep -c 'd.wan.wan_vlan' $B/www/luci-static/resources/view/athena/index.html
echo FE_PWD8:; grep -c '至少 8 位' $B/www/luci-static/resources/view/athena/index.html
echo FE_PINGFIELDS:; grep -c 'avg_ms' $B/www/luci-static/resources/view/athena/index.html
echo FE_FMT_FS:; grep -c 'vfat' $B/www/luci-static/resources/view/athena/index.html
echo FE_REBOOT_HOUR:; grep -c 'd.hour' $B/www/luci-static/resources/view/athena/index.html
echo FE_PKG_NOUPDATE:; grep -c '可更新' $B/www/luci-static/resources/view/athena/index.html
echo FE_WIZFAIL:; grep -c 'cmdFailed' $B/www/luci-static/resources/view/athena/index.html
'''
i, o, e = c.exec_command(cmd, timeout=300)
out = o.read().decode("utf-8", "replace")
c.close()
print(out)

# 本地哈希
lo = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
for n in ["AthenaWrt-v1.2.18-jdcloud_re-cs-02-sysupgrade.bin", "AthenaWrt-v1.2.18-jdcloud_re-cs-02-factory.bin"]:
    h = hashlib.sha256(open(os.path.join(lo, n), "rb").read()).hexdigest()
    print("HASH", n, h)
