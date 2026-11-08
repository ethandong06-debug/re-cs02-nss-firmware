#!/usr/bin/env python3
"""Run static checks for the V1.0 source and the packaged LuCI frontend."""
from __future__ import annotations
import re, subprocess, sys, tempfile
from pathlib import Path

def run(cmd):
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode:
        print(p.stdout)
        raise SystemExit(p.returncode)

def main():
    if len(sys.argv)!=6:
        print("usage: check_frontend.py prototype.html index.html gateway.sh acl.json Makefile",file=sys.stderr)
        return 2
    prototype,index,gateway,acl,makefile=map(Path,sys.argv[1:])
    run([sys.executable,str(Path(__file__).with_name("check_v1_menu.py")),str(prototype)])
    html=index.read_text(encoding="utf-8")
    scripts=re.findall(r"<script\b[^>]*>([\s\S]*?)</script>",html,re.I)
    if not scripts:
        raise SystemExit("FAIL: frontend contains no inline JavaScript")
    with tempfile.TemporaryDirectory() as td:
        for i,script in enumerate(scripts):
            f=Path(td)/f"inline-{i}.js"
            f.write_text(script,encoding="utf-8")
            run(["node","--check",str(f)])
    run(["sh","-n",str(gateway)])
    run([sys.executable,str(Path(__file__).with_name("check_rpc_wiring.py")),str(index),str(gateway),str(acl),str(makefile)])
    print(f"前端静态检查通过：{len(scripts)} 个内联 JS 块语法正确；网关 shell 语法正确；V1.0 菜单基准未变化。")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
