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

# 逐 inode 解析，打印每个 inode 的类型/编号/位置/长度，直到崩
p = 0
ino_last = 0
lines = []
while p + 16 <= len(raw):
    it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
    if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
        lines.append('BAD type %d at %d (p-16=%d)' % (it, p, p-16))
        break
    base = p
    p += 16
    desc = ''
    if it == 1:
        sb, nl, fs, off, par = struct.unpack('<IIHHI', raw[p:p+16])
        p += 16
        desc = 'sb=%d nl=%d fs=%d off=%d par=%d' % (sb, nl, fs, off, par)
    elif it == 2:
        sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
        nb = (fs + 262143)//262144 if fr == 0xffffffff else fs // 262144
        desc = 'sb=%d frag=%d fo=%d fs=%d nb=%d' % (sb, fr, fo, fs, nb)
        p += nb*4
    elif it == 3:
        nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
        target = raw[p:p+sz]
        desc = 'nl=%d sz=%d target=%s' % (nl, sz, target[:40])
        p += sz
    else:
        desc = '?'
        break
    lines.append('ino=%d it=%d off=%d len=%d %s' % (ino, it, base, p-base, desc))
    if ino < ino_last:
        lines.append('  <<< ino decreased! prev=%d' % ino_last)
        break
    ino_last = ino
    if p > 2400:
        break

open(r'C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\dbg_seq.txt','w').write('\n'.join(lines))
print('done', len(lines))
