import re, subprocess, io, sys, tempfile, os, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = []
try:
    p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
    html = open(p, encoding="utf-8").read()
    m = re.search(r"<script>(.*)</script>", html, re.S)
    js = m.group(1)
    out.append("JS 长度: %d" % len(js))
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js); tmp = f.name
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    out.append("node --check: " + ("PASS" if r.returncode==0 else "FAIL"))
    if r.returncode!=0:
        out.append(r.stderr[:3000])
    else:
        calls = set(re.findall(r"onclick=\"([a-zA-Z_$][\w$]*)", html))
        calls |= set(re.findall(r"\b(window\.)?([a-zA-Z_$][\w$]*)\(", js))
        defined = set(re.findall(r"function\s+([a-zA-Z_$][\w$]*)\s*\(", js))
        defined |= set(re.findall(r"const\s+([A-Z_][\w$]*)\s*=", js))
        undefined = sorted(c for c in calls if c not in defined and c not in {'if','return','function','for','while'})
        out.append("引用但未定义: " + (", ".join(undefined) if undefined else "无"))
        out.append("占位残留: " + ("有!!" if "==VIEWS==" in html or "==OPS==" in html or "==INIT==" in html else "无"))
        missing = []
        for fn in ["go","loadStatus","loadWireless","openBandConfig","applyBandConfig","toggleGuest","resetWirelessDefaults","switchDevTab","openDevDetail","renameDev","openBlockModal","addKnownDev","blockByMac","pcListHTML","saveParentRule","clearParentRule","pickMode","saveWan","saveSingle","saveAp","saveBypass","runScan","runDiag","runPing","runSpeedTest","diskRowDisk","openFileShare","toggleMatrixEnabled","setMatrix","toggleMatrixNight","toggleBreath","openMatrixFull","openRebootModal","openRebootScheduleModal","openUpgrade","openResetModal","backupNow","openRestoreModal","toggleAutoBackup","openAutoBackupModal","openBackupList","pickRes","openSvcWin","toggleSvc","openPackages","updatePackageList","openSyslog","exportLog","clearLog","openPasswordModal","openThemeModal","setUiMode","openSortModal","setSpeedUnit","doLogin","wizardShow","applyWizardConfig","boot","loadParentRules","loadRebootStatus","loadPackageList","loadServices","loadResources","loadUiMode","renderWifi","renderDevices","renderNetwork","renderStorage","renderLighting","renderMaintain","renderAdvanced","loadDisks","loadMatrix","loadLed","loadGuest","loadTheme","loadBackupList","pkgRender","pkgTab","logRender","logLv","metricsHTML","topologyHTML","trendHTML","updateMetrics","pushTrend","drawTrend","switchTrend","wanProtoName","wanSpeedTxt","wanStateTag","portMatrixHTML","modeFormHTML","renderModeActs","speedNodeInfo","changeSpeedNode","mountDisk","umountDisk","formatDisk","doFormat","openSvcWin","doRename","doBlock","doBlockByMac","openParentModal","updateNewDevs","doResetWireless","switchNativeUI","applyDark","toggleTheme","openModal","closeModal","pickPalette","setGlassParam","resetTheme","saveGlassTheme","iconSVG","renderNav","cycleUnit"]:
            if fn not in defined:
                missing.append(fn)
        out.append("缺失函数: " + (", ".join(missing) if missing else "无"))
        out.append("检查完成")
    os.unlink(tmp)
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_check13.txt","w",encoding="utf-8").write("\n".join(out))
