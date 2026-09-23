#!/usr/bin/env python3
"""Measure a rack-mount face from a face-on product render.

THE SCALE COMES FROM THE FACE'S WIDTH AND IS CHECKED AGAINST ITS HEIGHT. Give
the tool a face whose two dimensions are known and it scales an image on the
width, then VERIFIES by asking whether that scale reproduces the height. A
three-quarter render fails that check, which is the whole point: it is what
separates a measurement from a guess, and most of the connectors in this library
have only three-quarter renders and are therefore estimated instead.

A FACE IS BOTH CONSTANTS AT ONCE, and that is deliberate. The width will scale
anything you point it at; only the height can tell you the scale was taken off
the wrong object. Holding them apart is how a caller ends up validating a
MaiaEdge chassis against an FHD cassette's height - so they travel as one
`Face`, and `measure()` applies one face to both steps so they cannot be
mismatched at all.

The faceplate is the widest full-width dark band in the image - the module body
behind it is narrower and sits above it in these renders. Its left edge is the
median over that band, because a rounded corner starts the band's first rows
inboard of the real edge (see `plate()`).

`plate()` locates that band HEURISTICALLY, and the heuristic is correct only
for renders that put a dark chassis on a light ground - on a render shot against
a dark backdrop, the backdrop is the widest full-width dark band instead.
`validate()` is what makes the result trustworthy: it enforces its own tolerance
rather than just reporting one, so never call `plate()` without it. `measure()`
is the way to be sure you have.
"""
import collections

Face = collections.namedtuple("Face", "name w_mm h_mm")

# THE FHD MODULE FACE, and the default because every figure in the library
# measured with this tool so far was measured against it. Every FHD cassette and
# adapter panel is this size, dimensioned on FS's own render of SKU 57016 and
# corroborated by the dimension line on 57016.B.jpg reading 4.29in x 1.38in.
FHD_MODULE = Face("FHD module", 108.97, 35.05)

# THE MAIAEDGE PBC CHASSIS, from page 3 of MaiaEdge-PBC-PCE-Datasheet-v3.pdf:
# chassis 1.625 x 17.24 x 11.46 in. NOT the 19.02 in "with ears and tabs" width
# on the row below it - the ears are a separate part and the bezel face is inset
# from them, so scaling on 483.11 would make every port on the face too small.
MAIAEDGE_PBC = Face("MaiaEdge PBC chassis", 437.90, 41.27)


def _dark(p):
    return sum(p) < 690


def plate(im, face=FHD_MODULE):
    """(x0, y0, x1, y1, mm_per_px) for the faceplate in a face-on render.

    `face` supplies the known width the scale is taken from. Pass the same face
    to `validate`, or use `measure` and avoid the question.

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
    # x0 IS THE MEDIAN LEFT EDGE OVER THE BAND, NOT THE FIRST ROW'S. A plate
    # with rounded corners starts its first rows inboard of its true edge, and
    # they are still wide enough to be in the band. Taking x0 from the first
    # row put it 1.25-1.53 mm right of the edge on every FS FHD cassette render,
    # and `openings()` counts from x0, so every adapter measured with it came out
    # that much too far left. The corner rows at the top and bottom of the band
    # are a minority of it, so they cannot move the median.
    y0, y1 = start, end
    x0 = sorted(x for _y, _w, x in rows[start:end + 1])[(end - start) // 2]
    return x0, y0, x0 + wmax - 1, y1, face.w_mm / wmax


def validate(mm, y0, y1, *, face=FHD_MODULE, limit=3.0):
    """Percent by which the scaled plate height misses the face's known height.

    RAISES rather than reporting, because a caller can ignore a number and
    cannot ignore an exception. Everything downstream of this module writes
    `confidence: measured` into a shipped contract; a scale that is wrong
    because `plate` locked onto a dark backdrop instead of a faceplate would
    turn that claim into a fabrication. Pass `limit=float("inf")` to get the
    percentage back without the gate - only worth doing when you are
    deliberately measuring how far off a render is.
    """
    h = (y1 - y0 + 1) * mm
    off = abs(h - face.h_mm) / face.h_mm * 100
    if off > limit:
        raise ValueError(
            f"scaled plate height {h:.2f} mm misses {face.name}'s known "
            f"{face.h_mm} mm by {off:.1f}% - likely a three-quarter render, a "
            "dark background, or the wrong face")
    return off


def measure(im, face=FHD_MODULE, limit=3.0):
    """`((x0, y0, x1, y1, mm_per_px), off_percent)` for one face.

    THE WAY TO CALL THIS MODULE. `plate` and `validate` each take a face because
    they have to, and a caller who passes one and forgets the other validates a
    scale against somebody else's height - which fails for the wrong reason, or
    passes for no reason. Here one face does both, so the mismatch has nowhere
    to live.
    """
    box = plate(im, face)
    return box, validate(box[4], box[1], box[3], face=face, limit=limit)


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
