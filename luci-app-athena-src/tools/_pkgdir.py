# -*- coding: utf-8 -*-
import paramiko, io
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
out = []
out.append("== package/feeds 下的目录 ==")
out.append(run("ls %s/package/feeds/" % B))
out.append("== 各处 luci-app-athena 链接 ==")
out.append(run("find %s/package -maxdepth 3 -name 'luci-app-athena' -o -maxdepth 3 -name 'luci-app-athena' 2>/dev/null | head" % B))
out.append(run("ls -l %s/package/feeds/*/luci-app-athena 2>/dev/null" % B))
out.append("== feeds.conf ==")
out.append(run("cat %s/feeds.conf.default 2>/dev/null | head; cat %s/feeds.conf 2>/dev/null | head" % (B, B)))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\pkgdir.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
