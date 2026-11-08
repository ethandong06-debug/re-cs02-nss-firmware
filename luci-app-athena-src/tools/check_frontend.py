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
    run([sys.executable,str(Path(__file__).with_name("check_v1_menu.py")),str(prototype)])
    html=index.read_text(encoding="utf-8")
    scripts=re.findall(r"<script\b[^>]*>([\s\S]*?)</script>",html,re.I)
    if not scripts: raise SystemExit("FAIL: no inline scripts")
    with tempfile.TemporaryDirectory() as td:
        for i,script in enumerate(scripts):
            f=Path(td)/("inline-%d.js"%i); f.write_text(script,encoding="utf-8"); run(["node","--check",str(f)])
        run(["node","--check",str(runtime)])
    run(["sh","-n",str(gateway)]); run(["sh","-n",str(wifi)])
    run([sys.executable,str(Path(__file__).with_name("check_rpc_wiring.py")),str(index),str(runtime),str(gateway),str(acl),str(makefile)])
    print("静态检查通过：V1.0 菜单、HTML 内联 JS、外部 runtime、网关和 Wi-Fi 定时脚本。")
    return 0
if __name__=="__main__": raise SystemExit(main())
