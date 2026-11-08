#!/usr/bin/env python3
from __future__ import annotations
import re, subprocess, sys, tempfile
from pathlib import Path

def run(cmd):
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode:
        print(p.stdout); raise SystemExit(p.returncode)

def main():
    if len(sys.argv)!=8:
        print("usage: check_frontend.py prototype.html index.html runtime.js gateway.sh acl.json Makefile wifi-schedule.sh",file=sys.stderr); return 2
    prototype,index,runtime,gateway,acl,makefile,wifi=map(Path,sys.argv[1:])
    menu_check=str(Path(__file__).with_name("check_v1_menu.py"))
    run([sys.executable,menu_check,str(prototype)])
    run([sys.executable,menu_check,str(index)])
    html=index.read_text(encoding="utf-8")
    scripts=re.findall(r"<script\b[^>]*>([\s\S]*?)</script>",html,re.I)
    if not scripts: raise SystemExit("FAIL: no inline scripts")
    with tempfile.TemporaryDirectory() as td:
        for i,script in enumerate(scripts):
            f=Path(td)/("inline-%d.js"%i); f.write_text(script,encoding="utf-8"); run(["node","--check",str(f)])
        run(["node","--check",str(runtime)])
    run(["sh","-n",str(gateway)]); run(["sh","-n",str(wifi)])
    # Syntax-check every shell script that the APK Makefile installs.
    mk=makefile.read_text(encoding="utf-8")
    for rel in re.findall(r"INSTALL_BIN\\s+\\./root/usr/libexec/([^ \\t]+\\.sh)",mk):
        script=gateway.parent/rel
        if not script.is_file():
            raise SystemExit("FAIL: Makefile 安装清单缺少文件："+str(script))
        run(["sh","-n",str(script)])
    run([sys.executable,str(Path(__file__).with_name("check_rpc_wiring.py")),str(index),str(runtime),str(gateway),str(acl),str(makefile)])
    if "forceEnterConsole = function() { toast('已禁用登录绕过" not in html:
        raise SystemExit("FAIL: 前端登录绕过入口未明确禁用")
    if "V.call('backup-restore'" in runtime.read_text(encoding="utf-8"):
        raise SystemExit("FAIL: runtime 不应调用整份配置恢复")
    print("静态检查通过：原型与安装前端菜单一致；JS/runtime 语法、全部已安装 shell 脚本、网关、ACL 和 APK 接线均通过。")
    return 0
if __name__=="__main__": raise SystemExit(main())
