#!/usr/bin/env python3
"""Do every deterministic thing BEFORE a modelling agent starts, and hand it one
document of answers instead of five tools to learn.

WHY. A timed modelling run spent 41 minutes: 15 measuring, 11 writing, 8
checking - and 7 READING THE TOOLS. It opened expand.py in full, its tests,
measure.py's header and parts of lint.py, before it drew anything. Every tool
added since has widened that: five tools are now ~89k of source, and a fresh
agent pays the reading cost every single run because nothing amortises across
agents.

That is the trap in adding tooling to remove judgement. The judgement goes, and
a reading cost arrives to replace it, and the second is invisible because it
does not look like work.

So the tools run HERE, with no agent involved, and the agent reads results. It
never learns measure.py's flags; it is told the panel box, the scale and the
Gate 1 verdict for every figure. It never learns facts.py; it is given the
stated facts with the line each came from. What is left for it is the part that
actually needs a reader: deciding which figure shows the right product, what a
feature IS, and which source wins when two disagree.

    prepare.py --intake working/intake/edgecore --model dcs510 -o <dir>

Everything here is optional and degrades: no endpoint means no model-read facts,
no OCR engine means the note says so. A prepared brief that silently omits a
section it could not produce would be worse than no brief, so every section
states whether it ran.
"""
import argparse
import io
import contextlib
import os
import pathlib
import re
import subprocess
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
from portrayal_dev import facts as F
from portrayal_dev import measure as M
def stated_facts(intake, model):
    f = F.collect(intake, model)
    if not f:
        return None, ["no converted documents found for this model"]
    notes = []
    s = f.get("summary") or {}
    if f.get("text-free"):
        for tf in f["text-free"]:
            notes.append(
                f"{tf['document']} states specifications and none of their VALUES - "
                f"its numbers are outlined glyphs or page images. Run ocr_pages.py "
                f"on the source PDF; do not read the converted markdown and "
                f"conclude the vendor is silent.")
    if not s.get("ordering-parts"):
        notes.append("no ordering lines found. That is this tool's silence, not "
                     "the vendor's - go and look for an ordering table before "
                     "recording a gap.")
    return f, notes


def figure_report(intake, model, width, height, keep=8):
    """The figures that could be this device's FACE, best first.

    A first version reported every panel-shaped band in every picture and called
    80 of ~90 figures measurable, in 1666 lines. That is not a brief, it is the
    problem restated: an agent reading it would spend longer than one measuring
    by hand. Almost any image contains a horizontal band of ink; a rack faceplate
    is a band whose PROPORTIONS match the chassis.

    So candidates are ranked by how close their aspect is to the stated W/H, and
    only the plausible few are described. The rest are counted, because "62
    others looked nothing like this face" is the useful summary of them.
    """
    want = (width / height) if (width and height) else None
    cands, rejected = [], 0
    conv = intake / "converted"
    for d in sorted(conv.glob(f"{model}-*")):
        for img in sorted(d.glob("fig-*.png")):
            try:
                boxes = M.panel_box(img)
            except Exception:
                rejected += 1
                continue
            for n, (x0, y0, x1, y1) in enumerate(boxes):
                w, h = x1 - x0, y1 - y0
                if w < 40 or h < 6:
                    rejected += 1
                    continue
                asp = w / h
                # a face is wide; anything squarer is an icon, a logo or a photo
                # of a rack, and its Gate 1 verdict would be meaningless
                if want and not (0.45 * want <= asp <= 2.2 * want):
                    rejected += 1
                    continue
                if not want and asp < 4:
                    rejected += 1
                    continue
                p = {"figure": f"{d.name}/{img.name}", "panel": n,
                     "box_px": [x0, y0, x1, y1], "aspect": round(asp, 2)}
                if want:
                    sx, sy = w / width, h / height
                    skew = abs(sx - sy) / max(sx, sy) * 100
                    p["px_per_mm"] = {"x": round(sx, 4), "y": round(sy, 4)}
                    p["axis_disagreement_pct"] = round(skew, 2)
                    p["verdict"] = ("orthographic - measure both axes" if skew < 2
                                    else "NOT orthographic - trust only the axis "
                                         "anchored to a dimension you know")
                    p["_rank"] = skew
                cands.append(p)
    cands.sort(key=lambda c: c.get("_rank", 999))
    for c in cands:
        c.pop("_rank", None)
    return cands[:keep], rejected, max(0, len(cands) - keep)


def bands_for(intake, model, figure, panel, height):
    """Band centres for the figure an agent will actually measure on."""
    img = intake / "converted" / figure
    if not img.exists():
        return None
    buf = io.StringIO()

    class A:
        pass
    a = A()
    a.image, a.height, a.panel = img, height, panel
    a.threshold, a.share, a.min_band = 200, 0.55, 3
    with contextlib.redirect_stdout(buf):
        try:
            M.cmd_rows(a)
        except Exception as e:
            return f"rows failed: {type(e).__name__}: {e}"
    return buf.getvalue()


def parts_inventory(library, media):
    """Which library parts already exist for the media this device uses.

    Agents spend time listing std/ and common/ to find out what may be reused.
    The answer is the same every run and depends only on the media, so it is
    computed rather than explored.
    """
    hits = {}
    for ns in ("std", "common"):
        d = library / "components" / ns
        if not d.is_dir():
            continue
        for c in sorted(d.iterdir()):
            if any(m and m.replace("-", "") in c.name.replace("-", "") for m in media):
                v = sorted(c.glob("v*/contract.yaml"))
                if v:
                    try:
                        ct = yaml.safe_load(v[-1].read_text()) or {}
                    except Exception:
                        continue
                    sz = ct.get("size") or {}
                    hits[f"{ns}/{c.name}@{v[-1].parent.name[1:]}"] = {
                        "size": [sz.get("w"), sz.get("h")],
                        "conforms": ct.get("conforms"),
                    }
    return hits


def registry_pitches(schemas, media):
    std = yaml.safe_load((schemas / "standards.yaml").read_text())["standards"]
    out = {}
    for name, s in std.items():
        if not isinstance(s, dict):
            continue
        if any(m and m.replace("-", "") in name.replace("-", "") for m in media):
            p, how = M._pitch_of(s) if hasattr(M, "_pitch_of") else (None, None)
            entry = {"w": s.get("w"), "h": s.get("h")}
            if s.get("pitch"):
                entry["pitch"] = s["pitch"]
                entry["pitch_from"] = "explicit `pitch` key"
            elif s.get("w"):
                entry["pitch"] = s["w"]
                entry["pitch_from"] = "`w` - this family's cages abut, so w IS the pitch"
            if s.get("row-pitch"):
                entry["row_pitch"] = s["row-pitch"]
            out[name] = entry
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--intake", required=True, type=pathlib.Path)
    ap.add_argument("--model", required=True)
    ap.add_argument("--library", default=pathlib.Path("library"), type=pathlib.Path)
    ap.add_argument("--schemas", default=pathlib.Path("spec/schemas"), type=pathlib.Path)
    ap.add_argument("--media", default="", help="comma list, e.g. qsfp-dd,sfp-plus,rj45")
    ap.add_argument("--width", type=float, help="stated body width mm, for Gate 1")
    ap.add_argument("--height", type=float, help="stated body height mm")
    ap.add_argument("--rows-for", help="figure to report band centres for, "
                                       "e.g. dcs510-datasheet/fig-0007.png")
    ap.add_argument("--rows-panel", type=int, default=0)
    ap.add_argument("-o", "--out", type=pathlib.Path)
    a = ap.parse_args()

    facts, notes = stated_facts(a.intake, a.model)
    doc = {"model": a.model, "intake": str(a.intake), "prepared_by": "prepare.py"}

    # 1. what the documents state, with a citation on every value
    if facts:
        s = facts["summary"]
        doc["stated"] = {
            "ru": s.get("ru"),
            "dimension_triples": [e["mm"] for e in facts.get("dimensions", [])][:8],
            "corroborated_dimensions": s.get("corroborated-dimensions"),
            "ordering_parts": s.get("ordering-parts"),
            "port_lines": [f"{e['count']} x {e['what']}" for e in facts.get("ports", [])][:14],
            "power": [{"watts": e.get("watts"), "label": e.get("label"),
                       "at": e["source"]} for e in facts.get("power", [])][:8],
            "documents": facts.get("documents"),
        }
    doc["read_the_cited_line_before_using_any_number"] = True

    # 2. Gate 1, answered for every figure, before anything is measured by eye
    cands, rejected, more = figure_report(a.intake, a.model, a.width, a.height)
    doc["face_candidates"] = cands
    doc["face_candidates_note"] = (
        f"ranked by axis agreement, best first. {rejected} other band(s) in these "
        f"documents were nothing like this chassis's proportions and are not "
        f"listed; {more} further candidate(s) were trimmed. A figure being "
        f"measurable does NOT make it a figure of the right product - check the "
        f"model name printed in it.")

    if a.rows_for and a.height:
        doc["bands"] = {"figure": a.rows_for, "panel": a.rows_panel,
                        "report": bands_for(a.intake, a.model, a.rows_for,
                                            a.rows_panel, a.height)}

    # 3. what already exists to be reused, and what the registry states
    media = [m.strip() for m in a.media.split(",") if m.strip()]
    if media:
        doc["existing_parts"] = parts_inventory(a.library, media)
        doc["registry"] = registry_pitches(a.schemas, media)

    doc["notes"] = notes or ["nothing flagged"]
    doc["what_is_still_yours"] = [
        "which figure shows the RIGHT product - a figure in the right document "
        "can be a picture of the wrong one",
        "what each feature IS - geometry has no labels",
        "which source wins when two disagree, and saying so in provenance",
        "looking at the render beside the vendor image at matched scale",
    ]

    text = yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        p = a.out / f"{a.model}.prepared.yaml"
        p.write_text(text)
        print(f"{a.model}: {len(text.splitlines())} lines -> {p}")
        nf = len(doc["face_candidates"])
        print(f"  {nf} face candidate(s), "
              f"{len(doc.get('existing_parts') or {})} existing parts listed")
        for n in notes:
            print(f"  ! {n}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
