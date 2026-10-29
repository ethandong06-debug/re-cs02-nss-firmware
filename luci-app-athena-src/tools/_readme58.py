# -*- coding: utf-8 -*-
import io
P = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
SEC = u"""

### 7.8.7 v1.2.58 真机收尾：ddnsto 404（前导斜杠）+ 老式控制器自动发现

装机后 ddnsto 点「打开」404。真机 `ls /usr/lib/lua/luci/controller/` 发现：ddnsto 是**老式控制器**（`controller/ddnsto.lua`），根本不在 menu.d 里——前三轮兜底全在 menu.d 翻当然找不到。

两个真因：

1. **path 少前导斜杠（404 直接原因）**：静态表里 ddns/ttyd 的 path 是 `/admin/services/ddns`（带斜杠），而 menu.d / 控制器解析出来是 `admin/services/ddnsto`（不带）。前端拼 URL 是 `'/cgi-bin/luci' + path`，不带斜杠就拼成 `/cgi-bin/luciadmin/services/ddnsto`。修法：前端 openSvcWin 统一补斜杠，后端输出时也统一 `'/' + path`。
2. **控制器自动发现**：`detect_path()` 加第四轮兜底——读 `/usr/lib/lua/luci/controller/<base>.lua`（找不到再全量扫含 base 的文件），逐行找 `entry({...})`，只取第一个 `}` 之前的引号节点名拼成路径。注意：**逐字符扫引号**，不要用 `index(s, '"', from)`——ucode 的 index() 只吃两个参数，第三个参数被忽略会死循环（实测 rc=124）。

真机输出（VM 同源副本验证）：`"id":"ddnsto",...,"path":"/admin/services/ddnsto"`，ddns 静态表保持 `/admin/services/ddns`，格式统一。

**关键结论（回答 Jason「装一个应用就要更一次文件吗」）：不用。** 入口是运行时现场扫 init.d + menu.d + controller 自动发现的，跟 GWRT 原版 LuCI 侧边栏一个思路；新装任何带 LuCI 页面的插件，刷新页面自己就出现「打开」。写死的只有三个内置服务（ddns/ttyd/athena_led）。

| 文件 | 字节 | sha256 | CDN |
|---|---|---|---|
| athena-services.uc | 13,933 | `4425fecce2f78ccc24afbc238e617c4aa27783758f8e91413f5925908c089a9a` | https://aka.doubaocdn.com/s/TgdaIUwj3f |
| index.html | 307,002 | `51c8c234766c1fc1aee8fa9bb9aeddbfb1dbbd217b633beb52ed3356a6d4ac16` | https://aka.doubaocdn.com/s/fhIOUUpsss |

Jason 验收：ddnsto 点「打开」正常进入原生配置页，网速卡峰值对上。
"""
t = io.open(P, encoding="utf-8").read()
io.open(P, "w", encoding="utf-8").write(t.rstrip() + SEC)
print("ok")
