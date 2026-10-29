# -*- coding: utf-8 -*-
"""Create preview HTML: copy index.html + inject preview-mode script (skip login when not on LuCI)."""
import io, os, sys

src = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
dst_dir = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\preview"
dst = os.path.join(dst_dir, "preview-v1.2.0.html")

with io.open(src, "r", encoding="utf-8") as f:
    html = f.read()

inject = r"""
<script>
/* ===== 预览模式（静态打开自动进入：仅界面结构预览，无真实数据；真机 LuCI 下走正常登录） ===== */
(function(){
  var P = { on: false };
  window.ATHENA_PREVIEW = P;
  function tryBoot(){
    try { if (typeof boot === 'function') { boot(); return; } } catch (e) {}
    try {
      document.getElementById('login').style.display = 'none';
      document.getElementById('app').classList.add('show');
    } catch (e2) {}
  }
  function enterPreview(){
    if (P.on) return; P.on = true;
    try {
      if (typeof athenaRPC !== 'undefined' && athenaRPC) {
        athenaRPC.exec = function(){ return new Promise(function(res, rej){ rej(new Error('预览模式：未连接路由器（界面预览无真实数据）')); }); };
      }
    } catch (e) {}
    tryBoot();
  }
  /* file:// 直开 → 同步立即进入预览，不依赖网络探测 */
  if (location.protocol === 'file:') { enterPreview(); }
  else {
    fetch('/ubus/', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
      .then(function(r){ if (!r.ok) enterPreview(); })
      .catch(function(){ enterPreview(); });
    setTimeout(function(){
      var lg = document.getElementById('login');
      if (lg && lg.style && lg.style.display !== 'none') enterPreview();
    }, 4000);
  }
})();
</script>
"""

marker = "</body>"
idx = html.rfind(marker)
if idx < 0:
    print("ERROR: no </body> found")
    sys.exit(1)
out = html[:idx] + inject + html[idx:]

os.makedirs(dst_dir, exist_ok=True)
with io.open(dst, "w", encoding="utf-8") as f:
    f.write(out)
print("OK ->", dst, len(out), "bytes")

# sanity: file parses (check injection present)
with io.open(dst, "r", encoding="utf-8") as f:
    chk = f.read()
print("injected:", "ATHENA_PREVIEW" in chk, "| original intact:", chk[:60] == html[:60])
