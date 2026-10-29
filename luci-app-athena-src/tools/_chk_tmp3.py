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
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1500:]))
    run("ps aux | grep -E 'make -j6' | grep -v grep | wc -l", "make 进程数")
    run("date '+%H:%M:%S'", "VM 当前时间")
    run("ls -lt %s/bin/targets/qualcommax/ipq60xx/*.bin 2>/dev/null | head -3" % base, "固件文件时间")
    run("ls -d %s/build_dir/target-aarch64_cortex-a53_musl/filebrowser* 2>/dev/null; ls -la %s/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax/usr/bin/filebrowser* 2>/dev/null" % (base, base), "filebrowser 产物")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13b.txt","w",encoding="utf-8").write("\n".join(out))
