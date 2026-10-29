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

p = 44032
out = []
for i in range(p, p+256, 16):
    h = ' '.join('%02x'%x for x in raw[i:i+16])
    a = ''.join(chr(x) if 32<=x<127 else '.' for x in raw[i:i+16])
    out.append('%04x: %-48s |%s|' % (i, h, a))
open(r'C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\dbg8_full.txt','w').write('\n'.join(out))
print('ok')
