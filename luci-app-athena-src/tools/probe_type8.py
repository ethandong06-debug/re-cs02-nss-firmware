# -*- coding: utf-8 -*-
"""暴力试探 type 8 (ldir) inode 布局：枚举头部长度与 index 条目格式，找出能解析完 7182 个 inode 的组合"""
import struct, lzma, sys

data = open(r'C:\Users\Administrator\Downloads\gwrt-雅典娜-cs-02-gwrt2-260818-43-12M-factory.bin','rb').read()
rootfs = 12582912
inode_table = 119733126
dir_table = 119787810

pos = inode_table
blocks = []
while pos < dir_table:
    hdr = struct.unpack('<H', data[rootfs+pos:rootfs+pos+2])[0]
    comp = not (hdr & 0x8000)
    sz = hdr & 0x7fff
    payload = data[rootfs+pos+2:rootfs+pos+2+sz]
    if comp:
        payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
    blocks.append(payload)
    pos += 2 + sz
raw = b''.join(blocks)
print('inode stream len:', len(raw))

def try_layout(hdr8, idx_hdr):
    """hdr8: type8 固定头长度(不含 index list); idx_hdr: 每条 index 条目的头长度(index+start_block+size)"""
    p = 0
    count = 0
    ino_last = 0
    while p + 16 <= len(raw):
        it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
        if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
            return count, p, 'bad type %d' % it
        if ino <= ino_last and ino != 1:
            return count, p, 'ino not increasing: %d after %d' % (ino, ino_last)
        ino_last = ino
        p += 16
        if it == 1:
            p += 16
        elif it == 2:
            sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
            nb = (fs + 262143)//262144 if fr == 0xffffffff else fs // 262144
            p += nb*4
        elif it == 3:
            nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
            p += sz
        elif it == 8:
            p += hdr8
            ic = struct.unpack('<I', raw[p-8:p-4])[0]  # 头倒数第二字段？不对，取决于布局
            # 这里不能用假设的 ic 位置，改为试：跳过 hdr8 后逐条 index 直到下一个合法 inode
            # 先假设 i_count 在头内某固定位置，由调用方传 ic_off
            return count, p, 'need ic_off'
        else:
            p += 8  # 4/5/6/7/9/10/11/12/13/14 先用保守值，后面细调
        count += 1
    return count, p, 'ok'

# 更精细：type 8 头结构候选（相对 inode 基座 16 字节后的部分）
# 候选 A: nlink(4) file_size(4) start_block(4) i_count(4) i_size(2) xattr(4) = 22 -> 总 38
# 候选 B: nlink(4) file_size(4) start_block(4) i_count(4) i_size(2) = 18 -> 总 34 (无 xattr)
# 候选 C: nlink(4) file_size(4) start_block(4) i_count(4) i_size(4) xattr(4) = 24 -> 总 40
# 候选 D: nlink(4) file_size(4) start_block(4) i_count(4) i_size(2) = 18 且 index 头不同
# 候选 E: nlink(4) file_size(4) start_block(4) i_count(2) i_size(2) xattr(4) = 20 -> 总 36

def try_full(cands, idx_hdr_cands):
    results = []
    for hdr_total, ic_pos in cands:  # ic_pos 相对 inode 起点(含16基座)的 i_count 偏移
        for idxh in idx_hdr_cands:
            p = 0
            count = 0
            ino_last = 0
            err = None
            while p + 16 <= len(raw):
                it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
                if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
                    err = 'bad type %d at %d' % (it, p)
                    break
                if ino < ino_last:
                    err = 'ino dec %d<-%d at %d' % (ino, ino_last, p)
                    break
                ino_last = ino
                p += 16
                if it == 1:
                    p += 16
                elif it == 2:
                    sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
                    nb = (fs + 262143)//262144 if fr == 0xffffffff else fs // 262144
                    p += nb*4
                elif it == 3:
                    nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                    p += sz
                elif it == 8:
                    # i_count 在 ic_pos
                    if ic_pos + 4 > len(raw):
                        err = 'eof'; break
                    ic = struct.unpack('<I', raw[p+ic_pos-16:p+ic_pos-12])[0]
                    if ic > 100000:
                        err = 'ic huge %d' % ic; break
                    p += hdr_total - 16
                    for _ in range(ic):
                        if p + idxh > len(raw):
                            err = 'eof idx'; break
                        # size 字段位置：idxh 最后 4 或 2 字节
                        if idxh >= 12:
                            szf = struct.unpack('<I', raw[p+8:p+12])[0]
                        else:
                            szf = struct.unpack('<H', raw[p+6:p+8])[0]
                        if szf > 300:
                            err = 'bad idx size %d at %d' % (szf, p); break
                        p += idxh + szf
                    if err: break
                elif it == 9:
                    p += 4 + 16 + 16  # sb + fs8 + sp8 + nl4 + fr4 + fo4 + xa4 = 4+16+16
                elif it == 10:
                    nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                    p += sz
                elif it in (4,5):
                    p += 8
                elif it in (6,7):
                    p += 4
                elif it == 11:
                    p += 12
                elif it == 12:
                    p += 12
                elif it in (13,14):
                    p += 8
                else:
                    err = 'unhandled %d' % it; break
                count += 1
            results.append((count, err, hdr_total, ic_pos, idxh))
    return results

# 候选 (总头长, i_count 相对基座16的偏移)
cands = [
    (38, 16+12),  # A: 基座16+nlink4+fs4+sb4, ic 在 16+12
    (34, 16+12),  # B
    (40, 16+12),  # C
    (36, 16+12),  # D
    (36, 16+14),  # E: ic 16位在 16+12, is 16位 16+14
]
idx_hdr_cands = [12, 10]
res = try_full(cands, idx_hdr_cands)
for r in sorted(res, key=lambda x: -x[0])[:12]:
    print('count=%d err=%s hdr=%d ic_off=%d idxh=%d' % r)
