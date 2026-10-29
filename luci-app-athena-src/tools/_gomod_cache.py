import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
cmds = [
    ("GO_MOD_CACHE_DIR 定义",
     "grep -n 'GO_MOD_CACHE_DIR' /home/vboxuser/jdc-build/immortalwrt_ipq-main/feeds/packages/lang/golang/golang-values.mk | head -5"),
    ("已有 cache 目录",
     "ls -d /home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/host/go* 2>/dev/null; ls -d /home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/host/gopath* 2>/dev/null"),
    ("已下载模块样例",
     "find /home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir -type d -path '*cache/download/github.com*' 2>/dev/null | head -3"),
]
for name, cmd in cmds:
    i, o, e = c.exec_command(cmd, timeout=30)
    out.append("=== %s ===\n%s" % (name, o.read().decode("utf-8", "replace").strip()[:1200]))
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomod_cache.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
