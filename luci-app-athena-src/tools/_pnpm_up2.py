import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"

out = []
i, o, e = c.exec_command("grep -E 'PKG_SOURCE|PKG_HASH|PKG_VERSION' " + base + "/feeds/packages/lang/node/node-pnpm/Makefile")
out.append("=== node-pnpm Makefile ===\n" + o.read().decode("utf-8", "replace").strip())

sftp = c.open_sftp()
src = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_pnpm-11.22.0.tgz"
dst = base + "/dl/pnpm-11.22.0.tgz"
sftp.put(src, dst)
sftp.close()
i, o, e = c.exec_command("ls -la " + dst + "; sha256sum " + dst)
out.append("=== 上传后 ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_pnpm_up_result.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
