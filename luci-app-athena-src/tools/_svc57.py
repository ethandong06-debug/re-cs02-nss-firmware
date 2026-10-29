# -*- coding: utf-8 -*-
"""VM 上造一个假的 /usr/lib/lua/luci/controller/ddnsto.lua，验证 detect_controller_path 能拼出原生路径。"""
import io, paramiko

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


ctrl = '''module("luci.controller.ddnsto", package.seeall)

function index()
	if not nixio.fs.access("/etc/config/ddnsto") then
		return
	end
	entry({"admin","services","ddnsto"}, cbi("ddnsto"), _("ddnsto"), 60).dependent = false
end
'''
s = c.open_sftp()
s.put(BASE + r"\athena-services.uc", "/tmp/svc.uc")
s.close()
s = c.open_sftp()
s.putfo(io.BytesIO(ctrl.encode("utf-8")), "/tmp/ddnsto.lua")
s.close()

print("== 装假控制器 ==")
print(run("echo vboxuser | sudo -S mkdir -p /usr/lib/lua/luci/controller; echo vboxuser | sudo -S cp /tmp/ddnsto.lua /usr/lib/lua/luci/controller/ddnsto.lua; ls -l /usr/lib/lua/luci/controller/"))

print("== services list 里 ddnsto 这一条 ==")
print(run(UC + " /tmp/svc.uc list 2>&1 | tr ',' '\\n' | grep -A1 -B1 ddnsto | head -20"))
print("---- 完整 ddnsto 段 ----")
print(run(UC + " /tmp/svc.uc list 2>&1 | grep -o '\"id\":\"ddnsto\"[^}]*'"))

c.close()
