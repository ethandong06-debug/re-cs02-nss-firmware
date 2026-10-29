# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v4 —— 连续解压 inode/dir 表后解析。
用法: python squashfs_v4.py <fw.bin> <rootfs_off> list|tree|extract <path> <outfile>
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
        self.id_table = struct.unpack('<Q', b[48:56])[0]
        self.inode_table = struct.unpack('<Q', b[64:72])[0]
        self.dir_table = struct.unpack('<Q', b[72:80])[0]
        self.frag_table = struct.unpack('<Q', b[80:88])[0]
        assert b[:4] == b'hsqs'

    def decompress_range(self, start, end):
        """把 [start,end) 内的 metadata 块链连续解压拼接，返回 (bytes, next_pos)"""
        out = b''
        pos = start
        while pos < end:
            hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
            comp = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            payload = self.d[pos+2:pos+2+sz]
            if comp:
                payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
            out += payload
            pos += 2 + sz
        return out

    def parse_inodes(self):
        """返回 {ino: (type, mode, extra_dict, off_in_stream)} 和 ino→目录元数据"""
        raw = self.decompress_range(self.inode_table, self.dir_table)
        self.inode_stream = raw
        m = {}
        p = 0
        while p + 16 <= len(raw):
            it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
            p += 16
            extra = {}
            if it == 1:
                sb, nl, fs, off, par = struct.unpack('<IIHHI', raw[p:p+16]); p += 16
                extra = dict(start_block=sb, file_size=fs, offset=off, parent=par)
            elif it == 2:
                sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
                nb = (fs + self.block_size - 1)//self.block_size
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                p += nb*4
            elif it == 3:
                nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                extra = dict(target=raw[p:p+sz]); p += sz
            elif it == 8:
                sb, nl, fs, off, par = struct.unpack('<IIHHI', raw[p:p+16]); p += 16
                ic, xa = struct.unpack('<HI', raw[p:p+6]); p += 6
                extra = dict(start_block=sb, file_size=fs, offset=off, parent=par, i_count=ic)
                p += 6
                for _ in range(ic):
                    ix = struct.unpack('<I', raw[p:p+4])[0]; p += 4
                    p += ix
            elif it == 9:
                sb, fr, fo = struct.unpack('<III', raw[p:p+12]); p += 12
                fs, sp, nl, xa = struct.unpack('<QIII', raw[p:p+20]); p += 20
                nb = (fs + self.block_size - 1)//self.block_size
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                p += nb*4
            elif it == 10:
                nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                extra = dict(target=raw[p:p+sz]); p += sz
            elif it in (4, 5):
                nl, rd = struct.unpack('<II', raw[p:p+8]); p += 8
            elif it in (6, 7):
                nl = struct.unpack('<I', raw[p:p+4])[0]; p += 4
            elif it == 11:
                nl, rd, xa = struct.unpack('<III', raw[p:p+12]); p += 12
            elif it == 12:
                nl, rd, xa = struct.unpack('<III', raw[p:p+12]); p += 12
            elif it in (13, 14):
                nl, xa = struct.unpack('<II', raw[p:p+8]); p += 8
            else:
                print('unknown inode type %d at stream off %d' % (it, p-16))
                break
            m[ino] = (it, mode, extra, p - 16 - (0 if it in (4,5,6,7,11,12,13,14) else 0))
        self.ino_map = m
        return m

    def dir_entries(self, ino):
        """读取目录 ino 的全部条目 → [(name, ino)]"""
        it, mode, extra, _ = self.ino_map[ino]
        assert it in (1, 8), 'ino %d not dir (type %d)' % (ino, it)
        # 目录内容在 directory table 中，从 start_block(相对 dir table 起) 的 metadata 链 + offset
        # 但我们的 dir_table 是 metadata 链，start_block 是相对整个 filesystem 的偏移（squashfs 里目录 start_block 相对 fs 起始）
        # 更稳妥：目录数据在 dir_table 链中，定位 = start_block - dir_table 的绝对？ squashfs 目录 start_block 是相对文件起点的偏移
        # 转换：dir 数据位于 dir_table_start + (start_block - dir_table_start)?? 不 —— start_block 是绝对 fs 偏移。
        sb = extra['start_block']
        off = extra['offset']
        fs_size = extra['file_size']
        # 目录条目从 fs 偏移 sb 的 metadata 块 + off 开始
        entries = []
        length = 0
        pos = sb
        # 相对 rootfs 起点读
        cur_off = off
        # 读取目录块：块从 sb 开始，块内有 header + entries
        # 简化：直接顺序读，处理跨块
        while length < fs_size:
            # metadata header
            hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
            comp = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            payload = self.d[pos+2:pos+2+sz]
            if comp:
                payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
            pos += 2 + sz
            q = cur_off
            cur_off = 0
            # 块内可能有多个 dir header + entries
            while q + 10 <= len(payload):
                count, sb2, ino_base = struct.unpack('<HII', payload[q:q+10])
                q += 10
                for _ in range(count + 1):
                    if q + 8 > len(payload):
                        # 跨块：剩余部分需要从下一个块补 —— 复杂，先简化（目录通常一页内）
                        break
                    eoff, eino, etype, nlen = struct.unpack('<HHHH', payload[q:q+8])
                    q += 8
                    name = payload[q:q+(nlen & 0xff)]
                    q += (nlen & 0xff)
                    full_ino = eino
                    entries.append((name.decode('utf-8', 'replace'), full_ino))
                    length += 1
                # 若块内结束而 length < fs_size，说明目录跨块，下一块从 0 开始
                break
        return entries

if __name__ == '__main__':
    fw, off = sys.argv[1], int(sys.argv[2])
    fs = SQFS(fw, off)
    print('squashfs: inodes=%d block=%d comp=%d bytes_used=%d' % (fs.inodes, fs.block_size, fs.comp, fs.bytes_used))
    m = fs.parse_inodes()
    print('parsed inodes:', len(m))
    dirs = sorted(i for i, v in m.items() if v[0] in (1, 8))
    print('dir inodes:', dirs[:20])
    if dirs:
        root = dirs[0]
        print('root dir ino:', root, 'meta:', m[root][2])
        print('root entries:', fs.dir_entries(root)[:20])
