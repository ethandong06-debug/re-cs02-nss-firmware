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
run("ls %s/feeds/luci/applications/ | grep -i filebrowser; ls %s/feeds/packages/net/ | grep -i filebrowser" % (base, base), "确认 feeds 包存在", 30)
run("cd %s && ./scripts/feeds install luci-app-filebrowser-go 2>&1 | tail -5" % base, "feeds install filebrowser", 120)
run("cd %s && grep -n 'CONFIG_PACKAGE_luci-app-filebrowser-go' .config || echo NOT_IN_CONFIG" % base, ".config 现状", 30)
c.close()
