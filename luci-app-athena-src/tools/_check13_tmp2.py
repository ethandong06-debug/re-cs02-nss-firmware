import re, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = []
p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
html = open(p, encoding="utf-8").read()
m = re.search(r"<script>(.*)</script>", html, re.S)
js = m.group(1)
calls = set(re.findall(r"onclick=\"([a-zA-Z_$][\w$]*)", html))
calls |= set(re.findall(r"(?:window\.)?([a-zA-Z_$][\w$]*)\(", js))
defined = set(re.findall(r"function\s+([a-zA-Z_$][\w$]*)\s*\(", js))
defined |= set(re.findall(r"const\s+([A-Z_][\w$]*)\s*=", js))
defined |= set(re.findall(r"let\s+([a-zA-Z_$][\w$]*)\s*=", js))
defined |= set(re.findall(r"var\s+([a-zA-Z_$][\w$]*)\s*=", js))
skip = {'if','return','function','for','while','new','typeof','in','of','catch','else','do','switch','case','delete','void','throw','try'}
undefined = sorted(c for c in calls if c not in defined and c not in skip)
out.append("引用但未定义: " + (", ".join(undefined) if undefined else "无"))
out.append("占位残留: " + ("有!!" if "==VIEWS==" in html or "==OPS==" in html or "==INIT==" in html else "无"))
missing = []
need = ["go","loadStatus","loadWireless","openBandConfig","applyBandConfig","toggleGuest","resetWirelessDefaults","switchDevTab","openDevDetail","renameDev","openBlockModal","addKnownDev","blockByMac","pcListHTML","saveParentRule","clearParentRule","pickMode","saveWan","saveSingle","saveAp","saveBypass","runScan","runDiag","runPing","runSpeedTest","diskRowDisk","openFileShare","toggleMatrixEnabled","setMatrix","toggleMatrixNight","toggleBreath","openMatrixFull","openRebootModal","openRebootScheduleModal","openUpgrade","openResetModal","backupNow","openRestoreModal","toggleAutoBackup","openAutoBackupModal","openBackupList","pickRes","openSvcWin","toggleSvc","openPackages","updatePackageList","openSyslog","exportLog","clearLog","openPasswordModal","openThemeModal","setUiMode","openSortModal","setSpeedUnit","doLogin","wizardShow","applyWizardConfig","boot","loadParentRules","loadRebootStatus","loadPackageList","loadServices","loadResources","loadUiMode","renderWifi","renderDevices","renderNetwork","renderStorage","renderLighting","renderMaintain","renderAdvanced","loadDisks","loadMatrix","loadLed","loadGuest","loadTheme","loadBackupList","pkgRender","pkgTab","logRender","logLv","metricsHTML","topologyHTML","trendHTML","updateMetrics","pushTrend","drawTrend","switchTrend","wanProtoName","wanSpeedTxt","wanStateTag","portMatrixHTML","modeFormHTML","renderModeActs","speedNodeInfo","changeSpeedNode","mountDisk","umountDisk","formatDisk","doFormat","doRename","doBlock","doBlockByMac","openParentModal","updateNewDevs","doResetWireless","switchNativeUI","applyDark","toggleTheme","openModal","closeModal","pickPalette","setGlassParam","resetTheme","saveGlassTheme","iconSVG","renderNav","cycleUnit","changeSpeedNode","loadUiMode","loadGuest","loadParentRules","renderLive","applyStatus","ensureFreshStatus","drawTrend","updateMetrics"]
for fn in need:
    if fn not in defined:
        missing.append(fn)
out.append("缺失函数: " + (", ".join(missing) if missing else "无"))
out.append("DOMContentLoaded: " + ("有" if "DOMContentLoaded" in js else "无"))
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_check13.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
