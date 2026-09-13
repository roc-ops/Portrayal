#!/usr/bin/env python3
"""Measure an FHD module face from a face-on product render.

THE SCALE COMES FROM THE FACEPLATE AND IS CHECKED AGAINST THE OTHER AXIS. Every
FHD cassette and adapter panel is 108.97 x 35.05 mm, dimensioned on FS's own
render of SKU 57016. So a face-on image can be scaled on its plate width and then
VERIFIED by asking whether that scale reproduces the plate height. A
three-quarter render fails that check, which is the whole point: it is what
separates a measurement from a guess, and five of the eight connectors in this
plan have only three-quarter renders and are therefore estimated instead.

The faceplate is the widest full-width dark band in the image - the module body
behind it is narrower and sits above it in these renders.

`plate()` locates that band HEURISTICALLY, and the heuristic is correct only
for FS's own renders, which put a black module on a white ground - on a render
shot against a dark backdrop, the backdrop is the widest full-width dark band
instead. `validate()` is what makes the result trustworthy: it now enforces
its own tolerance rather than just reporting one, so never call `plate()`
without it.
"""
W_MM = 108.97
H_MM = 35.05


def _dark(p):
    return sum(p) < 690


def plate(im):
    """(x0, y0, x1, y1, mm_per_px) for the faceplate in a face-on render.

    Raises ValueError if no contiguous band of qualifying rows reaches 20 px
    tall - see the comment on `runs(mask, gap=0)` below for why contiguity is
    required rather than just spanning the first and last matching row.
    """
    px, py = im.size
    rows = []
    for y in range(py):
        xs = [x for x in range(px) if _dark(im.getpixel((x, y)))]
        rows.append((y, (xs[-1] - xs[0] + 1) if xs else 0, xs[0] if xs else 0))
    wmax = max(w for _y, w, _x in rows)
    mask = [w > wmax * 0.97 for _y, w, _x in rows]
    # gap=0: text, a shadow or a reflection elsewhere in the frame can put a
    # stray qualifying row far from the faceplate. Taking the first and last
    # matching row (the old approach) would stretch y0/y1 across everything
    # between - the scale would still be right but the height would be
    # measured on the wrong rows, so the check that is supposed to catch a
    # bad scale would pass on a bad one. Requiring the longest CONTIGUOUS run
    # keeps stray rows from ever entering the band.
    bands = runs(mask, gap=0)
    start, end = max(bands, key=lambda se: se[1] - se[0]) if bands else (0, -1)
    if end - start + 1 < 20:
        raise ValueError(
            f"widest contiguous full-width dark band is only "
            f"{max(end - start + 1, 0)} rows tall - no faceplate found "
            "(a dark backdrop or a three-quarter render fails this way)")
    y0, y1, x0 = start, end, rows[start][2]
    return x0, y0, x0 + wmax - 1, y1, W_MM / wmax


def validate(mm, y0, y1, *, limit=3.0):
    """Percent by which the scaled plate height misses the known 35.05 mm.

    RAISES rather than reporting, because a caller can ignore a number and
    cannot ignore an exception. Everything downstream of this module writes
    `confidence: measured` into a shipped contract; a scale that is wrong
    because `plate` locked onto a dark backdrop instead of a faceplate would
    turn that claim into a fabrication. Pass `limit=float("inf")` to get the
    percentage back without the gate - only worth doing when you are
    deliberately measuring how far off a render is.
    """
    h = (y1 - y0 + 1) * mm
    off = abs(h - H_MM) / H_MM * 100
    if off > limit:
        raise ValueError(
            f"scaled plate height {h:.2f} mm misses the known {H_MM} mm by "
            f"{off:.1f}% - likely a three-quarter render or a dark background")
    return off


def runs(mask, gap=3):
    out, start, hole = [], None, 0
    for i, v in enumerate(mask):
        if v:
            if start is None:
                start = i
            hole = 0
        elif start is not None:
            hole += 1
            if hole > gap:
                out.append((start, i - hole))
                start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def _pale(p):
    r, g, b = p
    return b > 120 and r > 90 and abs(b - r) < 90 and sum(p) > 330


def openings(im, box, band=(0.10, 0.90), min_mm=4.0, test=_pale):
    """Adapter openings across a horizontal band, as (x0_mm, x1_mm, centre_mm).

    `band` is the fraction of the plate height to scan between. The default
    `test` finds the pale interior of an adapter against a black plate; pass
    another for a panel whose adapters are not pale.

    `min_mm` DISCARDS THE THUMB-KNOBS. Every FHD panel carries two of them, one
    at each end, and they are round, dark-edged and about 2.5 mm of pale in these
    renders - narrow enough to separate from a real opening by width alone, and
    wide enough to wreck a pitch if left in. Measured on 35510.G they turned a
    13.8 mm pitch into a 14.5 mm mean with a 7.9 spread.
    """
    x0, y0, x1, y1, mm = box
    ya = y0 + int((y1 - y0) * band[0])
    yb = y0 + int((y1 - y0) * band[1])
    col = []
    for x in range(x0, x1 + 1):
        n = sum(1 for y in range(ya, yb) if test(im.getpixel((x, y))))
        col.append(n > (yb - ya) * 0.30)
    out = []
    for a, b in runs(col):
        w = (b + 1 - a) * mm
        if w < min_mm:
            continue
        out.append((a * mm, (b + 1) * mm, ((a + b + 1) / 2) * mm))
    return out
