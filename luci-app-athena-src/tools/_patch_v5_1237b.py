# -*- coding: utf-8 -*-
"""v1.2.37 预览稿同步：逐条替换并报告命中数。"""
import io

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\preview\AthenaWrt-全站v5.html"
s = io.open(P, encoding="utf-8").read()

PAIRS = [
 ("groups[app].svc.push(p.name||p.cmd||'?');",
  "var _sn=(p.name||p.cmd||'?'); if(groups[app].svc.indexOf(_sn)<0) groups[app].svc.push(_sn);"),
 ("loadActiveApps(); },15000);", "loadActiveApps(); },60000);"),
 ("d.name=name; toast('设备已改名'); window.closeModal(); loadClients();",
  "d.name=name; toast('设备已改名'); document.querySelectorAll('.mask').forEach(function(m){ m.remove(); }); loadClients();"),
 ("async _call(sid,obj,method,params){",
  "async _call(sid,obj,method,params,timeoutMs){"),
 ("var timer=setTimeout(function(){ctrl.abort();},30000);",
  "var timer=setTimeout(function(){ctrl.abort();},timeoutMs||30000);"),
 ("async exec(file,args){", "async exec(file,args,timeoutMs){"),
 ("var r=await this._call(sid,'file','exec',{command:cmd,params:params});",
  "var r=await this._call(sid,'file','exec',{command:cmd,params:params},timeoutMs);"),
 ("athenaRPC.exec('athena-packages.sh',['update'])",
  "athenaRPC.exec('athena-packages.sh',['update'],180000)"),
 ("  _STATUS=d;\n}", "  _STATUS=d;\n  try{ var _pgNet=document.getElementById('pg-net'); if(_pgNet&&_pgNet.classList.contains('on')&&typeof renderNetPage==='function') renderNetPage(); }catch(e){}\n}"),
 ("},2000);", "},5000);"),
 ("1.2.36", "1.2.37"),
]

for old, new in PAIRS:
    n = s.count(old)
    print("hit", n, "|", old[:48].replace("\n", "\\n"))
    if n:
        s = s.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("written", len(s))
