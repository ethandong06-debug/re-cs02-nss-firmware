import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
cmds = [
    ("Go 模块缓存路径",
     "find /home/vboxuser/jdc-build/immortalwrt_ipq-main -type d -path '*pkg/mod*' 2>/dev/null | head -5; "
     "grep -rE 'GOMODCACHE|GO_GOMODCACHE' /home/vboxuser/jdc-build/immortalwrt_ipq-main/feeds/packages/lang/golang/*.mk 2>/dev/null | head -5"),
    ("filebrowser go.mod require",
     "grep -E '^\\s+[a-z]' /home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.mod | head -80"),
    ("go.sum 模块数",
     "wc -l /home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.sum"),
]
for name, cmd in cmds:
    i, o, e = c.exec_command(cmd, timeout=30)
    out.append("=== %s ===\n%s" % (name, o.read().decode("utf-8", "replace").strip()[:2500]))
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomod_info.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
