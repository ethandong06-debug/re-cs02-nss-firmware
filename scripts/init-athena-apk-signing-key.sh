#!/bin/sh
# One-time P-256 APK signing-key bootstrap for AthenaWrt.
# Run as root on the router. The private key stays on the router; copy it only
# into the GitHub Actions repository secret ATHENAWRT_APK_SIGNING_KEY.

set -eu

[ "$(id -u)" = "0" ] || { echo "请使用 root 身份运行此脚本。" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || {
	echo "系统缺少 openssl 命令。请先安装 openssl-util：apk add openssl-util" >&2
	exit 1
}

KEY_DIR="/root/athena-apk-signing"
PRIVATE_KEY="$KEY_DIR/private-key.pem"
PUBLIC_TMP="$KEY_DIR/public-key.pem"
PUBLIC_KEY="/etc/apk/keys/athenawrt-fixed-signing.pem"

umask 077
mkdir -p "$KEY_DIR" /etc/apk/keys
chmod 700 "$KEY_DIR"

if [ ! -s "$PRIVATE_KEY" ]; then
	tmp="$KEY_DIR/private-key.pem.tmp"
	rm -f "$tmp"
	openssl ecparam -name prime256v1 -genkey -noout -out "$tmp"
	chmod 600 "$tmp"
	mv "$tmp" "$PRIVATE_KEY"
fi

openssl pkey -in "$PRIVATE_KEY" -noout
openssl pkey -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_TMP"
openssl pkey -pubin -in "$PUBLIC_TMP" -noout
openssl pkey -pubin -in "$PUBLIC_TMP" -text -noout | grep -q 'prime256v1'
install -m 0644 "$PUBLIC_TMP" "$PUBLIC_KEY"
chmod 600 "$PRIVATE_KEY"

echo
echo "固定签名密钥已生成并安装公钥。"
echo "公钥路径：$PUBLIC_KEY"
echo "公钥 SHA256："
sha256sum "$PUBLIC_KEY"
echo
echo "下一步：在 GitHub 仓库 Settings -> Secrets and variables -> Actions 中"
echo "创建 Repository secret，名称必须是：ATHENAWRT_APK_SIGNING_KEY"
echo "Secret 的值必须是下面完整私钥内容（包含 BEGIN/END 行）。"
echo "不要把私钥提交到仓库，也不要发给任何人。"
echo
cat "$PRIVATE_KEY"
