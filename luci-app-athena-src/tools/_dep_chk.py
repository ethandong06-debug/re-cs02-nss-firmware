import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"

cmds = [
    ("node 相关 y 包",
     "grep -E 'CONFIG_PACKAGE_(node|node-pnpm|luci-app-filebrowser|luci-app-filebrowser-go|smartdns|sub-web|frp|cloudreve|luci-app-sub-web|luci-app-smartdns)=' " + base + "/.config | grep '=y' || echo 无"),
    ("引用 node host 的 feeds 包",
     "grep -rln 'node-pnpm/host\\|node/host' " + base + "/feeds/luci/applications/ " + base + "/feeds/packages/net/ 2>/dev/null | head -8"),
    ("Makefile 引用 pnpm 的包",
     "grep -rln 'pnpm' " + base + "/feeds/luci/applications/ 2>/dev/null | head -6"),
]
for name, cmd in cmds:
    i, o, e = c.exec_command(cmd, timeout=30)
    print("=== %s ===" % name)
    print(o.read().decode("utf-8", "replace").strip()[:2000] or "(空)")
c.close()
