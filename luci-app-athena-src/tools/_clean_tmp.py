import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=60):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1800:]))
    run("pkill -9 -f 'node-v22.23.2' ; pkill -9 -f 'make -w -r world' ; pkill -9 -f 'make -j6' ; pkill -9 -f 'curl.real.*node' ; pkill -9 -f 'download.pl' ; sleep 2 ; ps aux | grep -E 'make|node-v22|download.pl|curl.real' | grep -v grep | wc -l", "杀掉全部残留编译/下载进程", 30)
    run("grep -rln 'node/host' %s/feeds/luci/applications/ %s/feeds/packages/net/ 2>/dev/null | head -5" % (base, base), "谁依赖 node host")
    run("ls %s/package/feeds/luci/applications/ 2>/dev/null | grep -i filebrowser; ls %s/package/feeds/packages/ 2>/dev/null | grep -i node | head -3" % (base, base), "feeds symlink 现状")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_clean13.txt","w",encoding="utf-8").write("\n".join(out))
