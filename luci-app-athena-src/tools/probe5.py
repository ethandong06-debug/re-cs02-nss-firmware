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

# type8 inode 663 @44032 (0xac00)
base = 44032
print('base16:', raw[base:base+16].hex())
print('hdr  :', raw[base+16:base+44].hex())
# 尝试 index 条目解析: 起点 ac28=44072, size 字段 4字节=34
p = 44072
ix, sbx, szf = struct.unpack('<III', raw[p:p+12])
print('idx1: index=%d start_block=%d size=%d' % (ix, sbx, szf))
name = raw[p+12:p+12+szf]
print('name(%d): %s' % (szf, name))
# name 实际有多长可打印？
q = p+12
while q < len(raw) and 32 <= raw[q] < 127:
    q += 1
print('printable run from ac34: %d bytes' % (q - (p+12)))
print('raw after name:', raw[p+12+szf:p+12+szf+16].hex())
# 若 name 多 1 字节
for extra in (0,1,2,3):
    np = p + 12 + szf + extra
    it = struct.unpack('<H', raw[np:np+2])[0]
    print('next at +%d: type=%d (%s)' % (extra, it, 'ok' if it in (1,2,3,4,5,6,7,8,9,10,11,12,13,14) else 'bad'))
