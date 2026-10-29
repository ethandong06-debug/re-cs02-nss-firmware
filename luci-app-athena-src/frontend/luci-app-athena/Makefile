#
# Copyright (C) 2026 AthenaWrt
# AthenaWrt 专属产品级管理界面（luci-app-athena）
# 液态玻璃单页前端（htdocs/luci-static/resources/view/athena/index.html）
# + 23 个后端 shell 脚本（root/usr/libexec/athena-*.sh）
#
include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-athena
# 版本号与固件发布版本同步（登录页/状态页展示一致）；每次固件迭代递增
PKG_VERSION:=1.2.58
PKG_RELEASE:=1

PKG_LICENSE:=Apache-2.0

LUCI_TYPE:=app
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

define Package/luci-app-athena/install
	# ---- 后端脚本（23 个）----
	$(INSTALL_DIR) $(1)/usr/libexec
	$(INSTALL_BIN) ./root/usr/libexec/athena-status.sh $(1)/usr/libexec/athena-status.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-status-legacy.sh $(1)/usr/libexec/athena-status-legacy.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-status.uc $(1)/usr/libexec/athena-status.uc
	$(INSTALL_BIN) ./root/usr/libexec/athena-mode.sh $(1)/usr/libexec/athena-mode.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-single.sh $(1)/usr/libexec/athena-single.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-client.sh $(1)/usr/libexec/athena-client.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-services.sh $(1)/usr/libexec/athena-services.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-services-legacy.sh $(1)/usr/libexec/athena-services-legacy.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-services.uc $(1)/usr/libexec/athena-services.uc
	$(INSTALL_BIN) ./root/usr/libexec/athena-resources.sh $(1)/usr/libexec/athena-resources.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-resources-legacy.sh $(1)/usr/libexec/athena-resources-legacy.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-resources.uc $(1)/usr/libexec/athena-resources.uc
	$(INSTALL_BIN) ./root/usr/libexec/athena-diag.sh $(1)/usr/libexec/athena-diag.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-log.sh $(1)/usr/libexec/athena-log.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-passwd.sh $(1)/usr/libexec/athena-passwd.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-packages.sh $(1)/usr/libexec/athena-packages.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-packages-legacy.sh $(1)/usr/libexec/athena-packages-legacy.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-packages.uc $(1)/usr/libexec/athena-packages.uc
	$(INSTALL_BIN) ./root/usr/libexec/athena-backup.sh $(1)/usr/libexec/athena-backup.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-reset.sh $(1)/usr/libexec/athena-reset.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-scan.sh $(1)/usr/libexec/athena-scan.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-reboot.sh $(1)/usr/libexec/athena-reboot.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-upgrade.sh $(1)/usr/libexec/athena-upgrade.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-disk.sh $(1)/usr/libexec/athena-disk.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-theme.sh $(1)/usr/libexec/athena-theme.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-matrix.sh $(1)/usr/libexec/athena-matrix.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-wireless.sh $(1)/usr/libexec/athena-wireless.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-speedtest.sh $(1)/usr/libexec/athena-speedtest.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-led.sh $(1)/usr/libexec/athena-led.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-ui.sh $(1)/usr/libexec/athena-ui.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-parent.sh $(1)/usr/libexec/athena-parent.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-apps.sh $(1)/usr/libexec/athena-apps.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-prefs.sh $(1)/usr/libexec/athena-prefs.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-wanip.sh $(1)/usr/libexec/athena-wanip.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-logcap.sh $(1)/usr/libexec/athena-logcap.sh
	$(INSTALL_BIN) ./root/usr/libexec/athena-rate.uc $(1)/usr/libexec/athena-rate.uc
	# 运行时版本文件（状态脚本读取，首页/维护页固件版本显示 AthenaWrt v$(PKG_VERSION)）
	echo '$(PKG_VERSION)' > $(1)/usr/libexec/athena-version

	# ---- OAF 应用映射表（活跃应用识别：DNS 指纹匹配用）----
	$(INSTALL_DIR) $(1)/usr/share/athena
	$(INSTALL_DATA) ./root/usr/share/athena/oaf-app-map.json $(1)/usr/share/athena/oaf-app-map.json

	# ---- uci 配置 ----
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_DATA) ./root/etc/config/athena $(1)/etc/config/athena

	# ---- uci-defaults（LAN IP / 主机名密码 / 无线品牌覆盖）----
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-athena-defaults $(1)/etc/uci-defaults/99-athena-defaults
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-athena-custom.sh $(1)/etc/uci-defaults/99-athena-custom.sh
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-zz-athena-wifi.sh $(1)/etc/uci-defaults/99-zz-athena-wifi.sh
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-zz-athena-redirect $(1)/etc/uci-defaults/99-zz-athena-redirect
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-athena-filebrowser.sh $(1)/etc/uci-defaults/99-athena-filebrowser.sh
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-athena-apps-dns.sh $(1)/etc/uci-defaults/99-athena-apps-dns.sh
	$(INSTALL_BIN) ./root/etc/uci-defaults/99-athena-uhttpd-timeout $(1)/etc/uci-defaults/99-athena-uhttpd-timeout

	# ---- init.d（开机自恢复呼吸灯状态 / 界面模式入口同步 / filebrowser 文件共享 / 单臂冷启动修复 / 网络自检回退）----
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./root/etc/init.d/athena-boot $(1)/etc/init.d/athena-boot
	$(INSTALL_BIN) ./root/etc/init.d/athena-ui $(1)/etc/init.d/athena-ui
	$(INSTALL_BIN) ./root/etc/init.d/filebrowser $(1)/etc/init.d/filebrowser
	$(INSTALL_BIN) ./root/etc/init.d/athena-vlan-pre $(1)/etc/init.d/athena-vlan-pre
	$(INSTALL_BIN) ./root/etc/init.d/athena-netcheck $(1)/etc/init.d/athena-netcheck

	# ---- filebrowser 预编译二进制（官方 release，aarch64 静态链接，34.5MB）----
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./root/usr/bin/filebrowser $(1)/usr/bin/filebrowser

	# ---- LuCI 菜单 ----
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./root/usr/share/luci/menu.d/luci-app-athena.json $(1)/usr/share/luci/menu.d/luci-app-athena.json

	# ---- rpcd ACL ----
	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./root/usr/share/rpcd/acl.d/luci-app-athena.json $(1)/usr/share/rpcd/acl.d/luci-app-athena.json

	# ---- 前端 SPA（液态玻璃产品级界面）----
	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/athena
	$(INSTALL_DATA) ./htdocs/luci-static/resources/view/athena/index.html $(1)/www/luci-static/resources/view/athena/index.html
	$(INSTALL_DATA) ./htdocs/luci-static/resources/view/athena/index.js $(1)/www/luci-static/resources/view/athena/index.js
endef

# call BuildPackage - OpenWrt build system signature
$(eval $(call BuildPackage,luci-app-athena))
