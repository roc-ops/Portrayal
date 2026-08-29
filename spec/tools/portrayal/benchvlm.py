#!/usr/bin/env python3
"""Ask a vision model to find the ports, in the same coordinates as the truth.

The question this exists to answer is narrow and worth keeping narrow: can a
model that costs almost nothing to run do the PERCEPTION half of a modelling
job - look at a faceplate and say where the ports are - well enough to be worth
building on. Not model a device. Find the cages.

TWO THINGS ABOUT THESE IMAGES THAT DECIDE THE RESULT BEFORE THE MODEL DOES.

A FACEPLATE IS 10:1. A 1RU panel at 3 px/mm is about 1330 x 130 pixels, and
handing that to a vision model whole means every port is a few pixels in a strip
the model will letterbox into a square. So the panel is cut into overlapping
tiles about two-to-one and each is enlarged before it is sent. That is not
flattering the model - it is the same thing a person does when they zoom in -
but it IS a choice this harness makes, and a poor score at one tile size is not
a poor score at every tile size.

THE TILES OVERLAP, SO THE MODEL SEES SOME PORTS TWICE. Merging is by IoU, and a
duplicate that survives merging is a false positive the score should keep,
because a detector that reports a cage twice has reported it twice.

Nothing here is specific to one model. `--model` names any mlx-vlm checkpoint;
the prompt asks for JSON and the parse tolerates the fences and prose a chat
model wraps it in, because refusing to parse those would measure the model's
manners rather than its eyesight.

    benchvlm.py --truth gt.json --intake <tree> --out vlm.json
    benchvlm.py --truth gt.json --intake <tree> --out vlm.json --only s6301 --overlay ov/
"""
import argparse
import json
import pathlib
import re

from PIL import Image

# THE PROMPT IS IN THE MODEL'S OWN DIALECT, AND THAT IS NOT A DETAIL.
#
# The first version here was a careful specification - what a cage is, what to
# ignore, and a JSON schema to answer in. On a tile showing twelve RJ45 jacks
# it returned `{"ports": []}`, every time, at every size. The same tile, asked
# in the phrasing Qwen's grounding was trained on - "outline the position of
# ... and output all the coordinates in JSON format" - returned boxes.
#
# So a zero from a vision model is three different findings until you check
# which: it did not answer, it answered in a coordinate system you did not
# expect, or it genuinely cannot see. Only the third is about the model.
#
# "each individual ... one box per port" is here because without it the model
# returns ONE box around a whole row of twenty-four cages. It has some idea
# that ports are there; itemising them is the part it does not do.
PROMPT = (
    "Outline the position of each individual ethernet port, transceiver cage "
    "and socket, one box per port, and output all the coordinates in JSON "
    "format."
)


def tiles(w, h, aspect=2.0, overlap=0.25):
    """Cut a long panel into overlapping windows about `aspect` to one.

    A whole 10:1 strip gives a model a few pixels per port; one tile per port
    gives it no context to see a row with. Two-to-one is the middle, and the
    overlap is what stops a cage that straddles a seam from being lost by both
    tiles.
    """
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


def parse_boxes(text, sx, sy, ox, oy):
    """Pull boxes out of whatever the model said, and put them back in figure px.

    A chat model fences its JSON, prefaces it, or trails an explanation. So
    every 4-number list in the whole reply is taken, rather than the contents of
    a `"ports"` key - a model that answered correctly in a shape we did not ask
    for still answered correctly, and an attempt to find that key first was
    tripped by its own nested braces and returned nothing at all.
    """
    out = []
    for nums in re.findall(r'\[\s*(-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?){3})\s*\]',
                           text):
        x1, y1, x2, y2 = [float(v) for v in re.split(r'\s*,\s*', nums)]
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            continue
        out.append([ox + x1 / sx, oy + y1 / sy, w / sx, h / sy, 1.0])
    return out


def iou(a, b):
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def merge(boxes, thresh=0.5):
    """One box per cage across the seams. Anything below `thresh` stays separate."""
    kept = []
    for b in sorted(boxes, key=lambda b: -(b[2] * b[3])):
        if not any(iou(b, k) >= thresh for k in kept):
            kept.append(b)
    return kept


def run_device(model, processor, config, path, origin, panel, scale, aspect, overlay):
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template

    im = Image.open(path).convert("RGB")
    x0, y0 = origin
    pw, ph = panel
    panel_im = im.crop((x0, y0, x0 + pw, y0 + ph))
    found, shots = [], []
    for (tx, ty, tw, th) in tiles(pw, ph, aspect=aspect):
        tile = panel_im.crop((tx, ty, tx + tw, ty + th))
        big = tile.resize((int(tw * scale), int(th * scale)), Image.LANCZOS)
        prompt = apply_chat_template(processor, config, PROMPT, num_images=1)
        out = generate(model, processor, prompt, [big], max_tokens=1200,
                       temperature=0.0, verbose=False)
        text = out.text if hasattr(out, "text") else str(out)
        found += parse_boxes(text, scale, scale, x0 + tx, y0 + ty)
        if overlay:
            shots.append((big, text))
    return merge(found), shots


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", required=True)
    ap.add_argument("--intake", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="mlx-community/Qwen2.5-VL-7B-Instruct-4bit")
    # 2x, MEASURED, NOT ASSUMED. Enlarging looked free and is not: at 4x the
    # model called a switch faceplate "a digital clock or timer interface",
    # where at 2x it read the port numbers off the same tile. A sweep of
    # aspect x scale x phrasing on one device put 2.0/2 ahead of the other
    # eleven combinations, so these defaults are the model's best showing and
    # not the first thing that ran.
    ap.add_argument("--scale", type=float, default=2.0,
                    help="how much to enlarge each tile before sending it")
    ap.add_argument("--aspect", type=float, default=2.0, help="tile width / height")
    ap.add_argument("--only", help="one device, by substring")
    ap.add_argument("--overlay", help="draw the merged boxes onto the figure, here")
    args = ap.parse_args(argv)

    from mlx_vlm import load
    from mlx_vlm.utils import load_config
    model, processor = load(args.model)
    config = load_config(args.model)

    truth = json.loads(pathlib.Path(args.truth).read_text())
    preds = {}
    for dev, v in sorted(truth.items()):
        if args.only and args.only not in dev:
            continue
        boxes, _ = run_device(model, processor, config,
                              pathlib.Path(args.intake) / v["figure"],
                              v["origin"], v["box"], args.scale, args.aspect,
                              args.overlay)
        preds[dev] = boxes
        print(f"  {len(boxes):5d}  {dev}", flush=True)
        if args.overlay:
            from PIL import ImageDraw
            im = Image.open(pathlib.Path(args.intake) / v["figure"]).convert("RGB")
            d = ImageDraw.Draw(im)
            for b in boxes:
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
