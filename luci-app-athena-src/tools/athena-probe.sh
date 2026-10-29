#!/bin/sh
# AthenaWrt 真机环境采集脚本（只读，不修改任何配置）
# 用途：校准后端脚本里的推断字段（uci 键、init 名、radio 序号、DSA 端口名、磁盘设备名、点阵屏驱动键等）
# 刷机后 SSH 运行：
#   sh athena-probe.sh > /tmp/athena-probe.txt 2>&1
# 然后把 /tmp/athena-probe.txt 拷回来（或 cat 出来复制全文）发给开发者。

SEP="============================================================"

echo "$SEP"
echo "[0] 系统版本"
echo "$SEP"
cat /etc/openwrt_release 2>/dev/null
cat /etc/os-release 2>/dev/null | head -5
uname -a

echo "$SEP"
echo "[1] 无线 radio / 接口（重点：确认 radio 序号与频段对应）"
echo "$SEP"
uci show wireless 2>/dev/null
echo "--- iw phy ---"
for p in /sys/class/ieee80211/phy*; do
  [ -e "$p" ] || continue
  echo "PHY=$(basename $p) device=$(readlink $p/device 2>/dev/null | xargs basename 2>/dev/null)"
  iw dev 2>/dev/null
done

echo "$SEP"
echo "[2] 网络配置（重点：DSA 端口名、VLAN、bridge）"
echo "$SEP"
uci show network 2>/dev/null
echo "--- /sys/class/net 物理网口 ---"
ls -1 /sys/class/net 2>/dev/null
echo "--- ip -o link ---"
ip -o link show 2>/dev/null
echo "--- bridge vlan show ---"
bridge vlan show 2>/dev/null
echo "--- bridge link show ---"
bridge link show 2>/dev/null

echo "$SEP"
echo "[3] 磁盘与挂载（重点：eMMC/USB 设备名与挂载点）"
echo "$SEP"
block info 2>/dev/null
echo "--- lsblk ---"
lsblk 2>/dev/null
echo "--- 实际挂载 ---"
mount 2>/dev/null | grep -Ev 'proc|sysfs|devpts|tmpfs|overlay|/rom|/dev/root|cgroup|debugfs|securityfs|pstore'

echo "$SEP"
echo "[4] 点阵屏驱动（重点：athena-led 真实 uci 键与 init 名）"
echo "$SEP"
echo "--- uci show athena ---"
uci show athena 2>/dev/null
echo "--- uci show athena-led ---"
uci show athena-led 2>/dev/null
echo "--- uci show led / system.led ---"
uci show system 2>/dev/null | grep -Ei 'led|matrix'
echo "--- init 脚本含 led/athena ---"
ls -1 /etc/init.d/ 2>/dev/null | grep -Ei 'led|athena|matrix'
echo "--- 已装包含 athena/led ---"
opkg list-installed 2>/dev/null | grep -Ei 'athena|led'

echo "$SEP"
echo "[5] 已安装包（重点：ddns/ttyd/fullcone/加速/无线固件/测速等）"
echo "$SEP"
opkg list-installed 2>/dev/null | grep -Ei 'ddns|ttyd|fullcone|nat|athena|led|nss|ecm|offload|ath11k|qcn|iperf|samba|ksmbd|block-mount|usb|fstools|luci-app'

echo "$SEP"
echo "[6] init 脚本全量清单（重点：确认 ddns/ttyd/fullconenat/nss/ecm 的真实名字）"
echo "$SEP"
ls -1 /etc/init.d/ 2>/dev/null

echo "$SEP"
echo "[7] NSS / 硬件加速（重点：真实 init 名与开关）"
echo "$SEP"
ls -1 /etc/init.d/ 2>/dev/null | grep -Ei 'nss|ecm|offload|qca'
echo "--- firewall offload 配置 ---"
uci show firewall 2>/dev/null | grep -Ei 'offload|flow'
echo "--- 已加载 NSS/ECM 内核模块 ---"
lsmod 2>/dev/null | grep -Ei 'nss|ecm|qca'
echo "--- /sys/module 下 nss/ecm ---"
ls -1 /sys/module 2>/dev/null | grep -Ei 'nss|ecm'

echo "$SEP"
echo "[8] 无线固件文件（确认三频固件是否齐全）"
echo "$SEP"
ls -lR /lib/firmware/ath11k 2>/dev/null
ls -lR /lib/firmware/qca 2>/dev/null
ls -1 /lib/firmware 2>/dev/null | grep -Ei 'qcn|ipq|board|ath|bdwlan|qca'
echo "--- board 文件 ---"
find /lib/firmware -name 'board*' -o -name 'bdwlan*' 2>/dev/null

echo "$SEP"
echo "[9] 测速工具可用性（重点：iperf3/curl）"
echo "$SEP"
which iperf3 curl wget 2>/dev/null
opkg list-installed 2>/dev/null | grep -Ei 'iperf|curl|wget'

echo "$SEP"
echo "[10] ubus 可用对象（确认 file/system/network 等）"
echo "$SEP"
ubus list 2>/dev/null

echo "$SEP"
echo "[11] DHCP 客户端租约（确认客户端字段来源）"
echo "$SEP"
cat /tmp/dhcp.leases 2>/dev/null
echo "--- uci show dhcp（前 40 行）---"
uci show dhcp 2>/dev/null | head -40

echo "$SEP"
echo "[12] mtd 分区（只读展示，确认不修改）"
echo "$SEP"
cat /proc/mtd 2>/dev/null

echo "$SEP"
echo "[13] 默认配置文件（确认默认 WiFi/IP/密码是否按预期生效）"
echo "$SEP"
echo "--- /etc/config/network ---"
cat /etc/config/network 2>/dev/null
echo "--- /etc/config/wireless ---"
cat /etc/config/wireless 2>/dev/null

echo "$SEP"
echo "[采集结束] 请把以上全文发回。"
echo "$SEP"
