# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v6 —— 完整遍历 + 文件提取。
用法: python squashfs_v6.py <fw.bin> <rootfs_off> tree|list|extract <path> <outfile>|extract-all <outdir>
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
        self._init()

    def _decompress_range(self, start, end):
        out = b''
        pos = start
        while pos < end and pos + 2 <= len(self.d):
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

    def _init(self):
        self.inode_stream = self._decompress_range(self.inode_table, self.dir_table)
        self.dir_stream = self._decompress_range(self.dir_table, self.frag_table)
        raw = self.inode_stream
        self.ino_map = {}
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
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                nb = (fs + self.block_size - 1)//self.block_size if fr == 0xffffffff else fs // self.block_size
                p += nb*4
            elif it == 3:
                nl, sz = struct.unpack('<II', raw[p:p+8]); p += 8
                extra = dict(target=raw[p:p+sz]); p += sz
            elif it == 8:
                nl, fs = struct.unpack('<II', raw[p:p+8]); p += 8
                off = struct.unpack('<H', raw[p:p+2])[0]; p += 2
                sb = struct.unpack('<I', raw[p:p+4])[0]; p += 4
                ic, isz, xa = struct.unpack('<IHI', raw[p:p+8]); p += 8
                extra = dict(start_block=sb, file_size=fs, offset=off, i_count=ic)
                # index 列表：每条 index(4)+start_block(4)+size(4)+name[size]
                for _ in range(ic):
                    ix, sb2, sz = struct.unpack('<III', raw[p:p+12]); p += 12
                    p += sz
            elif it == 9:
                sb = struct.unpack('<I', raw[p:p+4])[0]; p += 4
                fs, sp = struct.unpack('<QQ', raw[p:p+16]); p += 16
                nl, fr, fo, xa = struct.unpack('<IIII', raw[p:p+16]); p += 16
                extra = dict(start_block=sb, frag=fr, frag_off=fo, file_size=fs)
                nb = (fs + self.block_size - 1)//self.block_size if fr == 0xffffffff else fs // self.block_size
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
                print('WARN: unknown inode type %d at stream offset %d, ino=%d' % (it, p-16, ino))
                break
            self.ino_map[ino] = (it, mode, extra)
        # fragment 表
        self.frag_blocks = []
        if self.frag_table != 0xffffffffffffffff and self.frag_table < self.bytes_used:
            fraw = self._decompress_range(self.frag_table, self.bytes_used)
            for i in range(0, len(fraw) - 11, 12):
                sb, sz = struct.unpack('<QI', fraw[i:i+12])
                self.frag_blocks.append((sb, sz))

    def type_name(self, it):
        return {1:'dir',2:'reg',3:'sym',4:'blk',5:'chr',6:'fifo',7:'sock',8:'dir',9:'reg',10:'sym'}.get(it, str(it))

    def dir_entries(self, ino):
        it, mode, extra = self.ino_map[ino]
        entries = []
        if it not in (1, 8):
            return entries
        sb = extra['start_block']
        off = extra['offset']
        total = extra['file_size']
        length = 0
        pos = self.dir_table + sb
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
            while q + 10 <= len(payload):
                count, sb2, ino_base = struct.unpack('<HII', payload[q:q+10])
                q += 10
                for _ in range(count + 1):
                    if q + 8 > len(payload):
                        break
                    eoff, eino, etype, nlen = struct.unpack('<HHHH', payload[q:q+8])
                    q += 8
                    name = payload[q:q+nlen]
                    q += nlen
                    full_ino = (ino_base & 0xffff0000) | eino
                    entries.append((name.decode('utf-8', 'replace'), full_ino))
                    length += 1
                if length >= total:
                    break
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
        nb = (fs + self.block_size - 1)//self.block_size if extra['frag'] == 0xffffffff else fs // self.block_size
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

    def walk(self, ino, path, out, depth=0):
        it, mode, extra = self.ino_map[ino]
        if it in (1, 8):
            out.append((path, 'dir', 0))
            for name, cin in self.dir_entries(ino):
                if cin in self.ino_map:
                    self.walk(cin, path + '/' + name, out, depth+1)
        elif it in (2, 9):
            out.append((path, 'file', extra['file_size']))
        else:
            out.append((path, self.type_name(it), 0))

if __name__ == '__main__':
    fw, off = sys.argv[1], int(sys.argv[2])
    fs = SQFS(fw, off)
    print('squashfs: inodes=%d block=%d comp=%d bytes_used=%d parsed=%d' % (fs.inodes, fs.block_size, fs.comp, fs.bytes_used, len(fs.ino_map)))
    # root = max inode 或 root_inode 字段语义
    root = fs.inodes if fs.inodes in fs.ino_map else max(fs.ino_map)
    print('root ino =', root, fs.ino_map[root])
    if sys.argv[3] == 'tree':
        out = []
        fs.walk(root, '', out)
        for p, t, s in out:
            print('%s\t%s\t%d' % (t, p, s))
    elif sys.argv[3] == 'root':
        print('root entries:', fs.dir_entries(root))
    elif sys.argv[3] == 'extract' and len(sys.argv) >= 6:
        # 找路径
        target = sys.argv[4]
        found = []
        def find(ino, path):
            it, mode, extra = fs.ino_map[ino]
            if path == target:
                found.append(ino)
                return True
            if it in (1, 8):
                for name, cin in fs.dir_entries(ino):
                    if find(cin, path + '/' + name):
                        return True
            return False
        find(root, '')
        if not found:
            print('NOT_FOUND')
        else:
            data = fs.read_file(found[0])
            if data is None:
                print('NOT_A_FILE')
            else:
                open(sys.argv[5], 'wb').write(data)
                print('EXTRACTED %d bytes' % len(data))
    elif sys.argv[3] == 'extract-all' and len(sys.argv) >= 5:
        outdir = sys.argv[4]
        os.makedirs(outdir, exist_ok=True)
        counter = [0]
        def walk2(ino, path):
            it, mode, extra = fs.ino_map[ino]
            if it in (1, 8):
                for name, cin in fs.dir_entries(ino):
                    walk2(cin, path + '/' + name)
            elif it in (2, 9):
                data = fs.read_file(ino)
                if data is not None:
                    dest = outdir + path
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as f:
                        f.write(data)
                    counter[0] += 1
            elif it in (3, 10):
                dest = outdir + path
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'wb') as f:
                    f.write(b'')
        walk2(root, '')
        print('extracted files:', counter[0])
