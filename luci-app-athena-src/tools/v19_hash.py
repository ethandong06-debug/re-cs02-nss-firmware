import hashlib, io, os, sys, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
files = ["AthenaWrt-v1.2.19-jdcloud_re-cs-02-sysupgrade.bin", "AthenaWrt-v1.2.19-jdcloud_re-cs-02-factory.bin"]
res = []
for n in files:
    p = os.path.join(out, n)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    s = os.path.getsize(p)
    res.append((n, s, h))
    print("OK", n, s, h)

lines = []
lines.append("AthenaWrt v1.2.19 固件交付（JDCloud RE-CS-02 / IPQ6018 / ImmortalWrt SNAPSHOT r1-20261017）")
lines.append("生成时间: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
lines.append("")
lines.append("【本版内容】首页质感重构（用户确认的 v2 设计稿正式集成）：")
lines.append(" 1. 网速 Hero：下载/上传双数字 + 60 秒双曲线 SVG 实时走势（渐变面积 + 峰值实时显示）")
lines.append(" 2. 设备状态 KPI 排：CPU/内存环形进度（含 10 点迷你历史柱）+ 在线设备/WiFi/存储/运行时长图标卡，支持自定义排序（原有排序弹窗复用）")
lines.append(" 3. 网络信息带：网络模式 / WAN 协议 / 外网 IP（新增接收后端 wan.ip 字段）/ 各频段 WiFi 状态 / 固件版本")
lines.append(" 4. 家庭网络拓扑 v2：互联网→光猫→雅典娜→LAN/WiFi/IPTV 纵向示意，接入真实在线设备数与 VLAN 配置")
lines.append(" 5. 登录页版本标记同步为 v1.2.19")
lines.append("")
for n, s, h in res:
    lines.append("SHA256 (%s): %s" % (n, h))
    lines.append("大小: %d 字节 (%d MB)" % (s, s // 1024 // 1024))
    lines.append("")
lines.append("刷机说明: 保留配置升级用 sysupgrade；全新刷入用 factory。")
open(os.path.join(out, "version.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("VERSION_TXT_WRITTEN")
