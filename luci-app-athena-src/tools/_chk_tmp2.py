import paramiko, io, sys, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-2000:]))
    run("ps aux | grep -E 'make -j6|go build|compile' | grep -v grep | head -5", "make 进程")
    run("ls -la %s/build_dir/target-aarch64_cortex-a53_musl/ 2>/dev/null | grep -i filebrowser | head -3" % base, "filebrowser 目录")
    run("ls -lt %s/bin/targets/qualcommax/ipq60xx/ 2>/dev/null | head -6" % base, "固件输出")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13.txt","w",encoding="utf-8").write("\n".join(out))
