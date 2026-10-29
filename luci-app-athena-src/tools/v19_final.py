import paramiko, os, hashlib, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out_dir = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
os.makedirs(out_dir, exist_ok=True)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
s = c.open_sftp()
base = "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-{t}.bin"
for t in ["sysupgrade", "factory"]:
    remote = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx/" + base.format(t=t)
    local = os.path.join(out_dir, "AthenaWrt-v1.2.19-jdcloud_re-cs-02-{}.bin".format(t))
    s.get(remote, local)
    h = hashlib.sha256(open(local, "rb").read()).hexdigest()
    print("OK", os.path.basename(local), os.path.getsize(local), h)
s.close(); c.close()
