#!/usr/bin/env python3
"""A vendor CAD part's FACE OUTLINE, as an SVG path in device millimetres.

WHAT A FACE VIEW SHOWS IS WHAT STANDS IN FRONT OF THE PANEL, and a part's full
silhouette is not that. The R740xd's rear handle is 74.5 mm deep and about a
third of it - the mounting flange, its bosses, the returns that bolt through -
is INSIDE the chassis. Project the whole part and you get a solid frame; project
only what is in front of the sheet metal and you get the hardware: a block on
the left, a rail across, a leg falling at the right. The first version of that
handle was traced from the whole part and was simply the wrong drawing.

So the cut plane is the argument that matters, and it is not guessable from the
part. Two ways to find it in a chassis scene, both used on the R740xd:

    the chassis shell's own rear face          `glb_parts.py --zone rear`
    a part known to sit in the panel plane     a PSU faceplate, an inlet

A part's own flange gives it away too - if some region of it stops dead at one z
while everything else reaches much further, that z IS the panel and the region
is what bolts to it.

Emits the outline SIMPLIFIED, with holes, in coordinates local to the visible
box, and prints the face position to place it at. Simplification is stated in mm
so a reader knows what was thrown away: a 0.3 tolerance cannot be measured back
off the result as if it were a chamfer.

    cad_outline.py chassis.glb "rear handle" --plane 713.5
"""
import argparse
import json
import math
import pathlib
import struct

import cv2
import numpy as np


def chunks(path):
    b = pathlib.Path(path).read_bytes()
    off, js, bin_ = 12, None, None
    while off < len(b):
        ln, kind = struct.unpack_from("<II", b, off)
        if kind == 0x4E4F534A:
            js = json.loads(b[off + 8:off + 8 + ln])
        elif kind == 0x004E4942:
            bin_ = b[off + 8:off + 8 + ln]
        off += 8 + ln
    return js, bin_


def mul(a, b):
    return [sum(a[i + k * 4] * b[k + j * 4] for k in range(4))
            for j in range(4) for i in range(4)]


def local(n):
    if "matrix" in n:
        return list(n["matrix"])
    t = n.get("translation", [0, 0, 0])
    x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
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


def load(scene, pattern):
    """Every triangle of the first node whose name matches, in scene space."""
    import DracoPy
    js, sbin = chunks(scene)
    nodes = js["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    meshdir = scene.parent / (scene.stem + "-meshes")
    lodfile = {}
    for mi, mesh in enumerate(js.get("meshes", [])):
        pg = mesh.get("extensions", {}).get("NEEDLE_progressive")
        for lod in (pg or {}).get("lods", []):
            p = meshdir / pathlib.Path(lod.get("path", "")).name
            if p.exists():
                lodfile[mi] = p
                break

    def decode(blob):
        m = DracoPy.decode(blob)
        pts = m.points
        return [(tuple(pts[f[0]]), tuple(pts[f[1]]), tuple(pts[f[2]]))
                for f in m.faces]

    def prims(doc, blob, mi):
        out = []
        for prim in doc["meshes"][mi].get("primitives", []):
            dr = prim.get("extensions", {}).get("KHR_draco_mesh_compression")
            if not dr:
                continue
            bv = doc["bufferViews"][dr["bufferView"]]
            o = bv.get("byteOffset", 0)
            out += decode(blob[o:o + bv["byteLength"]])
        return out

    hit = [i for i, n in enumerate(nodes)
           if pattern in n.get("name", "").lower()]
    if not hit:
        raise SystemExit(f"no node matching {pattern!r}")
    root = hit[0]
    chain = []
    j = root
    while j in parent:
        j = parent[j]
        chain.append(j)
    m0 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for j in reversed(chain):
        m0 = mul(m0, local(nodes[j]))

    tris = []

    def walk(i, m):
        n = nodes[i]
        m = mul(m, local(n))
        mi = n.get("mesh")
        if mi is not None:
            if mi in lodfile:
                mjs, mbin = chunks(lodfile[mi])
                got = prims(mjs, mbin, 0) if mjs["meshes"] else []
                got = [t for k in range(len(mjs["meshes"]))
                       for t in prims(mjs, mbin, k)]
            else:
                got = prims(js, sbin, mi)
            tris.extend(tuple(ap(m, p) for p in t) for t in got)
        for c in n.get("children", []):
            walk(c, m)

    walk(root, m0)
    return nodes[root].get("name", "?"), tris


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("file")
    ap_.add_argument("pattern")
    ap_.add_argument("--plane", type=float, required=True,
                     help="cut plane in scene z. Geometry BEHIND this is not "
                          "drawn, because a face view cannot see it. Find it "
                          "with glb_parts.py --zone rear, or from a part known "
                          "to sit in the panel")
    ap_.add_argument("--face", default="434x86.8",
                     help="chassis WxH in mm, to report face coordinates")
    ap_.add_argument("--px", type=float, default=16.0,
                     help="raster resolution; the outline cannot be finer")
    ap_.add_argument("--tol", type=float, default=0.30,
                     help="simplification tolerance in mm. STATED because a "
                          "reader must not measure it back off the result")
    ap_.add_argument("--min-area", type=float, default=1.0,
                     help="drop islands and holes smaller than this, in mm2")
    ap_.add_argument("--png", help="also write the silhouette here, to look at")
    a = ap_.parse_args()

    fw, fh = (float(v) for v in a.face.lower().split("x"))
    name, tris = load(pathlib.Path(a.file), a.pattern.lower())
    if not tris:
        raise SystemExit("no geometry reached - is the mesh dir fetched?")

    # KEEP A TRIANGLE IF ANY VERTEX IS IN FRONT. Testing the centroid drops the
    # ones straddling the plane, and those are exactly the returns where the
    # visible face meets the panel - the outline's own boundary.
    front = [t for t in tris if max(p[2] * 1000 for p in t) > a.plane]
    print(f"{name}: {len(front)} of {len(tris)} triangles in front of "
          f"z {a.plane}")
    if not front:
        raise SystemExit("nothing in front of that plane - wrong plane?")

    fx = [fw / 2 + p[0] * 1000 for t in front for p in t]
    fy = [fh - p[1] * 1000 for t in front for p in t]
    zs = [p[2] * 1000 for t in front for p in t]
    x0, x1, y0, y1 = min(fx), max(fx), min(fy), max(fy)
    print(f"  face x {x0:.2f} .. {x1:.2f}   ({x1 - x0:.2f} wide)")
    print(f"  face y {y0:.2f} .. {y1:.2f}   ({y1 - y0:.2f} tall)")
    print(f"  stands {max(zs) - a.plane:.2f} proud of the plane")

    pad = 2
    W = int(math.ceil((x1 - x0) * a.px)) + 2 * pad
    H = int(math.ceil((y1 - y0) * a.px)) + 2 * pad
    img = np.zeros((H, W), np.uint8)
    for t in front:
        pts = np.array([[((fw / 2 + p[0] * 1000 - x0) * a.px + pad),
                         ((fh - p[1] * 1000 - y0) * a.px + pad)]
                        for p in t], np.int32)
        cv2.fillConvexPoly(img, pts, 255)
    if a.png:
        cv2.imwrite(a.png, 255 - img)
        print(f"  {a.png}  {W}x{H} at {a.px} px/mm")

    cnts, hier = cv2.findContours(img, cv2.RETR_CCOMP,
                                  cv2.CHAIN_APPROX_SIMPLE)
    eps = a.tol * a.px
    min_px = a.min_area * a.px * a.px
    subpaths, kept, dropped = [], 0, 0
    for i, c in enumerate(cnts):
        if cv2.contourArea(c) < min_px:
            dropped += 1
            continue
        s = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        d = " ".join(("M" if k == 0 else "L") +
                     f"{(px - pad) / a.px:.2f} {(py - pad) / a.px:.2f}"
                     for k, (px, py) in enumerate(s)) + " Z"
        subpaths.append(d)
        kept += 1
    print(f"  {kept} subpath(s) kept, {dropped} below {a.min_area} mm2 dropped;"
          f" simplified at {a.tol} mm")
    print(f"\nplace at [{x0:.2f}, {y0:.2f}], size [{x1 - x0:.2f}, "
          f"{y1 - y0:.2f}]\n")
    print(" ".join(subpaths))


if __name__ == "__main__":
    main()
