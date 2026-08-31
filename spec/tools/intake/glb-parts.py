#!/usr/bin/env python3
"""Read MEASUREMENTS out of a vendor GLB. Never the geometry.

Vendor service documentation increasingly ships as 3D: Dell's interactive repair
guides are Needle Engine scenes pulling plain glTF 2.0 over HTTPS, and the parts
in them are named and at real-world scale. That makes them a source in exactly
the sense a datasheet is - something to READ facts out of and cite, not something
to copy. Nothing this tool emits is geometry. It emits a table of names, sizes
and positions in millimetres, which is what a `vendor-cad` provenance line is
made of; the model built from it is our own simplified drawing, as it would be
from a photograph or a mechanical drawing.

WHAT IT IS FOR is the axis a faceplate figure cannot give you. An orthographic
rear view answers x and y to a tenth of a millimetre and says nothing whatever
about how far a handle stands off the panel. Depth is where this earns its
place - and after that, the parts a face-on view never sees at all: what is
under the lid, where the DIMMs sit, how deep a supply runs.

THREE THINGS WILL GIVE YOU A CONFIDENT WRONG NUMBER, and all three have.

    the names are on GROUP nodes and the geometry is on their children
                    A first reading looked for a mesh on the node called
                    `R740XD_ Riser1`, found none, and reported that the file
                    contained no riser. The meshes hang off unnamed children two
                    or three levels down, so a part's box is the union over its
                    DESCENDANTS. This tool always descends.

    an assembly's box is not a part's width
                    `740XD_PSU_ASSEMBLY` boxes 135.3 wide where the supplies sit
                    on an 89.8 pitch - two of them would overlap by 45 mm. The
                    box is real and it is not a width: something inside it
                    protrudes. Any named node that CONTAINS other named nodes is
                    flagged `assembly` here, and its number should be treated as
                    an envelope until you descend into it.

    one name, many instances
                    `Coolingfan-1` appears 77 times and `2.5 HDD` 71. Union them
                    and you get a box spanning the chassis, which looks like a
                    measurement of a fan and is a measurement of the fan BAY.
                    Instances are listed separately and never merged.

A SCENE THAT LOOKS EMPTY IS PROBABLY DRACO. Counting accessors that carry a
`bufferView` is a tempting one-pass test for "does this file have geometry" and
it is wrong: KHR_draco_mesh_compression puts the vertices in a blob the
extension points at, and leaves POSITION with no bufferView BY DESIGN. 212 of
the R740XD scene's 411 meshes read as empty that way and every one of them is
readable - see glb-view.py, which draws them. Boxes are unaffected either way,
because min/max live in the accessor regardless.

AND THE SCENE IS EXPLODED. Each guide is posed for its own procedure - the
battery guide has the cover lifted clear, which is why the scene bounds exceed
the chassis. Sizes survive that; POSITIONS do not. Take a position only from a
guide that leaves the part where it lives, and say which guide in provenance.

Usage:
    glb-parts.py FILE [pattern] [--face WxH] [--sort size|name|depth]
    glb-parts.py FILE --names           what is named in here at all
"""
import argparse
import json
import pathlib
import struct
import sys
from collections import Counter, defaultdict

IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def read_json_chunk(path):
    """The JSON chunk of a GLB. The binary chunk is never touched."""
    b = pathlib.Path(path).read_bytes()
    if b[:4] != b'glTF':
        raise SystemExit(f'{path}: not a GLB')
    off = 12
    while off < len(b):
        length, kind = struct.unpack_from('<II', b, off)
        if kind == 0x4E4F534A:                      # 'JSON'
            return json.loads(b[off + 8:off + 8 + length])
        off += 8 + length
    raise SystemExit(f'{path}: no JSON chunk')


def mul(a, b):
    return [sum(a[i + k * 4] * b[k + j * 4] for k in range(4))
            for j in range(4) for i in range(4)]


def local(node):
    """A node's own transform, from `matrix` or from TRS."""
    if 'matrix' in node:
        return list(node['matrix'])
    tx, ty, tz = node.get('translation', [0, 0, 0])
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    sx, sy, sz = node.get('scale', [1, 1, 1])
    return [(1 - 2 * (y * y + z * z)) * sx, (2 * (x * y + z * w)) * sx,
            (2 * (x * z - y * w)) * sx, 0,
            (2 * (x * y - z * w)) * sy, (1 - 2 * (x * x + z * z)) * sy,
            (2 * (y * z + x * w)) * sy, 0,
            (2 * (x * z + y * w)) * sz, (2 * (y * z - x * w)) * sz,
            (1 - 2 * (x * x + y * y)) * sz, 0, tx, ty, tz, 1]


def xform(m, p):
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


class Scene:
    def __init__(self, path):
        self.js = read_json_chunk(path)
        self.nodes = self.js.get('nodes', [])
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get('children', []):
                self.parent[c] = i

    def world(self, idx):
        """The transform ABOVE a node, composed root-down."""
        chain = []
        j = idx
        while j in self.parent:
            j = self.parent[j]
            chain.append(j)
        m = IDENT
        for j in reversed(chain):
            m = mul(m, local(self.nodes[j]))
        return m

    def box(self, idx, m=None, acc=None):
        """World-space AABB of a node AND ITS DESCENDANTS, in metres.

        Descending is the whole point: the names are on group nodes.
        """
        if acc is None:
            acc = [[1e30] * 3, [-1e30] * 3]
            m = self.world(idx)
        n = self.nodes[idx]
        m = mul(m, local(n))
        if 'mesh' in n:
            for prim in self.js['meshes'][n['mesh']].get('primitives', []):
                # accessors is a LIST; POSITION is an index into it, and an
                # absent attribute must not index [-1] into the last accessor
                pos = prim.get('attributes', {}).get('POSITION')
                if pos is None:
                    continue
                a = self.js['accessors'][pos]
                if 'min' not in a:
                    continue
                for corner in range(8):
                    p = [a['max' if corner >> k & 1 else 'min'][k]
                         for k in range(3)]
                    q = xform(m, p)
                    for k in range(3):
                        acc[0][k] = min(acc[0][k], q[k])
                        acc[1][k] = max(acc[1][k], q[k])
        for c in n.get('children', []):
            self.box(c, m, acc)
        return acc if acc[1][0] > -1e29 else None

    def named(self):
        """Indices of nodes carrying a name, and which of those nest others."""
        idx = [i for i, n in enumerate(self.nodes) if n.get('name')]
        nested = set()
        for i in idx:
            stack = list(self.nodes[i].get('children', []))
            while stack:
                c = stack.pop()
                if self.nodes[c].get('name'):
                    nested.add(i)
                    break
                stack.extend(self.nodes[c].get('children', []))
        return idx, nested


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('pattern', nargs='?', default='')
    ap.add_argument('--face', help='chassis WxH in mm, e.g. 434x86.8 - maps CAD '
                                   'coordinates into face coordinates so numbers '
                                   'drop straight into a device.yaml')
    ap.add_argument('--names', action='store_true',
                    help='just list what is named, with instance counts')
    ap.add_argument('--sort', default='name', choices=('name', 'size', 'depth', 'z'))
    ap.add_argument('--zone', choices=('front', 'rear'),
                    help='only parts REACHING that face of the chassis. Which '
                         'face a part is on is the question a bounding box '
                         'answers worst and a name answers not at all, so it is '
                         'answered here by where the part ENDS along z')
    ap.add_argument('--tol', type=float, default=25.0,
                    help='mm from the face a part may stop and still count as '
                         'reaching it (default 25)')
    a = ap.parse_args()

    sc = Scene(a.file)
    idx, nested = sc.named()

    if a.names:
        c = Counter(sc.nodes[i]['name'] for i in idx)
        print(f'{len(sc.nodes)} nodes, {len(idx)} named, {len(c)} distinct names')
        print('\nINSTANCE COUNTS - a repeated name is repeated HARDWARE. Never')
        print('union them: 77 fans unioned is a measurement of the fan bay.\n')
        for name, n in c.most_common():
            if a.pattern and a.pattern.lower() not in name.lower():
                continue
            print(f'  {n:4d}  {name[:66]}')
        return

    fw = fh = None
    if a.face:
        fw, fh = (float(v) for v in a.face.lower().split('x'))

    rows, seen = [], set()
    for i in idx:
        name = sc.nodes[i]['name']
        if a.pattern.lower() not in name.lower():
            continue
        b = sc.box(i)
        if b is None:
            continue
        lo = [v * 1000 for v in b[0]]
        hi = [v * 1000 for v in b[1]]
        size = [hi[k] - lo[k] for k in range(3)]
        # LOD copies repeat a name at an identical box; that is one part
        key = (name, tuple(round(v, 1) for v in size),
               tuple(round(v, 1) for v in lo))
        if key in seen:
            continue
        seen.add(key)
        rows.append((name, size, lo, i in nested, lo[2] + size[2]))

    if not rows:
        print('nothing named matches')
        return

    # WHICH FACE A PART IS ON is the question the model most needs and the one
    # a name answers worst - `DELL_R740XD_ Rear Handle` says it, `Body_4_4.004`
    # does not. It is answered by geometry: the scene's z extent gives the two
    # faces, and a part reaching within `--tol` of one is on it.
    zmin = min(r[2][2] for r in rows)
    zmax = max(r[4] for r in rows)
    if a.zone:
        plane, pick = (zmin, lambda r: r[2][2]) if a.zone == 'front' else \
                      (zmax, lambda r: r[4])
        rows = [r for r in rows if abs(pick(r) - plane) <= a.tol]
        print(f'# parts reaching the {a.zone} face: z within {a.tol} of '
              f'{plane:.1f} (scene z {zmin:.1f}..{zmax:.1f})\n')

    keyf = {'name': lambda r: r[0].lower(),
            'size': lambda r: -max(r[1]),
            'depth': lambda r: -r[1][2],
            'z': lambda r: r[2][2]}[a.sort]
    rows.sort(key=keyf)

    dup = Counter(r[0] for r in rows)
    hdr = f'{"part":<46} {"w":>8} {"h":>7} {"depth":>7}'
    hdr += f'   {"face x":>8} {"face y":>7}' if fw else f'   {"cad x":>8} {"cad y":>7}'
    hdr += f'   {"z0":>7} {"z1":>7}'
    print(hdr)
    print('-' * len(hdr))
    for name, size, lo, is_asm, z1 in rows:
        if fw:
            # CAD is chassis-centred with y up; a face is left-origin with y down
            px, py = fw / 2 + lo[0], fh - (lo[1] + size[1])
        else:
            px, py = lo[0], lo[1]
        flag = ' assembly' if is_asm else ''
        flag += f'  x{dup[name]}' if dup[name] > 1 else ''
        print(f'{name[:46]:<46} {size[0]:8.1f} {size[1]:7.1f} {size[2]:7.1f}'
              f'   {px:8.1f} {py:7.1f}   {lo[2]:7.1f} {z1:7.1f}{flag}')

    n_asm = sum(1 for r in rows if r[3])
    print(f'\n{len(rows)} part(s); {n_asm} flagged `assembly` - a named node '
          'containing other\nnamed nodes, whose box is an ENVELOPE and not a '
          'part width until you descend.')
    if fw:
        print('face x/y are the part\'s top-left in device coordinates; depth is '
              'the axis\na faceplate figure cannot give you, and is the reason '
              'to be here.')
    print('POSITIONS ARE ONLY AS GOOD AS THE POSE - each guide explodes the parts '
          'its own\nprocedure needs. Sizes survive that; positions do not. Cite '
          'the guide.')


if __name__ == '__main__':
    main()
