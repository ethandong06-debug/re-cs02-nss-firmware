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

base = 70979
print('base16:', raw[base:base+16].hex())
print('hdr  :', raw[base+16:base+48].hex())
print('dump 80 bytes:')
for i in range(0, 80, 16):
    seg = raw[base+i:base+i+16]
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in seg)
    print('%04x: %s  %s' % (i, seg.hex(), asc))
