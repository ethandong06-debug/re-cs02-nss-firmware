import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
def run(cmd, name, t=30):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    out = stdout.read().decode("utf-8", "replace")
    print("=== %s ===" % name)
    print((out.strip() or "(空)")[-2000:])
run("ps aux | grep -E 'make -j6|compile' | grep -v grep | head -5", "make 进程")
run("ls -la %s/build_dir/target-aarch64_cortex-a53_musl/filebrowser-go* 2>/dev/null | head -3; ls %s/dl/ 2>/dev/null | grep -i filebrowser" % (base, base), "filebrowser 编译产物")
run("ls -lt %s/bin/targets/qualcommax/ipq60xx/ 2>/dev/null | head -6" % base, "固件输出目录")
c.close()
