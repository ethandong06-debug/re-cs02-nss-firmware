# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
t = io.open(p, encoding="utf-8").read()

rep = [
    ("| `athena-services.uc` | `/usr/libexec/` | 10,456 | `46be24ddff69e7ec…` | https://aka.doubaocdn.com/s/qQS9UuaCLY |",
     "| `athena-services.uc` | `/usr/libexec/` | 11,557 | `8cde41b53f402997…` | https://aka.doubaocdn.com/s/nmTxeOcRXg |"),
    ("46be24ddff69e7ecd1c0e47b63d602c47523a2a06675bb157a9db3b49c22b126  athena-services.uc",
     "8cde41b53f402997e33dd19638717cb62a0df5c4615004b2dfc3446652ff2056  athena-services.uc"),
    ("wget -O s.uc \"https://aka.doubaocdn.com/s/qQS9UuaCLY\"",
     "wget -O s.uc \"https://aka.doubaocdn.com/s/nmTxeOcRXg\""),
    ("`detect_port()`（从 `/etc/init.d/<base>` 匹配 `-p` / `--port` / `-port`，取 2–5 位端口）",
     "`detect_port()`（从 `/etc/init.d/<base>` 逐行找 `--port` / `-port` / `_PORT=` / `PORT=` / `-p` 后跟 2–5 位数字；不用字符类正则，全部 `index()/substr()` 走位，因为真机上 `[ \\t]` 边界不稳）；顺带修掉一处潜伏 bug——`it.port` 输出原来用未定义的 `i()` 拼，端口一旦探测到就直接报 `left-hand side is not a function`"),
    ("| 日志解析 | 假 `logread` 喂 7 行",
     "| 服务端口 | 造 4 个 init 脚本样本（`FB_PORT=8081` / `-p 7681` / `PORT=\"6800\"` / 只有 `--path` 无端口） | 输出 `filebrowser=8081 ttyd=7681 aria2=6800 noport=0`，无误报 |\n| 日志解析 | 假 `logread` 喂 7 行"),
]
for a, b in rep:
    assert a in t, a[:40]
    t = t.replace(a, b)

io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("ok")
