import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)

cmd = r'''
cd ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx
F=immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin
OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1)
dd if=$F of=/tmp/v19.sq bs=1 skip=$OFF 2>/dev/null
rm -rf /tmp/fwv19 && unsquashfs -d /tmp/fwv19 /tmp/v19.sq >/dev/null 2>&1
B=/tmp/fwv19
H=$B/www/luci-static/resources/view/athena/index.html
echo VER_1.2.19:; grep -o 'AthenaWrt v1.2.19' $H | head -1
echo HERO_DNV:; grep -c 'id="dnV"' $H
echo HERO_SPARK:; grep -c 'id="sparkSvg"' $H
echo KPI_GRID:; grep -c 'id="kpisGrid"' $H
echo TOPO2:; grep -c 'class="topo2"' $H
echo WAN_IP_FE:; grep -c 'd.wan.ip' $H
echo SPARK_FN:; grep -c 'function drawSpark' $H
echo PKG_VER:; grep -r 'v1.2.19' $B/usr/lib/lua/luci 2>/dev/null | head -1
echo SIZE:; ls -l $F | awk '{print $5}'
'''
i, o, e = c.exec_command(cmd, timeout=300)
out = o.read().decode("utf-8", "replace")
c.close()
print(out)
