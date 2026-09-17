"""Draw one named part from a vendor GLB - three orthographic views, to a PNG.

FOR LOOKING, NOT FOR COPYING, and the reason it exists is that a box cannot tell
you a shape. `740XD_Powersupply_Unit-Latch` boxes 13.5 x 16.6 x 62.6, and that
number is the same whether the 62.6 is a lever standing off the face or a body
buried in the supply. Those are different parts. Drawing it settles it in one
look, which is the same act as opening a figure in a PDF; the model built
afterwards is still our own simplified drawing.

A GLB THAT LOOKS EMPTY USUALLY IS NOT. Counting accessors that carry a
`bufferView` reports this scene as having no geometry at all, and that reading
is wrong twice over:

    KHR_draco_mesh_compression   a Draco primitive's POSITION accessor has NO
                                 bufferView BY DESIGN - the vertices are in the
                                 Draco blob the extension points at. 212 of the
                                 R740XD scene's 411 meshes are this, the supply
                                 latch among them, and they are all readable.
    NEEDLE_progressive           the other 199 keep their geometry in per-mesh
                                 GLBs the viewer fetches on demand, each one
                                 named in `extensions.NEEDLE_progressive.lods[]`
                                 so the list never needs scraping.

Both are handled here. The only thing that genuinely means "no geometry" is a
mesh with neither.

Three orthographic views. Front is the face (x right, y up); side looks along x
with z to the right, and the chassis rear is at HIGH z, so anything protruding
from the rear sticks out to the RIGHT.
"""
import argparse
import json
import pathlib
import struct
import sys

import DracoPy
from PIL import Image, ImageDraw

# A GUARD, for the reason face_inventory.py gives: importable since #178, and
# this reads sys.argv at module scope.
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("scene", help="a .glb")
    ap.add_argument("pattern", help="match node names containing this, case-insensitive")
    ap.add_argument("out", help="write the SVG here")
    ARGS = ap.parse_args()
    SCENE = pathlib.Path(ARGS.scene)
    PAT = ARGS.pattern.lower()
    OUT = ARGS.out
    MESHDIR = SCENE.parent / (SCENE.stem + '-meshes')


    def chunks(path):
        b = pathlib.Path(path).read_bytes()
        off, js, bind = 12, None, None
        while off < len(b):
            ln, kind = struct.unpack_from('<II', b, off)
            if kind == 0x4E4F534A:
                js = json.loads(b[off + 8:off + 8 + ln])
            elif kind == 0x004E4942:
                bind = b[off + 8:off + 8 + ln]
            off += 8 + ln
        return js, bind


    def mul(a, b):
        return [sum(a[i + k * 4] * b[k + j * 4] for k in range(4))
                for j in range(4) for i in range(4)]


    def local(n):
        if 'matrix' in n:
            return list(n['matrix'])
        t = n.get('translation', [0, 0, 0])
        x, y, z, w = n.get('rotation', [0, 0, 0, 1])
        s = n.get('scale', [1, 1, 1])
        return [(1 - 2 * (y * y + z * z)) * s[0], (2 * (x * y + z * w)) * s[0],
                (2 * (x * z - y * w)) * s[0], 0,
                (2 * (x * y - z * w)) * s[1], (1 - 2 * (x * x + z * z)) * s[1],
                (2 * (y * z + x * w)) * s[1], 0,
                (2 * (x * z + y * w)) * s[2], (2 * (y * z - x * w)) * s[2],
                (1 - 2 * (x * x + y * y)) * s[2], 0, t[0], t[1], t[2], 1]


    def ap(m, p):
        return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
                m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
                m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


    js, _ = chunks(SCENE)
    nodes = js['nodes']
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i


    def world(i):
        ch = []
        j = i
        while j in parent:
            j = parent[j]
            ch.append(j)
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        for j in reversed(ch):
            m = mul(m, local(nodes[j]))
        return m


    # mesh index -> the LOD file that holds its geometry
    lodfile = {}
    for mi, mesh in enumerate(js.get('meshes', [])):
        pg = mesh.get('extensions', {}).get('NEEDLE_progressive')
        if not pg:
            continue
        for lod in pg.get('lods', []):
            p = MESHDIR / pathlib.Path(lod.get('path', '')).name
            if p.exists():
                lodfile[mi] = p
                break


    def tris_of(path):
        """Triangles from a per-mesh GLB, decompressing Draco where present."""
        mjs, mbin = chunks(path)
        out = []
        for mesh in mjs.get('meshes', []):
            for prim in mesh.get('primitives', []):
                dr = prim.get('extensions', {}).get('KHR_draco_mesh_compression')
                if not dr:
                    continue
                bv = mjs['bufferViews'][dr['bufferView']]
                blob = mbin[bv.get('byteOffset', 0):
                            bv.get('byteOffset', 0) + bv['byteLength']]
                m = DracoPy.decode(blob)
                pts, faces = m.points, m.faces
                for f in faces:
                    out.append((tuple(pts[f[0]]), tuple(pts[f[1]]),
                                tuple(pts[f[2]])))
        return out


    _, SCENE_BIN = chunks(SCENE)


    def tris_inline(mi):
        """Draco triangles held in the SCENE's own BIN chunk.

        THIS IS WHERE THE EARLIER READING WENT WRONG. A Draco primitive's POSITION
        accessor legitimately has NO bufferView - the data is in the Draco blob the
        extension points at - so counting accessors-with-bufferView reports a file
        full of geometry as empty. 212 of this scene's 411 meshes are exactly that,
        the latch among them.
        """
        out = []
        for prim in js['meshes'][mi].get('primitives', []):
            dr = prim.get('extensions', {}).get('KHR_draco_mesh_compression')
            if not dr:
                continue
            bv = js['bufferViews'][dr['bufferView']]
            o = bv.get('byteOffset', 0)
            mesh = DracoPy.decode(SCENE_BIN[o:o + bv['byteLength']])
            pts = mesh.points
            for f in mesh.faces:
                out.append((tuple(pts[f[0]]), tuple(pts[f[1]]), tuple(pts[f[2]])))
        return out


    tris = []


    def gather(i, m):
        n = nodes[i]
        m = mul(m, local(n))
        mi = n.get('mesh')
        if mi is not None:
            got = tris_of(lodfile[mi]) if mi in lodfile else tris_inline(mi)
            for t in got:
                tris.append(tuple(ap(m, p) for p in t))
        for c in n.get('children', []):
            gather(c, m)


    hit = [i for i, n in enumerate(nodes) if PAT in n.get('name', '').lower()]
    if not hit:
        raise SystemExit('no such name')
    i = hit[0]
    print(f'{nodes[i]["name"]}   ({len(hit)} instance(s); drawing the first)')
    gather(i, world(i))
    print(f'{len(tris)} triangles')
    if not tris:
        raise SystemExit('no geometry reached - is the mesh dir fetched?')

    xs = [p[0] for t in tris for p in t]
    ys = [p[1] for t in tris for p in t]
    zs = [p[2] for t in tris for p in t]
    print(f'mm  x {min(xs)*1000:8.1f}..{max(xs)*1000:8.1f}   '
          f'y {min(ys)*1000:7.1f}..{max(ys)*1000:7.1f}   '
          f'z {min(zs)*1000:7.1f}..{max(zs)*1000:7.1f}')

    VIEWS = [('FRONT   x right, y up   - the face view', 0, 1, False),
             ('SIDE    z right, y up   - REAR FACE IS TO THE RIGHT', 2, 1, False),
             ('TOP     x right, z down', 0, 2, True)]
    S, PAD, GAP = 9.0, 34, 46
    spanx = (max(xs) - min(xs)) * 1000
    spanz = (max(zs) - min(zs)) * 1000
    spany = (max(ys) - min(ys)) * 1000
    W = int(max(spanx, spanz) * S) + 2 * PAD
    rowh = [int(spany * S) + PAD, int(spany * S) + PAD, int(spanz * S) + PAD]
    img = Image.new('RGB', (W, sum(rowh) + GAP * 3), 'white')
    d = ImageDraw.Draw(img)
    lo = [min(xs), min(ys), min(zs)]
    oy = 0
    for (label, ax, ay, ydown), rh in zip(VIEWS, rowh):
        d.text((8, oy + 10), label, fill=(20, 20, 20))
        depth_axis = 2 if ax != 2 else 0
        for t in sorted(tris, key=lambda t: sum(p[depth_axis] for p in t)):
            pts = []
            for p in t:
                u = (p[ax] - lo[ax]) * 1000 * S + PAD
                v = (p[ay] - lo[ay]) * 1000 * S
                v = v + 26 if ydown else (rh - PAD / 2 - v) + 26
                pts.append((u, oy + v))
            d.polygon(pts, fill=(198, 204, 210), outline=(96, 102, 108))
        oy += rh + GAP
    img.save(OUT)
    print(OUT)
