# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
t = io.open(p, encoding="utf-8").read()

add = r"""

## 7. v1.2.55 日志限额修复 + v1.2.56 登录卡死修复（2026-10-28 22:3x）

### 7.1 v1.2.55：日志限额一次都没裁过（真机取证）

上机后日志不降反涨到 44,818,699 B、`Shmem` 涨到 102,060 kB，锁目录 `/tmp/.athena-logcap.lock` 和记录文件 `/tmp/athena-logcap.log` **都不存在**——说明脚本从来没走通过。真机 `sh -x` 输出：

```
+ '[' -f /tmp/dnsmasq.log ]
+ stat -c '%s' /tmp/dnsmasq.log
+ sz=
+ exit 0
```

**根因**：这台 BusyBox v1.38.0 的 `stat -c '%s'` 返回空串，`sz` 读不到就直接 `exit 0`。

**改法**（v1.2.55）：新增 `fsize()`，优先 `wc -c < 文件 | tr -d ' \t'`，失败再退回 `stat -c %s`；所有尺寸读取都走它。

编译机实测：3,188,894 B / 40,000 行 → **1,600,000 B / 20,000 行**，首行 `test20001`、末行 `test40000`（保留尾部正确）；第二次运行 `rc=0` 且尺寸不变（正确跳过）；记录文件 60 行 → 50 行。

真机实测（22:36）：44,818,699 B → **2,270,892 B**，`Shmem` 102,060 → **60,820 kB**。

### 7.2 v1.2.56：真实 20000 行是 2.27MB，比 2MB 上限还大

`CAP=2097152` 而 `KEEP=20000` 在真机上约 2.27MB，裁完仍超限 → **每分钟都会再裁一次空转**。
改法：`CAP=4194304`（4MB）。

### 7.3 v1.2.56：登录卡在「登录中…」——ACL 缺 athena-prefs.sh

**现象**：输入密码后按钮永远显示「登录中…」，背景页不出现，无任何报错。

**取证**：真机 `/ubus/` 直接 POST `session.login`（`wget --post-data`）**成功**返回 `ubus_rpc_session`，但返回的 ACL 列表里 `file` 段逐条列了 `athena-apps.sh`、`athena-disk.sh`、`athena-log.sh`、`athena-packages.sh`、`athena-parent.sh`、`athena-passwd.sh`、`athena-reboot.sh`… **唯独没有 `athena-prefs.sh`**。本地 `root/usr/share/rpcd/acl.d/luci-app-athena.json` 核对一致——确认缺失。

**失效链条**：
1. v1.2.54 在 `boot()` 里新增 `loadKpiOrderRemote()`（指标卡排序远端持久化），它第一个调 `athenaRPC.exec('athena-prefs.sh')`；
2. rpcd 因 ACL 未放行返回**返回码 6**；
3. 旧 `exec()` 把 5/6 一律当成「会话过期」，调 `_authFail()`；
4. `_authFail()` 会把登录遮罩 `display:flex` 顶回来，但**当时不复位按钮文字**；
5. 于是「登录成功 → 立刻被顶回登录页 → 按钮还停在登录中…」= 用户看到的永久「登录中」。

**改法（三处）**：
| 文件 | 改动 |
|---|---|
| `root/usr/share/rpcd/acl.d/luci-app-athena.json` | `file` 段补 `/usr/libexec/athena-prefs.sh: ["exec"]`（条目 31 → 32） |
| `index.html` `exec()` | 返回码 6 → 只抛「执行权限不足（rpcd ACL 未放行该脚本）」，**不再 `_authFail`**；返回码 5 → 「命令未返回数据」；`j.error` 仅在 `this.session` 存在且消息匹配 `access denied / invalid session / expired` 时才踢回登录页 |
| `index.html` `_authFail()` | 遮罩弹回时同步复位按钮（`disabled=false`、文字回「登 录」） |
| `index.html` `doLogin()` | 整个 await 包 try/catch，异常原文显示在红字里；`boot()` 单独 try/catch，报「登录成功但页面初始化失败：xxx」 |
| `index.html` `boot()` | 新增 `_safe(fn,tag)`，18 个 `loadXxx()` 与 8 个 `renderXxx()` 逐个包起来，**任何一张卡失败都不再拖垮登录流程** |

### 7.4 文件与链接（v1.2.55/1.2.56 交付）

| 文件 | 设备路径 | 字节 | sha256 | 链接 |
|---|---|---|---|---|
| index.html | `/www/luci-static/resources/view/athena/index.html`（644） | 305,347 | `f419fd74998183023fe576f6c8f182179c3195caddb2fafa83f6dd290e92cbfe` | https://aka.doubaocdn.com/s/FfT9Xv6JlA |
| luci-app-athena.json | `/usr/share/rpcd/acl.d/luci-app-athena.json`（644） | 1,976 | `e08ea89c94e7a44c86979071f5928e037cec8416b33b04a1b01dc78f02ae7e40` | https://aka.doubaocdn.com/s/5Jj4LyxqS2 |
| athena-logcap.sh | `/usr/libexec/`（755） | 2,349 | `543defb08adbc5b7e8cd139ddf3a92d11f839d358e0f498d271116e55ed038ae` | https://aka.doubaocdn.com/s/n8VoV1cZAu |

`apk`：`luci-app-athena-1.2.56-r1.apk` = 14,675,452 B（编译机 `bin/packages/aarch64_cortex-a53/base/`），**未刷机**。
`athena-version` = `1.2.56`。staging 七个脚本 + ACL 与本地逐字节一致。

### 7.5 安装（一行，`;` 连接）

```sh
wget -qO- -T 20 https://aka.doubaocdn.com/s/FfT9Xv6JlA > /tmp/i3.html;wget -qO- -T 20 https://aka.doubaocdn.com/s/5Jj4LyxqS2 > /tmp/a3.json;wget -qO- -T 20 https://aka.doubaocdn.com/s/n8VoV1cZAu > /tmp/c3.sh;wc -c /tmp/i3.html /tmp/a3.json /tmp/c3.sh
```

```sh
cp /tmp/i3.html /www/luci-static/resources/view/athena/index.html;cp /tmp/a3.json /usr/share/rpcd/acl.d/luci-app-athena.json;cp /tmp/c3.sh /usr/libexec/athena-logcap.sh;chmod 755 /usr/libexec/athena-logcap.sh;chmod 644 /www/luci-static/resources/view/athena/index.html /usr/share/rpcd/acl.d/luci-app-athena.json;/etc/init.d/rpcd restart;sleep 2;ps|grep -c rpcd;sha256sum /www/luci-static/resources/view/athena/index.html /usr/share/rpcd/acl.d/luci-app-athena.json /usr/libexec/athena-logcap.sh;echo OK56
```

**`/etc/init.d/rpcd restart` 是必须的**：ACL 只在 rpcd 启动时读取，不重启不生效（重启会使旧会话失效，需重新登录）。

### 7.6 验收

| 检查 | 期望 |
|---|---|
| `ps|grep -c rpcd` | ≥1（重启后再数） |
| 三条 sha256 | `f419fd74…` / `e08ea89c…` / `543defb0…` |
| 页面登录（无痕窗口） | 能进主界面；万一再失败，红字会写明是「登录异常（RPC）」「登录成功但页面初始化失败」还是「无法连接路由器服务」 |
| 指标卡排序 | 改完顺序后刷新页面仍保持（这次才真正能远端持久化） |
| `sh /usr/libexec/athena-logcap.sh;ls -l /tmp/dnsmasq.log` | 当前 2.27MB < 4MB，应当**不动**（正确跳过）；再涨过 4MB 才裁一次 |
"""

io.open(p, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + add)
print("ok")
