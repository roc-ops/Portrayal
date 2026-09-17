#!/usr/bin/env python3
"""Pair each device with the figure of its face, and with the scale that measures it.

This is the lookup every figure job in this project has rebuilt by hand: for a
given device, WHICH image is its front elevation, and what is the transform from
that image's pixels to the device's millimetres. Without it, correcting a vent
starts by hunting through an intake directory and rediscovering a scale; with it,
a detector has (image, transform, boxes) triples and a benchmark has something to
score against.

TWO QUESTIONS, AND ONLY ONE OF THEM IS ABOUT PIXELS.

WHICH FACE - read the document, not the drawing. A front and a rear have the same
outline, so aspect cannot separate them: matching on it alone picked the S6301's
REAR as its front. Two image-comparison attempts were tried and both were thin -
column brightness gave that device's front 0.143 against its rear's 0.103, and
gradient profiles cut the margin to 0.001, because our render and a vendor
schematic share a layout and nothing else. Meanwhile the conversion had kept the
headings all along: `fig-0020` sits under `## Port Overview` and `fig-0018` under
`## Fan Overview`. That is not an inference, it is what the vendor wrote.

WHAT SCALE - Gate 1, which is both the test and the answer. A figure whose
outline matches the device's own width-over-height is orthographic and carries
geometry; the ratio that proves it is the px/mm that measures it. A figure that
fails is reported with its error rather than dropped, because "this device has a
figure and it is 8% out" is a different fact from "this device has no figure".

The manifest names files under an intake tree that is not in this repository, so
it is written where the caller asks and nothing here depends on it existing.
"""
import argparse
import collections
import glob
import json
import pathlib
import re

import numpy as np
import yaml
from PIL import Image
from portrayal import libwalk

# A HYPHEN IS NOT A DIFFERENT WORD. Six headings in the intake read
# "Front-Panel Features And Indicators", and a `front panel` pattern is silent
# about every one of them - which reads as "this document shows no front".
FRONT = re.compile(r"port overview|front[- ]panel|front view|port id|ports", re.I)
REAR = re.compile(r"fan overview|psu overview|power supply|rear[- ]panel|rear view",
                  re.I)
TOL = 0.03
MIN_PX = 600


def figure_context(doc):
    """fig-NNNN -> the nearest heading and caption, in conversion order.

    The conversion numbers `<!-- image -->` markers from zero in document order,
    which is the only handle the figure files carry - so the walk has to count
    them the same way and attribute to each the heading it is UNDER, not the one
    that follows it.
    """
    out, n, head, cap = {}, -1, "", ""
    for line in pathlib.Path(doc).read_text().split("\n"):
        st = line.strip()
        if st.startswith("#"):
            head, cap = st.lstrip("# ").strip(), ""
        elif st.startswith("Figure"):
            cap = st
        if "<!-- image -->" in line:
            n += 1
            out[f"fig-{n:04d}"] = f"{head} {cap}"
    return out


def wants(context, view):
    """Does this figure's own context say it shows the face we asked for?

    Both ways round: a context that says front AND rear says neither, because
    that is a chapter heading over a page holding both elevations.
    """
    want, other = (FRONT, REAR) if view == "front" else (REAR, FRONT)
    return bool(want.search(context)) and not other.search(context)


def bands(path, min_frac=0.55, gap=6, join=30):
    """The horizontal strips of device-like ink in a figure, top to bottom.

    A DATASHEET FIGURE OFTEN HOLDS TWO FACES. Edgecore's EPS203 draws the front
    above the rear with numbered callout bubbles around both, and `outline`
    takes the ink bounding box of the lot - one rectangle spanning 780 px of
    which the device is a tenth, measurable as nothing. Split it first and each
    face is exact: 1.87% and 0.85% against the datasheet's own W/H.

    `min_frac` is what separates a face from a callout: a faceplate is dark
    across nearly the whole frame, a numbered bubble across a few percent.

    A FACE IS NOT ONE UNBROKEN BAND, which is why the strips are then joined.
    That same front splits into four - a vent strip, each row of jacks, and the
    printed numbering - because the metal between the rows is pale, while its
    REAR came back whole. The difference is the drawing, not the device, so
    bands a few pixels apart are one face and the 250 px between two faces is
    not.
    """
    a = np.asarray(Image.open(path).convert('L'), dtype=float)
    h, w = a.shape
    dark = (a < 200).sum(axis=1) > w * min_frac
    out, start = [], None
    for y in range(h):
        if dark[y] and start is None:
            start = y
        elif not dark[y] and start is not None:
            if y - start > gap:
                out.append((start, y - 1))
            start = None
    if start is not None and h - start > gap:
        out.append((start, h - 1))
    merged = []
    for b in out:
        if merged and b[0] - merged[-1][1] <= join:
            merged[-1] = (merged[-1][0], b[1])
        else:
            merged.append(b)
    return merged


def band_box(path, y0, y1, min_frac=0.30):
    """One band's left and right edges, so a face becomes a full rectangle."""
    a = np.asarray(Image.open(path).convert('L'), dtype=float)[y0:y1 + 1]
    hh, w = a.shape
    cols = np.where((a < 200).sum(axis=0) > hh * min_frac)[0]
    if not len(cols):
        return None
    return int(cols[0]), int(cols[-1]), y0, y1


def outline(path):
    """The device box within a figure, or None if nothing device-shaped is there."""
    try:
        a = np.asarray(Image.open(path).convert('L'), dtype=float)
    except Exception:
        return None
    h, w = a.shape
    if w < MIN_PX:
        return None
    d = a < 200
    rows = np.where(d.sum(axis=1) > w * 0.3)[0]
    cols = np.where(d.sum(axis=0) > h * 0.3)[0]
    if len(rows) < 10 or len(cols) < 10:
        return None
    return int(cols[0]), int(cols[-1]), int(rows[0]), int(rows[-1])


def better(cand, best):
    """GATE 1 IS A THRESHOLD, NOT A SCORE.

    Ranking every candidate by aspect error picks the figure that happens to be
    drawn most exactly, which among figures that all carry geometry is noise -
    and it cost resolution every time, because a guide figure sits at 2.6 px/mm
    where the same device's product photograph sits at 3.8. So a passer beats a
    failer, passers are ranked by px/mm, and only among failers does the
    least-wrong one win, since there the error is all we know.
    """
    if best is None:
        return True
    bp, cp = best["gate1_error"] <= TOL, cand["gate1_error"] <= TOL
    if cp != bp:
        return cp
    if cp:
        return cand["px_per_mm"] > best["px_per_mm"]
    return cand["gate1_error"] < best["gate1_error"]


def candidates(intake, docs, name, view):
    """Every image that claims, in its own words, to show this device's face."""
    out = []
    for docname, figs in docs.items():
        if name not in docname:
            continue
        for fig, context in figs.items():
            if not wants(context, view):
                continue
            for path in pathlib.Path(intake).glob(f"**/converted/{docname}/{fig}.png"):
                out.append((path, context.strip()[:60]))
    # A PRODUCT PHOTOGRAPH SAYS WHICH FACE IT IS IN ITS OWN NAME, and is often
    # the better source: the S9611-36D's front render is 3.83 px/mm against its
    # guide figure's 2.64, and passes Gate 1 at 0.1%. The naming convention here
    # is `<model>-N-front.png`, which is a label like any other.
    for path in pathlib.Path(intake).glob(f"**/*{name}*{view}*.png"):
        if "converted" not in str(path):
            out.append((path, f"product photograph ({path.name})"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library")
    ap.add_argument("--intake", required=True, help="root of the converted intake tree")
    ap.add_argument("--out", help="write the manifest here as JSON")
    ap.add_argument("--view", default="front", choices=["front", "rear"])
    args = ap.parse_args(argv)

    docs = {}
    for doc in glob.glob(f"{args.intake}/**/converted/*/doc.md", recursive=True):
        docs[pathlib.Path(doc).parent.name] = figure_context(doc)

    manifest, stats = {}, collections.Counter()
    for p in libwalk.iter_devices([args.library]):
        d = yaml.safe_load(open(p)) or {}
        dev = p.split('devices/')[1].replace('/device.yaml', '')
        name = d.get("name")
        size = ((d.get("views") or {}).get(args.view) or {}).get("size") or {}
        if not (name and size.get("w") and size.get("h")):
            continue
        stats["devices"] += 1
        want = size["w"] / size["h"]

        best = None
        for path, context in candidates(args.intake, docs, name, args.view):
            o = outline(path)
            if not o:
                continue
            x0, x1, y0, y1 = o
            w, h = x1 - x0 + 1, y1 - y0 + 1
            cand = {"figure": str(path.relative_to(args.intake)), "context": context,
                    "gate1_error": round(abs(w / h - want) / want, 4),
                    "px_per_mm": round(w / size["w"], 4),
                    "origin": [x0, y0], "box": [w, h]}
            if better(cand, best):
                best = cand
        if best is None:
            continue
        if any(name in k for k in docs):
            stats["with a document"] += 1
        best["passes_gate1"] = best["gate1_error"] <= TOL
        stats["gate 1 PASSES" if best["passes_gate1"] else "gate 1 fails"] += 1
        manifest[dev] = best

    for k in ("devices", "with a document", "gate 1 PASSES", "gate 1 fails"):
        print(f"  {stats[k]:5d}  {k}")
    print()
    for dev, v in sorted(manifest.items(), key=lambda kv: kv[1]["gate1_error"])[:12]:
        print(f"  {'PASS' if v['passes_gate1'] else 'fail'}  "
              f"{v['gate1_error'] * 100:5.2f}%  {v['px_per_mm']:6.3f} px/mm  "
              f"{dev:26s} {'/'.join(v['figure'].split('/')[-2:])}")
    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(manifest, indent=1, sort_keys=True))
        print(f"\nwrote {args.out}")
    return manifest


if __name__ == "__main__":
    main()
