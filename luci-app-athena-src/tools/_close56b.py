# -*- coding: utf-8 -*-
"""把 #33 / #37 状态规范化，并在 README 7.6 补上验收结果。"""
import io

led = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\AthenaWrt-待修问题记录.md"
t = io.open(led, encoding="utf-8").read()

old33 = "路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev` |"
new33 = "路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev`；**真机通过（v1.2.56）**：ACL 放行 `athena-prefs.sh` 后，登录进主界面排序保存、刷新仍保持 |"
assert old33 in t, "33 未命中"
t = t.replace(old33, new33, 1)

old37 = "| **真机通过：Jason 22:5x 确认无痕窗口登录正常**，登录卡死闭环 |"
new37 = "| **真机通过（2026-10-28 22:5x）**：无痕窗口输入密码直接进主界面；排序保存并刷新保持 |"
assert old37 in t, "37 未命中"
t = t.replace(old37, new37)
io.open(led, "w", encoding="utf-8", newline="\n").write(t)

rd = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
s = io.open(rd, encoding="utf-8").read()
anchor = "（正确跳过）；再涨过 4MB 才裁一次 |"
assert anchor in s, "README 锚点未命中"
add = anchor + """

### 7.7 真机验收结果（2026-10-28 22:5x）

| 项 | 结果 |
|---|---|
| 登录卡在「登录中」 | **已解决**：无痕窗口输入密码直接进主界面（ACL 补 `athena-prefs.sh` 后生效） |
| 指标卡排序 | **已解决**：真机上改序保存、刷新后顺序保持——远端持久化这次是真的写进路由器了 |
| 日志每分钟空转裁剪 | **已解决**：裁剪记录最后一条停在 22:43:00（换成 4MB 上限那一刻），之后不再新增 |
| 磁盘 0 MB / 服务「打开」/ 日志四列 / 内核线程开关 | 真机后端输出与前端渲染均已核对通过 |

**教训（两条都值得记住）**：
1. 页面调用的每一个 `/usr/libexec/athena-*.sh` 都必须在 `luci-app-athena.json` 的 `file` 段里逐条声明 `exec`；新增脚本时**同步改 ACL 并重启 rpcd**，否则 rpcd 返回 6，前端会把权限问题误判成会话过期。
2. 前端任何 `await` 都必须自带 try/catch 并把异常摆到界面或日志里——「登录中…」永久停在那一格，比报错难查十倍。
"""
s = s.replace(anchor, add, 1)
io.open(rd, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
