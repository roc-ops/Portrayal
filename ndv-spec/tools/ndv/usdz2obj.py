#!/usr/bin/env python3
"""Convert an Apple Object Capture .usdz to OBJ + texture for browser use.

three.js's USDZLoader can't read Object Capture crates; OBJ loads everywhere.
Requires: pip install usd-core
"""
import argparse
import zipfile
from pathlib import Path

from pxr import Usd, UsdGeom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("usdz")
    ap.add_argument("--out", required=True, help="output directory (model.obj/.mtl/model_tex.png)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    stage = Usd.Stage.Open(args.usdz)
    mesh = UsdGeom.Mesh(next(p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)))
    pts = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    idx = mesh.GetFaceVertexIndicesAttr().Get()
    st_pv = UsdGeom.PrimvarsAPI(mesh.GetPrim()).GetPrimvar("st")
    st = st_pv.Get()
    uvidx = st_pv.GetIndices()

    with open(out / "model.obj", "w") as f:
        f.write("mtllib model.mtl\nusemtl scan\n")
        for p in pts:
            f.write(f"v {p[0]} {p[1]} {p[2]}\n")
        for uv in st:
            f.write(f"vt {uv[0]} {uv[1]}\n")
        c = 0
        for n in counts:
            if uvidx:
                face = " ".join(f"{idx[c+k]+1}/{uvidx[c+k]+1}" for k in range(n))
            else:
                face = " ".join(f"{idx[c+k]+1}/{c+k+1}" for k in range(n))
            f.write(f"f {face}\n")
            c += n
    (out / "model.mtl").write_text("newmtl scan\nmap_Kd model_tex.png\n")
    with zipfile.ZipFile(args.usdz) as z:
        tex = next(n for n in z.namelist() if "tex" in n and n.endswith(".png"))
        (out / "model_tex.png").write_bytes(z.read(tex))
    print(f"wrote {out}/model.obj ({len(pts)} verts, {len(counts)} faces) + model_tex.png")


if __name__ == "__main__":
    main()
