# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v2 —— 从 inode table 顺序遍历所有 inode，再按 inode 编号找 root。
用法: python squashfs_v2.py <fw.bin> <rootfs_off>
"""
import struct, lzma, sys

class SQFS:
    def __init__(self, fw_path, off):
        with open(fw_path, 'rb') as f:
            f.seek(off)
            self.d = f.read()
        b = self.d
        self.inodes = struct.unpack('<I', b[4:8])[0]
        self.block_size = struct.unpack('<I', b[12:16])[0]
        self.comp = struct.unpack('<H', b[20:22])[0]
        self.root_inode = struct.unpack('<Q', b[32:40])[0]
        self.bytes_used = struct.unpack('<Q', b[40:48])[0]
        self.inode_table = struct.unpack('<Q', b[64:72])[0]
        self.dir_table = struct.unpack('<Q', b[72:80])[0]
        self.frag_table = struct.unpack('<Q', b[80:88])[0]
        assert b[:4] == b'hsqs'

    def meta_block(self, abs_off):
        """解压一个 metadata 块，返回 (payload, next_abs_off)"""
        hdr = struct.unpack('<H', self.d[abs_off:abs_off+2])[0]
        comp = not (hdr & 0x8000)
        sz = hdr & 0x7fff
        payload = self.d[abs_off+2:abs_off+2+sz]
        if comp:
            payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
        return payload, abs_off + 2 + sz

    def iter_inodes(self):
        """顺序遍历 inode table 所有 metadata 块，产出 (ino, type, size, extra)。"""
        pos = self.inode_table
        while pos < self.dir_table:
            payload, pos = self.meta_block(pos)
            p = 0
            while p < len(payload):
                it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', payload[p:p+16])
                p += 16
                size = None
                if it == 1:   # basic dir
                    sb, nl, fs, off, par = struct.unpack('<IIHHI', payload[p:p+16]); p += 16
                    size = fs
                elif it == 2: # basic reg
                    sb, fr, fo, fs = struct.unpack('<QIII', payload[p:p+20]); p += 20
                    size = fs
                    nb = (fs + self.block_size - 1)//self.block_size
                    p += nb*4
                elif it == 3: # symlink
                    nl, sz = struct.unpack('<II', payload[p:p+8]); p += 8
                    p += sz
                    size = sz
                elif it == 8: # ext dir
                    sb, nl, fs, off, par = struct.unpack('<IIHHI', payload[p:p+16]); p += 16
                    ic, xa = struct.unpack('<HI', payload[p:p+6]); p += 6
                    size = fs
                    # skip index list
                    if ic > 0:
                        for _ in range(ic):
                            ix = struct.unpack('<I', payload[p:p+4])[0]; p += 4
                            p += ix
                elif it == 9: # ext reg
                    sb, fr, fo, fs, sp, nl = struct.unpack('<QIIIII', payload[p:p+28]); p += 28
                    size = fs
                    nb = (fs + self.block_size - 1)//self.block_size
                    p += nb*4
                elif it == 10: # ext symlink
                    nl, sz = struct.unpack('<II', payload[p:p+8]); p += 8
                    p += sz
                    size = sz
                elif it in (4, 5, 6, 7, 11, 12, 13, 14):
                    # blk/chr/fifo/sock: nlink(4) rdev(4) [+xattr for ext]
                    nl, rd = struct.unpack('<II', payload[p:p+8]); p += 8
                    if it >= 11:
                        xa = struct.unpack('<I', payload[p:p+4])[0]; p += 4
                    size = 0
                else:
                    break
                yield ino, it, size
                if ino >= self.inodes:
                    return
        # end

def main(fw, off):
    fs = SQFS(fw, off)
    print('inodes=%d block=%d comp=%d root_inode_field=%d' % (fs.inodes, fs.block_size, fs.comp, fs.root_inode))
    # 收集所有 inode 编号与类型
    all_ino = {}
    for ino, it, size in fs.iter_inodes():
        all_ino[ino] = (it, size)
    print('parsed inodes:', len(all_ino))
    # root 通常是 ino=1 或最小的 dir inode
    dirs = [(i, v) for i, v in all_ino.items() if v[0] in (1, 8)]
    dirs.sort()
    print('dir inodes (first 15):', dirs[:15])
    print('min ino:', min(all_ino), 'max ino:', max(all_ino))
    # 找 ino=1
    if 1 in all_ino:
        print('ino=1 type=%s size=%s' % (all_ino[1][0], all_ino[1][1]))

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]))
