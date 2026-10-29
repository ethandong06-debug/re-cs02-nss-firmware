import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
cmds = [
    (".config 里 filebrowser 相关", "grep -n 'filebrowser' /home/vboxuser/jdc-build/immortalwrt_ipq-main/.config"),
    (".config 里 node 相关", "grep -nE 'CONFIG_PACKAGE_(node|node-pnpm)=' /home/vboxuser/jdc-build/immortalwrt_ipq-main/.config"),
    ("feeds symlink", "ls /home/vboxuser/jdc-build/immortalwrt_ipq-main/package/feeds/luci/applications/ | grep -i filebrowser"),
]
for name, cmd in cmds:
    i, o, e = c.exec_command(cmd, timeout=20)
    out.append("=== %s ===\n%s" % (name, (o.read().decode("utf-8", "replace").strip() or "(空)")[:1200]))
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_fb_config.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
