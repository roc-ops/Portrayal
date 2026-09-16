"""prepare.py - the brief must stay SHORT and must not flatter itself.

Its whole purpose is to cost an agent less reading than doing the work by hand.
A first version described every panel-shaped band in every picture, called 80 of
about 90 figures measurable, and ran to 1666 lines - which is not a brief, it is
the problem restated in a different file.

So the two things worth testing are that the face filter rejects things that are
not faces, and that what it cannot do is stated rather than omitted.
"""
import pathlib
import sys

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import prepare as P


def figure(dirpath, name, size, band):
    dirpath.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    d.rectangle(band, fill="#555555")
    im.save(dirpath / name)


def test_a_square_picture_is_not_a_face(tmp_path):
    """A logo, an icon or a photo of a rack contains a band of ink too. Ranking
    it as a face candidate hands the agent a confident scale for something that
    is not the chassis."""
    conv = tmp_path / "converted" / "x-datasheet"
    figure(conv, "fig-0001.png", (400, 400), [40, 150, 360, 260])   # squarish
    figure(conv, "fig-0002.png", (900, 160), [20, 55, 880, 105])    # face-shaped
    cands, rejected, more = P.figure_report(tmp_path, "x", 438.4, 43.1)
    names = [c["figure"] for c in cands]
    assert any("fig-0002" in n for n in names), names
    assert not any("fig-0001" in n for n in names), "a squarish band is not a face"
    assert rejected >= 1


def test_candidates_are_ranked_with_the_best_agreement_first(tmp_path):
    conv = tmp_path / "converted" / "x-qsg"
    # 860x84 is very close to 438.4/43.1; 860x120 is not
    figure(conv, "fig-0001.png", (900, 200), [20, 40, 880, 160])
    figure(conv, "fig-0002.png", (900, 140), [20, 30, 880, 114])
    cands, _, _ = P.figure_report(tmp_path, "x", 438.4, 43.1)
    assert len(cands) >= 2
    skews = [c["axis_disagreement_pct"] for c in cands]
    assert skews == sorted(skews), skews


def test_a_verdict_is_only_given_when_a_size_is_known(tmp_path):
    """Without stated dimensions there is no Gate 1 answer, and inventing one
    would be worse than saying nothing."""
    conv = tmp_path / "converted" / "x-datasheet"
    figure(conv, "fig-0001.png", (900, 160), [20, 55, 880, 105])
    cands, _, _ = P.figure_report(tmp_path, "x", None, None)
    assert cands, "a wide band is still a candidate without dimensions"
    assert "verdict" not in cands[0]
    assert "px_per_mm" not in cands[0]


def test_a_text_free_document_is_called_out_not_left_empty(tmp_path):
    """The failure this whole pipeline exists for: a datasheet that NAMES
    specifications and states none of their values converts to labels and no
    numbers. An empty facts section looks identical to a vendor who published
    nothing, and only one of those is a claim about the world."""
    conv = tmp_path / "converted" / "x-datasheet"
    conv.mkdir(parents=True)
    (conv / "doc.md").write_text(
        "## KEY FEATURES\n\n- ■\n- ■\n\nPower Supply\n\nMemory\n\n"
        "Processor\n\nSpecifications\n\nAll information is subject to change\n")
    (conv / "fig-0001.png").write_bytes(b"")
    facts, notes = P.stated_facts(tmp_path, "x")
    assert facts is not None
    assert any("outlined glyphs or page images" in n for n in notes), notes
    assert any("ocr_pages" in n for n in notes)


def test_absent_ordering_lines_are_reported_as_the_tools_silence(tmp_path):
    conv = tmp_path / "converted" / "x-datasheet"
    conv.mkdir(parents=True)
    (conv / "doc.md").write_text("## PHYSICAL\n\n2RU, 436 x 762 x 87.7 mm\n")
    _, notes = P.stated_facts(tmp_path, "x")
    assert any("this tool's silence, not" in n for n in notes), notes
