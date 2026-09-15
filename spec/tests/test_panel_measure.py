"""The panel measurer, checked against a face whose answer is already known.

35510.G.jpg is the 12x MTP adapter panel, face-on. Its faceplate must scale to
108.97 x 35.05 within a few percent, and its openings must come out as two rows
of six at a consistent pitch. If the tool cannot reproduce that, no connector
measured with it can be trusted.
"""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/intake"))


def _corpus():
    """`working/` lives in the MAIN checkout, so a worktree must go find it.

    Reference imagery is gitignored, and gitignored files in a worktree die with
    the worktree - an intake was lost that way once - so the intake convention
    stages the corpus in the main checkout only. A worktree therefore holds a
    stub `working/intake` with nothing under it, and resolving this path against
    the test file's own root makes these two tests skip wherever the real work
    happens. They are the only proof that `panel_measure` reproduces the numbers
    three contracts call MEASURED, so a silent skip here is the expensive kind.

    The shared repository directory's parent is the main checkout; in a plain
    clone it is that clone, so both cases land correctly. Falling back to ROOT
    keeps this working with no version control at all.
    """
    try:
        shared = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ROOT / "working"
    main = (ROOT / shared).resolve().parent
    staged = main / "working"
    return staged if staged.is_dir() else ROOT / "working"


IMG = _corpus() / "intake" / "fs" / "fhd" / "photos"


@pytest.fixture(scope="module")
def pm():
    return pytest.importorskip("panel_measure")


def _im(pm, name):
    Image = pytest.importorskip("PIL.Image")
    p = IMG / name
    if not p.exists():
        pytest.skip(f"{name} not staged - reference imagery lives in working/")
    return Image.open(p).convert("RGB")


def test_the_mtp_panel_scales_true_on_both_axes(pm):
    im = _im(pm, "35510.G.jpg")
    x0, y0, x1, y1, mm = pm.plate(im)
    off = pm.validate(mm, y0, y1)
    assert off < 3.0, (
        f"the plate scales to {(y1 - y0 + 1) * mm:.2f} mm tall against a known "
        f"35.05 - {off:.1f}% out. Either the image is not face-on or `plate` "
        "found the wrong band")


def test_the_mtp_panel_has_six_openings_per_row(pm):
    im = _im(pm, "35510.G.jpg")
    box = pm.plate(im)
    top = pm.openings(im, box, band=(0.10, 0.45), min_mm=4.0)
    assert len(top) == 6, [round(c, 2) for _a, _b, c in top]
    pitches = [top[i][2] - top[i - 1][2] for i in range(1, 6)]
    spread = max(pitches) - min(pitches)
    assert spread < 2.0, f"pitches {pitches} spread {spread:.2f} - not a pitch"


def test_validate_refuses_a_scale_that_misses_the_other_axis(pm):
    """This is the guard that stops a three-quarter render being recorded as
    a measurement."""
    with pytest.raises(ValueError):
        pm.validate(1.0, 0, 9)  # scales to 10 mm against a known 35.05


def test_plate_refuses_an_image_with_no_faceplate(pm):
    """A mostly-white field with a couple of stray dark rows has no
    contiguous band, so there is no faceplate to measure."""
    Image = pytest.importorskip("PIL.Image")
    im = Image.new("RGB", (200, 100), (255, 255, 255))
    for y in (10, 60):
        for x in range(200):
            im.putpixel((x, y), (0, 0, 0))
    with pytest.raises(ValueError):
        pm.plate(im)


# --- a face is two constants that must travel together -----------------------

def test_a_face_carries_its_width_and_height_as_one_thing(pm):
    """THE TWO CONSTANTS ARE THE POINT and they must not be separable.

    The scale comes from the width and the CHECK comes from the height, so a
    caller that supplies one without the other gets a scale validated against
    somebody else's face - which either fails for the wrong reason or, worse,
    passes. This library's recurring defect is two numbers held in one place and
    never compared; a face is the fix, not a convenience.
    """
    assert pm.FHD_MODULE.w_mm == 108.97
    assert pm.FHD_MODULE.h_mm == 35.05
    assert "FHD" in pm.FHD_MODULE.name


def test_the_default_face_is_still_the_fhd_module(pm):
    """Three contracts call figures MEASURED on the strength of this default.

    `plate` and `validate` keep answering for an FHD face when asked for
    nothing, so every existing caller and every figure already in the library
    is untouched by the generalisation.
    """
    im = _im(pm, "35510.G.jpg")
    x0, y0, x1, y1, mm = pm.plate(im)
    assert pm.validate(mm, y0, y1) < 3.0
    assert abs((x1 - x0 + 1) * mm - 108.97) < 0.01


def test_measure_does_both_steps_against_one_face(pm):
    """The mismatch is impossible when one call owns both constants."""
    im = _im(pm, "35510.G.jpg")
    (x0, y0, x1, y1, mm), off = pm.measure(im)
    assert off < 3.0
    assert abs((x1 - x0 + 1) * mm - pm.FHD_MODULE.w_mm) < 0.01


def test_measuring_a_face_against_the_wrong_face_refuses(pm):
    """An FHD panel declared as a MaiaEdge chassis must not validate.

    This is the whole safety property: the width scales anything, and only the
    height check can tell you the scale was taken off the wrong object.
    """
    im = _im(pm, "35510.G.jpg")
    with pytest.raises(ValueError) as e:
        pm.measure(im, face=pm.MAIAEDGE_PBC)
    assert "MaiaEdge" in str(e.value), \
        "the refusal must name the face it was measured against"


def test_the_maiaedge_face_carries_the_datasheet_figures(pm):
    """437.90 x 41.27 mm, the chassis without its ears.

    From page 3 of MaiaEdge-PBC-PCE-Datasheet-v3.pdf: chassis 1.625 x 17.24 x
    11.46 in. NOT the 19.02 in with-ears width - the ears are a separate part and
    the bezel face is inset from them.
    """
    assert round(pm.MAIAEDGE_PBC.w_mm, 2) == 437.90
    assert round(pm.MAIAEDGE_PBC.h_mm, 2) == 41.27
