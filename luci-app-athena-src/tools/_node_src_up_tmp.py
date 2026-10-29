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
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1200:]))
    # 先杀当前 make（避免与上传竞争）
    run("pkill -9 -f 'make -j6' ; pkill -9 -f 'download.pl.*node-v22.23.2.tar.gz' ; pkill -9 -f 'curl.real.*node' ; sleep 1 ; echo killed", "杀掉卡住的 make", 30)
    # 上传源码包
    sftp = c.open_sftp()
    src = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node-src.tar.gz"
    dst = base + "/dl/node-v22.23.2.tar.gz"
    sftp.put(src, dst)
    sftp.close()
    out.append("=== 上传 ===")
    run("ls -la %s/dl/node-v22.23.2.tar.gz" % base, "源码包大小", 30)
    run("echo 'cdaed46fcd8923a55974b7bbc7caaadeaaf7aed60cc137e59837b72f575ef641  %s/dl/node-v22.23.2.tar.gz' | sha256sum -c -" % base, "校验", 30)
    run("rm -f %s/dl/node-v22.23.2.tar.gz.dl %s/dl/node-v22.23.2.tar.gz.hash; ps aux | grep -E 'make|download.pl|curl.real' | grep -v grep | wc -l" % (base, base), "清理残留", 30)
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node_src_up.txt","w",encoding="utf-8").write("\n".join(out))
