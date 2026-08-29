#!/usr/bin/env python3
"""Project a device's own geometry onto the figure that shows it, as boxes.

`figmap.py` says WHICH image is a device's front and what its px/mm is. This
turns that into the thing a detector can be scored against: for every port,
lamp and module the library says is on that face, the pixel rectangle it should
occupy in the vendor's own drawing.

WHAT MAKES THIS GROUND TRUTH AND NOT A GUESS. Nothing here is measured. Every
box comes from a number a person already wrote down and defended in provenance
- the placement's `at`, the component contract's `size` - and the only new
arithmetic is the affine that figmap derived and Gate 1 certified. So a box
that lands wrong is a claim about the MODEL or the TRANSFORM, and either is
worth knowing; it is never a claim about this tool's eyesight.

THE OVERLAY IS NOT OPTIONAL. A projection like this is trivially plausible and
easy to get systematically wrong - an anchor read as a centre, a y-axis the
other way up, a scale from the wrong axis - and every one of those errors
produces a tidy JSON file full of confident numbers. `--overlay` draws the
boxes back onto the figure so a person can look. Look before you score
anything against this.

    benchgt.py --figmap fm.json --intake <tree> --out gt.json
    benchgt.py --figmap fm.json --intake <tree> --overlay out/ --only s6301-56st
"""
import argparse
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifest as mf  # noqa: E402

ROT_SWAPS = (90, 270, -90, -270)


def contract(ref, library):
    """`ns/name@major` -> the contract dict, or None if it is not in the library."""
    nsname, major = ref.rsplit("@", 1)
    p = pathlib.Path(library) / "components" / nsname / f"v{major}" / "contract.yaml"
    return mf.load_yaml(p) if p.exists() else None


def part_size(ref, rotate, library):
    """A part's footprint on the face it is installed in, in millimetres.

    A rotation of a quarter turn swaps the box - that is the whole of the
    geometry render.py applies, because it rotates about the centre and the
    `at` stays the top-left of the RESULT.
    """
    c = contract(ref, library)
    size = (c or {}).get("size") or {}
    w, h = size.get("w"), size.get("h")
    if w is None or h is None:
        return None
    return (h, w) if rotate in ROT_SWAPS else (w, h)


def boxes_mm(view, library, groups=None):
    """Every rectangle the library says is on this face, in face millimetres.

    Three sources, and they are not the same claim. A CUTOUT is a hole in the
    metal, which is what a drawing actually draws. A PLACEMENT is a part seated
    in the face, which is what a drawing shows INSIDE that hole. A BAY is an
    opening for a part that may or may not be fitted. All three are ink in the
    figure, so all three are scoreable, and each says which it is.

    EACH BOX CARRIES ITS GROUP'S `term`, WHICH IS THE LIBRARY SAYING WHAT THE
    THING IS. It is not inferred from the contract and not guessed from the
    size: 261 groups in the portfolio say Port and 144 say LED, in a field an
    author wrote. That distinction is what keeps a benchmark honest, because
    half of these boxes are lamps 1 to 3 mm across, which at 3 px/mm is six
    pixels - not a detection target, and scoring them alongside a 25 mm cage
    would report a model's failure to see the invisible.
    """
    parts = mf.view_parts(view)
    groups = groups or {}

    def term(g):
        return ((groups.get(g) or {}).get("term") or "").strip() or None

    out = []
    for c in parts["cutouts"]:
        if c.get("at") and c.get("size"):
            out.append({"id": c["id"], "source": "cutout", "ref": None,
                        "mm": [c["at"][0], c["at"][1], c["size"][0], c["size"][1]]})
    for b in parts["bays"]:
        size = b.get("size")
        if b.get("at") and size:
            w, h = (size["w"], size["h"]) if isinstance(size, dict) else size
            if b.get("rotate") in ROT_SWAPS:
                w, h = h, w
            out.append({"id": b.get("id"), "source": "bay", "ref": b.get("accepts"),
                        "mm": [b["at"][0], b["at"][1], w, h]})
    for p in parts["placements"]:
        if not p.get("at") or not p.get("ref"):
            continue
        wh = part_size(p["ref"], p.get("rotate"), library)
        if wh is None:
            continue
        out.append({"id": p.get("id"), "source": "placement", "ref": p["ref"],
                    "group": p.get("group"), "term": term(p.get("group")),
                    "mm": [p["at"][0], p["at"][1], wh[0], wh[1]]})
    return out


def project(box_mm, origin, ppm):
    """Face millimetres -> figure pixels. One scale: Gate 1 is what says we may."""
    x, y, w, h = box_mm
    return [round(origin[0] + x * ppm, 1), round(origin[1] + y * ppm, 1),
            round(w * ppm, 1), round(h * ppm, 1)]


def draw_overlay(src, dst, boxes):
    """Draw the projected boxes back onto the figure, for a person to look at."""
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    colour = {"cutout": (0, 160, 255), "bay": (255, 160, 0),
              "placement": (255, 0, 128)}
    for b in boxes:
        x, y, w, h = b["px"]
        d.rectangle([x, y, x + w, y + h], outline=colour.get(b["source"]), width=2)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--figmap", required=True, help="the manifest figmap.py wrote")
    ap.add_argument("--intake", required=True, help="root the figmap paths are under")
    ap.add_argument("--library", default="library")
    ap.add_argument("--view", default="front")
    ap.add_argument("--out", help="write the box set here as JSON")
    ap.add_argument("--overlay", help="draw the boxes onto the figures, into this dir")
    ap.add_argument("--only", help="one device, by model name")
    ap.add_argument("--all-figures", action="store_true",
                    help="include devices whose figure failed Gate 1")
    args = ap.parse_args(argv)

    fm = json.loads(pathlib.Path(args.figmap).read_text())
    out, skipped = {}, []
    for dev, entry in sorted(fm.items()):
        if args.only and args.only not in dev:
            continue
        if not entry.get("passes_gate1") and not args.all_figures:
            continue
        d = mf.load_yaml(pathlib.Path(args.library) / "devices" / dev / "device.yaml")
        view = (d.get("views") or {}).get(args.view) or {}
        mm = boxes_mm(view, args.library, d.get("groups"))
        if not mm:
            skipped.append(dev)
            continue
        ppm, origin = entry["px_per_mm"], entry["origin"]
        boxes = [dict(b, px=project(b["mm"], origin, ppm)) for b in mm]
        out[dev] = {"figure": entry["figure"], "px_per_mm": ppm, "origin": origin,
                    "box": entry["box"], "gate1_error": entry["gate1_error"],
                    "boxes": boxes}
        if args.overlay:
            draw_overlay(pathlib.Path(args.intake) / entry["figure"],
                         pathlib.Path(args.overlay) / f"{dev.replace('/', '-')}.png",
                         boxes)

    n = sum(len(v["boxes"]) for v in out.values())
    print(f"  {len(out):5d}  devices")
    print(f"  {n:5d}  boxes")
    for src in ("cutout", "bay", "placement"):
        c = sum(1 for v in out.values() for b in v["boxes"] if b["source"] == src)
        print(f"  {c:5d}    {src}s")
    terms = {}
    for v in out.values():
        for b in v["boxes"]:
            terms[b.get("term")] = terms.get(b.get("term"), 0) + 1
    for t, c in sorted(terms.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {c:5d}  term {t}")
    if skipped:
        print(f"  {len(skipped):5d}  devices with a figure but nothing to project")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True))
        print(f"\nwrote {args.out}")
    return out


if __name__ == "__main__":
    main()
