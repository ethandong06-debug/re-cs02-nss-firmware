#!/bin/bash
# ============================================================
#  AthenaWrt 构建专用 curl 镜像映射 (自建, 不走 VM 既有 wrapper)
#  - GitHub 源 -> ghfast.top 加速
#  - 内核源码 -> 阿里云镜像
#  - GNU 源码 -> 阿里云镜像
# 其余直连真实 curl (/usr/bin/curl.real)
# ============================================================
REAL=/usr/bin/curl.real

args=()
for a in "$@"; do
  case "$a" in
    https://codeload.github.com/*)
      # ghfast.top 对 codeload 返回 403, 改用 gh-proxy.com (实测 200)
      args+=("https://gh-proxy.com/$a") ;;
    https://github.com/*|https://raw.githubusercontent.com/*|https://objects.githubusercontent.com/*)
      args+=("https://ghfast.top/$a") ;;
    https://cdn.kernel.org/pub/linux/kernel/*)
      args+=("https://mirrors.aliyun.com/linux-kernel/${a#https://cdn.kernel.org/pub/linux/kernel/}") ;;
    https://www.kernel.org/pub/linux/kernel/*)
      args+=("https://mirrors.aliyun.com/linux-kernel/${a#https://www.kernel.org/pub/linux/kernel/}") ;;
    https://ftp.gnu.org/gnu/*)
      args+=("https://mirrors.aliyun.com/gnu/${a#https://ftp.gnu.org/gnu/}") ;;
    https://mirrors.edge.kernel.org/pub/linux/kernel/*)
      args+=("https://mirrors.aliyun.com/linux-kernel/${a#https://mirrors.edge.kernel.org/pub/linux/kernel/}") ;;
    *)
      args+=("$a") ;;
  esac
done

exec "$REAL" --connect-timeout 15 --retry 2 "${args[@]}"
