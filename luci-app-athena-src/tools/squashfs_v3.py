# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v3 —— 修正 inode 布局（squashfs_fs.h 标准）。
用法: python squashfs_v3.py <fw.bin> <rootfs_off> [list|tree|get <path>|extract <path> <out>]
"""
import struct, lzma, sys, os

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
        self.id_table = struct.unpack('<Q', b[48:56])[0]
        assert b[:4] == b'hsqs'

    def meta_block(self, abs_off):
        hdr = struct.unpack('<H', self.d[abs_off:abs_off+2])[0]
        comp = not (hdr & 0x8000)
        sz = hdr & 0x7fff
        payload = self.d[abs_off+2:abs_off+2+sz]
        if comp:
            payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
        return payload, abs_off + 2 + sz

    def read_meta_chain(self, start_off, byte_off, length):
        """从 metadata 链 start_off 处 byte_off 偏移读 length 字节"""
        out = b''
        pos = start_off
        # 跳到 byte_off 所在块
        consumed = 0
        while consumed + 8192 <= byte_off:
            payload, pos = self.meta_block(pos)
            consumed += 8192
        rem = byte_off - consumed
        while len(out) < length:
            payload, pos = self.meta_block(pos)
            chunk = payload[rem:]
            out += chunk
            rem = 0
            if len(out) > length:
                out = out[:length]
        return out

    def iter_inodes(self):
        """遍历 inode table 所有 metadata 块，产出 (ino, type, mode, extra_dict)"""
        pos = self.inode_table
        while pos < self.dir_table:
            payload, pos = self.meta_block(pos)
            p = 0
            while p + 16 <= len(payload):
                it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', payload[p:p+16])
                p += 16
                extra = {}
                if it == 1:   # basic dir
                    sb, nl, fs, off, par = struct.unpack('<IIHHI', payload[p:p+16]); p += 16
                    extra = dict(start_block=sb, nlink=nl, file_size=fs, offset=off, parent=par)
                elif it == 2: # basic reg
                    sb, fr, fo, fs = struct.unpack('<IIII', payload[p:p+16]); p += 16
                    nb = (fs + self.block_size - 1)//self.block_size
                    extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                    p += nb*4
                elif it == 3: # symlink
                    nl, sz = struct.unpack('<II', payload[p:p+8]); p += 8
                    target = payload[p:p+sz]; p += sz
                    extra = dict(target=target)
                elif it == 8: # ext dir
                    sb, nl, fs, off, par = struct.unpack('<IIHHI', payload[p:p+16]); p += 16
                    ic, xa = struct.unpack('<HI', payload[p:p+6]); p += 6
                    extra = dict(start_block=sb, nlink=nl, file_size=fs, offset=off, parent=par, i_count=ic, xattr=xa)
                    for _ in range(ic):
                        ix = struct.unpack('<I', payload[p:p+4])[0]; p += 4
                        p += ix
                elif it == 9: # ext reg
                    sb, fr, fo = struct.unpack('<III', payload[p:p+12]); p += 12
                    fs, sp, nl, xa = struct.unpack('<QIII', payload[p:p+20]); p += 20
                    nb = (fs + self.block_size - 1)//self.block_size
                    extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs, sparse=sp, nlink=nl, xattr=xa)
                    p += nb*4
                elif it == 10: # ext symlink
                    nl, sz = struct.unpack('<II', payload[p:p+8]); p += 8
                    target = payload[p:p+sz]; p += sz
                    extra = dict(target=target)
                elif it in (4, 5): # blk/chr
                    nl, rd = struct.unpack('<II', payload[p:p+8]); p += 8
                elif it in (6, 7): # fifo/sock
                    nl = struct.unpack('<I', payload[p:p+4])[0]; p += 4
                elif it == 11: # ext blk
                    nl, rd, xa = struct.unpack('<III', payload[p:p+12]); p += 12
                elif it == 12: # ext chr
                    nl, rd, xa = struct.unpack('<III', payload[p:p+12]); p += 12
                elif it in (13, 14): # ext fifo/sock
                    nl, xa = struct.unpack('<II', payload[p:p+8]); p += 8
                else:
                    return
                yield ino, it, mode, extra
                if ino >= self.inodes:
                    return

    def read_file(self, extra):
        """读取常规文件内容（支持 fragment）"""
        fs = extra['file_size']
        out = b''
        pos = extra['start_block']
        nb = (fs + self.block_size - 1)//self.block_size
        for i in range(nb):
            # block_list 在 inode 里，但我们没保存 —— 这里需要重新定位
            pass
        return b''

if __name__ == '__main__':
    fw, off = sys.argv[1], int(sys.argv[2])
    fs = SQFS(fw, off)
    print('inodes=%d block=%d comp=%d root_inode_field=%d bytes_used=%d' % (fs.inodes, fs.block_size, fs.comp, fs.root_inode, fs.bytes_used))
    count = 0
    dirs = []
    for ino, it, mode, extra in fs.iter_inodes():
        count += 1
        if it in (1, 8):
            dirs.append((ino, extra.get('file_size')))
        if count <= 5:
            print('ino=%d type=%d mode=%o extra=%s' % (ino, it, mode, extra))
    print('total parsed:', count)
    print('dir count:', len(dirs), 'first dirs:', dirs[:5])
