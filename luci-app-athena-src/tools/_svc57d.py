# -*- coding: utf-8 -*-
"""重传修好的 services.uc，用 timeout 跑，确认 ddnsto 拿到原生 path。"""
import paramiko

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


s = c.open_sftp()
s.put(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-services.uc", "/tmp/svc.uc")
s.close()

print("== 15s 超时跑 ==")
print(run("timeout 15 " + UC + " /tmp/svc.uc list > /tmp/svc.out 2>/tmp/svc.err; echo rc=$?"))
print("== ddnsto 段 ==")
print(run("grep -o '\"id\":\"ddnsto\"[^}]*' /tmp/svc.out"))
print("== stderr ==")
print(run("head -c 300 /tmp/svc.err"))
c.close()
