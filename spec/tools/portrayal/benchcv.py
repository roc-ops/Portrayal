#!/usr/bin/env python3
"""The floor a model has to clear: find the ports with arithmetic and no model.

A benchmark without a baseline reports a number nobody can size. This is the
cheapest detector that is not a joke - threshold the panel, take the connected
dark regions, keep the ones whose MILLIMETRE size could be a port - and it runs
in a second on a laptop for nothing. Whatever a GPU is asked to do afterwards
has to beat this, or the answer to "can a smaller model do this" is that no
model was needed.

IT IS GIVEN THE SCALE, AND THAT IS FAIR. `figmap` derives px/mm from the
device's own outline before any detector runs, so filtering candidates by
millimetres is information the pipeline genuinely has. What it is NOT given is
where the ports are, how many there are, or what pitch they sit on - which is
the whole of the question.

    benchcv.py --truth gt.json --intake <tree> --out cv.json
"""
import argparse
import json
import pathlib

import cv2
import numpy as np

# A cage is a real object with a real size: an SFP is 13.7 x 9.8 mm, a QSFP-DD
# 18.4 x 13.6, an RJ45 about 12.7 x 11, and a ganged pair twice one of those.
# Nothing on a faceplate that is a PORT is under 5 mm or over 45 mm on a side.
MIN_MM, MAX_MM = 5.0, 45.0
MAX_ASPECT = 4.0


def detect(path, ppm, origin, panel):
    """Dark blobs of port-like size, as [x, y, w, h, score] in figure pixels."""
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return []
    x0, y0 = origin
    pw, ph = panel
    crop = im[max(0, y0):y0 + ph, max(0, x0):x0 + pw]
    if crop.size == 0:
        return []
    # A port is an OPENING, so it is darker than the metal around it. Otsu picks
    # the split for each figure rather than a constant that suits one vendor.
    _, th = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # close the internal detail - a cage's tongue and lamps break it into pieces
    k = max(1, int(round(1.0 * ppm)))
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        wmm, hmm = w / ppm, h / ppm
        if not (MIN_MM <= wmm <= MAX_MM and MIN_MM <= hmm <= MAX_MM):
            continue
        if max(wmm / hmm, hmm / wmm) > MAX_ASPECT:
            continue
        # how solidly the blob fills its own box - a cage does, a vent field
        # and a stray run of shadow do not
        out.append([float(x0 + x), float(y0 + y), float(w), float(h),
                    round(float(area) / (w * h), 3)])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", required=True, help="benchgt.py's output, for the scale")
    ap.add_argument("--intake", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    truth = json.loads(pathlib.Path(args.truth).read_text())
    preds = {}
    for dev, v in sorted(truth.items()):
        preds[dev] = detect(pathlib.Path(args.intake) / v["figure"],
                            v["px_per_mm"], v["origin"], v["box"])
    pathlib.Path(args.out).write_text(json.dumps(preds, indent=1, sort_keys=True))
    n = sum(len(p) for p in preds.values())
    print(f"  {len(preds)} devices, {n} candidate boxes\nwrote {args.out}")
    return preds


if __name__ == "__main__":
    main()
