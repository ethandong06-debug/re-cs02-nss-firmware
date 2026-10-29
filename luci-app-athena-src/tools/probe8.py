# -*- coding: utf-8 -*-
import struct, lzma

data = open(r'C:\Users\Administrator\Downloads\gwrt-雅典娜-cs-02-gwrt2-260818-43-12M-factory.bin','rb').read()
rootfs = 12582912
dir_table = 119787810
frag_table = 119856270

# 目录表 metadata 块链解压（到 frag_table 前）
pos = dir_table
blocks = []
offsets = []
while pos < frag_table:
    hdr = struct.unpack('<H', data[rootfs+pos:rootfs+pos+2])[0]
    comp = not (hdr & 0x8000)
    sz = hdr & 0x7fff
    payload = data[rootfs+pos+2:rootfs+pos+2+sz]
    if comp:
        payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
    blocks.append(payload)
    offsets.append(pos - dir_table)
    pos += 2 + sz
    if len(blocks) > 120:
        break

# root: start_block=62952, offset=7444, file_size=260
sb, off, total = 62952, 7444, 260
# 找到包含 sb 的块
bidx = None
for i, o in enumerate(offsets):
    if o <= sb:
        bidx = i
    else:
        break
print('target block idx=%s off=%d blocks_total=%d' % (bidx, offsets[bidx] if bidx is not None else None, len(blocks)))
blk = blocks[bidx]
print('block len=%d' % len(blk))
print('=== hex dump root dir data (offset %d, %d bytes) ===' % (off, total))
seg = blk[off:off+total]
for i in range(0, len(seg), 16):
    chunk = seg[i:i+16]
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('%04x: %-47s %s' % (i, chunk.hex(), asc))
