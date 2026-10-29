# -*- coding: utf-8 -*-
import os, json, sys

ROOT = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"
BATCH = sys.argv[1]

SETS = {
 "root": [
  "frontend/luci-app-athena/root/usr/libexec/athena-apps.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-backup.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-client.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-diag.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-disk.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-led.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-log.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-logcap.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-matrix.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-mode.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-packages.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-packages.uc",
  "frontend/luci-app-athena/root/usr/libexec/athena-parent.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-passwd.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-prefs.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-rate.uc",
  "frontend/luci-app-athena/root/usr/libexec/athena-reboot.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-reset.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-resources.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-resources.uc",
  "frontend/luci-app-athena/root/usr/libexec/athena-scan.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-services.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-services.uc",
  "frontend/luci-app-athena/root/usr/libexec/athena-single.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-speedtest.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-status.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-status.uc",
  "frontend/luci-app-athena/root/usr/libexec/athena-theme.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-ui.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-upgrade.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-wanip.sh",
  "frontend/luci-app-athena/root/usr/libexec/athena-wireless.sh",
  "frontend/luci-app-athena/root/usr/share/rpcd/acl.d/luci-app-athena.json",
  "frontend/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json",
  "frontend/luci-app-athena/root/usr/share/athena/oaf-app-map.json",
 ],
 "etc": [
  "frontend/luci-app-athena/root/etc/config/athena",
  "frontend/luci-app-athena/root/etc/init.d/athena-boot",
  "frontend/luci-app-athena/root/etc/init.d/athena-netcheck",
  "frontend/luci-app-athena/root/etc/init.d/athena-ui",
  "frontend/luci-app-athena/root/etc/init.d/athena-vlan-pre",
  "frontend/luci-app-athena/root/etc/init.d/filebrowser",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-athena-apps-dns.sh",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-athena-custom.sh",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-athena-defaults",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-athena-filebrowser.sh",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-athena-uhttpd-timeout",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-zz-athena-redirect",
  "frontend/luci-app-athena/root/etc/uci-defaults/99-zz-athena-wifi.sh",
 ],
 "web": [
  "frontend/luci-app-athena/htdocs/luci-static/resources/view/athena/index.html",
  "frontend/luci-app-athena/htdocs/luci-static/resources/view/athena/index.js",
  "frontend/luci-app-athena/Makefile",
  "frontend/luci-app-athena/po/zh_Hans/athena.po",
  "frontend/rpcd-mod-athena/src/athena_stats.c",
 ],
 "docs": [
  "README.md", "PROGRESS-v1.2.28.md",
  "docs/刷机教程.md", "docs/前端定制方案.md", "docs/固件特性.md", "docs/底层适配方案.md",
  "configs/brand.append", "configs/packages.list",
  "files/etc/sysctl.d/99-athena-tune.conf",
  "files/etc/uci-defaults/99-athena-custom.sh",
  "files/etc/uci-defaults/99-zz-athena-wifi.sh",
  "scripts/build.sh", "scripts/setup.sh", "scripts/mirror-curl.sh",
  "target-files/ipq60xx-base-files/etc/board.d/03_defaults",
 ],
}

files = []
for rel in SETS[BATCH]:
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    with open(p, "rb") as f:
        raw = f.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        continue
    files.append({"path": rel, "content": content})

out = json.dumps(files, ensure_ascii=False)
open(sys.argv[2], "w", encoding="utf-8").write(out)
print(BATCH, len(files), "files,", len(out)//1024, "KB json ->", sys.argv[2])
