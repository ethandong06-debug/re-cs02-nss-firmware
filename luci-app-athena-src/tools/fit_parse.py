# -*- coding: utf-8 -*-
"""解析 OpenWrt FIT (Flattened Image Tree) 固件结构。
用法: python fit_parse.py <firmware.bin>
输出: images/ 节点树 + 每个 data 分区的偏移/大小/压缩方式
"""
import struct, sys, os

FDT_BEGIN_NODE = 1
FDT_END_NODE   = 2
FDT_PROP       = 3
FDT_NOP        = 4
FDT_END        = 9

def rd32(b, o):
    return struct.unpack(">I", b[o:o+4])[0]

def align4(n):
    return (n + 3) & ~3

def parse_fdt(data, base_off=0):
    assert data[base_off:base_off+4] == b'\xd0\x0d\xfe\xed', "not a FDT/FIT"
    totalsize = rd32(data, base_off+4)
    off_struct = rd32(data, base_off+8)
    off_strings = rd32(data, base_off+12)
    size_strings = rd32(data, base_off+32)
    size_struct = rd32(data, base_off+36)
    print("FIT totalsize=%d (%.2f MB) struct_off=%d strings_off=%d" % (totalsize, totalsize/1048576, off_struct, off_strings))
    strings = data[base_off+off_strings : base_off+off_strings+size_strings]

    def getstr(idx):
        end = strings.find(b'\0', idx)
        return strings[idx:end].decode('utf-8', 'replace')

    # 遍历 struct block
    nodes = []          # (depth, name)
    props = {}          # path -> {propname: (len, value_bytes)}
    path = []
    o = base_off + off_struct
    end = base_off + off_struct + size_struct
    while o < end:
        tok = rd32(data, o); o += 4
        if tok == FDT_BEGIN_NODE:
            name_end = data.find(b'\0', o)
            name = data[o:name_end].decode('utf-8', 'replace')
            o = align4(name_end + 1)
            path.append(name)
            props["/".join(path)] = {}
        elif tok == FDT_END_NODE:
            path.pop()
        elif tok == FDT_PROP:
            plen = rd32(data, o); poff = rd32(data, o+4); o += 8
            val = data[o:o+plen]; o = align4(o+plen)
            pname = getstr(poff)
            if path:
                props["/".join(path)][pname] = val
        elif tok == FDT_NOP:
            pass
        elif tok == FDT_END:
            break
        else:
            print("unknown token %d at %d" % (tok, o-4))
            break
    return props

def u32v(v):
    return struct.unpack(">I", v[:4])[0] if len(v) >= 4 else None

def main(path):
    with open(path, 'rb') as f:
        data = f.read()
    print("file size = %d (%.2f MB)" % (len(data), len(data)/1048576))
    props = parse_fdt(data, 0)
    # 按路径打印节点与关键属性
    for p in sorted(props):
        depth = p.count('/')
        indent = "  " * depth
        print("%s[%s]" % (indent, p))
        for k, v in props[p].items():
            if k == 'data':
                print("%s   data=<inline %d bytes>" % (indent, len(v)))
            elif k in ('data-offset', 'data-size', 'load', 'entry', 'size'):
                print("%s   %s=%s" % (indent, k, u32v(v)))
            elif k == 'hash-1' or k == 'hash':
                continue
            else:
                txt = v.rstrip(b'\0').decode('utf-8', 'replace')
                print("%s   %s=%r" % (indent, k, txt))

    # 汇总可提取的 data 分区
    print("\n=== DATA PARTITIONS ===")
    for p in sorted(props):
        pr = props[p]
        if 'data' in pr and len(pr['data']) > 0:
            print("INLINE %s : %d bytes" % (p, len(pr['data'])))
        elif 'data-offset' in pr and 'data-size' in pr:
            off = u32v(pr['data-offset'])
            sz = u32v(pr['data-size'])
            comp = pr.get('compression', b'').rstrip(b'\0').decode('utf-8', 'replace')
            typ = pr.get('type', b'').rstrip(b'\0').decode('utf-8', 'replace')
            print("EXTERNAL %s : offset=%d size=%d comp=%s type=%s" % (p, off, sz, comp, typ))

if __name__ == '__main__':
    main(sys.argv[1])
