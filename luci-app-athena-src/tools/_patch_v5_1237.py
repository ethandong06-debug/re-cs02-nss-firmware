# -*- coding: utf-8 -*-
"""把 v1.2.37 的前端修复同步到预览稿（精确替换，逐条断言）。"""
import io, sys

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\preview\AthenaWrt-全站v5.html"
src = io.open(P, encoding="utf-8").read()

PAIRS = [
 ("openSvcFrame('点阵屏完整管理','/admin/athena_led');",
  "openSvcFrame('点阵屏完整管理','/admin/services/athena_led');"),
 ('<iframe src="/cgi-bin/luci" id="nativeLuciIframe"',
  '<iframe src="/cgi-bin/luci/admin/status/overview" id="nativeLuciIframe"'),
 ("window.open('/cgi-bin/luci','_blank')",
  "window.open('/cgi-bin/luci/admin/status/overview','_blank')"),
 ("groups[app].svc.push(p.name||p.cmd||'?');",
  "var _sn=(p.name||p.cmd||'?'); if(groups[app].svc.indexOf(_sn)<0) groups[app].svc.push(_sn);"),
 ("loadActiveApps(); },15000);",
  "loadActiveApps(); },60000);"),
 ("d.name=name; toast('设备已改名'); window.closeModal(); loadClients();",
  "d.name=name; toast('设备已改名'); document.querySelectorAll('.mask').forEach(function(m){ m.remove(); }); loadClients();"),
]

# 备份下载主通道改 base64（三段替换）
OLD_DL = """  toast('正在生成下载链接…');
  // 优先走 http 直链（大文件 base64 经 rpcd 传输易截断）；直链失败再降级 base64→Blob
  athenaRPC.exec('athena-backup.sh',['export',file]).then(function(d){
    if(d&&d.url){
      var url=d.url.indexOf('http')===0?d.url:location.origin+d.url;
      window.open(url,'_blank');
      toast('备份下载已开始：'+file);
    } else { dlB64(file); }
  }).catch(function(){ dlB64(file); });"""
NEW_DL = """  toast('正在读取备份…');
  /* 主通道：ubus 取 base64 → 前端 Blob 直存，不依赖 /www 静态目录（避免 403/404） */
  athenaRPC.exec('athena-backup.sh',['download',file]).then(function(d){
    if(d&&d.base64){ dlB64(file); } else { dlExport(file); }
  }).catch(function(){ dlExport(file); });"""
PAIRS.append((OLD_DL, NEW_DL))

# dlB64 后面补一个 dlExport
OLD_TAIL = "window.restoreBackup=function(file){"
NEW_TAIL = """function dlExport(file){
  athenaRPC.exec('athena-backup.sh',['export',file]).then(function(d){
    if(d&&d.url){
      var url=d.url.indexOf('http')===0?d.url:location.origin+d.url;
      window.open(url,'_blank');
      toast('备份下载已开始：'+file);
    } else { toast('下载失败：后端未返回下载地址'); }
  }).catch(function(e){ toast('下载失败：'+(e.message||'')); });
}
window.restoreBackup=function(file){"""
PAIRS.append((OLD_TAIL, NEW_TAIL))

fails = []
for old, new in PAIRS:
    n = src.count(old)
    if n != 1:
        fails.append((old[:40], n))
        continue
    src = src.replace(old, new, 1)

if fails:
    print("FAIL:", fails)
    sys.exit(1)

io.open(P, "w", encoding="utf-8", newline="").write(src)
print("OK patched, len=", len(src))
