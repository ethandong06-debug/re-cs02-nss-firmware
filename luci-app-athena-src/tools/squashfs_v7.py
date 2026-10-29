# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器 v7 —— 完整遍历 + 文件提取。
关键修正: type8(ldir) 固定头=16+24=40字节; index条目=index(4)+start_block(4)+size(4)+name[size]。
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
            if it not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
                break
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
                # ldir 固定头 24 字节(base16之外): nlink4+file_size4+start_block4+parent4+i_count2+offset2+pad4, 之后 index 列表
                nl, fs = struct.unpack('<II', raw[p:p+8]); p += 8
                sb = struct.unpack('<I', raw[p:p+4])[0]; p += 4
                parent = struct.unpack('<I', raw[p:p+4])[0]; p += 4
                i_count, off = struct.unpack('<HH', raw[p:p+4]); p += 4
                p += 4  # padding
                extra = dict(start_block=sb, file_size=fs, offset=off)
                # index 条目: index(4)+start_block(4)+size(4)+name[size]
                # 本固件 size 字段与实际 name 长度差 1, 用可打印 run 贪婪推进
                idx_list = []
                while True:
                    if p + 12 > len(raw):
                        break
                    q = p + 12
                    nq = q
                    while nq < len(raw) and 32 <= raw[nq] < 127:
                        nq += 1
                    name = raw[q:nq]
                    if len(name) < 3:
                        break
                    nxt = nq
                    if nxt + 16 <= len(raw):
                        t2 = struct.unpack('<H', raw[nxt:nxt+2])[0]
                        if t2 in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
                            idx_list.append(name)
                            p = nxt
                            break
                    idx_list.append(name)
                    p = nq
                extra['index'] = idx_list
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
            self.ino_map[ino] = (it, mode, extra)
        # fragment 查找表: frag_table 处直接是 u64 数组 (每项指向包含 fragment entries 的 metadata 块)
        self.frag_lookup = []
        if self.frag_table != 0xffffffffffffffff and self.frag_table < self.bytes_used:
            pos = self.frag_table
            while pos + 8 <= self.bytes_used and pos + 8 <= len(self.d):
                v = struct.unpack('<Q', self.d[pos:pos+8])[0]
                if v == 0 or v >= self.bytes_used:
                    break
                self.frag_lookup.append(v)
                pos += 8
        self.frag_blocks = []  # 按需懒加载 (frag_idx -> (start_block, size))

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
        # 从 start_block 对应的 metadata 块起逐块解压，拼接连续字节流直至覆盖 [off, off+total)
        pos = self.dir_table + sb
        buf = b''
        while len(buf) < off + total and pos + 2 <= len(self.d):
            hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
            comp = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            if sz == 0:
                break
            payload = self.d[pos+2:pos+2+sz]
            if comp:
                payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
            buf += payload
            pos += 2 + sz
        if len(buf) < off + total:
            return entries
        data = buf[off:off+total]
        q = 0
        consumed = 0
        while consumed < total:
            if q + 12 > len(data):
                break
            count, sb2, ino_base = struct.unpack('<III', data[q:q+12])
            q += 12
            consumed += 12
            for _ in range(count + 1):
                if q + 8 > len(data):
                    break
                eoff, eino, etype, nlen = struct.unpack('<HHHH', data[q:q+8])
                q += 8
                name = data[q:q+nlen+1]
                q += nlen + 1
                consumed += 8 + nlen + 1
                # 权威公式 (内核 fs/squashfs/dir.c): ino = dirh.inode_number + (short)dirent.inode_number
                short_ino = eino - 0x10000 if eino & 0x8000 else eino
                full_ino = ino_base + short_ino
                entries.append((name.decode('utf-8', 'replace'), full_ino))
            if consumed >= total:
                break
        return entries

    def read_block(self, pos):
        """读取一个无头 XZ 数据块 (sasquatch 变体: 数据块直接是 xz 流, 无 2 字节头). 返回 (解压数据, 下一块位置)."""
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        feed = self.d[pos:pos + 262144 + 4096]
        out = b''
        p = 0
        while p < len(feed) and not dec.eof:
            chunk = feed[p:p+65536]
            out += dec.decompress(chunk)
            p += len(chunk)
            if len(out) > self.block_size:
                break
        return out, pos + p

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
            entry = self._frag_entry(frag_idx)
            if entry is not None:
                sb, sz = entry
                payload, _ = self.read_block(sb)
                out += payload[fo:fo + (fs % self.block_size)]
        return out[:fs]

    def _frag_entry(self, frag_idx):
        """从 fragment 查找表定位并读取 16B fragment entry (start_block(8)+size(4)+unused(4)).
        lookup[i] 指向包含 fragment entry 的 metadata 块 (带头)."""
        if frag_idx >= len(self.frag_lookup) * 512:
            return None
        blk_base = self.frag_lookup[frag_idx // 512]
        in_blk = (frag_idx % 512) * 16
        payload = self._read_meta_block(blk_base)
        if in_blk + 16 > len(payload):
            return None
        sb, sz = struct.unpack('<QI', payload[in_blk:in_blk+12])
        return sb, sz

    def _read_meta_block(self, pos):
        """读取一个带头 metadata 块: 2B头(bit15=压缩标志, 低15位=压缩后长度), xz 解压."""
        hdr = struct.unpack('<H', self.d[pos:pos+2])[0]
        comp = not (hdr & 0x8000)
        sz = hdr & 0x7fff
        payload = self.d[pos+2:pos+2+sz]
        if comp:
            payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
        return payload

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
    root = fs.inodes if fs.inodes in fs.ino_map else max(fs.ino_map)
    print('root ino =', root, fs.ino_map.get(root, 'MISSING'))
    if sys.argv[3] == 'tree':
        out = []
        fs.walk(root, '', out)
        for p, t, s in out:
            print('%s\t%s\t%d' % (t, p, s))
    elif sys.argv[3] == 'root':
        print('root entries:', fs.dir_entries(root))
    elif sys.argv[3] == 'extract' and len(sys.argv) >= 6:
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
                    if cin in fs.ino_map:
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
