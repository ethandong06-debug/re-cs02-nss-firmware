#!/bin/sh
# AthenaWrt 磁盘管理
# 用法:
#   athena-disk.sh list                   列出块设备与挂载点
#   athena-disk.sh mount <dev> <mp> [fs]  挂载
#   athena-disk.sh umount <dev>           卸载
#   athena-disk.sh format <dev> <fs>      格式化（ext4/vfat/exfat/f2fs）
# 输出单行 JSON

CMD="${1:-list}"
json_str() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

case "$CMD" in
	list)
		DISKS=""
		for dev in /sys/block/mmcblk* /sys/block/sd* /sys/block/nvme*; do
			[ -d "$dev" ] || continue
			name=$(basename "$dev")
			# 跳过 boot0/boot1/rpmb 等伪块设备（无实际存储，会误判为内置盘）
			echo "$name" | grep -qE 'boot[0-9]+$|rpmb$' && continue
			size_sectors=$(cat "$dev/size" 2>/dev/null || echo 0)
			size_mb=$((size_sectors/2048))
			[ "$size_mb" -le 0 ] && continue
			[ -n "$DISKS" ] && DISKS="$DISKS,"
			mount=""; fs=""; used_mb=0
			# 汇总该设备所有分区的挂载点与已用（eMMC 可能多分区：overlay + 数据盘）
			for part in /sys/block/$name/${name}p* /sys/block/$name/${name}*; do
				[ -e "$part" ] || continue
				pname=$(basename "$part")
				# 跳过 boot0/boot1 等非分区伪设备
				echo "$pname" | grep -qE 'boot[0-9]+$' && continue
				mp=$(grep -E " /dev/$pname " /proc/mounts 2>/dev/null | awk '{print $2}')
				[ -z "$mp" ] && continue
				[ -z "$mount" ] && { mount="$mp"; fs=$(grep -E " /dev/$pname " /proc/mounts 2>/dev/null | awk '{print $3}'); }
				du_kb=$(df -k "$mp" 2>/dev/null | awk 'NR==2{print $3}')
				[ -n "$du_kb" ] && used_mb=$((used_mb + du_kb/1024))
			done
			# 设备本身（非分区）直接挂载的少见情况
			if [ -z "$mount" ]; then
				mp=$(grep -E " /dev/$name " /proc/mounts 2>/dev/null | awk '{print $2}')
				if [ -n "$mp" ]; then
					mount="$mp"; fs=$(grep -E " /dev/$name " /proc/mounts 2>/dev/null | awk '{print $3}')
					du_kb=$(df -k "$mp" 2>/dev/null | awk 'NR==2{print $3}')
					[ -n "$du_kb" ] && used_mb=$((used_mb + du_kb/1024))
				fi
			fi
			DISKS="$DISKS{\"name\":\"$name\",\"size_mb\":$size_mb,\"used_mb\":$used_mb,\"mount\":\"$(printf '%s' "$mount" | json_str)\",\"fs\":\"$fs\"}"
		done
		echo "{\"ok\":true,\"disks\":[$DISKS]}"
		;;
	mount)
		DEV="${2:-}"; MP="${3:-}"; FS="${4:-auto}"
		[ -z "$DEV" ] || [ -z "$MP" ] && { echo '{"ok":false,"msg":"缺少设备或挂载点"}'; exit 1; }
		mkdir -p "$MP" 2>/dev/null
		if [ "$FS" = "auto" ]; then
			mount "$DEV" "$MP" >/dev/null 2>&1
		else
			mount -t "$FS" "$DEV" "$MP" >/dev/null 2>&1
		fi
		[ $? -eq 0 ] && echo "{\"ok\":true,\"msg\":\"$DEV 已挂载到 $MP\"}" || echo "{\"ok\":false,\"msg\":\"挂载失败，检查分区或文件系统\"}"
		;;
	umount)
		DEV="${2:-}"
		[ -z "$DEV" ] && { echo '{"ok":false,"msg":"缺少设备"}'; exit 1; }
		umount "$DEV" >/dev/null 2>&1 && echo "{\"ok\":true,\"msg\":\"$DEV 已卸载\"}" || echo "{\"ok\":false,\"msg\":\"卸载失败（可能正在使用）\"}"
		;;
	format)
		DEV="${2:-}"; FS="${3:-ext4}"
		[ -z "$DEV" ] && { echo '{"ok":false,"msg":"缺少设备"}'; exit 1; }
		# 先卸载
		umount "$DEV" >/dev/null 2>&1
		case "$FS" in
			ext4) mkfs.ext4 -F "$DEV" >/dev/null 2>&1 ;;
			vfat) mkfs.vfat -F 32 "$DEV" >/dev/null 2>&1 ;;
			exfat) mkfs.exfat "$DEV" >/dev/null 2>&1 ;;
			f2fs) mkfs.f2fs -f "$DEV" >/dev/null 2>&1 ;;
			*) echo "{\"ok\":false,\"msg\":\"不支持的文件系统 $FS\"}"; exit 1 ;;
		esac
		[ $? -eq 0 ] && echo "{\"ok\":true,\"msg\":\"$DEV 已格式化为 $FS\"}" || echo "{\"ok\":false,\"msg\":\"格式化失败\"}"
		;;
	*)
		echo '{"ok":false,"msg":"未知命令（支持 list|mount|umount|format）"}'
		exit 1
		;;
esac
