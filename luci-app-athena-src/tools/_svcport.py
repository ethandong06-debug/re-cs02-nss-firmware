# -*- coding: utf-8 -*-
"""验证 detect_port：把 INITD 常量改到 /tmp/initd 后跑真实 init 脚本样本。"""
import paramiko, io

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services.uc"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

src = io.open(LOCAL, encoding="utf-8").read()
src2 = src.replace("'/etc/init.d'", "'/tmp/initd'")
src2 += ("\nprintf('PORTTEST filebrowser=%d ttyd=%d aria2=%d noport=%d rdlen=%d\\n',"
         " detect_port('filebrowser'), detect_port('ttyd'), detect_port('aria2'), detect_port('noport'),"
         " length(rd('/tmp/initd/filebrowser')));\n")
f = s.open("/tmp/svc_t.uc", "w")
f.write(src2)
f.close()

samples = {
    "filebrowser": '#!/bin/sh /etc/rc.common\nFB_PORT=8081\nstart_service() {\n\tprocd_set_param command /usr/bin/filebrowser -c /etc/filebrowser.db\n}\n',
    "ttyd": '#!/bin/sh /etc/rc.common\nprocd_set_param command /usr/bin/ttyd -p 7681 -i br-lan\n',
    "aria2": '#!/bin/sh /etc/rc.common\n# aria2 rpc\nPORT="6800"\nstart_service() { aria2c --rpc-listen-port=6800; }\n',
    "noport": '#!/bin/sh /etc/rc.common\nstart_service() { /usr/bin/foo --path=/tmp -x; }\n',
}
cmds = ["rm -rf /tmp/initd", "mkdir -p /tmp/initd"]
run(" && ".join(cmds))
for k, v in samples.items():
    p = "/tmp/initd/" + k
    fh = s.open(p, "w")
    fh.write(v)
    fh.close()
    cmds.append("chmod 755 " + p)
s.close()
run(" ; ".join(["chmod 755 /tmp/initd/" + k for k in samples]))

UCODE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
out = [run(UCODE + " /tmp/svc_t.uc 2>&1 | head -c 1200")]
io.open(r"C:\Users\Administrator\AppData\Local\Temp\svcport.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
