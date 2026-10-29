import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    rootfs = base + "/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1500:]))
    run("ls -la %s/www/luci-static/resources/view/athena/index.html %s/www/luci-static/resources/view/athena/index.js 2>/dev/null" % (rootfs, rootfs), "athena 前端安装时间")
    run("ls -la %s/usr/libexec/athena-ui.sh %s/usr/libexec/athena-parent.sh %s/etc/init.d/athena-ui 2>/dev/null" % (rootfs, rootfs, rootfs), "新脚本安装时间")
    run("ls -lt %s/tmp/ 2>/dev/null | head -5" % base, "编译临时产物最新")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13g.txt","w",encoding="utf-8").write("\n".join(out))
