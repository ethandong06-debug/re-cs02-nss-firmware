# -*- coding: utf-8 -*-
"""v1.2.40 热修自检：把 apps.sh 改成可离线跑的测试版，传到编译 VM 用 BusyBox/awk 实测匹配逻辑。"""
import io, os, re, sys
import paramiko

HOST, PORT, USER, PWD = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"

apps = io.open(BASE + r"\root\usr\libexec\athena-apps.sh", encoding="utf-8").read()

# 1) 路径改到 /tmp/at
test = apps
test = test.replace("JSON=/usr/share/athena/oaf-app-map.json", "JSON=/tmp/at/oaf-app-map.json")
test = test.replace("MAP_TMP=/tmp/athena-oaf-map.tsv", "MAP_TMP=/tmp/at/oaf.tsv")
test = test.replace('RULES=/tmp/athena-app-rules-v2.tsv', 'RULES=/tmp/at/rules.tsv')

# 2) 截掉末尾的 case 分发
cut = test.index('case "$1" in')
test = test[:cut]

# 3) 取出 emit 里的 awk 主体，原样复用
m = re.search(r"awk -F'\\t' '\n(.*?)\n\t' \"\$RULES\" -", test, re.S)
assert m, "找不到 emit awk 主体"
awk_body = m.group(1)

harness = '''
build_rules
echo "RULES_LINES=$(wc -l < "$RULES")"
echo "MAP_LINES=$(wc -l < "$MAP_TMP")"
echo "--- rules sample ---"
head -n 3 "$RULES"
grep -c "\\t1$" "$RULES" | sed "s/^/prio1=/"
grep -c "\\t2$" "$RULES" | sed "s/^/prio2=/"
cat > /tmp/at/log.tsv <<'EOF'
www.google.com\t192.168.10.5
google.com\t192.168.10.6
www.apple.com\t192.168.10.7
163.com\t192.168.10.8
music.163.com\t192.168.10.9
weibo.com\t192.168.10.10
amazon.com\t192.168.10.11
youtube.com\t192.168.10.12
qq.com\t192.168.10.13
zhihu.com\t192.168.10.14
unknown-nothing-zzz.com\t192.168.10.15
music.163.com\t192.168.10.16
www.taobao.com\t192.168.10.17
twitch.tv\t192.168.10.18
netflix.com\t192.168.10.19
www.bilibili.com\t192.168.10.20
spotify.com\t192.168.10.21
microsoft.com\t192.168.10.22
line.me\t192.168.10.23
mail.google.com\t192.168.10.24
EOF
sed -i 's/\\\\t/\\t/g' /tmp/at/log.tsv
echo "--- RESULT(id|name|clients) ---"
awk -F'\\t' '
''' + awk_body + '''
' "$RULES" /tmp/at/log.tsv | sort -u
'''

out = test + harness
io.open(os.environ["TEMP"] + r"\apps_test.sh", "w", encoding="utf-8", newline="\n").write(out)

# 4) 上传 + 执行
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=20)
sftp = c.open_sftp()
c.exec_command("rm -rf /tmp/at && mkdir -p /tmp/at")[1].channel.recv_exit_status()
sftp.put(os.environ["TEMP"] + r"\apps_test.sh", "/tmp/at/apps_test.sh")
sftp.put(BASE + r"\root\usr\share\athena\oaf-app-map.json", "/tmp/at/oaf-app-map.json")
for name, path in (
    ("apps.sh", BASE + r"\root\usr\libexec\athena-apps.sh"),
    ("backup.sh", BASE + r"\root\usr\libexec\athena-backup.sh"),
    ("upgrade.sh", BASE + r"\root\usr\libexec\athena-upgrade.sh"),
    ("uhttpd-defaults", BASE + r"\root\etc\uci-defaults\99-athena-uhttpd-timeout"),
):
    sftp.put(path, "/tmp/at/" + name)
sftp.close()

cmds = [
    "cd /tmp/at && for f in apps.sh backup.sh upgrade.sh uhttpd-defaults; do sh -n $f && echo \"SYNTAX_OK $f\"; done",
    "sh /tmp/at/apps_test.sh",
]
for cmd in cmds:
    stdin, stdout, stderr = c.exec_command(cmd, timeout=180)
    print("$", cmd)
    print(stdout.read().decode("utf-8", "replace"))
    e = stderr.read().decode("utf-8", "replace")
    if e.strip():
        print("[stderr]", e)
c.close()
