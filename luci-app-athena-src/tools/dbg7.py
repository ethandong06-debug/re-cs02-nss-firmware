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

p = 0
count = 0
lines = []
while p + 16 <= len(raw):
    it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
    if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
        lines.append('STOP badtype=%d at %d after %d inodes' % (it, p, count))
        break
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
        nl, fs = struct.unpack('<II', raw[p:p+8]); p += 8
        sb = struct.unpack('<I', raw[p:p+4])[0]; p += 4
        ic = struct.unpack('<I', raw[p:p+4])[0]; p += 4
        p += 8
        idx = []
        while True:
            if p + 12 > len(raw):
                break
            ix, sbx, szf = struct.unpack('<III', raw[p:p+12])
            q = p + 12
            if q >= len(raw):
                break
            nq = q
            while nq < len(raw) and 32 <= raw[nq] < 127:
                nq += 1
            name = raw[q:nq]
            if len(name) < 3:
                break
            nxt = nq
            if nxt + 16 <= len(raw):
                t2 = struct.unpack('<H', raw[nxt:nxt+2])[0]
                if t2 in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
                    idx.append((ix, sbx, name[:16]))
                    p = nxt
                    break
            if szf < 3 or szf > 300:
                break
            if p + 12 + szf > len(raw):
                break
            idx.append((ix, sbx, name[:16]))
            p = p + 12 + szf
        if count >= 1900:
            lines.append('type8 ino=%d at %d ic=%d idx_count=%d next_p=%d next_type=%d' % (ino, base, ic, len(idx), p, struct.unpack('<H', raw[p:p+2])[0]))
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
lines.append('END count=%d p=%d' % (count, p))
open(r'C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\dbg_v7.txt','w').write('\n'.join(lines))
print('done')
