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
print('stream len', len(raw))

def printable(name):
    if not name: return False
    return all(32 <= b < 127 for b in name)

def try_combo(hdr_extra, idx_size_bytes, ic_off, dump=False):
    """hdr_extra: type8 基座16之外的固定头字节数（不含index list）; idx条目=index4+sb4+size{N}+name"""
    p = 0
    count = 0
    while p + 16 <= len(raw):
        it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
        if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
            return count, p, 'badtype %d' % it
        base = p
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
            if p + hdr_extra > len(raw): return count, p, 'eof'
            ic = struct.unpack('<I', raw[p+ic_off:p+ic_off+4])[0]
            if ic > 200000: return count, base, 'ic %d' % ic
            p += hdr_extra
            ok = True
            for k in range(ic):
                if p + 8 + idx_size_bytes > len(raw): ok=False; break
                idx = struct.unpack('<I', raw[p:p+4])[0]
                sbx = struct.unpack('<I', raw[p+4:p+8])[0]
                if idx_size_bytes == 4:
                    szf = struct.unpack('<I', raw[p+8:p+12])[0]
                else:
                    szf = struct.unpack('<H', raw[p+6:p+8])[0]
                if szf < 3 or szf > 300: ok=False; break
                if p+8+idx_size_bytes+szf > len(raw): ok=False; break
                name = raw[p+8+idx_size_bytes:p+8+idx_size_bytes+szf]
                if not printable(name): ok=False; break
                p += 8 + idx_size_bytes + szf
            if not ok: return count, base, 'idxfail@%d' % base
        elif it == 9:
            p += 4+16+16
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
        count += 1
    return count, p, 'ok'

results = []
# 候选: (extra头字节数, index size字段宽度, i_count相对extra起点偏移)
# extra = nlink4+fs4+sb4+ic4+is2+xa4=22 -> total 38; 无xattr: 18 -> 34
for extra, idw, icoff in [
    (22, 4, 12), (22, 2, 12), (18, 4, 12), (18, 2, 12),
    (24, 4, 12), (24, 2, 12), (16, 4, 8), (16, 2, 8),
    (20, 4, 12), (20, 2, 12),
]:
    c, stop, err = try_combo(extra, idw, icoff)
    results.append((c, err, extra, idw, icoff))
    print('extra=%d idxw=%d ic_off=%d -> count=%d stop=%d err=%s' % (extra, idw, icoff, c, stop, err))

# 对最佳组合dump细节
best = max(results, key=lambda r: r[0])
print('\nBEST:', best)
