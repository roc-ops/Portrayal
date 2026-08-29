"""The device-to-figure manifest, and the two decisions in it that were got wrong.

`figmap.py` answers "which image is this device's front, and at what px/mm".
Neither half is obvious, and both have a recorded wrong answer behind them:

  WHICH FACE was first decided from the drawing, and picked the S6301's REAR -
  a front and a rear share an outline, so aspect cannot separate them. Two
  pixel comparisons were tried and both were thin (brightness 0.143 vs 0.103,
  gradients 0.001). The heading above the figure settles it outright.

  WHICH FIGURE was first ranked by aspect error, which quietly preferred the
  guide figure at 2.6 px/mm over the product photograph of the same face at
  3.8, because Gate 1 was being read as a score when it is a threshold.

The intake tree is not in this repository, so what is tested here is the logic,
against documents written inline.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

import figmap  # noqa: E402


DOC = """# S6301-56ST

## Port Overview

Figure 9. Front panel

<!-- image -->

## Fan Overview

Figure 11. Fan modules

<!-- image -->
"""


def _doc(tmp_path, text=DOC):
    p = tmp_path / "doc.md"
    p.write_text(text)
    return p


# ---- which face -------------------------------------------------------------

def test_figures_are_numbered_from_zero_in_document_order(tmp_path):
    """The conversion's own numbering is the only handle the files carry."""
    assert list(figure_keys(tmp_path)) == ["fig-0000", "fig-0001"]


def figure_keys(tmp_path):
    return figmap.figure_context(_doc(tmp_path))


def test_a_figure_takes_the_heading_it_is_under_not_the_next_one(tmp_path):
    """The S6301 bug in miniature: fig-0001 sits under Fan Overview, and reading
    forward instead of back is what put the rear where the front belonged."""
    ctx = figmap.figure_context(_doc(tmp_path))
    assert "Port Overview" in ctx["fig-0000"]
    assert "Fan Overview" in ctx["fig-0001"]


def test_the_caption_travels_with_the_figure(tmp_path):
    ctx = figmap.figure_context(_doc(tmp_path))
    assert "Figure 9." in ctx["fig-0000"]
    assert "Figure 9." not in ctx["fig-0001"], "a caption must not outlive its figure"


def test_a_new_heading_clears_the_previous_caption(tmp_path):
    """Otherwise a heading with no caption of its own inherits the last one and
    every figure under it claims to be Figure 9."""
    ctx = figmap.figure_context(_doc(tmp_path, DOC.replace("Figure 11. Fan modules", "")))
    assert "Figure 9." not in ctx["fig-0001"]


def test_front_and_rear_each_select_only_their_own():
    assert figmap.wants("Port Overview Figure 9.", "front")
    assert not figmap.wants("Port Overview Figure 9.", "rear")
    assert figmap.wants("Fan Overview Figure 11.", "rear")
    assert not figmap.wants("Fan Overview Figure 11.", "front")


def test_a_context_naming_both_faces_names_neither():
    """A chapter heading over a page holding both elevations tells us nothing,
    and guessing from it is exactly the mistake this module refuses to make.

    Note what this does NOT catch, deliberately: "Rear view of the system with
    front I/O configuration" is read as rear, because the bare word `front`
    qualifies the configuration and not the picture. Only a phrase that names a
    FACE counts on either side."""
    both = "Front Panel and Rear Panel Overview"
    assert not figmap.wants(both, "front")
    assert not figmap.wants(both, "rear")


def test_a_hyphen_is_not_a_different_word():
    """Six headings in the intake are written this way, and a `front panel`
    pattern is silent about every one of them."""
    assert figmap.wants("Front-Panel Features And Indicators", "front")
    assert figmap.wants("Rear-Panel Features And Indicators", "rear")


# ---- which figure -----------------------------------------------------------

def _cand(err, ppm):
    return {"gate1_error": err, "px_per_mm": ppm}


def test_a_figure_that_passes_gate_one_beats_one_that_does_not():
    assert figmap.better(_cand(0.001, 2.0), _cand(0.20, 40.0))
    assert not figmap.better(_cand(0.20, 40.0), _cand(0.001, 2.0))


def test_among_passers_the_higher_resolution_wins():
    """The regression itself: the guide figure at 2.64 px/mm is more exactly
    drawn than the photograph at 3.83, and is the worse source to measure from."""
    guide, photo = _cand(0.0011, 2.64), _cand(0.0014, 3.83)
    assert figmap.better(photo, guide)
    assert not figmap.better(guide, photo)


def test_among_failers_the_least_wrong_wins():
    """Where nothing carries geometry, the error is all we know, and a big
    picture of the wrong shape is not an improvement."""
    assert figmap.better(_cand(0.05, 2.0), _cand(0.40, 20.0))
    assert not figmap.better(_cand(0.40, 20.0), _cand(0.05, 2.0))


def test_the_first_candidate_is_taken():
    assert figmap.better(_cand(0.9, 1.0), None)


def test_the_gate_is_inclusive_at_the_tolerance():
    """A figure exactly at TOL passes, so the boundary cannot silently move the
    same figure between the two ranking rules."""
    assert figmap.better(_cand(figmap.TOL, 2.0), _cand(0.10, 90.0))


# ---- the outline ------------------------------------------------------------

def test_a_figure_too_small_to_measure_is_refused(tmp_path):
    """Below MIN_PX a pixel is worth a third of a millimetre and every box read
    off it would be a guess with a transform attached."""
    from PIL import Image
    p = tmp_path / "small.png"
    Image.new("L", (200, 100), 0).save(p)
    assert figmap.outline(p) is None


def test_a_blank_page_has_no_device_in_it(tmp_path):
    from PIL import Image
    p = tmp_path / "blank.png"
    Image.new("L", (900, 300), 255).save(p)
    assert figmap.outline(p) is None


def test_the_box_is_the_dark_body_not_the_page(tmp_path):
    from PIL import Image
    p = tmp_path / "panel.png"
    im = Image.new("L", (900, 300), 255)
    im.paste(0, (100, 50, 700, 250))
    im.save(p)
    x0, x1, y0, y1 = figmap.outline(p)
    assert (x0, x1, y0, y1) == (100, 699, 50, 249)
