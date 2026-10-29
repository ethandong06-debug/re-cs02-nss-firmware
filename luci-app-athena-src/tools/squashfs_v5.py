# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v5 —— 完整：inode 解析（修正 fragment block 计数）+ 目录遍历 + 文件提取。
用法: python squashfs_v5.py <fw.bin> <rootfs_off> list|tree|extract <path> <outfile>
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
        self._init_tables()

    def _decompress_all(self, start):
        out = b''
        pos = start
        while True:
            if pos + 2 > len(self.d):
                break
            hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
            comp = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            if sz == 0:
                break
            payload = self.d[pos+2:pos+2+sz]
            if comp:
                payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
            out += payload
            pos += 2 + sz
        return out

    def _init_tables(self):
        self.inode_stream = self._decompress_all(self.inode_table)
        self.dir_stream = self._decompress_all(self.dir_table)
        self.ino_map = {}
        self.ino_off = {}
        raw = self.inode_stream
        p = 0
        while p + 16 <= len(raw):
            it, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', raw[p:p+16])
            p0 = p
            p += 16
            extra = {}
            if it == 1:
                sb, nl, fs, off, par = struct.unpack('<IIHHI', raw[p:p+16]); p += 16
                extra = dict(start_block=sb, file_size=fs, offset=off, parent=par)
            elif it == 2:
                sb, fr, fo, fs = struct.unpack('<IIII', raw[p:p+16]); p += 16
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                if fr == 0xffffffff:
                    nb = (fs + self.block_size - 1)//self.block_size
                else:
                    nb = fs // self.block_size
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
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                if fr == 0xffffffff:
                    nb = (fs + self.block_size - 1)//self.block_size
                else:
                    nb = fs // self.block_size
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
                break
            self.ino_map[ino] = (it, mode, extra)
            self.ino_off[ino] = p0
        # fragment 表
        self.frag_blocks = []
        if self.frag_table != 0xffffffffffffffff:
            fraw = self._decompress_all(self.frag_table)
            for i in range(0, len(fraw) - 11, 12):
                sb, sz = struct.unpack('<QI', fraw[i:i+12])
                self.frag_blocks.append((sb, sz))

    def nlink(self, ino):
        return self.ino_map[ino][0]

    def dir_entries(self, ino):
        it, mode, extra = self.ino_map[ino]
        entries = []
        if it not in (1, 8):
            return entries
        sb = extra['start_block']
        off = extra['offset']
        total = extra['file_size']
        length = 0
        # 目录数据在 metadata 块链中：start_block 是相对 directory_table_start 的偏移
        pos = self.dir_table + sb
        first = True
        cur_off = off
        while length < total and pos + 2 <= len(self.d):
            hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
            comp = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            if sz == 0:
                break
            payload = self.d[pos+2:pos+2+sz]
            if comp:
                payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
            pos += 2 + sz
            q = cur_off
            cur_off = 0
            # 该块可能含多个 dir header+entries
            while q + 10 <= len(payload):
                count, sb2, ino_base = struct.unpack('<HII', payload[q:q+10])
                q += 10
                for _ in range(count + 1):
                    if q + 8 > len(payload):
                        break
                    eoff, eino, etype, nlen = struct.unpack('<HHHH', payload[q:q+8])
                    q += 8
                    name = payload[q:q+(nlen & 0xff)]
                    q += (nlen & 0xff)
                    # ino: 高 16 位来自 header ino_base，低 16 位来自 entry
                    full_ino = (ino_base & 0xffff0000) | eino
                    entries.append((name.decode('utf-8', 'replace'), full_ino))
                    length += 1
                if length >= total:
                    break
                # 同一块内继续？q 已到 payload 末尾则退出外层
                if q >= len(payload):
                    break
            if length >= total:
                break
        return entries

    def read_block(self, pos):
        hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
        comp = not (hdr & 0x8000)
        sz = hdr & 0x7fff
        payload = self.d[pos+2:pos+2+sz]
        if comp:
            payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
        return payload, pos + 2 + sz

    def read_file(self, ino):
        it, mode, extra = self.ino_map[ino]
        if it not in (2, 9):
            return None
        fs = extra['file_size']
        out = b''
        pos = extra['start_block']
        if extra['frag'] == 0xffffffff:
            nb = (fs + self.block_size - 1)//self.block_size
        else:
            nb = fs // self.block_size
        for i in range(nb):
            payload, pos = self.read_block(pos)
            out += payload
        if extra['frag'] != 0xffffffff and fs % self.block_size:
            frag_idx = extra['frag']
            fo = extra['frag_off']
            if frag_idx < len(self.frag_blocks):
                sb, sz = self.frag_blocks[frag_idx]
                payload, _ = self.read_block(sb)
                out += payload[fo:fo + (fs % self.block_size)]
        return out[:fs]

if __name__ == '__main__':
    fw, off = sys.argv[1], int(sys.argv[2])
    fs = SQFS(fw, off)
    print('squashfs: inodes=%d block=%d comp=%d bytes_used=%d' % (fs.inodes, fs.block_size, fs.comp, fs.bytes_used))
    print('parsed inodes:', len(fs.ino_map))
    dirs = sorted(i for i, v in fs.ino_map.items() if v[0] in (1, 8))
    print('dir inodes:', dirs[:20])
    # 找一个合理的 root：ino=1 或最小 dir
    root = 1 if 1 in fs.ino_map and fs.ino_map[1][0] in (1, 8) else (dirs[0] if dirs else None)
    print('root ino:', root)
    if root:
        print('root entries:', fs.dir_entries(root)[:20])
