"""Run a trained detector down the same path the VLM took, so the two compare.

A detector's own validation number is computed on TILES and cannot be set
beside the other results here, which are per-device on a whole panel: a tile
score does not pay for the boxes a merge across seams gets wrong, and it counts
each faceplate as many samples rather than one. So the trained weights get the
identical treatment - cut the panel, predict, merge by IoU, project back into
figure pixels, and hand the result to the same scorer.

Only devices the training never saw are worth reading. `--val-only` uses the
same every-Nth-by-name rule `benchdata.py` split on, so the held-out set is the
held-out set and not a hopeful subset of it.

    benchyolo.py --truth gt.json --intake <tree> --weights best.pt --out y.json
"""
import argparse
import json
import pathlib
import sys

from PIL import Image

from portrayal_bench import benchvlm
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", required=True)
    ap.add_argument("--intake", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--aspect", type=float, default=2.0)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--val-every", type=int, default=4)
    ap.add_argument("--val-only", action="store_true",
                    help="score only the devices benchdata.py held out")
    ap.add_argument("--overlay")
    args = ap.parse_args(argv)

    from ultralytics import YOLO
    model = YOLO(args.weights)

    truth = json.loads(pathlib.Path(args.truth).read_text())
    preds = {}
    for i, (dev, v) in enumerate(sorted(truth.items())):
        if args.val_only and i % args.val_every != 0:
            continue
        im = Image.open(pathlib.Path(args.intake) / v["figure"]).convert("RGB")
        x0, y0 = v["origin"]
        pw, ph = v["box"]
        panel = im.crop((x0, y0, x0 + pw, y0 + ph))
        found = []
        for (tx, ty, tw, th) in benchvlm.tiles(pw, ph, aspect=args.aspect):
            tile = panel.crop((tx, ty, tx + tw, ty + th))
            big = tile.resize((int(tw * args.scale), int(th * args.scale)),
                              Image.LANCZOS)
            r = model.predict(big, conf=args.conf, verbose=False)[0]
            for b, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()):
                bx1, by1, bx2, by2 = b
                found.append([x0 + tx + bx1 / args.scale, y0 + ty + by1 / args.scale,
                              (bx2 - bx1) / args.scale, (by2 - by1) / args.scale,
                              round(c, 3)])
        preds[dev] = benchvlm.merge(found)
        print(f"  {len(preds[dev]):5d}  {dev}", flush=True)
        if args.overlay:
            from PIL import ImageDraw
            d = ImageDraw.Draw(im)
            for b in preds[dev]:
                d.rectangle([b[0], b[1], b[0] + b[2], b[1] + b[3]],
                            outline=(0, 255, 0), width=2)
            o = pathlib.Path(args.overlay)
            o.mkdir(parents=True, exist_ok=True)
            im.save(o / f"{dev.replace('/', '-')}.png")
    pathlib.Path(args.out).write_text(json.dumps(preds, indent=1, sort_keys=True))
    print(f"\nwrote {args.out}")
    return preds


if __name__ == "__main__":
    main()
