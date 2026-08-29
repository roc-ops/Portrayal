#!/usr/bin/env python3
"""OCR the vendor PDFs whose text layer is empty, and cite every string.

THE PROBLEM. Some vendor datasheets - UfiSpace's newest ones among them - set
the specification VALUES as outlined vector glyphs rather than as text. The
headings are text, the bullet marks are text, the numbers are drawings. So
`pdftotext` returns a page of labels with nothing after the colons, and the
converted document looks complete and is empty. That is not a hypothetical: it
already cost this project a device modelled blind.

THE FIX, deliberately narrow. Render the page with pdftoppm at 300 dpi and read
it with RapidOCR directly. NOT through docling - its `do_ocr` path renders too
coarsely and, on the reference page, reads '2x16G' for '2x400G' and '76 kg' for
a depth. Going direct to the same engine reads that page correctly in about a
second and a half.

EVERY STRING CARRIES ITS PAGE, ITS BOX AND ITS CONFIDENCE, and that is the
point of the file rather than decoration. This library's discipline is that a
number cites a source a reader can go and check; a transcription that cannot be
located on the page cannot be checked, so a sidecar without positions would
only be a faster way to be confidently wrong. Boxes are in PIXELS at the
recorded `render_dpi`, origin top-left - the coordinates the engine actually
saw. Re-render the page at that dpi and the crop is exactly the string.

WORD BOUNDARIES ARE LOST, and are left lost. The engine returns
'QSFP-DDports', '4x100GQSFP-DD' and 'constrainededgeenvironments'. Do not
re-space this text with a dictionary or a splitting heuristic: the strings worth
most on a datasheet page are part numbers, and any splitter confident enough to
fix 'QSFP-DDports' will also mangle 'S9620-54DC'. The text is emitted as read.
WHATEVER CONSUMES THIS FILE MUST MATCH LOOSELY - strip spaces from both sides of
the comparison, or search for the digits.

ONLY WHAT NEEDS IT. Real text beats OCR every time, so a document with a healthy
text layer is recorded as skipped and never rendered. The gate is non-whitespace
characters per page, default 700 (--threshold). Across the UfiSpace corpus that
separates the two vectorised datasheets - 568 and 577 chars/page - from every
healthy one, the nearest of which is a hardware guide at 764 and the nearest
datasheet at 1551. The margin above is thin and the margin below is wide, which
is the right way round: a false OCR costs seconds, a missed one costs a device.

Output, one sidecar per document, under --out:
    <stem>.ocr.yaml   the counts, the settings, and the strings with their boxes

Usage:
    ocr_pages.py --pdf <file> -o <dir>
    ocr_pages.py --intake <vendor dir> --all -o <dir>
"""
import argparse, re, shutil, subprocess, sys, tempfile, time
from math import ceil, floor
from pathlib import Path

# Non-whitespace characters per page below which a document is assumed to have
# lost its content to vector glyphs. See the module docstring for the corpus
# measurement this comes from.
DEFAULT_THRESHOLD = 700

# Rendering resolution. 300 is what recovers the reference page; docling's
# default is far coarser and that is exactly why it misreads it.
DEFAULT_DPI = 300

# Below this the string is MARKED, never dropped. A wrong reading a reader can
# see and distrust is worth more than a missing one they never know about.
LOW_CONFIDENCE = 0.5

# RapidOCR's own `text_score` defaults to 0.5 and it DELETES anything below,
# which is the same silent-drop failure this file exists to prevent - measured
# on the S9620-54DC page, the default threw away two readings before we ever saw
# them. So the engine's filter is turned down to near-nothing and the judgement
# is made here, in the open, by LOW_CONFIDENCE. Not zero: at zero the detector
# emits pure noise boxes with no text worth recording.
ENGINE_TEXT_SCORE = 0.05


# ---- what pdftotext already got ---------------------------------------------

def text_chars(pdf: Path) -> int:
    """Non-whitespace characters in the PDF's own text layer."""
    out = subprocess.run(["pdftotext", str(pdf), "-"],
                         capture_output=True, timeout=300).stdout
    return len("".join(out.decode("utf-8", "replace").split()))


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)],
                         capture_output=True, timeout=120).stdout.decode(
                             "utf-8", "replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        raise RuntimeError(f"pdfinfo gave no page count for {pdf.name}")
    return int(m.group(1))


def needs_ocr(chars: int, pages: int, threshold: int = DEFAULT_THRESHOLD) -> bool:
    if pages <= 0:
        return True
    return chars / pages < threshold


# ---- reading the page -------------------------------------------------------

def render(pdf: Path, page: int, dpi: int, into: Path) -> Path:
    """One page to PNG. pdftoppm names the file for us, so glob it back."""
    stem = into / f"p{page:04d}"
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page),
                    "-r", str(dpi), "-png", str(pdf), str(stem)],
                   check=True, capture_output=True, timeout=600)
    hits = sorted(into.glob(f"p{page:04d}*.png"))
    if not hits:
        raise RuntimeError(f"pdftoppm produced nothing for {pdf.name} p{page}")
    return hits[0]


def _engine():
    """Imported here, not at module scope, so this file can be read and tested
    on a machine without the OCR engine - the same reason extract.py defers
    docling. The build and lint gates require none of the intake dependencies.
    """
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(text_score=ENGINE_TEXT_SCORE)


def engine_version() -> str:
    try:
        from importlib.metadata import version
        return f"rapidocr_onnxruntime {version('rapidocr_onnxruntime')}"
    except Exception:
        return "rapidocr_onnxruntime (version unknown)"


def read_page(ocr, png: Path, page: int) -> list:
    """Run the engine over one rendered page and normalise what comes back.

    RapidOCR returns [polygon, text, confidence] triples with a four-point
    polygon; the polygon is near-rectangular but not exactly, so the box is its
    extent, rounded OUTWARD - a box that clips the string it names is worse than
    one a pixel too generous. Nothing is filtered out here - see LOW_CONFIDENCE.
    """
    res, _elapse = ocr(str(png))
    strings = []
    for poly, text, conf in (res or []):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, y0 = floor(min(xs)), floor(min(ys))
        x1, y1 = ceil(max(xs)), ceil(max(ys))
        rec = {
            "page": page,
            "box": [x0, y0, x1 - x0, y1 - y0],
            "conf": round(float(conf), 3),
            "text": text,
        }
        if rec["conf"] < LOW_CONFIDENCE:
            rec["low_confidence"] = True
        strings.append(rec)
    return strings


# ---- the sidecar ------------------------------------------------------------

def _q(s: str) -> str:
    """A YAML double-quoted scalar. Written by hand rather than with pyyaml so
    the sidecar stays byte-stable and diffable: OCR text is full of the
    characters a dumper likes to reflow or re-quote."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sidecar(doc: dict) -> str:
    L = [f"# Written by spec/tools/portrayal/ocr_pages.py - read its docstring before",
         f"# citing anything here. Text has NO WORD BOUNDARIES; match loosely.",
         f"document: {_q(doc['document'])}",
         f"source: {_q(doc['source'])}",
         f"pages: {doc['pages']}",
         f"pdftotext_chars: {doc['pdftotext_chars']}",
         f"pdftotext_chars_per_page: {doc['pdftotext_chars_per_page']}",
         f"ocr_threshold_chars_per_page: {doc['threshold']}",
         f"status: {doc['status']}"]
    if doc["status"] == "skipped":
        L += ["# The text layer was healthy. Use the real text, not OCR.",
              "strings: []"]
        return "\n".join(L) + "\n"
    L += [f"render_dpi: {doc['render_dpi']}",
          f"engine: {_q(doc['engine'])}",
          f"low_confidence_below: {LOW_CONFIDENCE}",
          "# box is [x, y, w, h] in PIXELS at render_dpi, origin top-left.",
          "page_size_px:"]
    for p, (w, h) in sorted(doc["page_size_px"].items()):
        L.append(f"  {p}: [{w}, {h}]")
    L.append("strings:")
    for s in doc["strings"]:
        b = s["box"]
        low = "    low_confidence: true\n" if s.get("low_confidence") else ""
        L.append(f"  - page: {s['page']}\n"
                 f"    box: [{b[0]}, {b[1]}, {b[2]}, {b[3]}]\n"
                 f"    conf: {s['conf']}\n"
                 f"{low}"
                 f"    text: {_q(s['text'])}")
    return "\n".join(L) + "\n"


# ---- driving ----------------------------------------------------------------

def process(pdf: Path, out_dir: Path, dpi: int = DEFAULT_DPI,
            threshold: int = DEFAULT_THRESHOLD, ocr=None,
            source_root: Path = None) -> dict:
    """One document. Returns the record; writes <out_dir>/<stem>.ocr.yaml.

    `ocr` is injectable so the decision logic can be tested without the engine,
    and so a caller running over a directory pays for loading the model once.
    """
    pages = page_count(pdf)
    chars = text_chars(pdf)
    src = pdf
    if source_root:
        try:
            src = pdf.relative_to(source_root)
        except ValueError:
            pass
    doc = {
        "document": pdf.name,
        "source": str(src),
        "pages": pages,
        "pdftotext_chars": chars,
        "pdftotext_chars_per_page": chars // max(pages, 1),
        "threshold": threshold,
        "strings": [],
    }
    if not needs_ocr(chars, pages, threshold):
        doc["status"] = "skipped"
    else:
        doc["status"] = "ocr"
        doc["render_dpi"] = dpi
        doc["engine"] = engine_version()
        doc["page_size_px"] = {}
        if ocr is None:
            ocr = _engine()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for p in range(1, pages + 1):
                png = render(pdf, p, dpi, td)
                doc["page_size_px"][p] = png_size(png)
                doc["strings"] += read_page(ocr, png, p)
                png.unlink(missing_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pdf.stem}.ocr.yaml").write_text(sidecar(doc))
    return doc


def png_size(png: Path) -> tuple:
    """Width and height from the PNG header. No pillow dependency for this."""
    b = png.read_bytes()[:33]
    if b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        return (0, 0)
    return (int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", help="one PDF")
    ap.add_argument("--intake", help="a vendor directory")
    ap.add_argument("--all", action="store_true",
                    help="with --intake, walk it for every PDF")
    ap.add_argument("-o", "--out", required=True, help="where sidecars land")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                    help=f"non-whitespace chars per page below which a document "
                         f"is OCR'd (default {DEFAULT_THRESHOLD})")
    a = ap.parse_args()

    if a.pdf:
        pdfs, root = [Path(a.pdf)], Path(a.pdf).parent
    elif a.intake and a.all:
        root = Path(a.intake)
        pdfs = sorted(root.rglob("*.pdf"))
    else:
        ap.error("give --pdf FILE, or --intake DIR --all")

    for t in ("pdftotext", "pdftoppm", "pdfinfo"):
        if not shutil.which(t):
            sys.exit(f"{t} is not on PATH (brew install poppler)")

    out = Path(a.out)
    ocr = None
    ocrd, skipped, failed = [], [], []
    for pdf in pdfs:
        t0 = time.time()
        try:
            pages, chars = page_count(pdf), text_chars(pdf)
            if needs_ocr(chars, pages, a.threshold) and ocr is None:
                ocr = _engine()          # loaded once, on first real need
            doc = process(pdf, out, a.dpi, a.threshold, ocr, root)
        except Exception as e:
            failed.append(pdf.name)
            print(f"FAIL  {pdf.name}: {type(e).__name__}: {e}", flush=True)
            continue
        cp = doc["pdftotext_chars_per_page"]
        if doc["status"] == "skipped":
            skipped.append(pdf.name)
            print(f"skip  {pdf.name}: {cp} chars/page, text layer is fine",
                  flush=True)
        else:
            ocrd.append(pdf.name)
            low = sum(1 for s in doc["strings"] if s.get("low_confidence"))
            print(f"OCR   {pdf.name}: {cp} chars/page -> "
                  f"{len(doc['strings'])} strings ({low} low-confidence) "
                  f"in {time.time()-t0:.0f}s", flush=True)

    print(f"\n{len(ocrd)} OCR'd, {len(skipped)} skipped, {len(failed)} failed "
          f"(threshold {a.threshold} chars/page) -> {out}")
    for n in ocrd:
        print(f"  needed OCR: {n}")


if __name__ == "__main__":
    main()
