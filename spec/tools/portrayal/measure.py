#!/usr/bin/env python3
"""Measure a vendor figure and return NUMBERS, not another picture.

WHY THIS EXISTS. Modelling one device took 43 minutes, and roughly 25 of them
went on measurement: deciding which figure could be measured at all, deriving
px/mm, finding a repeating pitch, locating a row of features. Every step of that
was done by cropping an image, looking at it, reasoning, cropping again - and
every one of those loops is an image round-trip, which is slow and expensive and
produces a number with no derivation attached.

None of it needs a model. A panel outline, a repeat period, a run of colour and
the centroids of a set of blobs are all arithmetic over pixels, and arithmetic
can show its working. That last part matters more than the speed: this library's
discipline is that every number cites where it came from, so a measurement tool
has to report HOW it measured and how well it fits, not just an answer.

WHAT IT DOES NOT DO. It does not decide what a feature IS. It will tell you
there are sixteen columns on a 62.5 px step; whether those are ports, screws or
vent slots is yours, and so is whether the figure is of the right product.

STATUS - READ THIS BEFORE TRUSTING A NUMBER FROM HERE.

`panel` is VALIDATED. Asked for the scale of the figure that cost a modelling
run 25 minutes, it returns 3.2892 px/mm where the agent derived 3.287 by hand,
and it independently reaches that agent's conclusion: of the two elevations
stacked on that page, the front is not orthographic and the rear is. Use it.

`pitch`, `runs` and `blobs` are NOT VALIDATED and are here as plumbing. Each was
tested against an answer already known and each failed in the same way, which is
worth stating rather than tuning away: they need to be TOLD where to look - a
band, a row, a colour - and choosing that is the judgement, not the arithmetic
that follows it. `pitch` returned the 6px weave of a vent pattern, then a 181px
stride belonging to nothing, because the band it was given contained vent fields
as well as cages. `runs` picks the most colourful row on its own now, and lands
on the printed band correctly, but the numerals printed ON that band chop its
colour runs into fragments. The arithmetic in all three is right. It is aimed by
hand, and aiming it is the part that was slow.

    measure.py panel  fig.png --width 438.4 --height 43.1
    measure.py pitch  fig.png --band 124,270 --px-per-mm 3.287
    measure.py runs   fig.png            # picks its own row
    measure.py blobs  fig.png --colour c22f2f --tolerance 60 --px-per-mm 1.82
"""
import argparse
import collections
import pathlib
import sys

try:
    from PIL import Image
except ImportError:                                  # pragma: no cover
    sys.exit("measure.py needs Pillow")


# ----------------------------------------------------------------- panel ---

def panel_box(path, thresh=200, share=0.55):
    """The faceplate's own box, not the figure's.

    Taking the ink bounding box of the whole image swallows callout numerals,
    leader lines and captions - which made the QSG elevation an agent measured
    SUCCESSFULLY come out 41% off, condemning the best source in the intake. A
    rack faceplate is instead the widest continuous band of ink in the picture:
    rows belonging to it span most of the panel's width, rows belonging to
    callouts do not.
    """
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    step = max(1, w // 700)
    rows = []
    for y in range(h):
        n, first, last = 0, None, None
        for x in range(0, w, step):
            if px[x, y] < thresh:
                n += 1
                if first is None:
                    first = x
                last = x
        rows.append((n * step, first, last))
    widest = max((r[0] for r in rows), default=0) or 1
    ok = [i for i, r in enumerate(rows) if r[0] >= share * widest]
    if not ok:
        return []
    # EVERY qualifying band, not just the biggest. One datasheet figure carries
    # the front AND rear elevations stacked on one page, and returning only the
    # widest picked one of the two silently - handing back a confident px/mm for
    # a face the caller was not asking about. Two panels is a question for the
    # caller, not something to resolve by picking.
    runs, cur = [], [ok[0]]
    for a, b in zip(ok, ok[1:]):
        if b - a <= 2:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    runs.append(cur)
    out = []
    for r in runs:
        if len(r) < 6:                      # a caption underline is not a panel
            continue
        # A LEADER LINE REACHING THE PANEL IS NOT PART OF THE PANEL. A single
        # callout arrow extended one band's right edge from 1449 to 1534 px,
        # which made an ORTHOGRAPHIC front elevation report 2.68% axis
        # disagreement and 'NOT orthographic' - so the tool condemned a usable
        # figure, and an agent that trusted it would have thrown away a good x
        # axis. That is the dangerous direction for this rule to fail in.
        #
        # Take the x extent each row VOTES for, not the widest single row: a
        # face contributes its full width on most rows, a leader on one or two.
        left = collections.Counter(rows[y][1] for y in r if rows[y][1] is not None)
        right = collections.Counter(rows[y][2] for y in r if rows[y][2] is not None)
        if not left:
            continue
        # the modal edge, with a small tolerance so antialiasing does not split
        # the vote across neighbouring columns
        def modal(counter, pick):
            best, hits = None, 0
            for v in counter:
                n = sum(c for u, c in counter.items() if abs(u - v) <= 2)
                if n > hits or (n == hits and pick(v, best)):
                    best, hits = v, n
            return best
        x0 = modal(left, lambda v, b: b is None or v < b)
        x1 = modal(right, lambda v, b: b is None or v > b)
        out.append((x0, r[0], x1, r[-1]))

    # A FACE IS NOT ONE UNBROKEN BAND OF INK. Between two rows of ports there is
    # bare metal, and a row-coverage test reads that as the end of the panel - so
    # a front elevation came back as three separate 'panels' stacked 10px apart,
    # each with a nonsense height and a 71% axis disagreement. Bands that share
    # their x extent and sit a few rows apart are one face with a gap in it; a
    # front and a rear elevation on the same page are hundreds of rows apart and
    # stay separate, which is the distinction that matters.
    merged = []
    for b in out:
        if merged:
            p = merged[-1]
            gap = b[1] - p[3]
            ov = min(p[2], b[2]) - max(p[0], b[0])
            span = max(p[2] - p[0], b[2] - b[0])
            if 0 <= gap <= 20 and span and ov / span >= 0.8:
                merged[-1] = (min(p[0], b[0]), p[1], max(p[2], b[2]), b[3])
                continue
        merged.append(b)

    # Re-vote the x extent over the WHOLE merged band. Doing it per sub-band and
    # then taking the widest let a single leader-heavy strip set the edge for the
    # entire face - the very overrun the modal vote was added to stop.
    final = []
    for x0, y0, x1, y1 in merged:
        span = range(y0, y1 + 1)
        left = collections.Counter(rows[y][1] for y in span if rows[y][1] is not None)
        right = collections.Counter(rows[y][2] for y in span if rows[y][2] is not None)
        if not left:
            final.append((x0, y0, x1, y1))
            continue

        def modal(counter, prefer_low):
            best, hits = None, -1
            for v in counter:
                n = sum(c for u, c in counter.items() if abs(u - v) <= 2)
                if n > hits or (n == hits and best is not None
                                and ((v < best) if prefer_low else (v > best))):
                    best, hits = v, n
            return best
        final.append((modal(left, True), y0, modal(right, False), y1))
    return final


def cmd_panel(a):
    boxes = panel_box(a.image, a.threshold, a.share)
    if not boxes:
        print("panel: no continuous band of ink found - is this a figure of a face?")
        return 1
    if len(boxes) > 1:
        print(f"# {len(boxes)} panel-shaped bands in this figure. A datasheet page")
        print(f"# often stacks the front and rear elevations; pick the one you want")
        print(f"# by its y position rather than assuming the first.")
    for n, (x0, y0, x1, y1) in enumerate(boxes):
        wpx, hpx = x1 - x0, y1 - y0
        print(f"panel-{n}:")
        print(f"  box-px: [{x0}, {y0}, {x1}, {y1}]")
        print(f"  size-px: [{wpx}, {hpx}]")
        if not (a.width and a.height):
            continue
        sx, sy = wpx / a.width, hpx / a.height
        skew = abs(sx - sy) / max(sx, sy) * 100
        print(f"  px-per-mm: {{x: {sx:.4f}, y: {sy:.4f}}}")
        print(f"  axis-disagreement-percent: {skew:.2f}")
        if skew < 2.0:
            print("  verdict: orthographic - both axes may be measured here")
        else:
            print(f"  verdict: NOT orthographic ({skew:.1f}% apart). Anchor to a "
                  f"dimension you know and measure only the axis that matches it; "
                  f"the other is foreshortened, or this band is not the face.")
    if not (a.width and a.height):
        print("# give --width and --height in mm for a scale and a Gate 1 verdict")
        return 0
    print("# NOTE: an orthographic OUTLINE does not make every FEATURE measurable."
          "\n# A recessed cage seen slightly from above still reads short. When a"
          "\n# feature you measure disagrees with this scale, believe the scale.")
    return 0


# ------------------------------------------------------------------ rows ---

def cmd_rows(a):
    """The horizontal bands of a face, measured against the panel this same call
    found - which is the point.

    TWO CAREFUL RUNS OF ONE DEVICE DISAGREED ON EXACTLY TWO NUMBERS: the block
    origin y and the row pitch. Every other block parameter matched, because
    every other one is a registry lookup. These two were eyeball, and the chain
    behind them - find the panel edge, derive px/mm, find the feature row,
    subtract - was re-made independently each run, with a one-pixel judgement at
    every link.

    The corpus says row pitch cannot be a lookup: 134 stacked QSFP-DD columns
    across 15 devices run from 12.86 to 17.30mm, so belly-to-belly spacing is a
    cage-assembly choice and not a standard. Inventing a registry value would
    make fifteen honest measurements look like deviations.

    So it is measured - but measured ONCE, here, with the panel edge and the
    scale that produced it printed alongside, so two runs start from identical
    pixels instead of two independent readings of the same edge.
    """
    boxes = panel_box(a.image, a.threshold, a.share)
    if not boxes:
        print("rows: no panel found")
        return 1
    if a.panel >= len(boxes):
        print(f"rows: --panel {a.panel} but only {len(boxes)} band(s) found")
        return 1
    x0, y0, x1, y1 = boxes[a.panel]
    im = Image.open(a.image).convert("L")
    px = im.load()
    inset = max(2, (x1 - x0) // 40)          # skip the panel's own side walls
    xs = range(x0 + inset, x1 - inset)
    prof = [sum(px[x, y] for x in xs) / max(1, len(list(xs))) for y in range(y0, y1 + 1)]

    scale = None
    if a.height:
        scale = (y1 - y0) / a.height
    print(f"panel: {a.panel}  box-px: [{x0}, {y0}, {x1}, {y1}]")
    if scale:
        print(f"y-px-per-mm: {scale:.4f}   # from this box and --height {a.height}")
    print(f"# brightness averaged across x {x0 + inset}..{x1 - inset}, "
          f"one value per row")

    # A cage opening is DARK and its bezel is BRIGHT, so a face reads as
    # alternating bands. BOTH polarities are reported, because which one is the
    # feature depends on the drawing: one agent read this face off its bright
    # bezel highlights, and a dark-only listing does not contain the rows it
    # used.
    #
    # WHAT THIS TOOL DECIDES AND WHAT IT DOES NOT. It decides where the bands
    # are, to the pixel, from a stated panel box and a stated scale. It does NOT
    # decide which band is your port row - that is the drawing's meaning and
    # yours to read. The point is that the choice becomes an INDEX into a list
    # both runs see identically, instead of two independent judgements about
    # where an edge sits. Picking band-3 twice gives the same millimetres;
    # eyeballing the same edge twice does not.
    mean = sum(prof) / len(prof)
    bands, start, pol = [], 0, prof[0] < mean
    for i, v in enumerate(prof):
        p = v < mean
        if p != pol:
            if i - start >= a.min_band:
                bands.append((start, i - 1, pol))
            start, pol = i, p
    if len(prof) - start >= a.min_band:
        bands.append((start, len(prof) - 1, pol))

    print(f"bands: {len(bands)}   # dark = opening or shadow, light = bezel or plate")
    prev = {}
    for n, (b0, b1, isdark) in enumerate(bands):
        c = (b0 + b1) / 2
        kind = "dark " if isdark else "light"
        line = (f"  band-{n:<2d} {kind} rows {y0 + b0}..{y0 + b1}"
                f"  centre-px {y0 + c:7.1f}  h-px {b1 - b0 + 1:3d}")
        if scale:
            line += (f"  centre-mm {c / scale:6.2f}"
                     f"  h-mm {(b1 - b0 + 1) / scale:5.2f}")
        if isdark in prev:
            step = c - prev[isdark]
            line += f"  step-to-previous-{kind.strip()} {step / scale:.2f}mm" if scale \
                else f"  step-px {step:.1f}"
        print(line)
        prev[isdark] = c
    print("# `at.y` = that band's centre-mm minus half the component's height."
          "\n# `row-pitch` = the step between the two bands of the same kind that"
          "\n# are your two port rows. Quote the band index and this box in"
          "\n# provenance, and the next run reproduces the number instead of"
          "\n# re-deriving it.")
    return 0


# ----------------------------------------------------------------- pitch ---

def column_profile(path, band=None, thresh=200):
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    y0, y1 = band if band else (0, h)
    y0, y1 = max(0, y0), min(h, y1)
    return [sum(1 for y in range(y0, y1) if px[x, y] < thresh) for x in range(w)]


def dominant_period(sig, lo=4, hi=None):
    """Repeat period from autocorrelation - the pitch a human gets by measuring
    two features and dividing, but taken over the whole row at once, so one
    mis-placed edge cannot set the answer.

    THE ANSWER IS A LOCAL PEAK, NOT THE GLOBAL MAXIMUM. Autocorrelation of any
    real signal falls away with lag, so the largest value is always at the
    smallest lag tried - which returned the 6px surface texture of a vent
    pattern, and then obediently returned whatever floor was set instead. A
    period announces itself as a BUMP: higher than its immediate neighbours.
    """
    n = len(sig)
    hi = hi or n // 3
    mean = sum(sig) / n if n else 0
    d = [v - mean for v in sig]
    lags = list(range(lo, max(lo + 1, hi)))
    ac = []
    for lag in lags:
        s = sum(d[i] * d[i + lag] for i in range(n - lag))
        ac.append(s / (n - lag))
    peaks = [(ac[i], lags[i]) for i in range(1, len(ac) - 1)
             if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0]
    if not peaks:
        return None, list(zip(ac, lags))
    peaks.sort(reverse=True)
    return peaks[0], peaks


def cmd_pitch(a):
    band = tuple(int(v) for v in a.band.split(",")) if a.band else None
    sig = column_profile(a.image, band, a.threshold)
    best, scores = dominant_period(sig, a.min_period, a.max_period)
    if not best:
        print("pitch: nothing repeating found")
        return 1
    score, lag = best
    ranked = sorted(scores, reverse=True)[:5]
    print(f"period-px: {lag}")
    if a.px_per_mm:
        print(f"period-mm: {lag / a.px_per_mm:.3f}")
    print(f"runners-up-px: {[l for _, l in ranked[1:]]}"
          "   # a harmonic of the answer is normal; a stranger is a warning")
    # where the repeats actually fall, so a gutter shows up as a missing beat
    peaks = [x for x in range(1, len(sig) - 1)
             if sig[x] >= sig[x - 1] and sig[x] > sig[x + 1] and sig[x] > 0]
    if peaks:
        gaps = [b - a_ for a_, b in zip(peaks, peaks[1:]) if b - a_ >= a.min_period]
        c = collections.Counter(gaps)
        print(f"observed-gaps-px: {c.most_common(6)}")
        if a.px_per_mm and c:
            common = c.most_common(1)[0][0]
            wide = [g for g in set(gaps) if g > common * 1.15]
            if wide:
                print(f"wider-gaps-px: {sorted(wide)[:6]}   # shell boundaries: a "
                      f"block repeats then steps out by the wall between ganged cages")
    print("# the pitch of a STANDARD cage is a registry lookup, not this number."
          "\n# Use this to confirm the registry, and to find where a block starts.")
    return 0


# ------------------------------------------------------------------ runs ---

def cmd_runs(a):
    """Runs of colour along one row - the technique that recovered a port-group
    breakdown from a 520-pixel render when the printed legend was illegible."""
    im = Image.open(a.image).convert("RGB")
    w, h = im.size
    px = im.load()
    q = a.quantise

    def scan(y):
        out, start, prev = [], 0, None
        for x in range(w):
            r, g, b = px[x, y]
            key = (r // q, g // q, b // q)
            if prev is None:
                prev = key
            elif key != prev:
                if x - start >= a.min_run:
                    out.append((start, x, prev))
                start, prev = x, key
        if w - start >= a.min_run:
            out.append((start, w, prev))
        return out

    if a.row is None:
        # FINDING THE ROW IS THE JUDGEMENT, not counting the runs once you have
        # it. A printed band identifying port groups is the most COLOURFUL row
        # on the face - several long runs of different saturated colour - while
        # a row through the ports is two greys repeating. Score every row by how
        # many distinct saturated runs it holds and take the best, so the caller
        # does not have to guess a y and try again.
        def score(y):
            rs = scan(y)
            sat = [k for _, _, k in rs
                   if max(k) - min(k) >= 2]        # not a grey
            return len({tuple(k) for k in sat}), len(rs)
        y = max(range(h), key=lambda yy: score(yy))
        print(f"# row chosen automatically as the most colourful on the face")
    else:
        y = a.row
    if not 0 <= y < h:
        print(f"runs: row {y} is outside the image (0..{h - 1})")
        return 1
    out = scan(y)
    print(f"row: {y}")
    for x0, x1, k in out:
        hexc = "%02x%02x%02x" % tuple(v * q + q // 2 for v in k)
        mm = f"  {(x1 - x0) / a.px_per_mm:7.2f}mm" if a.px_per_mm else ""
        print(f"  x {x0:5d}..{x1:<5d} w {x1 - x0:4d}px{mm}  #{hexc}")
    return 0


# ----------------------------------------------------------------- blobs ---

def cmd_blobs(a):
    """Centroids of everything matching a colour.

    A device's fan bays were placed 3.5mm out because they were derived from an
    eyeballed module edge; the six red pull bars isolate by colour and gave a
    48.89mm step over five intervals. That is this, and it takes a second.
    """
    im = Image.open(a.image).convert("RGB")
    w, h = im.size
    px = im.load()
    tr, tg, tb = (int(a.colour[i:i + 2], 16) for i in (0, 2, 4))
    tol = a.tolerance
    mask = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - tr) <= tol and abs(g - tg) <= tol and abs(b - tb) <= tol:
                mask[y * w + x] = 1
    seen, blobs = bytearray(w * h), []
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if not mask[i] or seen[i]:
                continue
            stack, cells = [(x, y)], []
            seen[i] = 1
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if mask[j] and not seen[j]:
                            seen[j] = 1
                            stack.append((nx, ny))
            if len(cells) >= a.min_area:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                blobs.append((sum(xs) / len(xs), sum(ys) / len(ys),
                              min(xs), min(ys), max(xs), max(ys), len(cells)))
    blobs.sort(key=lambda b: (b[0], b[1]))
    print(f"blobs: {len(blobs)}")
    for cx, cy, x0, y0, x1, y1, n in blobs:
        mm = f"  ({cx / a.px_per_mm:7.2f}, {cy / a.px_per_mm:6.2f})mm" if a.px_per_mm else ""
        print(f"  centroid ({cx:7.1f}, {cy:6.1f})px{mm}  box {x1 - x0 + 1}x{y1 - y0 + 1}  area {n}")
    if len(blobs) > 1:
        steps = [round(b[0] - a_[0], 2) for a_, b in zip(blobs, blobs[1:])]
        print(f"x-steps-px: {steps}")
        if a.px_per_mm:
            mmsteps = [round(s / a.px_per_mm, 2) for s in steps]
            print(f"x-steps-mm: {mmsteps}")
            mean = sum(mmsteps) / len(mmsteps)
            spread = max(mmsteps) - min(mmsteps)
            print(f"mean-step-mm: {mean:.2f}   spread: {spread:.2f}"
                  f"   # a spread over ~0.3mm means these are not evenly spaced,"
                  f" or one blob is not the same feature as the others")
    return 0


# ------------------------------------------------------------------ main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("panel", help="panel box, px/mm per axis, Gate 1 verdict")
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--width", type=float, help="stated body width in mm")
    p.add_argument("--height", type=float, help="stated body height in mm")
    p.add_argument("--threshold", type=int, default=200)
    p.add_argument("--share", type=float, default=0.55)
    p.set_defaults(fn=cmd_panel)

    p = sub.add_parser("rows", help="horizontal bands of a face, against its own panel")
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--height", type=float, help="stated body height in mm")
    p.add_argument("--panel", type=int, default=0, help="which band, when a page stacks two")
    p.add_argument("--threshold", type=int, default=200)
    p.add_argument("--share", type=float, default=0.55)
    p.add_argument("--min-band", type=int, default=3)
    p.set_defaults(fn=cmd_rows)

    p = sub.add_parser("pitch", help="dominant repeat period across a band")
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--band", help="y0,y1 in px - restrict to the row of features")
    p.add_argument("--px-per-mm", type=float)
    p.add_argument("--threshold", type=int, default=200)
    p.add_argument("--min-period", type=int, default=6)
    p.add_argument("--max-period", type=int, default=0)
    p.set_defaults(fn=cmd_pitch)

    p = sub.add_parser("runs", help="runs of colour along one row")
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--row", type=int)
    p.add_argument("--quantise", type=int, default=24)
    p.add_argument("--min-run", type=int, default=3)
    p.add_argument("--px-per-mm", type=float)
    p.set_defaults(fn=cmd_runs)

    p = sub.add_parser("blobs", help="centroids of everything matching a colour")
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--colour", required=True, help="rrggbb")
    p.add_argument("--tolerance", type=int, default=40)
    p.add_argument("--min-area", type=int, default=12)
    p.add_argument("--px-per-mm", type=float)
    p.set_defaults(fn=cmd_blobs)

    a = ap.parse_args()
    if getattr(a, "max_period", None) == 0:
        a.max_period = None
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
