import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=120):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1500:]))
    run("pkill -f 'make -j6' ; pkill -f 'download.pl.*node' ; sleep 2; ps aux | grep -E 'make -j6|download.pl' | grep -v grep | wc -l", "杀掉卡住的编译", 30)
    run("cd %s && sed -i 's/^CONFIG_PACKAGE_luci-app-filebrowser-go=y/# CONFIG_PACKAGE_luci-app-filebrowser-go is not set/' .config && grep -n 'CONFIG_PACKAGE_luci-app-filebrowser-go' .config" % base, "config 还原", 30)
    run("cd %s && make defconfig 2>&1 | tail -2" % base, "defconfig", 180)
    run("cd %s && rm -f dl/node-v22.23.2-linux-x64.tar.gz.dl dl/node-v22.23.2-linux-x64.tar.gz.hash; grep -c 'CONFIG_PACKAGE_luci-app-athena=y' .config" % base, "清理残留+确认 athena 选中", 30)
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_kill13.txt","w",encoding="utf-8").write("\n".join(out))
