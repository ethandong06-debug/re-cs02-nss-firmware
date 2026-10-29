# -*- coding: utf-8 -*-
"""v1.2.49：available 走 APKINDEX 的等价性、缓存命中、冷/热耗时、路由。"""
import paramiko, os, io, time

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
TMP = os.environ.get("TEMP", ".")

REPO_A = [("libc", "1.2.5-r4"), ("luci-app-athena", "1.2.49-r1"), ("kmod-nss-drv", "12.0.0~2024-01-01"),
          ("base-files", "1655~r1"), ("curl", "8.9.1-r1")]
REPO_B = [("curl", "8.9.1-r1"), ("libc", "1.2.5-r4"), ("wget-ssl", "1.24.5-r1"),
          ("ttyd", "1.7.7-r1"), ("zonename", "1.0-r0")]


def mkindex(repo):
    lines = []
    for n, v in repo:
        lines += ["C:Q1%s=" % ("A" * 20), "P:" + n, "V:" + v,
                  "A:aarch64_cortex-a53", "S:1000", "I:2000", "T:" + n, "D:libc", ""]
    return "\n".join(lines) + "\n"


ref = sorted(set([n for n, _ in REPO_A] + [n for n, _ in REPO_B]))
first_ver = {}
for n, v in REPO_A + REPO_B:
    if n not in first_ver:
        first_ver[n] = v

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


run("rm -rf /tmp/pkav; mkdir -p /tmp/pkav/a /tmp/pkav/b")
s = c.open_sftp()
for tag, repo in (("a", REPO_A), ("b", REPO_B)):
    p = os.path.join(TMP, "idx_%s.txt" % tag)
    io.open(p, "w", encoding="utf-8", newline="\n").write(mkindex(repo))
    s.put(p, "/tmp/pkav/%s/APKINDEX" % tag)
s.close()
run("cd /tmp/pkav/a && tar -czf /tmp/pkav/APKINDEX.aaaa1111.tar.gz APKINDEX && cd /tmp/pkav/b && tar -czf /tmp/pkav/APKINDEX.bbbb2222.tar.gz APKINDEX")

s = c.open_sftp()
s.put(os.path.join(LOCAL, "athena-packages.uc"), "/tmp/pkav/uc_raw.uc")
s.put(os.path.join(LOCAL, "athena-packages.sh"), "/tmp/pkav/wrap_raw.sh")
s.close()

SED = ("sed \"s#/lib/apk/db/installed#/tmp/pk/db/installed#; s#/var/cache/apk#/tmp/pkav#; "
       "s#/tmp/athena-pkg-available.json#/tmp/pkav/cache.json#; s#/tmp/athena-pkg-av.stamp#/tmp/pkav/stamp#\" ")
run(SED + "/tmp/pkav/uc_raw.uc > /tmp/pkav/uc.uc; "
    "sed \"s#/usr/libexec/athena-packages.uc#/tmp/pkav/uc.uc#; s#/usr/libexec/athena-packages-legacy.sh#/tmp/pkw/stub.sh#; s#/usr/bin/ucode#%s#\" /tmp/pkav/wrap_raw.sh > /tmp/pkav/wrap.sh; "
    "chmod 755 /tmp/pkav/wrap.sh; ls -l /tmp/pkav" % U)

out = []
out.append("== 冷跑 available（含 tar 解压 + 解析 + 写缓存）==")
out.append(run("rm -f /tmp/pkav/cache.json /tmp/pkav/stamp; time sh /tmp/pkav/wrap.sh list available"))
out.append("== 热跑（缓存命中）==")
out.append(run("time sh /tmp/pkav/wrap.sh list available > /tmp/pkav/w2.json; cmp -s /tmp/pkav/w2.json /tmp/pkav/cache.json && echo '热跑输出与缓存一致'"))
out.append("== 缓存过期后重建（TTL 1800s 之外）==")
out.append(run("printf '0' > /tmp/pkav/stamp; time sh /tmp/pkav/wrap.sh list available > /tmp/pkav/w3.json; cmp -s /tmp/pkav/w3.json /tmp/pkav/cache.json && echo '重建结果一致'"))
out.append("== installed 未受影响 ==")
out.append(run("time sh /tmp/pkav/wrap.sh list installed | head -c 120; echo"))
out.append("== 索引缺失时回退 legacy ==")
out.append(run("mv /tmp/pkav/APKINDEX.aaaa1111.tar.gz /tmp/pkav/x1; mv /tmp/pkav/APKINDEX.bbbb2222.tar.gz /tmp/pkav/x2; rm -f /tmp/pkav/cache.json /tmp/pkav/stamp; sh /tmp/pkav/wrap.sh list available | head -c 120; echo; mv /tmp/pkav/x1 /tmp/pkav/APKINDEX.aaaa1111.tar.gz; mv /tmp/pkav/x2 /tmp/pkav/APKINDEX.bbbb2222.tar.gz"))
out.append("== 带关键字仍走 legacy ==")
out.append(run("sh /tmp/pkav/wrap.sh list available wget | head -c 120; echo"))

io.open(os.path.join(TMP, "pkg49.txt"), "w", encoding="utf-8").write("\n".join(out))
io.open(os.path.join(TMP, "pk49_ref.txt"), "w", encoding="utf-8").write(
    "\n".join("%s | %s" % (n, first_ver[n]) for n in ref))
c.close()
print("done")
