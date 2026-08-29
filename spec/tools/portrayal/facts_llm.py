#!/usr/bin/env python3
"""Read a converted document with a language model, and VERIFY every answer.

WHY, when facts.py already exists. facts.py reads by regex, and a regex sees a
line. Two of the most consequential fields on one device were invisible to it
for two different reasons: the ordering information was a five-column markdown
TABLE where another vendor writes comma-separated SKUs, and the power figure was
split - `Power Consumption`, blank line, `1300 Watts maximum` - so a rule wanting
label and value together found neither. A reader has no trouble with either.
Both were reported as absent, and an agent that trusted the empty fields would
have shipped a model with no wattage and no orderable part numbers.

WHY THIS IS SAFE, WHICH IS THE ONLY INTERESTING PART. A model's answer carries
no derivation, and this library's whole discipline is that a number cites a
source somebody can go and check. That objection dissolves the moment the model
is required to cite a LINE, because a citation is checkable: resolve the line,
look for the text. A hallucinated value fails on the spot; a real one arrives
with its provenance attached AND already verified.

So nothing here is trusted. The model proposes and arithmetic disposes, and a
fact that cannot be located in the source it claims is reported as unverified
rather than quietly kept. Anything this file emits has been checked against the
bytes of the document.

    export LLM_ENDPOINT=... LLM_API_KEY=...
    facts_llm.py --intake working/intake/edgecore --model dcs510
    facts_llm.py --intake working/intake/ufispace --all -o .../facts-llm

The endpoint and key come from the environment and are never written to a file
in this repository.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.request

import yaml

# Endpoint and key both come from the environment. Neither the address of the
# lab's inference host nor its key belongs in a repository, and a default that
# happens to be right on one network is a default that is wrong everywhere else.
DEFAULT_ENDPOINT = os.environ.get("LLM_ENDPOINT")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "coder-8b")

FIELDS = ("dimensions", "weight", "rack-units", "power-consumption", "ac-input",
          "dc-input", "port-count", "ordering-part", "psu-part", "fan-part",
          "asic", "operating-temp")

PROMPT = """Extract stated facts from this datasheet extract. The line numbers are
authoritative.

Return ONLY YAML, no prose, no commentary:
facts:
  - field: <one of: {fields}>
    value: <the exact text as printed, copied not paraphrased>
    line: <the line number the VALUE appears on>

Rules that matter:
- A label and its value are often on DIFFERENT lines. Cite the line of the VALUE.
- Copy the value exactly as printed, including odd spacing. Do not tidy it.
- A table row is a fact: an ordering table gives one ordering-part per row.
- Omit any field this extract does not state. Never invent a line number.

{doc}

/no_think"""


def call(endpoint, key, model, prompt, max_tokens=1400, timeout=600):
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "temperature": 0,
                         "max_tokens": max_tokens,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]
    # Qwen3 reasons into a separate field and will spend the whole budget doing
    # it if asked to think; `/no_think` in the prompt is what keeps `content`
    # populated. An empty content with a full completion count means it thought
    # instead of answering.
    return ch["message"].get("content") or "", ch.get("finish_reason"), d.get("usage")


def chunks(lines, size, overlap):
    """Number every line, and overlap the windows.

    A fact split across a window boundary - a label at the end of one chunk and
    its value at the start of the next - is exactly the shape this tool exists
    to catch, so the windows have to overlap or it reintroduces the bug.
    """
    i = 0
    while i < len(lines):
        end = min(len(lines), i + size)
        yield i, "\n".join(f"{n + 1}: {lines[n]}" for n in range(i, end))
        if end == len(lines):
            return
        i += size - overlap


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# A CITATION PROVES THE TEXT IS THERE. IT DOES NOT PROVE THE LABEL IS RIGHT.
# The first run of this tool returned `ordering-part: '4. 产品标签'` - a numbered
# callout meaning 'product label' - and it verified perfectly, because that
# string IS on that line. Checking the citation catches invention; it cannot
# catch misclassification, and the two failures look identical in the output.
#
# So each field also states the SHAPE its value must have. These are deliberately
# loose - they reject a callout list item and a heading, not an unusual unit -
# because a tight pattern here would throw away the odd spellings the converter
# produces ('87. 7 mm') which are the whole reason a model is reading this at all.
SHAPE = {
    "dimensions":        r"\d.*(mm|cm|in\b|inch|\")",
    "weight":            r"\d.*(kg|lb|g\b|oz)",
    "rack-units":        r"\d\s*(ru|u\b)",
    "power-consumption": r"\d.*(w\b|watt)",
    "ac-input":          r"\d.*(v|hz|a\b)",
    "dc-input":          r"\d.*(v|a\b)",
    "port-count":        r"\d",
    # A PART NUMBER IS A TOKEN CARRYING BOTH LETTERS AND DIGITS, in either
    # order. The first pattern here assumed letters-then-digits and rejected
    # `9716-32D-O-AC-F-US` - which is the form the ordering TABLE uses, so the
    # check threw away exactly the rows worth having while keeping the model
    # name. A shape rule written from the examples you happen to remember is
    # shaped like those examples.
    "ordering-part":     r"\b(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{4,}\b",
    "psu-part":          r"\b(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{4,}\b|\d{3,}\s*w",
    "fan-part":          r"\b(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{4,}\b",
    "asic":              r"[A-Za-z]{2,}\s*\d{3,}|broadcom|marvell|intel",
    "operating-temp":    r"-?\d+\s*°?\s*[cf]\b",
    "storage-temp":      r"-?\d+\s*°?\s*[cf]\b",
}


def shaped(fact):
    """Does the value look like the KIND of thing the field claims it is?"""
    pat = SHAPE.get(str(fact.get("field")))
    if not pat:
        return True, "no shape declared for this field"
    v = str(fact.get("value") or "")
    if re.search(pat, v, re.I):
        return True, "shape ok"
    return False, f"does not look like a {fact.get('field')}"


def verify(fact, lines, window=2):
    """Is the value actually on the line it cites?

    A value may wrap, and the model may cite the line the value STARTS on, so a
    small window either side counts as a hit. Anything wider than that is not
    verification, it is looking until you find something.
    """
    n = fact.get("line")
    if not isinstance(n, int) or not 1 <= n <= len(lines):
        return False, "line out of range"
    v = norm(fact.get("value"))
    if not v:
        return False, "empty value"
    if v in norm(lines[n - 1]):
        return True, "exact line"
    lo, hi = max(0, n - 1 - window), min(len(lines), n + window)
    if v in norm(" ".join(lines[lo:hi])):
        return True, f"within {window} lines"
    return False, "not found at the cited line"


def parse(text):
    text = re.sub(r"^```\w*\s*|\s*```$", "", text.strip(), flags=re.M)
    try:
        d = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    return (d or {}).get("facts") or [] if isinstance(d, dict) else []


def extract(path, endpoint, key, model, size, overlap, quiet=False):
    lines = pathlib.Path(path).read_text(errors="replace").splitlines()
    seen, verified, rejected = set(), [], []
    for start, doc in chunks(lines, size, overlap):
        prompt = PROMPT.format(fields="|".join(FIELDS), doc=doc)
        try:
            text, finish, usage = call(endpoint, key, model, prompt)
        except Exception as e:
            if not quiet:
                print(f"  ! chunk at line {start + 1}: {type(e).__name__}: {e}",
                      file=sys.stderr)
            continue
        if finish == "length" and not text.strip():
            if not quiet:
                print(f"  ! chunk at line {start + 1}: model thought instead of "
                      f"answering - check /no_think reached it", file=sys.stderr)
            continue
        for f in parse(text):
            if not isinstance(f, dict):
                continue
            k = (f.get("field"), norm(f.get("value")), f.get("line"))
            if k in seen:
                continue                      # overlapping windows see it twice
            seen.add(k)
            ok, why = verify(f, lines)
            if ok:
                ok, why = shaped(f)
            entry = {"field": f.get("field"), "value": f.get("value"),
                     "line": f.get("line"), "checked": why}
            (verified if ok else rejected).append(entry)
    return verified, rejected, len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--intake", required=True, type=pathlib.Path)
    ap.add_argument("--model")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-o", "--out", type=pathlib.Path)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--llm", default=DEFAULT_MODEL, help="model name at the endpoint")
    ap.add_argument("--chunk", type=int, default=120, help="lines per window")
    ap.add_argument("--overlap", type=int, default=15)
    a = ap.parse_args()

    key = os.environ.get("LLM_API_KEY")
    if not key:
        sys.exit("set LLM_API_KEY - it is never stored in this repository")
    if not a.endpoint:
        sys.exit("set LLM_ENDPOINT (or pass --endpoint) - the address of an "
                 "inference host is site configuration, not a default")

    conv = a.intake / "converted"
    if a.all:
        models = sorted({d.name.rsplit("-", 1)[0] for d in conv.iterdir() if d.is_dir()})
    elif a.model:
        models = [a.model]
    else:
        ap.error("give --model or --all")

    for m in models:
        docs = sorted(d for d in conv.glob(f"{m}-*") if (d / "doc.md").exists())
        if not docs:
            continue
        allv, allr = [], []
        for d in docs:
            v, r, n = extract(d / "doc.md", a.endpoint, key, a.llm,
                              a.chunk, a.overlap)
            for e in v + r:
                e["source"] = f"{d.name}/doc.md:{e['line']}"
            allv += v
            allr += r
        out = {"model": m, "extracted-by": f"{a.llm} @ {a.endpoint}",
               "verified": allv, "unverified": allr,
               "note": "every entry under `verified` was checked against the bytes "
                       "of the cited line. Entries under `unverified` are what the "
                       "model claimed and the document does not support - they are "
                       "kept so the failure is visible, and must not be used."}
        text = yaml.safe_dump(out, sort_keys=False, width=100, allow_unicode=True)
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f"{m}.yaml").write_text(text)
            print(f"{m:16s} verified={len(allv):3d}  unverified={len(allr):2d}")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
