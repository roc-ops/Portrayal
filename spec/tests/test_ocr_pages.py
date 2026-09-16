"""The OCR sidecar, `spec/tools/portrayal/ocr_pages.py`.

Three things must hold, and each of them is a mistake this pipeline can make
silently:

1. A document whose text layer is healthy must be SKIPPED, not OCR'd. OCR is
   slower and worse than real text, and a pipeline that OCRs everything quietly
   replaces good extractions with mediocre ones.
2. Every emitted string must carry its page, its box and its confidence. A
   transcription that cannot be located on the page cannot be checked, and an
   unbounded, uncited number is exactly how a device gets modelled blind.
3. A low-confidence string must be emitted and MARKED, never dropped. A reading
   a reader can see and distrust beats one they never know was there.

The fixtures are synthetic PDFs written byte by byte below. The intake corpus
is gitignored, so a test that reached for it would pass or fail depending on
whose machine it ran on.
"""
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal import ocr_pages

HAS_POPPLER = all(shutil.which(t) for t in ("pdftotext", "pdftoppm", "pdfinfo"))
needs_poppler = pytest.mark.skipif(
    not HAS_POPPLER, reason="poppler (pdftotext/pdftoppm/pdfinfo) not installed")


# ---- synthetic PDFs ---------------------------------------------------------

def _pdf(objects: list) -> bytes:
    """Assemble numbered objects into a PDF with a correct xref table.

    Hand-rolled because the point of the fixtures is to control exactly how much
    text the file's text layer contains, and no PDF library in this repository's
    dependency set is willing to produce a page with none.
    """
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for o in offsets:
        out += f"{o:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            f"startxref\n{start}\n%%EOF\n").encode()
    return bytes(out)


def _page_pdf(content: bytes, with_font: bool) -> bytes:
    res = b"<< /Font << /F1 5 0 R >> >>" if with_font else b"<< >>"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources " + res + b" /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content
        + b"\nendstream",
    ]
    if with_font:
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return _pdf(objs)


def text_rich_pdf() -> bytes:
    """A page whose text layer holds well over the 700 chars/page gate."""
    lines = []
    y = 760
    for i in range(30):
        lines.append(f"BT /F1 10 Tf 40 {y} Td "
                     f"(Specification row {i}: depth 480 mm, "
                     f"2x400G QSFP-DD, 4x100G QSFP-DD, 8x50G SFP56) Tj ET")
        y -= 24
    return _page_pdf("\n".join(lines).encode(), with_font=True)


def text_free_pdf() -> bytes:
    """A page of vector marks and not one character - what an outlined-glyph
    datasheet looks like to pdftotext."""
    parts = ["0 0 0 rg"]
    for i in range(40):
        parts.append(f"{40 + i*12} 300 8 40 re f")
    return _page_pdf("\n".join(parts).encode(), with_font=False)


@pytest.fixture
def rich(tmp_path):
    p = tmp_path / "rich-datasheet.pdf"
    p.write_bytes(text_rich_pdf())
    return p


@pytest.fixture
def bare(tmp_path):
    p = tmp_path / "bare-datasheet.pdf"
    p.write_bytes(text_free_pdf())
    return p


class FakeOCR:
    """Stands in for RapidOCR: same [polygon, text, confidence] triples, same
    return shape. Injected so the sidecar's contract can be tested without the
    engine, whose readings are not this file's subject."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def __call__(self, path):
        self.calls += 1
        return list(self.rows), [0.1, 0.1, 0.1]


BOX = [[10.2, 20.4], [110.9, 21.0], [110.1, 50.7], [10.0, 49.9]]


# ---- 1. real text is not thrown away for OCR --------------------------------

def test_the_gate_is_chars_per_page_not_chars():
    """A 40-page guide with 20,000 characters is healthy; a 2-page datasheet
    with the same 20,000 would be extraordinary. The denominator matters."""
    assert not ocr_pages.needs_ocr(chars=20000, pages=2)
    assert ocr_pages.needs_ocr(chars=1155, pages=2)      # the reference case
    assert not ocr_pages.needs_ocr(chars=1155 * 3, pages=2)


def test_a_zero_page_document_is_not_divided_by():
    assert ocr_pages.needs_ocr(chars=0, pages=0)


@needs_poppler
def test_a_text_rich_pdf_is_skipped_rather_than_ocrd(rich, tmp_path):
    ocr = FakeOCR([[BOX, "should never be read", 0.99]])
    doc = ocr_pages.process(rich, tmp_path / "out", ocr=ocr)
    assert doc["status"] == "skipped"
    assert ocr.calls == 0, "the engine ran on a document with a good text layer"
    assert doc["strings"] == []
    written = (tmp_path / "out" / "rich-datasheet.ocr.yaml").read_text()
    assert "status: skipped" in written
    assert "strings: []" in written


@needs_poppler
def test_a_text_free_pdf_is_ocrd(bare, tmp_path):
    ocr = FakeOCR([[BOX, "480mm", 0.97]])
    doc = ocr_pages.process(bare, tmp_path / "out", ocr=ocr)
    assert doc["status"] == "ocr"
    assert ocr.calls == 1, "one page, one render, one read"
    assert [s["text"] for s in doc["strings"]] == ["480mm"]


@needs_poppler
def test_the_sidecar_records_why_ocr_was_needed(bare, tmp_path):
    """The pdftotext count is what lets a reader see WHY this file exists."""
    ocr_pages.process(bare, tmp_path / "out", ocr=FakeOCR([[BOX, "x", 0.9]]))
    y = (tmp_path / "out" / "bare-datasheet.ocr.yaml").read_text()
    assert "pdftotext_chars: 0" in y
    assert "ocr_threshold_chars_per_page: 700" in y
    assert "render_dpi: 300" in y
    assert "rapidocr" in y, "the engine and its version must be on the record"


# ---- 2. every string can be found on the page -------------------------------

def test_every_string_carries_page_box_and_confidence():
    rows = [[BOX, "2x400GQSFP-DDports", 0.99],
            [BOX, "480mm", 0.87],
            [BOX, "S9620-54DC", 0.95]]
    got = ocr_pages.read_page(FakeOCR(rows), pathlib.Path("unused.png"), page=7)
    assert len(got) == 3
    for s in got:
        assert s["page"] == 7
        assert len(s["box"]) == 4 and all(isinstance(v, int) for v in s["box"])
        assert 0.0 <= s["conf"] <= 1.0
        assert s["text"]


def test_the_box_is_the_extent_of_the_polygon():
    """RapidOCR's quadrilateral is near-rectangular but not exactly; the box has
    to contain it, or the crop a reader takes will clip the string."""
    s = ocr_pages.read_page(FakeOCR([[BOX, "480mm", 0.9]]),
                            pathlib.Path("unused.png"), page=1)[0]
    assert s["box"] == [10, 20, 101, 31]


@needs_poppler
def test_page_numbers_and_page_sizes_survive_into_the_sidecar(bare, tmp_path):
    ocr_pages.process(bare, tmp_path / "out", ocr=FakeOCR([[BOX, "480mm", 0.9]]))
    y = (tmp_path / "out" / "bare-datasheet.ocr.yaml").read_text()
    assert "- page: 1" in y
    assert "box: [10, 20, 101, 31]" in y
    assert "conf: 0.9" in y
    assert 'text: "480mm"' in y
    # 612x792pt at 300dpi, so the reader can convert a box back to the page.
    assert "  1: [2550, 3300]" in y


def test_quoting_survives_the_characters_ocr_actually_returns():
    """Part numbers and dimension strings carry quotes, colons and backslashes.
    A sidecar that cannot be parsed cites nothing."""
    s = ocr_pages._q('19" rack: 1U \\ 480mm')
    assert s == '"19\\" rack: 1U \\\\ 480mm"'
    import yaml
    assert yaml.safe_load(s) == '19" rack: 1U \\ 480mm'


def test_the_whole_sidecar_parses_as_yaml():
    doc = {"document": "d.pdf", "source": "a/d.pdf", "pages": 2,
           "pdftotext_chars": 1155, "pdftotext_chars_per_page": 577,
           "threshold": 700, "status": "ocr", "render_dpi": 300,
           "engine": "rapidocr_onnxruntime 1.4.4",
           "page_size_px": {1: [2480, 3508], 2: [2480, 3508]},
           "strings": [{"page": 1, "box": [1, 2, 3, 4], "conf": 0.9,
                        "text": '2x400G "QSFP-DD" ports'},
                       {"page": 2, "box": [5, 6, 7, 8], "conf": 0.2,
                        "low_confidence": True, "text": "iiiii"}]}
    import yaml
    d = yaml.safe_load(ocr_pages.sidecar(doc))
    assert d["pdftotext_chars"] == 1155
    assert d["page_size_px"][2] == [2480, 3508]
    assert d["strings"][0]["text"] == '2x400G "QSFP-DD" ports'
    assert d["strings"][1]["low_confidence"] is True
    assert "low_confidence" not in d["strings"][0]


# ---- 3. a doubtful reading is marked, never dropped -------------------------

def test_a_low_confidence_string_is_emitted_and_marked():
    rows = [[BOX, "480mm", 0.97],
            [BOX, "1|Ill0", 0.11],
            [BOX, "S9620-54DC", 0.95]]
    got = ocr_pages.read_page(FakeOCR(rows), pathlib.Path("unused.png"), page=1)
    assert len(got) == 3, "a doubtful reading was dropped instead of marked"
    assert [s["text"] for s in got] == ["480mm", "1|Ill0", "S9620-54DC"]
    assert got[1]["low_confidence"] is True
    assert "low_confidence" not in got[0]
    assert "low_confidence" not in got[2]


def test_the_engines_own_filter_is_turned_down_so_it_cannot_drop_first():
    """RapidOCR's text_score defaults to 0.5 and DELETES anything below it, so
    with the default the mark above could never fire - the engine would have
    thrown the doubtful strings away before this file ever saw them. Measured on
    the S9620-54DC page, the default discarded two readings. The engine's filter
    must sit well under ours."""
    assert ocr_pages.ENGINE_TEXT_SCORE < ocr_pages.LOW_CONFIDENCE
    assert ocr_pages.ENGINE_TEXT_SCORE > 0, "at zero the detector emits noise"

    captured = {}

    class FakeRapidOCR:
        def __init__(self, **kw):
            captured.update(kw)

    mod = type(sys)("rapidocr_onnxruntime")
    mod.RapidOCR = FakeRapidOCR
    sys.modules["rapidocr_onnxruntime"] = mod
    try:
        ocr_pages._engine()
    finally:
        del sys.modules["rapidocr_onnxruntime"]
    assert captured["text_score"] == ocr_pages.ENGINE_TEXT_SCORE, \
        "the engine was constructed with its default filter still in place"


def test_the_mark_lands_in_the_sidecar_where_a_reader_will_see_it():
    doc = {"document": "d.pdf", "source": "d.pdf", "pages": 1,
           "pdftotext_chars": 0, "pdftotext_chars_per_page": 0,
           "threshold": 700, "status": "ocr", "render_dpi": 300,
           "engine": "e", "page_size_px": {1: [10, 10]},
           "strings": [{"page": 1, "box": [1, 2, 3, 4], "conf": 0.11,
                        "low_confidence": True, "text": "1|Ill0"}]}
    y = ocr_pages.sidecar(doc)
    assert "low_confidence: true" in y
    assert "low_confidence_below: 0.5" in y
