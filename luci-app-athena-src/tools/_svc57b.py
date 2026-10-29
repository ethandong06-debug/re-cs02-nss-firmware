# -*- coding: utf-8 -*-
"""补一个 /etc/init.d/ddnsto，让它进入动态服务列表，再验证 controller 兜底。"""
import paramiko

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


s = c.open_sftp()
s.put(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services.uc", "/tmp/svc.uc")
s.close()

print(run("echo vboxuser | sudo -S touch /etc/init.d/ddnsto; echo vboxuser | sudo -S chmod +x /etc/init.d/ddnsto; ls -l /etc/init.d/ddnsto"))
print("== ddnsto 完整段 ==")
print(run(UC + " /tmp/svc.uc list 2>&1 | grep -o '\"id\":\"ddnsto\"[^}]*'"))
print("== 语法检查：list 整体 ==")
print(run(UC + " /tmp/svc.uc list 2>&1 | head -c 100; echo; " + UC + " /tmp/svc.uc list >/dev/null 2>&1; echo rc=$?"))
c.close()
