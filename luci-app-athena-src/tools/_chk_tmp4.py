import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1200:]))
    run("ps aux | grep -E 'make -j6|node|filebrowser|go build' | grep -v grep | head -8", "当前编译任务")
    run("ls -t %s/build_dir/target-aarch64_cortex-a53_musl/ | head -8" % base, "最新编译目录")
    run("ls -lt %s/bin/targets/qualcommax/ipq60xx/*.bin 2>/dev/null | head -2" % base, "固件时间")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13c.txt","w",encoding="utf-8").write("\n".join(out))
