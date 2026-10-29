# AthenaWrt v1.2.28 进度存档（2026-10-27）

> 记录保存于开始分析 gwrt 雅典娜固件之前。以下为已确认完成的成果与待办。

## 已交付 / 已完成的成果

### 前端 18 项反馈修复（全部落地 index.html，shot.py 自检通过）
1. 桌面内容铺满：`.wrap` max-width 1180px → 1560px
2. 内存 KPI 单位截断：<1024MB 显示 "325 / 897 MB" 紧凑格式
3. WiFi 无法编辑：band id b2/b5/b6 → b24/b52/b58（与 WIFI_BANDS 对齐）
4. 网口状态无文字：renderPortBox 运算符优先级 bug（+ 优先于 ||）已加括号
5. 网络模式双"当前使用"：router.tag 写死改为"常规"
6. 设备详情删"接入方式"行，新增"备注"输入（localStorage）
7. 改名后不刷新：doRename 成功后 loadClients()
8. 测速节点下拉补 value（cq-cu/cq-ct/cq-cm/cd-cu/pub）
9. 存储误显 mmcblk0boot1：前端+后端双层过滤 boot*/rpmb
10. 灯光"打开完整管理"：window.open → iframe 弹窗 openSvcFrame
11. 运行中服务"打开"：同改为 iframe 弹窗（openSvcWin）
12. 无入口第三方服务折叠（svc-fold，默认收起）
13. 第三方服务打开入口：athena-services.sh 动态探测 menu.d path
14. 软件包管理：opkg→apk 文案、可安装 tab 合并加载、upgradable 假值显示"—（apk 源）"、卸载确认弹窗
15. 高级 CPU/内存：标题跟随实际占用、按 tab 排序、同名进程去重、proc-m 118px+nowrap
16. 升级固件 `_writeChunked` offset bug 修复（base64 文本字节数 vs 解码字节数，大文件损坏根因）
17. 备份下载：http 直链 export + Blob 兜底双通道；列表改显示 size_kb
18. 版本号 v1.2.27 → v1.2.28 全局（前端 6 处 + Makefile）

### 后端契约（本轮核对一致）
- athena-status.sh：wan{proto,username,password,device,ip,wan_vlan,ret_vlan,iptv_vlan,iptv_port,static_*}
- athena-resources.sh：{cpu{total,temp},memory{total_mb,used_mb,pct},procs[{pid,name,label,desc,cpu,mem,prot}]}
- athena-packages.sh（apk 版）：list installed|available → {packages:[{name,version,installed}]}，无 upgradable/desc
- athena-backup.sh：create/list(仅 file,size_kb)/restore/download(base64)/export(url)/restore-upload/schedule
- athena-mode.sh：单臂 pstep 进度上报 + single-bg + 失败回滚看门狗（27819B）
- athena-upgrade.sh：KEEP=1 原版保留配置升级（2504B）
- athena-services.sh：静态表 + menu.d path 动态探测
- athena-disk.sh：list 顶层过滤 boot[0-9]+$|rpmb$

### 自检结果
- shot.py：status=pass，blocker=0 error=0 warning=0（桌面 1440×900 + 移动 390×844）
- 截图：`frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\_shots\index_desktop.jpg` / `index_mobile.jpg`
- 静态预览交付：`preview\AthenaWrt-全站-v1.2.28-静态预览.html`（263KB，含全部修改）

## 待办 / 未决
- **真机复核（未做）**：① 升级固件上传链路（分块 offset 修复后）；② 备份下载双通道；③ 网络体检/诊断异常态样式
- **未编译**：用户拍板"先不编译，确认无误后再编译"。Makefile 已 bump 1.2.28
- **搁置问题**：v1.2.26→v1.2.27 保留配置升级偶发失联（用户拍板搁置，B 方案已定）
- **第三方包入口**：ddnsto 类包 enabled=0 不注册菜单是包自身设计，非框架缺陷；已通过"运行中服务-打开"补入口
- **固件升级行为**：用户已确认理解"升级保留配置≠保留已安装软件包"（apk 时代升级后需重装第三方包）

## 关键文件路径
- 前端：`frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html`（245357 字符）
- 修改前备份：`frontend\luci-app-athena\_backup\index-v1.2.28-pre.html`
- Makefile：`frontend\luci-app-athena\Makefile`（PKG_VERSION=1.2.28）
- 后端脚本：`frontend\luci-app-athena\root\usr\libexec\athena-*.sh`（23 个）
- 静态预览：`preview\AthenaWrt-全站-v1.2.28-静态预览.html`

## 真机权威配置（2026-10-27 快照）
- mode=router；br-lan 192.168.10.1/24（lan1 lan2 lan3 wan.1）；wan=wan.2044 pppoe（clan2210158893/123456）；pppoe-wan 27.10.56.187；iptv br-iptv=lan4+wan.3066；athena.single wan_vlan=2044/ret_vlan=1/iptv_port=lan4
- 系统：ImmortalWRT SNAPSHOT r1-20261017，apk 包管理（opkg 不存在）
