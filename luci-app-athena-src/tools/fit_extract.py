# -*- coding: utf-8 -*-
"""从 FIT 中提取 inline data 分区（kernel / fdt），按 data 属性在 struct 中的偏移切出。"""
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

def main(path, outdir):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:4] == b'\xd0\x0d\xfe\xed'
    off_struct = rd32(data, 8)
    off_strings = rd32(data, 12)
    size_strings = rd32(data, 32)
    size_struct = rd32(data, 36)
    strings = data[off_strings:off_strings+size_strings]
    def getstr(idx):
        end = strings.find(b'\0', idx)
        return strings[idx:end].decode('utf-8', 'replace')
    stack = []                     # 路径栈
    nodes = {}                     # path -> {propname: (voff, vlen)}
    o = off_struct
    end = off_struct + size_struct
    while o < end:
        tok = rd32(data, o); o += 4
        if tok == FDT_BEGIN_NODE:
            name_end = data.find(b'\0', o)
            name = data[o:name_end].decode('utf-8', 'replace')
            o = align4(name_end + 1)
            stack.append(name)
        elif tok == FDT_END_NODE:
            stack.pop()
        elif tok == FDT_PROP:
            plen = rd32(data, o); poff = rd32(data, o+4); o += 8
            pname = getstr(poff)
            if stack:
                p = "/".join(stack)
                nodes.setdefault(p, {})[pname] = (o, plen)
            o = align4(o+plen)
        elif tok == FDT_NOP:
            pass
        elif tok == FDT_END:
            break
    os.makedirs(outdir, exist_ok=True)
    for path in sorted(nodes):
        for pname, (voff, vlen) in nodes[path].items():
            if pname == 'data' and vlen > 0:
                fn = path.replace('/', '-').replace('@', '-') + '.bin'
                with open(os.path.join(outdir, fn), 'wb') as f:
                    f.write(data[voff:voff+vlen])
                print("EXTRACT %s -> %s (%d bytes, file off %d)" % (path, fn, vlen, voff))
            elif pname in ('compression', 'type', 'os', 'arch', 'description'):
                txt = data[voff:voff+vlen].rstrip(b'\0').decode('utf-8', 'replace')
                print("  %s.%s=%s" % (path, pname, txt))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
