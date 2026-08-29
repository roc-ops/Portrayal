#!/usr/bin/env python3
"""Score a detector's boxes against what the library says is on the face.

Predictions are `{device: [[x, y, w, h, score], ...]}` in figure pixels, which
is the coordinate system `benchgt.py` already put the truth in. Matching is
greedy by confidence at an IoU threshold, one prediction to one box, and what
comes back is precision, recall and F1.

WHAT IS SCORED, AND WHY IT IS NOT EVERYTHING. Only boxes the library's own
`groups` call a Port. Half the ground truth is lamps, and a 1.5 mm lamp on a
figure at 3 px/mm is four pixels across - scoring those would measure the
figure's resolution and report it as the model's eyesight. They stay in the
truth file, because a detector that finds them has done something, and they
stay out of the headline.

EVERY RESULT CARRIES ITS px/mm. A score on the S9110's vendor render at 3.8
px/mm and a score on a guide figure at 2.9 are not the same test, and averaging
them into one number hides the only variable that has ever limited a reading in
this project. The per-device table is the result; the mean is a convenience.

AND IT CARRIES A FLOOR. A detector is only interesting against something, so
`--baseline` scores a fixed guess - the whole panel, once - which is what "no
information" looks like. Anything that cannot beat it has told us nothing.

    benchscore.py --truth gt.json --pred out.json
    benchscore.py --truth gt.json --pred out.json --iou 0.3 --term LED
"""
import argparse
import json
import pathlib


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def match(preds, truth, thresh):
    """Greedy by confidence: the surest prediction picks its box first.

    One prediction to one box, both ways. A detector that returns fifty
    overlapping boxes on one cage gets one hit and forty-nine false positives,
    which is the right answer - a port that is found fifty times is not found
    fifty times.
    """
    taken, hits, pairs = set(), 0, []
    for p in sorted(preds, key=lambda p: -(p[4] if len(p) > 4 else 1.0)):
        best, best_i = None, 0.0
        for i, t in enumerate(truth):
            if i in taken:
                continue
            v = iou(p[:4], t)
            if v > best_i:
                best, best_i = i, v
        if best is not None and best_i >= thresh:
            taken.add(best)
            hits += 1
            pairs.append((p, truth[best], best_i))
    return hits, pairs


def prf(hits, npred, ntrue):
    p = hits / npred if npred else 0.0
    r = hits / ntrue if ntrue else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", required=True)
    ap.add_argument("--pred", help="a detector's boxes; omit to score the floor only")
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--term", default="Port", help="which class to score; '' for all")
    ap.add_argument("--baseline", action="store_true",
                    help="also score one box covering the whole panel")
    ap.add_argument("--out", help="write the per-device table here as JSON")
    args = ap.parse_args(argv)

    truth = json.loads(pathlib.Path(args.truth).read_text())
    preds = json.loads(pathlib.Path(args.pred).read_text()) if args.pred else {}

    rows, tot = [], [0, 0, 0]
    for dev, v in sorted(truth.items()):
        boxes = [b["px"] for b in v["boxes"]
                 if not args.term or b.get("term") == args.term]
        if not boxes:
            continue
        got = preds.get(dev)
        if got is None and args.baseline:
            got = [[v["origin"][0], v["origin"][1], v["box"][0], v["box"][1], 1.0]]
        got = got or []
        hits, _ = match(got, boxes, args.iou)
        p, r, f = prf(hits, len(got), len(boxes))
        tot[0] += hits
        tot[1] += len(got)
        tot[2] += len(boxes)
        rows.append({"device": dev, "px_per_mm": v["px_per_mm"],
                     "gate1_error": v["gate1_error"], "truth": len(boxes),
                     "pred": len(got), "hits": hits,
                     "precision": round(p, 3), "recall": round(r, 3),
                     "f1": round(f, 3),
                     "figure": v["figure"]})

    print(f"  IoU >= {args.iou}   term {args.term or '(all)'}\n")
    print(f"  {'px/mm':>6} {'truth':>6} {'pred':>6} {'hit':>5} "
          f"{'P':>6} {'R':>6} {'F1':>6}  device")
    for x in sorted(rows, key=lambda x: -x["f1"]):
        print(f"  {x['px_per_mm']:6.2f} {x['truth']:6d} {x['pred']:6d} {x['hits']:5d} "
              f"{x['precision']:6.3f} {x['recall']:6.3f} {x['f1']:6.3f}  {x['device']}")
    p, r, f = prf(*tot)
    print(f"\n  {len(rows)} devices, {tot[2]} boxes, {tot[1]} predictions")
    print(f"  micro  P {p:.3f}  R {r:.3f}  F1 {f:.3f}")
    if rows:
        lo = min(rows, key=lambda x: x["px_per_mm"])
        hi = max(rows, key=lambda x: x["px_per_mm"])
        print(f"  spread {lo['px_per_mm']:.2f} px/mm F1 {lo['f1']:.3f}"
              f"  ->  {hi['px_per_mm']:.2f} px/mm F1 {hi['f1']:.3f}")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(rows, indent=1, sort_keys=True))
        print(f"\nwrote {args.out}")
    return rows


if __name__ == "__main__":
    main()
