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
		# v1.2.54：这台机器是整盘 overlay（/ = overlayfs:/tmp/root，/rom = /dev/root squashfs），
		# 没有任何分区被 /dev/mmcblk0pN 直接挂载，旧逻辑靠 /proc/mounts 反查必然全落空，
		# 于是"已用 0 MB / 115.2 GB（0%）"。现在改成：
		#   size_mb  取块设备物理容量（/sys/block/<dev>/size）
		#   parts[]  列出每个分区的名称与容量（未挂载就标 mount:"")
		#   used_mb  只累加真正挂载了的分区；mounted=false 时前端显示"未挂载"，不再报 0 MB/0%
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
			mount=""; fs=""; used_mb=0; PARTS=""; nparts=0
			for part in /sys/block/$name/${name}p*; do
				[ -e "$part" ] || continue
				pname=$(basename "$part")
				echo "$pname" | grep -qE 'boot[0-9]+$' && continue
				psec=$(cat "$part/size" 2>/dev/null || echo 0)
				pmb=$((psec/2048))
				[ "$pmb" -le 0 ] && continue
				line=$(grep -E " /dev/$pname " /proc/mounts 2>/dev/null | head -1)
				pmp=$(echo "$line" | awk '{print $2}')
				pfs=$(echo "$line" | awk '{print $3}')
				if [ -n "$pmp" ]; then
					[ -z "$mount" ] && { mount="$pmp"; fs="$pfs"; }
					du_kb=$(df -k "$pmp" 2>/dev/null | awk 'NR==2{print $3}')
					[ -n "$du_kb" ] && used_mb=$((used_mb + du_kb/1024))
				fi
				nparts=$((nparts+1))
				[ -n "$PARTS" ] && PARTS="$PARTS,"
				PARTS="$PARTS{\"name\":\"$pname\",\"size_mb\":$pmb,\"mount\":\"$(printf '%s' "$pmp" | json_str)\",\"fs\":\"$pfs\"}"
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
			mounted=false
			[ -n "$mount" ] && mounted=true
			DISKS="$DISKS{\"name\":\"$name\",\"size_mb\":$size_mb,\"used_mb\":$used_mb,\"mounted\":$mounted,\"parts_count\":$nparts,\"mount\":\"$(printf '%s' "$mount" | json_str)\",\"fs\":\"$fs\",\"parts\":[$PARTS]}"
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
