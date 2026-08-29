"""Read a faceplate nobody has modelled, and hand back millimetres to check.

WHAT THIS IS FOR. Modelling a device spends most of its time on one thing:
deciding which figure can be measured, deriving px/mm from it, and then finding
where every cage sits. That is arithmetic over pixels, and a detector that
recovers port positions to a quarter of a millimetre on faces it has never seen
can do it in a second.

WHAT IT IS NOT. It is not a model and it must not be committed as one. It says
where rectangles are; it does not know what KIND of port each is, what the
silkscreen reads, which group they belong to, or whether the vendor numbered
them left to right. Those are the decisions a modeller makes, and this exists
to give them a measured starting point instead of a blank file.

IT REPORTS THE ROWS AND THE PITCH, not just the boxes, because that is the
shape `layout.yaml` is written in - a bank with a count and a pitch, not
forty-eight hand-written placements. A row whose pitch scatters is the useful
output too: it means the detector disagreed with itself, or the block really is
irregular, and either way it is the thing to look at first.

GATE 1 STILL DECIDES. A figure whose outline does not match the datasheet's own
W/H is schematic, and no detector makes it measurable. The scale is refused
rather than guessed, because a confident wrong px/mm turns every number below
it into a confident wrong millimetre.

    portdraft.py --figure fig.png --width 438 --height 44 --weights best.pt
"""
import argparse
import collections
import pathlib
import statistics
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import benchtile  # noqa: E402
import benchvlm  # noqa: E402
import figmap  # noqa: E402

TOL = 0.03


def rows_of(boxes, tol_mm=2.0):
    """Group boxes into rows by their top edge, in millimetres.

    A faceplate's ports sit in rows and the row is the unit a layout is written
    in. Two millimetres is well under any real row separation and well over the
    detector's own scatter, which is a quarter of a millimetre.
    """
    rows = collections.defaultdict(list)
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        for key in rows:
            if abs(b[1] - key) <= tol_mm:
                rows[key].append(b)
                break
        else:
            rows[b[1]].append(b)
    return [sorted(v, key=lambda b: b[0]) for _, v in sorted(rows.items())]


def pitch_of(row):
    """The step between neighbours, and how much it scatters.

    A clean ganged block steps by one number all the way across; a block with a
    gutter in it has two. Reporting the spread rather than only the median is
    what distinguishes 'a regular bank' from 'the detector lost one'.
    """
    if len(row) < 2:
        return None, None
    steps = [b[0] - a[0] for a, b in zip(row, row[1:])]
    med = statistics.median(steps)
    return med, max(abs(s - med) for s in steps)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--figure", required=True)
    ap.add_argument("--width", type=float, required=True, help="body width, mm")
    ap.add_argument("--height", type=float, required=True, help="body height, mm")
    ap.add_argument("--weights", required=True)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--face", type=int, default=1,
                    help="which face in the figure, counting from the top "
                         "(datasheets draw the front above the rear)")
    ap.add_argument("--overlay")
    ap.add_argument("--force", action="store_true",
                    help="report millimetres even though Gate 1 failed")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.figure)
    want = args.width / args.height

    # GATE 1 CANNOT PICK THE FACE, and this is the second time that has had to
    # be learned. figmap says it in its own header - a front and a rear have
    # the same outline, so aspect cannot separate them - and ranking this
    # figure's candidates by Gate 1 duly chose the EPS203's REAR, which fits
    # 0.85% against the front's 1.87% and carries power supplies instead of
    # ports. Sixteen scattered detections, and every number below them wrong.
    #
    # So the faces are LISTED with their errors and the caller picks. The
    # default is the topmost, which is where these figures put the front, and
    # that is a convention worth stating rather than a fact worth trusting.
    cands = [figmap.band_box(path, y0, y1) for y0, y1 in figmap.bands(path)]
    cands = [c for c in cands if c]
    if not cands:
        o = figmap.outline(path)
        cands = [o] if o else []
    if not cands:
        sys.exit(f"no device-shaped body found in {path} - nothing to measure")
    if len(cands) > 1:
        print(f"  faces    {len(cands)} in this figure - aspect cannot say which "
              f"is the front, so --face picks and {args.face} is in use:")
        for i, (cx0, cx1, cy0, cy1) in enumerate(cands, 1):
            cw, ch = cx1 - cx0 + 1, cy1 - cy0 + 1
            e = abs(cw / ch - want) / want
            mark = "<--" if i == args.face else "   "
            print(f"    {mark} face {i}  y {cy0}..{cy1}  {cw} x {ch} px  "
                  f"gate 1 {e * 100:5.2f}%")
    if not 1 <= args.face <= len(cands):
        sys.exit(f"  --face {args.face} but this figure has {len(cands)}")
    x0, x1, y0, y1 = cands[args.face - 1]
    pw, ph = x1 - x0 + 1, y1 - y0 + 1
    err = abs(pw / ph - want) / want
    ppm = pw / args.width
    print(f"  figure   {path.name}  body {pw} x {ph} px at ({x0}, {y0})")
    print(f"  gate 1   outline {pw / ph:.3f} against {want:.3f} -> {err * 100:.2f}%"
          f"  {'PASS' if err <= TOL else 'FAIL'}")
    print(f"  scale    {ppm:.4f} px/mm")
    if err > TOL and not args.force:
        sys.exit("  this figure is schematic; its scale would be a guess. "
                 "Use --force to see the numbers anyway, and do not commit them.")

    from ultralytics import YOLO
    model = YOLO(args.weights)
    im = Image.open(path).convert("RGB")
    panel = im.crop((x0, y0, x0 + pw, y0 + ph))
    found = []
    for (tx, ty, tw, th) in benchtile.tiles(pw, ph):
        tile = panel.crop((tx, ty, tx + tw, ty + th))
        big = tile.resize((int(tw * args.scale), int(th * args.scale)), Image.LANCZOS)
        r = model.predict(big, conf=args.conf, verbose=False)[0]
        for b, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()):
            bx1, by1, bx2, by2 = b
            found.append([tx + bx1 / args.scale, ty + by1 / args.scale,
                          (bx2 - bx1) / args.scale, (by2 - by1) / args.scale, c])
    merged = benchvlm.merge(found)
    mm = [[round(b[0] / ppm, 2), round(b[1] / ppm, 2),
           round(b[2] / ppm, 2), round(b[3] / ppm, 2), round(b[4], 3)]
          for b in merged]

    print(f"\n  {len(mm)} candidate ports, in millimetres from the body's "
          f"top-left corner\n")
    rows = rows_of(mm)
    for i, row in enumerate(rows):
        med, spread = pitch_of(row)
        w = statistics.median([b[2] for b in row])
        h = statistics.median([b[3] for b in row])
        p = f"pitch {med:6.2f} +/- {spread:4.2f}" if med else "pitch     -      "
        print(f"  row {i + 1}  y {row[0][1]:6.2f}  n {len(row):3d}  x "
              f"{row[0][0]:6.2f} .. {row[-1][0]:6.2f}  {p}  "
              f"size {w:5.2f} x {h:5.2f}")

    print("\n  a draft, NOT a model - no port kind, no numbering, no silkscreen:")
    for i, row in enumerate(rows):
        med, _ = pitch_of(row)
        if med:
            print(f"  - {{bank: row-{i + 1}, count: {len(row)}, "
                  f"at: [{row[0][0]:.2f}, {row[0][1]:.2f}], pitch: {med:.2f}}}")
    if args.overlay:
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        for b in merged:
            d.rectangle([x0 + b[0], y0 + b[1], x0 + b[0] + b[2], y0 + b[1] + b[3]],
                        outline=(0, 255, 0), width=2)
        pathlib.Path(args.overlay).parent.mkdir(parents=True, exist_ok=True)
        im.save(args.overlay)
        print(f"\n  wrote {args.overlay} - look at it before believing any of this")
    return mm


if __name__ == "__main__":
    main()
