"""Cut the ground truth into a detection dataset, split so the score is honest.

The benchmark asks whether a model can find ports. If nothing off the shelf
can, the next question is whether a small one TRAINED on this can, and that
needs the truth as tiles and labels rather than as a manifest.

THE SPLIT IS BY DEVICE, AND THAT IS THE ONLY PART OF THIS FILE THAT MATTERS.
Every device here is a row of near-identical cages, so two tiles from one
faceplate are close to the same picture. Splitting tiles at random puts a
device's left half in train and its right half in val, and the val score then
measures memorisation and reports it as generalisation - on this corpus that
would be a very high number and a completely false one.

AND A SPLIT BY DEVICE IS STILL NOT A SPLIT BY VENDOR. Every figure in this set
is UfiSpace, drawn by one team in one house style. A model that scores well
here has learned to read UfiSpace drawings, which is worth having and is not
the same as reading a faceplate. Say so wherever the number is quoted.

    benchdata.py --truth gt.json --intake <tree> --out data/
"""
import argparse
import json
import pathlib

from PIL import Image

CLASSES = ["port"]


def tiles(w, h, aspect=2.0, overlap=0.25):
    """Same cut as the harness sends a model, so train and test see one shape."""
    tw = max(1, int(round(h * aspect)))
    if tw >= w:
        return [(0, 0, w, h)]
    step = max(1, int(round(tw * (1 - overlap))))
    out, x = [], 0
    while True:
        if x + tw >= w:
            out.append((w - tw, 0, tw, h))
            return out
        out.append((x, 0, tw, h))
        x += step


def clip(box, tx, ty, tw, th, keep=0.6):
    """A cage on a seam belongs to the tile that holds most of it.

    Labelling a sliver teaches a detector that a third of a cage is a cage,
    which on a face of forty-eight identical cages is a lesson it will apply
    everywhere.
    """
    x, y, w, h = box
    x1, y1 = max(x, tx), max(y, ty)
    x2, y2 = min(x + w, tx + tw), min(y + h, ty + th)
    if x2 <= x1 or y2 <= y1:
        return None
    if (x2 - x1) * (y2 - y1) < keep * w * h:
        return None
    return x1 - tx, y1 - ty, x2 - x1, y2 - y1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", required=True)
    ap.add_argument("--intake", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--term", default="Port")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--val-every", type=int, default=4,
                    help="every Nth device, by name, is held out")
    args = ap.parse_args(argv)

    truth = json.loads(pathlib.Path(args.truth).read_text())
    root = pathlib.Path(args.out)
    counts = {"train": [0, 0], "val": [0, 0]}
    held = []
    for i, (dev, v) in enumerate(sorted(truth.items())):
        split = "val" if i % args.val_every == 0 else "train"
        if split == "val":
            held.append(dev)
        im = Image.open(pathlib.Path(args.intake) / v["figure"]).convert("RGB")
        x0, y0 = v["origin"]
        pw, ph = v["box"]
        panel = im.crop((x0, y0, x0 + pw, y0 + ph))
        gt = [b["px"] for b in v["boxes"]
              if not args.term or b.get("term") == args.term]
        for j, (tx, ty, tw, th) in enumerate(tiles(pw, ph)):
            labels = []
            for b in gt:
                c = clip([b[0] - x0, b[1] - y0, b[2], b[3]], tx, ty, tw, th)
                if c is None:
                    continue
                cx, cy, cw, ch = c
                labels.append(f"0 {(cx + cw / 2) / tw:.6f} {(cy + ch / 2) / th:.6f} "
                              f"{cw / tw:.6f} {ch / th:.6f}")
            if not labels:
                continue
            stem = f"{dev.replace('/', '-')}-{j:02d}"
            for sub in ("images", "labels"):
                (root / sub / split).mkdir(parents=True, exist_ok=True)
            tile = panel.crop((tx, ty, tx + tw, ty + th))
            tile.resize((int(tw * args.scale), int(th * args.scale)),
                        Image.LANCZOS).save(root / "images" / split / f"{stem}.png")
            (root / "labels" / split / f"{stem}.txt").write_text("\n".join(labels))
            counts[split][0] += 1
            counts[split][1] += len(labels)

    (root / "data.yaml").write_text(
        f"path: {root.resolve()}\ntrain: images/train\nval: images/val\n"
        f"nc: {len(CLASSES)}\nnames: {CLASSES}\n")
    for k, (t, b) in counts.items():
        print(f"  {t:5d} tiles  {b:6d} boxes  {k}")
    print(f"\n  held out {len(held)} devices: {', '.join(held)}")
    print("  every figure in this set is one vendor - a score here is a score "
          "on UfiSpace drawings")
    print(f"\nwrote {root / 'data.yaml'}")


if __name__ == "__main__":
    main()
