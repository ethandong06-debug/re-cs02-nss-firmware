import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
def run(cmd, name, t=300):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print("=== %s ===" % name)
    print((out.strip() or err.strip() or "(空)")[-2500:])
run("cd %s && sed -i 's/^# CONFIG_PACKAGE_luci-app-filebrowser-go is not set/CONFIG_PACKAGE_luci-app-filebrowser-go=y/' .config && grep -n 'CONFIG_PACKAGE_luci-app-filebrowser-go' .config" % base, "改 .config 为 y", 30)
run("cd %s && make defconfig 2>&1 | tail -3" % base, "make defconfig", 240)
run("cd %s && grep -E 'CONFIG_PACKAGE_(luci-app-filebrowser-go|filebrowser-go)=' .config" % base, "确认选中与依赖", 30)
c.close()
