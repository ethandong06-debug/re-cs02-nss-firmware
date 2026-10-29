#!/usr/bin/env python3
"""验证 rootfs 脚本齐全 + 下载新固件到本地 output。"""
import paramiko, os

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
REMOTE_BIN = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx"
LOCAL_DIR = r"C:/Users/Administrator/WorkBuddy/2026-10-22-23-23-11/athena-openwrt/output"

FILES = [
    "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
    "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin",
    "sha256sums",
    "immortalwrt-qualcommax-ipq60xx.manifest",
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20, banner_timeout=20, auth_timeout=20)

# 1) 验证 staging root 里 20 个脚本齐全
cmd = (
    "root=~/jdc-build/immortalwrt_ipq-main/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax;"
    "echo '=== libexec 脚本数 ==='; ls $root/usr/libexec/athena-*.sh 2>/dev/null | wc -l;"
    "echo '=== 新脚本存在性 ==='; "
    "for s in wireless speedtest matrix theme led; do "
    "  [ -f $root/usr/libexec/athena-$s.sh ] && echo \"OK athena-$s.sh\" || echo \"MISS athena-$s.sh\"; "
    "done;"
    "echo '=== 固件清单 ==='; ls -la ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx/*.bin"
)
i, o, e = c.exec_command(cmd, timeout=60)
print(o.read().decode("utf-8", "replace"))
err = e.read().decode("utf-8", "replace")
if err.strip():
    print("[stderr]", err)

# 2) 下载固件
os.makedirs(LOCAL_DIR, exist_ok=True)
sftp = c.open_sftp()
for f in FILES:
    remote = REMOTE_BIN + "/" + f
    local = os.path.join(LOCAL_DIR, f)
    try:
        sftp.get(remote, local)
        print(f"OK  {f}  ({os.path.getsize(local)} bytes)")
    except Exception as ex:
        print(f"SKIP {f}: {ex}")
sftp.close()
c.close()
print("下载完成 ->", LOCAL_DIR)
