# -*- coding: utf-8 -*-
"""v1.2.50：多链路解压。验证三条链路都能取到同样的 P:/V: 文本，且输出与 Python 复算一致。"""
import paramiko, os, io

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
TMP = os.environ.get("TEMP", ".")

REPO_A = [("libc", "1.2.5-r4"), ("luci-app-athena", "1.2.50-r1"), ("kmod-nss-drv", "12.0.0~2024-01-01"),
          ("base-files", "1655~r1"), ("curl", "8.9.1-r1"), ("kmod-nls-iso8859-1", "6.18.55-r1")]
REPO_B = [("curl", "8.9.1-r1"), ("libc", "1.2.5-r4"), ("wget-ssl", "1.24.5-r1"),
          ("ttyd", "1.7.7-r1"), ("libusb-1.0-0", "1.0.29-r2")]


def mkindex(repo):
    lines = []
    for n, v in repo:
        lines += ["C:Q1%s=" % ("A" * 20), "P:" + n, "V:" + v,
                  "A:aarch64_cortex-a53", "S:1000", "I:2000", "T:" + n, "D:libc", ""]
    return "\n".join(lines) + "\n"


first = {}
for n, v in REPO_A + REPO_B:
    if n not in first:
        first[n] = v

ref = sorted(first)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


run("rm -rf /tmp/pkav; mkdir -p /tmp/pkav/a /tmp/pkav/b")
s = c.open_sftp()
for tag, repo in (("a", REPO_A), ("b", REPO_B)):
    p = os.path.join(TMP, "i50_%s.txt" % tag)
    io.open(p, "w", encoding="utf-8", newline="\n").write(mkindex(repo))
    s.put(p, "/tmp/pkav/%s/APKINDEX" % tag)
s.close()
# 真实仓库索引里 .tar.gz 内除 APKINDEX 外还有 DESCRIPTION，这里刻意加一个干扰成员
run("cd /tmp/pkav/a && printf 'a fake description file\\nP:wrong\\n' > DESCRIPTION && "
    "tar -czf /tmp/pkav/APKINDEX.aaaa1111.tar.gz DESCRIPTION APKINDEX && "
    "cd /tmp/pkav/b && tar -czf /tmp/pkav/APKINDEX.bbbb2222.tar.gz APKINDEX && ls -l /tmp/pkav/*.tar.gz")

s = c.open_sftp()
s.put(os.path.join(LOCAL, "athena-packages.uc"), "/tmp/pkav/uc_raw.uc")
s.put(os.path.join(LOCAL, "athena-packages.sh"), "/tmp/pkav/wrap_raw.sh")
s.close()

SED = ("sed \"s#/lib/apk/db/installed#/tmp/pk/db/installed#; s#/var/cache/apk#/tmp/pkav#; "
       "s#/tmp/athena-pkg-available.json#/tmp/pkav/cache.json#; s#/tmp/athena-pkg-av.stamp#/tmp/pkav/stamp#\" ")
run(SED + "/tmp/pkav/uc_raw.uc > /tmp/pkav/uc.uc; "
    "sed \"s#/usr/libexec/athena-packages.uc#/tmp/pkav/uc.uc#; s#/usr/libexec/athena-packages-legacy.sh#/tmp/pkw/stub.sh#; s#/usr/bin/ucode#%s#\" /tmp/pkav/wrap_raw.sh > /tmp/pkav/wrap.sh; "
    "chmod 755 /tmp/pkav/wrap.sh" % U)

out = []
out.append("== 链路1 gzip|tar -xO ==")
out.append(run("for f in /tmp/pkav/APKINDEX.*.tar.gz; do gzip -dc \"$f\" 2>/dev/null | tar -xO APKINDEX 2>/dev/null; done | grep -a -E '^(P|V):' | wc -l"))
out.append("== 链路3 gzip|dd skip=1 ==")
out.append(run("for f in /tmp/pkav/APKINDEX.*.tar.gz; do gzip -dc \"$f\" 2>/dev/null | dd bs=512 skip=1 2>/dev/null; done | grep -a -E '^(P|V):' | wc -l"))
out.append("== 链路2 tar -xzO ==")
out.append(run("for f in /tmp/pkav/APKINDEX.*.tar.gz; do tar -xzOf \"$f\" APKINDEX 2>/dev/null; done | grep -a -E '^(P|V):' | wc -l"))
out.append("== 完整冷跑 ==")
out.append(run("rm -f /tmp/pkav/cache.json /tmp/pkav/stamp; time sh /tmp/pkav/wrap.sh list available"))
out.append("== 热跑 ==")
out.append(run("time sh /tmp/pkav/wrap.sh list available > /tmp/pkav/w2.json; cmp -s /tmp/pkav/w2.json /tmp/pkav/cache.json && echo '热跑与缓存一致'"))
out.append("== 索引缺失 -> 回退 legacy ==")
out.append(run("mkdir -p /tmp/pkav/hold && mv /tmp/pkav/APKINDEX.*.tar.gz /tmp/pkav/hold/; rm -f /tmp/pkav/cache.json /tmp/pkav/stamp; sh /tmp/pkav/wrap.sh list available | head -c 80; echo; mv /tmp/pkav/hold/*.tar.gz /tmp/pkav/"))

io.open(os.path.join(TMP, "pkg50.txt"), "w", encoding="utf-8").write("\n".join(out))
io.open(os.path.join(TMP, "pk50_ref.txt"), "w", encoding="utf-8").write(
    "\n".join("%s | %s" % (n, first[n]) for n in ref))
c.close()
print("done")
