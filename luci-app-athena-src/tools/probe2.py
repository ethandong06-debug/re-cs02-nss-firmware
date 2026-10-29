# -*- coding: utf-8 -*-
import struct, lzma

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

def parse_all(hdr8_total, ic_pos_rel, idxh, verbose=False):
    """不带 ino 递增假设。返回 (解析数, 停止位置, 错误)"""
    p = 0
    count = 0
    last100 = []
    while p + 16 <= len(raw):
        it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
        if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
            return count, p, 'bad type %d (ino=%d)' % (it, ino), last100
        base = p
        p += 16
        ok = True
        if it == 1:
            if p+16 > len(raw): ok=False
            else:
                sb, nl, fs, off, par = struct.unpack('<IIHHI', raw[p:p+16]); p += 16
        elif it == 2:
            if p+16 > len(raw): ok=False
            else:
                sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
                nb = (fs + 262143)//262144 if fr == 0xffffffff else fs // 262144
                if p + nb*4 > len(raw): ok=False
                else: p += nb*4
        elif it == 3:
            if p+8 > len(raw): ok=False
            else:
                nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                if p+sz > len(raw): ok=False
                else: p += sz
        elif it == 8:
            if p + (hdr8_total-16) > len(raw): ok=False
            else:
                ic = struct.unpack('<I', raw[p+ic_pos_rel:p+ic_pos_rel+4])[0]
                if ic > 1000000: return count, base, 'ic huge %d' % ic, last100
                p += hdr8_total - 16
                for _ in range(ic):
                    if p + idxh > len(raw): ok=False; break
                    if idxh >= 12:
                        szf = struct.unpack('<I', raw[p+8:p+12])[0]
                    else:
                        szf = struct.unpack('<H', raw[p+6:p+8])[0]
                    if szf > 512: return count, base, 'idx size %d' % szf, last100
                    p += idxh + szf
                if not ok: break
        elif it == 9:
            if p+36 > len(raw): ok=False
            else:
                p += 36  # sb4+fs8+sp8+nl4+fr4+fo4+xa4
        elif it == 10:
            if p+8 > len(raw): ok=False
            else:
                nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                if p+sz > len(raw): ok=False
                else: p += sz
        elif it in (4,5):
            if p+8 > len(raw): ok=False
            else: p += 8
        elif it in (6,7):
            if p+4 > len(raw): ok=False
            else: p += 4
        elif it == 11:
            if p+12 > len(raw): ok=False
            else: p += 12
        elif it == 12:
            if p+12 > len(raw): ok=False
            else: p += 12
        elif it in (13,14):
            if p+8 > len(raw): ok=False
            else: p += 8
        if not ok:
            return count, base, 'eof', last100
        if verbose:
            last100.append('ino=%d it=%d off=%d len=%d' % (ino, it, base, p-base))
            last100 = last100[-100:]
        count += 1
    return count, p, 'ok', last100

for hdr_total, ic_pos in [(38,12),(34,12),(40,12),(36,12),(38,16),(34,16)]:
    for idxh in (12, 10):
        c, stop, err, _ = parse_all(hdr_total, ic_pos, idxh)
        print('hdr=%d ic=%d idxh=%d -> count=%d stop=%d err=%s' % (hdr_total, ic_pos, idxh, c, stop, err))

# 找最接近 51828 的失败点，dump 该处字节
c, stop, err, last = parse_all(38, 12, 12)
print('\nbest-ish failure at stop=%d err=%s' % (stop, err))
print('\n'.join(last[-25:]))
