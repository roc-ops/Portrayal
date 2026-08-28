#!/usr/bin/env python3
"""Pull the stated facts out of a device's converted documents, once.

WHY THIS EXISTS. Every modelling agent reads the same 13k tokens of converted
markdown to find the same dozen numbers - overall dimensions, RU, weight, port
counts, the ordering lines that name the PSU and fan SKUs, and the power
figures. That reading is identical every time and produces the same answers, so
it is inference spent on lookup. Worse, it is inference spent on lookup that
sometimes MISSES: 'not in the document I looked in' has been written as 'not in
the intake' seven times in one vendor's set, every one of them wrong.

WHAT IT REFUSES TO DO. It does not interpret, normalise units it is unsure of,
or fill a gap with a sibling's value. A fact it cannot read is simply absent,
and absence here means 'this tool did not find it', never 'the vendor does not
state it' - the two are different claims and only a person who has looked can
make the second. EVERY VALUE CARRIES THE FILE AND LINE IT CAME FROM, so the
agent can go and read the sentence rather than trusting this summary. A facts
file without provenance would just be a faster way to be confidently wrong.

WHAT IT IS FOR. The agent reads ~100 lines instead of paging a 60-page PDF, and
starts from a list of what IS stated, so the questions it spends its attention
on are the ones the documents do not answer.

    facts.py --intake working/intake/ufispace --model s9705-48d
    facts.py --intake working/intake/ufispace --all -o working/intake/ufispace/facts
"""
import argparse
import json
import pathlib
import re
import sys

import yaml


def _num(text):
    """`87. 7` -> 87.7, `19 . 86` -> 19.86.

    The converter drops spaces into numerals, so every numeric read has to
    tolerate them. Reading `87. 7` as 87 loses the fraction silently.
    """
    t = re.sub(r"\s+", "", str(text))
    try:
        return float(t)
    except ValueError:
        return None


DIMS = re.compile(r"([\d.\s]+?)\s*[x×]\s*([\d.\s]+?)\s*[x×]\s*([\d.\s]+?)\s*mm",
                  re.I)
RU = re.compile(r"\b(\d+)\s*RU\b", re.I)
KG = re.compile(r"([\d.\s]+?)\s*kg\b", re.I)
GRAMS = re.compile(r"([\d.\s]+?)\s*g\)", re.I)
PORTS = re.compile(r"^-?\s*(\d+)\s*[x×]\s*(.+?)\s*$")
WATTS = re.compile(r"([\d.\s]+?)\s*(?:W|Watts?)\b", re.I)


def _cite(path, i, line):
    return {"source": f"{path.parent.name}/{path.name}:{i}", "text": line.strip()[:160]}


def scan(path):
    """Every fact this tool knows how to read, with where it read it."""
    out = {"dimensions": [], "ru": [], "weight": [], "ports": [], "power": [],
           "ordering": [], "asic": []}
    lines = path.read_text(errors="replace").splitlines()
    section = None
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("##"):
            section = s.lstrip("#").strip()
            continue
        if not s:
            continue

        for m in DIMS.finditer(s):
            trio = [_num(m.group(k)) for k in (1, 2, 3)]
            if all(v and 1 < v < 2000 for v in trio):
                out["dimensions"].append(dict(_cite(path, i, s), mm=trio,
                                              section=section))
        m = RU.search(s)
        if m:
            out["ru"].append(dict(_cite(path, i, s), ru=int(m.group(1))))
        for m in KG.finditer(s):
            v = _num(m.group(1))
            if v and 0.01 < v < 500:
                out["weight"].append(dict(_cite(path, i, s), kg=v, section=section))
        m = PORTS.match(s)
        if m and not s.startswith("|"):
            out["ports"].append(dict(_cite(path, i, s), count=int(m.group(1)),
                                     what=m.group(2)))
        if re.search(r"\b(power|input)\b", s, re.I):
            w = WATTS.search(s)
            if w and _num(w.group(1)):
                out["power"].append(dict(_cite(path, i, s), watts=_num(w.group(1)),
                                         section=section))
            elif re.search(r"input\s*:", s, re.I):
                out["power"].append(dict(_cite(path, i, s), section=section))
        # An ordering line names a part a device can actually be bought with,
        # which is what decides WHICH library component a bay may seat. This is
        # the discrimination that keeps one wrong SKU out of ten devices.
        if re.match(r"^(PSU|FAN|MOD|ACC)-[A-Z0-9-]+,", s, re.I):
            out["ordering"].append(dict(_cite(path, i, s), section=section,
                                        part=s.split(",")[0].strip()))
        if re.search(r"\b(Broadcom|Marvell|Intel|Qumran|Jericho|Ramon|Tomahawk|Trident)"
                     r"\b.*\b[A-Z]{2,}\d{3,}", s):
            out["asic"].append(_cite(path, i, s))
    return out


def figures(doc_dir):
    """What pictures the conversion kept, and what their captions say.

    A negative answer about artwork is only as good as this count: 'no figure
    for this part' means something different at 62 of 62 than at 39 of 62.
    """
    idx = doc_dir / "index.json"
    if not idx.exists():
        return {"kept": len(list(doc_dir.glob("fig-*.png")))}
    try:
        data = json.loads(idx.read_text())
    except Exception:
        return {"kept": len(list(doc_dir.glob("fig-*.png")))}
    items = data if isinstance(data, list) else data.get("figures") or []
    caps = [str(it.get("caption") or "").strip() for it in items
            if isinstance(it, dict) and it.get("caption")]
    return {"kept": len(list(doc_dir.glob("fig-*.png"))),
            "captioned": len(caps), "captions": caps[:40]}


def collect(intake: pathlib.Path, model: str):
    conv = intake / "converted"
    docs = sorted(d for d in conv.glob(f"{model}-*") if (d / "doc.md").exists())
    if not docs:
        return None
    facts = {"model": model, "documents": [], "figures": {}, "text-free": []}
    merged = {}
    for d in docs:
        facts["documents"].append(d.name)
        got = scan(d / "doc.md")
        for k, v in got.items():
            merged.setdefault(k, []).extend(v)
        facts["figures"][d.name] = figures(d)

        # A DOCUMENT WITH NO EXTRACTABLE TEXT IS NOT A DOCUMENT WITH NOTHING IN
        # IT. Some vendor datasheets here are set entirely as outlined glyphs or
        # shipped as page images, so the conversion yields headings and bullet
        # marks and not one specification. An empty facts file then looks
        # identical to a device whose vendor publishes nothing - and the second
        # is a claim about the world that nobody has earned. Say which it is, and
        # point at the pictures, because that is where the content actually is.
        # THE LABELS SURVIVE AND THE VALUES DO NOT, which is what makes this
        # trap work. A word count says such a document is full of prose - it has
        # 93 distinct words - and every one of them is a legal disclaimer or a
        # section label like `Power Supply` or `Memory`. The specification
        # NUMBERS were set as outlined glyphs and extracted as nothing. So the
        # test is not how much text there is; it is whether a document that
        # advertises specifications yielded any VALUES.
        body = (d / "doc.md").read_text(errors="replace")
        labels = len(re.findall(r"\b(Specification|Power|Memory|Processor|Weight|"
                                r"Dimension|Physical|Environment|Redundancy|Buffer)\b",
                                body, re.I))
        found = sum(len(got[k]) for k in ("dimensions", "ru", "power", "ordering"))
        if labels >= 3 and found == 0:
            facts["text-free"].append({
                "document": d.name,
                "spec-labels-present": labels,
                "values-extracted": 0,
                "images": len(list(d.glob("fig-*.png"))),
                "meaning": "this document NAMES specifications and states none of "
                           "them: its labels came through as text and its numbers "
                           "did not, because they are outlined glyphs or page "
                           "images. Nothing is missing here because the vendor is "
                           "silent - it is missing because there is no text to read. "
                           "Open the figures; that is where the content is.",
            })
    if not facts["text-free"]:
        facts.pop("text-free")
    facts.update(merged)

    # A single unambiguous reading is worth calling out; more than one is a
    # question for the agent, not a thing to average.
    ru = {e["ru"] for e in merged.get("ru", [])}
    dims = {tuple(e["mm"]) for e in merged.get("dimensions", [])}

    # TWO DOCUMENTS STATING THE SAME TRIPLE IS EVIDENCE; two stating different
    # ones is the most useful thing this tool can hand over, because a
    # contradiction between a datasheet and an installation guide is exactly
    # what a modelling agent must resolve rather than average. Neither is
    # visible while the numbers sit in two PDFs nobody read side by side.
    by_triple = {}
    for e in merged.get("dimensions", []):
        by_triple.setdefault(tuple(e["mm"]), set()).add(e["source"].split("/")[0])
    corroborated = [{"mm": list(t), "stated-in": sorted(d)}
                    for t, d in sorted(by_triple.items()) if len(d) > 1]

    facts["summary"] = {
        "ru": (list(ru)[0] if len(ru) == 1 else sorted(ru)) or None,
        "distinct-dimension-triples": len(dims),
        "corroborated-dimensions": corroborated,
        "ordering-parts": sorted({e["part"] for e in merged.get("ordering", [])}),
        "port-lines": len(merged.get("ports", [])),
        "note": "every entry cites file:line - read the sentence before using it. "
                "Absence here means this tool did not find it, NOT that the vendor "
                "is silent. A triple under corroborated-dimensions is stated by more "
                "than one document; the rest are single readings and some are "
                "accessories, not the chassis.",
    }
    return facts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--intake", required=True, type=pathlib.Path)
    ap.add_argument("--model")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-o", "--out", type=pathlib.Path)
    a = ap.parse_args()

    if a.all:
        models = sorted({d.name.rsplit("-", 1)[0]
                         for d in (a.intake / "converted").iterdir() if d.is_dir()})
    elif a.model:
        models = [a.model]
    else:
        ap.error("give --model or --all")

    done = 0
    for m in models:
        f = collect(a.intake, m)
        if not f:
            continue
        text = yaml.safe_dump(f, sort_keys=False, width=100, allow_unicode=True)
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f"{m}.yaml").write_text(text)
            s = f["summary"]
            tf = f.get("text-free")
            flag = f'  TEXT-FREE:{len(tf)} doc(s) - content is in the images' if tf else ''
            print(f'{m:16s} ru={s["ru"]} dims={s["distinct-dimension-triples"]} '
                  f'ordering={len(s["ordering-parts"])} ports={s["port-lines"]}{flag}')
        else:
            print(text)
        done += 1
    if not done:
        print("facts: nothing converted matched", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
