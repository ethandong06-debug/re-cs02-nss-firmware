import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1500:]))
    run("grep -E '^DEPENDS|^LUCI_DEPENDS|DEPENDS' %s/feeds/luci/applications/luci-app-filebrowser-go/Makefile | head -5" % base, "filebrowser-go DEPENDS")
    run("grep -E '^DEPENDS' %s/feeds/luci/applications/luci-app-filebrowser/Makefile | head -5" % base, "filebrowser(旧) DEPENDS")
    run("ls -la %s/dl/node-v22* 2>/dev/null | head -3; echo ---; ls -la %s/dl/ 2>/dev/null | grep -i node | head -5" % (base, base), "node 下载进度")
    run("grep -E 'CONFIG_PACKAGE_node=' %s/.config 2>/dev/null || echo 'node 未选中'" % base, "node 是否已选")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_dep13.txt","w",encoding="utf-8").write("\n".join(out))
