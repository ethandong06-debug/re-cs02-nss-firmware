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

# 第 1144 个 inode 在 44032 (type8 ino=663)
p8 = 44032
# 下个 inode 候选起点：ac56 = 44118
# 验证 ac56 是否 inode 头
for cand in (44118, 44114, 44120, 44122, 44110):
    it, mode = struct.unpack('<HH', raw[cand:cand+4])
    ino = struct.unpack('<I', raw[cand+12:cand+16])[0]
    print('cand %d: type=%d mode=%04x ino=%d' % (cand, it, mode, ino))

# 尝试 index 起点 + size 宽度组合，从 p8 的头部字段推断
# 先猜头部额外字节 hdr_extra，index 从 p8+16+hdr_extra 开始
# 约束1: index 条目 = index(4) start_block(4) size(2或4) name[size]
# 约束2: 解析若干条后正好停在 44118（下一个 inode 起点）
def parse_idx(start, size_w, end_expected):
    p = start
    items = []
    guard = 0
    while p + 8 + size_w <= end_expected and guard < 50:
        idx, sbx = struct.unpack('<II', raw[p:p+8])
        if size_w == 4:
            szf = struct.unpack('<I', raw[p+8:p+12])[0]
        else:
            szf = struct.unpack('<H', raw[p+6:p+8])[0]
        if szf < 3 or szf > 300:
            return None, 'size %d' % szf
        name = raw[p+8+size_w:p+8+size_w+szf]
        if not all(32 <= b < 127 for b in name):
            return None, 'unprintable'
        items.append((idx, sbx, szf, name[:20]))
        p += 8 + size_w + szf
        guard += 1
    if p != end_expected:
        return items, 'end %d != %d' % (p, end_expected)
    return items, 'ok'

for hdr_extra in range(0, 26):
    for size_w in (2, 4):
        start = p8 + 16 + hdr_extra
        items, msg = parse_idx(start, size_w, 44118)
        if items is not None and msg == 'ok':
            print('HIT hdr_extra=%d size_w=%d items=%d' % (hdr_extra, size_w, len(items)))
            for it in items[:5]:
                print('   ', it)
        elif items and msg.startswith('end'):
            pass  # 解析出合法名字但终点不对，可能是条目数更多
