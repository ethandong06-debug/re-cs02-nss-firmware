# -*- coding: utf-8 -*-
import struct, lzma

data = open(r'C:\Users\Administrator\Downloads\gwrt-雅典娜-cs-02-gwrt2-260818-43-12M-factory.bin','rb').read()
rootfs = 12582912
dir_table = 119787810
frag_table = 119856270

# dir 表完整解压
pos = dir_table
blocks = []
while pos < frag_table:
    hdr = struct.unpack('<H', data[rootfs+pos:rootfs+pos+2])[0]
    comp = not (hdr & 0x8000)
    sz = hdr & 0x7fff
    payload = data[rootfs+pos+2:rootfs+pos+2+sz]
    if comp:
        payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
    blocks.append(payload)
    pos += 2 + sz
dirstream = b''.join(blocks)

# root dir: start_block=62952, file_size=260, offset=7444
sb, off, total = 62952, 7444, 260
p = sb
length = 0
cur_off = off
while length < total and p < len(dirstream):
    # 每个 metadata 块已解压; 我们直接从 p 开始读 (dirstream 已经是解压后连续流)
    payload = dirstream[p:p+4096]  # 元数据块最大 8KB
    q = cur_off
    cur_off = 0
    while q + 12 <= len(payload):
        # header: count(4) start_block(4) inode_number(4)
        count, hsb, hino = struct.unpack('<III', payload[q:q+12])
        q += 12
        for _ in range(count + 1):
            if q + 8 > len(payload):
                break
            eoff, eino, etype, nlen = struct.unpack('<HHHH', payload[q:q+8])
            q += 8
            # 尝试 nlen 直接作为名字长度
            name = payload[q:q+nlen]
            q += nlen
            full_ino = (hino & 0xffff0000) | eino
            print('count=%d sb=%d ino_base=%d eoff=%d eino=%d type=%d nlen=%d name=%r full_ino=%d' % (count, hsb, hino, eoff, eino, etype, nlen, name, full_ino))
            length += 1
        if length >= total:
            break
    if length >= total:
        break
    p += 1
