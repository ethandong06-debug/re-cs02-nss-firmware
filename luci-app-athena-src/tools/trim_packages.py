#!/usr/bin/env python3
"""在编译 VM 上精简 jdc-build 固件的 .config：删除 Docker/Samba/代理/Ruby/Perl/rclone/分区工具等无用包。
只改 .config，不触发任何编译。"""
import re, sys
import paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
CONFIG = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/.config"

# 精确包名（不含 CONFIG_PACKAGE_ 前缀）
EXACT = """docker dockerd containerd docker-compose runc tini luci-app-dockerman luci-i18n-dockerman-zh-cn
samba4-libs samba4-server luci-app-samba4 luci-i18n-samba4-zh-cn wsdd2
luci-app-openclash v2ray-geoip v2ray-geosite geoview iptasn iptables-mod-asn
ruby ruby-bigdecimal ruby-date ruby-digest ruby-enc ruby-pstore ruby-psych ruby-stringio ruby-yaml
perl perlbase-base perlbase-bytes perlbase-config perlbase-dynaloader perlbase-errno perlbase-essential
perlbase-fcntl perlbase-getopt perlbase-io perlbase-list perlbase-posix perlbase-scalar perlbase-selectsaver
perlbase-socket perlbase-symbol perlbase-tie perlbase-xsloader perl-net-cidr-lite perl-text-csv_xs
cfdisk cgdisk fdisk sfdisk sgdisk gdisk losetup resize2fs tune2fs btrfs-progs f2fs-tools mkf2fs f2fsck
ntfs3-mount e2fsprogs blkid block-mount automount
knot-resolver_dnstap avahi-dbus-daemon
kmod-fs-btrfs kmod-fs-exfat kmod-fs-f2fs kmod-fs-ntfs3 kmod-lib-raid6 kmod-lib-xor""".split()

# 前缀匹配（passwall / rclone 的 INCLUDE 子项）
PREFIX = ["luci-app-passwall_INCLUDE", "luci-app-rclone_INCLUDE"]

REMOTE = '''python3 - <<'PYEOF'
import re
pkg = set({EXACT!r})
prefix = {PREFIX!r}

lines = open({CONFIG!r}).read().splitlines()
out = []
removed = []
for ln in lines:
    m = re.match(r"^(# )?CONFIG_PACKAGE_([^=]+)=y$", ln)
    if m:
        name = m.group(2)
        if name in pkg or any(name.startswith(p) for p in prefix):
            out.append("# CONFIG_PACKAGE_" + name + " is not set")
            removed.append(name)
            continue
    out.append(ln)
open({CONFIG!r}, "w").write("\\n".join(out) + "\\n")
print("删除包数: %d" % len(removed))
for r in removed:
    print("  -", r)
PYEOF
'''.format(EXACT=EXACT, PREFIX=PREFIX, CONFIG=CONFIG)

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=20, banner_timeout=20, auth_timeout=20)
    stdin, stdout, stderr = c.exec_command(REMOTE, timeout=120)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    c.close()
    sys.stdout.write(out)
    if err.strip():
        sys.stderr.write("[stderr]\n" + err)
    sys.exit(code)

if __name__ == "__main__":
    main()
