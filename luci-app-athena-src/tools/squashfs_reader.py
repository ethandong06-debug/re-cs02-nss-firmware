# -*- coding: utf-8 -*-
"""squashfs 4.0 只读解析器（纯 Python，支持 xz 压缩）。
用法:
  from squashfs_reader import SquashFS
  fs = SquashFS(path, rootfs_offset)
  fs.walk()            # 递归打印文件树
  fs.extract('/etc/config/network')  # 提取单文件内容(bytes)
"""
import struct, lzma, os, sys

COMPRESSION_XZ = 4
METADATA_SIZE = 8192

class MetadataReader:
    """metadata 块链读取器：从给定起始偏移顺序解压 metadata 块。"""
    def __init__(self, data, base, comp):
        self.data = data
        self.base = base
        self.comp = comp

    def read(self, offset, length):
        """从相对 base 的 offset 读取 length 字节，自动跨 metadata 块。"""
        out = b''
        pos = offset
        while len(out) < length:
            hdr = struct.unpack('<H', self.data[self.base+pos:self.base+pos+2])[0]
            compressed = not (hdr & 0x8000)
            sz = hdr & 0x7fff
            payload = self.data[self.base+pos+2:self.base+pos+2+sz]
            if compressed:
                if self.comp == COMPRESSION_XZ:
                    payload = lzma.decompress(payload, format=lzma.FORMAT_XZ)
                elif self.comp == 1:
                    import zlib
                    payload = zlib.decompress(payload)
                else:
                    raise NotImplementedError('compression %d' % self.comp)
            out += payload
            pos += 2 + sz
        return out[:length]

class SquashFS:
    def __init__(self, fw_path, off):
        with open(fw_path, 'rb') as f:
            f.seek(off)
            self.data = f.read()
        b = self.data
        self.magic = b[0:4]
        self.inodes, mkfs_time, self.block_size, fragments = struct.unpack('<IIII', b[4:20])
        self.comp, block_log, flags, no_ids = struct.unpack('<HHHH', b[20:28])
        vmaj, vmin = struct.unpack('<HH', b[28:32])
        self.root_inode = struct.unpack('<Q', b[32:40])[0]
        self.bytes_used = struct.unpack('<Q', b[40:48])[0]
        self.id_table_start, self.xattr_id_table_start = struct.unpack('<QQ', b[48:64])
        self.inode_table_start, self.directory_table_start = struct.unpack('<QQ', b[64:80])
        self.fragment_table_start, self.lookup_table_start = struct.unpack('<QQ', b[80:96])
        assert self.magic == b'hsqs' and vmaj == 4, 'not squashfs 4.0'
        self.mr_inode = MetadataReader(self.data, self.inode_table_start, self.comp)
        self.mr_dir = MetadataReader(self.data, self.directory_table_start, self.comp)

    # ---- inode 解析 ----
    def read_inode(self, ref):
        """ref 为相对 inode_table_start 的偏移，返回 (type, fields_dict)"""
        base = self.mr_inode.read(ref, 16)
        itype, mode, uid, gid, mtime, ino = struct.unpack('<HHHHII', base)
        f = dict(itype=itype, mode=mode, uid=uid, gid=gid, mtime=mtime, ino=ino)
        off = 16
        if itype == 1:   # basic dir
            start_block, nlink, file_size, offset, parent = struct.unpack('<IIHHI', self.mr_inode.read(ref+off, 16))
            f.update(start_block=start_block, nlink=nlink, file_size=file_size, offset=offset, parent=parent)
        elif itype == 2: # basic reg
            start_block, frag, frag_off, file_size = struct.unpack('<QIII', self.mr_inode.read(ref+off, 20))
            f.update(start_block=start_block, frag=frag, frag_off=frag_off, file_size=file_size)
        elif itype == 3: # symlink
            nlink, sz = struct.unpack('<II', self.mr_inode.read(ref+off, 8))
            target = self.mr_inode.read(ref+off+8, sz)
            f.update(nlink=nlink, target=target)
        elif itype == 8: # extended dir
            start_block, nlink, file_size, offset, parent = struct.unpack('<IIHHI', self.mr_inode.read(ref+off, 16))
            i_count, xattr = struct.unpack('<HI', self.mr_inode.read(ref+off+16, 6))
            f.update(start_block=start_block, nlink=nlink, file_size=file_size, offset=offset, parent=parent, i_count=i_count, xattr=xattr)
        elif itype == 9: # extended reg
            start_block, frag, frag_off, file_size, sparse, nlink = struct.unpack('<QIIIII', self.mr_inode.read(ref+off, 28))
            f.update(start_block=start_block, frag=frag, frag_off=frag_off, file_size=file_size, sparse=sparse, nlink=nlink)
        elif itype == 10: # extended symlink
            nlink, sz = struct.unpack('<II', self.mr_inode.read(ref+off, 8))
            target = self.mr_inode.read(ref+off+8, sz)
            f.update(nlink=nlink, target=target)
        else:
            raise NotImplementedError('inode type %d' % itype)
        return itype, f

    # ---- 目录读取 ----
    def read_dir(self, ref):
        """读取目录 inode 的全部 entry，返回 [(name, inode_ref)]"""
        itype, f = self.read_inode(ref)
        assert itype in (1, 8), 'not a dir'
        entries = []
        length = 0
        block = f['start_block']
        offset = f['offset']
        total = f['file_size']
        while length < total:
            # dir header: count(2) start_block(4) inode_number(4)
            hdr = self.mr_dir.read(block*1 + 0, 0)  # placeholder
            # 直接从 (block,offset) 读取
            hdr = self._dir_read(block, offset, 10)
            count, start_block, ino_base = struct.unpack('<HII', hdr)
            length += 10
            offset += 10
            for i in range(count + 1):
                ent = self._dir_read(block, offset, 8)
                ent_off, ent_ino, etype, nlen = struct.unpack('<HHHH', ent)
                name = self._dir_read(block, offset+8, nlen & 0xff)
                if nlen & 0x100:  # name 跨块压缩标志
                    name = self._dir_read(block, offset+8, nlen & 0xff)
                ino_ref = ((ino_base & 0xffff0000) | ent_ino) if (ino_base >> 16) else ent_ino
                entries.append((name.rstrip(b'\0').decode('utf-8','replace'), ino_ref))
                offset += 8 + (nlen & 0xff)
                length += 8 + (nlen & 0xff)
            # 若长度未到 total，可能继续下一 header（metadata 块内连续）
            if length < total and offset >= 8192:
                block += 8192
                offset = 0
        return entries

    def _dir_read(self, block, offset, length):
        """从 directory_table 相对 block(字节) + offset 读 length 字节"""
        return self.mr_dir.read(block + offset, length)

    # ---- 文件读取 ----
    def read_file(self, ref, max_bytes=None):
        itype, f = self.read_inode(ref)
        assert itype in (2, 9), 'not a regular file'
        size = f['file_size']
        if max_bytes and size > max_bytes:
            return None  # 太大，跳过
        out = b''
        nblocks = (size + self.block_size - 1) // self.block_size
        pos = f['start_block']
        # 读 block_list
        bl = self.mr_inode.read(ref + (28 if itype == 9 else 20), nblocks * 4)
        for i in range(nblocks):
            v = struct.unpack('<I', bl[i*4:i*4+4])[0]
            bsz = v & 0xffffff
            comp = not (v & 0x1000000)  # bit24=1 表示未压缩
            chunk = self.data[pos:pos+bsz]
            if comp:
                if self.comp == COMPRESSION_XZ:
                    chunk = lzma.decompress(chunk, format=lzma.FORMAT_XZ)
                elif self.comp == 1:
                    import zlib
                    chunk = zlib.decompress(chunk)
            out += chunk
            pos += bsz
        # fragment 尾部
        if f.get('frag', 0xffffffff) != 0xffffffff and f.get('frag_off', 0) and size % self.block_size:
            frag = f['frag']
            foff = f['frag_off']
            fsb, fsz = self.read_fragment(frag)
            frag_data = self.data[fsb:fsb+fsz]
            if self.comp == COMPRESSION_XZ:
                frag_data = lzma.decompress(frag_data, format=lzma.FORMAT_XZ)
            out += frag_data[foff:foff + (size % self.block_size)]
        return out[:size]

    def read_fragment(self, idx):
        # fragment table：metadata 块链，每块 512 entries
        blk = idx // 512
        off = (idx % 512) * 12
        # 定位第 blk 个 metadata 块：fragment_table_start 处是 metadata 块链
        base = self.fragment_table_start
        for _ in range(blk):
            hdr = struct.unpack('<H', self.data[base:base+2])[0]
            base += 2 + (hdr & 0x7fff)
        mr = MetadataReader(self.data, base, self.comp)
        ent = mr.read(off, 12)
        start_block, size = struct.unpack('<QI', ent)
        return start_block, size

    # ---- 遍历 ----
    def walk(self, ref=None, prefix='', out=None):
        if ref is None:
            ref = self.root_inode
        itype, f = self.read_inode(ref)
        if itype in (1, 8):
            if out is not None:
                out.append((prefix or '/', 'dir'))
            for name, iref in self.read_dir(ref):
                self.walk(iref, prefix + '/' + name, out)
        else:
            if out is not None:
                out.append((prefix, 'file', f.get('file_size', 0), itype))
        return out

    def list_all(self):
        out = []
        self.walk(None, '', out)
        return out

if __name__ == '__main__':
    fw = sys.argv[1]
    off = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    fs = SquashFS(fw, off)
    print('squashfs: inodes=%d block_size=%d comp=%d bytes_used=%d' % (fs.inodes, fs.block_size, fs.comp, fs.bytes_used))
    n = 0
    for item in fs.list_all():
        if len(item) == 3:
            print('%s  [dir]' % item[0])
        else:
            print('%s  (%s, %d bytes)' % (item[0], ['','','reg','sym','','','','','dir','reg','sym'][item[3]] if item[3] < 11 else '?', item[2]))
        n += 1
        if n > 400:
            print('... (truncated)')
            break
