#!/usr/bin/env python3
"""Extract figures from vendor PDFs WITH their context.

pdfimages gives you a directory of anonymous PNGs. What makes a figure useful
for modelling is the sentence next to it - "Figure 218: Removing the Front Power
Tray Bezel on the Cisco ASR 9922 Router" is the difference between an image and
evidence. Docling keeps the caption, the page, and the reading order, so a
figure arrives with the text that says what it shows.

Two stages, on purpose. Converting a PDF costs tens of seconds; deciding which
pictures are figures costs nothing. So the converter saves EVERY picture and
writes raw.json, and classify() sorts them afterwards. Retuning the filter is
then a one-second re-read of raw.json instead of an hour of reconversion, and
the pictures the filter rejected are still on disk to be argued with.

Output per PDF, under working/images/<stem>/:
    fig-<n>.png       every picture found, kept or not
    raw.json          every picture: page, caption, w, h - no judgement
    index.json        figures[] = the keepers, rejected[] = the rest with a reason
    doc.md            the whole document as markdown

Everything lands in working/ and stays there. Nothing here is redistributable;
these are facts to read, not files to publish.
"""
import argparse, json, re, sys, time
from collections import Counter
from pathlib import Path

from PIL import Image

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# What a figure is NOT.
#
# An icon, a logo, a numbered callout bullet: small in both directions. 200px
# at scale 3.0 is about 0.9in on the page.
ICON_PX = 200
# The Cisco chapter-header cityscape: a wide photograph pasted at the top of
# every chapter. Dimensions cannot find it. A line-card faceplate is wide and
# short too, and they overlap: matching on width and aspect cost us the ASR 9900
# RP elevation, the SIP-700 with its numbered callouts, and a run of page-width
# power-cordset drawings that repeat because there is one per country.
#
# What is actually true of a banner is that it is the SAME PICTURE every time,
# in every guide the publisher ships. So compare the pictures, across the whole
# corpus rather than one document: an average hash over an 8x8 thumbnail is
# stable against the few-pixel crop wobble between chapters.
#
# Corpus-wide is what makes it safe. Within one document a run of near-identical
# real figures - thirty power cordsets, one per country - clusters just as
# tightly as furniture does. Across 69 Cisco PDFs the cityscape has 130 near
# copies and the largest cluster of real drawings has 6, so the threshold sits
# in open space. Measured on this corpus: at Hamming 3 and a cluster of 10 the
# rule takes 130 pictures and every one of them is the cityscape.
#
# The corollary is that this rule needs a corpus, and the corpus is ONE
# PUBLISHER. Pass all of a vendor's PDFs to one invocation. A single-PDF run
# pools only that document and under-detects; pooling every vendor together
# over-detects, because a 64-bit average hash does collide across unrelated
# documents and the extra hits push real figures over the threshold - that
# mistake cost the ASR 9001 DC power tray before it was caught.
BANNER_ASPECT = 2.5
BANNER_HAMMING = 3
BANNER_CLUSTER = 10


def ahash(im):
    """64-bit average hash: which of an 8x8 thumbnail's cells beat the mean."""
    g = im.convert("L").resize((8, 8), Image.BILINEAR)
    px = list(g.getdata())
    m = sum(px) / len(px)
    bits = 0
    for i, v in enumerate(px):
        if v > m:
            bits |= 1 << i
    return f"{bits:016x}"


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def classify(pics, banner_rule=True, pool=None):
    """Split raw picture records into keepers and rejects.

    Takes and returns plain dicts, so it can be re-run over an existing
    raw.json without touching the PDF.

    banner_rule=False disables the repeated-width rule. It is keyed on Cisco's
    chapter-header cityscape, and a publisher who simply draws every figure at
    the page width defeats it: on Casa's C100G guide EVERY wide figure shares a
    width, so the rule dropped fig-0038, the fan tray face with its HS button
    and its three status LEDs. Casa prints no repeated header image at all -
    the C40G guide, same rule, dropped zero - so for Casa the rule can only
    subtract. Pass --no-banner for a publisher whose figures are page-width.
    """
    def bannerish(p):
        return (not p["caption"] and p.get("ahash")
                and p["w"] / max(p["h"], 1) > BANNER_ASPECT)

    if not banner_rule:
        pool = []
    elif pool is None:
        pool = [p["ahash"] for p in pics if bannerish(p)]
    kept, rejected = [], []
    for p in pics:
        w, h, cap = p["w"], p["h"], p["caption"]
        aspect = w / max(h, 1)
        why = ""
        if w < ICON_PX and h < ICON_PX and not cap:
            why = "icon"
        elif bannerish(p) and sum(
                1 for q in pool if hamming(p["ahash"], q) <= BANNER_HAMMING
                ) >= BANNER_CLUSTER:
            why = "banner"
        if why:
            rejected.append(dict(p, drop_reason=why))
        else:
            kept.append(p)
    return kept, rejected


def sections(md, recs):
    """Tag each record with the markdown heading it sits under."""
    heads = [(m.start(), m.group(1).strip())
             for m in re.finditer(r"^#{1,6}\s+(.+)$", md, re.M)]
    for r in recs:
        r["section"] = ""
        if r["caption"]:
            k = md.find(r["caption"][:60])
            if k > 0:
                prior = [h for p, h in heads if p < k]
                r["section"] = prior[-1] if prior else ""


def convert(pdf: Path, out: Path, scale: float):
    opts = PdfPipelineOptions()
    opts.images_scale = scale
    opts.generate_picture_images = True
    opts.generate_page_images = False
    opts.do_ocr = False
    opts.do_table_structure = True
    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = conv.convert(str(pdf)).document

    out.mkdir(parents=True, exist_ok=True)
    pics = []
    for i, pic in enumerate(doc.pictures):
        im = pic.get_image(doc)
        if im is None:
            continue
        name = f"fig-{len(pics):04d}.png"
        im.save(out / name)
        cap = ""
        try:
            cap = (pic.caption_text(doc) or "").strip()
        except Exception:
            pass
        pics.append({"file": name, "page": pic.prov[0].page_no if pic.prov else None,
                     "caption": cap, "w": im.width, "h": im.height,
                     "ahash": ahash(im), "self_ref": pic.self_ref})
    md = doc.export_to_markdown()
    (out / "doc.md").write_text(md)
    (out / "raw.json").write_text(json.dumps(
        {"pdf": str(pdf), "scale": scale, "pictures": pics}, indent=1))
    return pics, md


def write_index(pdf, out, pics, md, banner_rule=True, pool=None):
    kept, rejected = classify(pics, banner_rule, pool)
    sections(md, kept)
    sections(md, rejected)
    (out / "index.json").write_text(json.dumps({
        "pdf": str(pdf),
        "figures": kept,
        "rejected": rejected,
        "dropped": len(rejected),
        "drops_by_reason": dict(Counter(r["drop_reason"] for r in rejected)),
    }, indent=1))
    return len(kept)


def hashes(out: Path):
    """Every uncaptioned wide picture's hash, for the corpus banner pool."""
    raw = out / "raw.json"
    if not raw.exists():
        return []
    return [p["ahash"] for p in json.loads(raw.read_text())["pictures"]
            if not p["caption"] and p.get("ahash")
            and p["w"] / max(p["h"], 1) > BANNER_ASPECT]


def run(pdf: Path, out_root: Path, scale: float, reclassify: bool,
        banner_rule: bool = True, pool=None):
    out = out_root / pdf.stem
    raw = out / "raw.json"
    if raw.exists():
        if not reclassify:
            return "skip", 0
        d = json.loads(raw.read_text())
        pics = d["pictures"]
        # raw.json written before hashing existed: fill it in from the PNGs,
        # once, so later reclassifies are free.
        if any("ahash" not in p for p in pics):
            for p in pics:
                if "ahash" not in p:
                    with Image.open(out / p["file"]) as im:
                        p["ahash"] = ahash(im)
            raw.write_text(json.dumps(d, indent=1))
        return "recls", write_index(pdf, out, pics,
                                    (out / "doc.md").read_text(), banner_rule,
                                    pool)
    pics, md = convert(pdf, out, scale)
    return "ok", write_index(pdf, out, pics, md, banner_rule, pool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--out", default="working/images")
    ap.add_argument("--scale", type=float, default=3.0)
    ap.add_argument("--reclassify", action="store_true",
                    help="re-run the filter over an existing raw.json; no PDF work")
    ap.add_argument("--no-banner", dest="banner", action="store_false",
                    help="disable the repeated-width banner rule; for a publisher "
                         "whose every figure is drawn at the page width")
    a = ap.parse_args()
    root = Path(a.out)
    # One pool for the whole invocation - see BANNER_CLUSTER.
    pool = []
    if a.banner:
        for p in a.pdfs:
            pool += hashes(root / Path(p).stem)
    for p in a.pdfs:
        p = Path(p)
        t0 = time.time()
        try:
            status, n = run(p, root, a.scale, a.reclassify, a.banner,
                            pool or None)
        except Exception as e:
            print(f"FAIL {p.name}: {type(e).__name__}: {e}", flush=True)
            continue
        print(f"{status:5s} {p.name}: {n} figures in {time.time()-t0:.0f}s",
              flush=True)


if __name__ == "__main__":
    main()
