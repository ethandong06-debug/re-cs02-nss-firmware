import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
cmds = [
    ("go.mod 头部", "head -6 /home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.mod"),
    ("go.mod go 指令", "grep -nE '^go ' /home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.mod"),
]
for name, cmd in cmds:
    i, o, e = c.exec_command(cmd, timeout=20)
    out.append("=== %s ===\n%s" % (name, o.read().decode("utf-8", "replace").strip()[:800]))
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomod_gover.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
