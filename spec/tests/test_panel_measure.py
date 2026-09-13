"""The panel measurer, checked against a face whose answer is already known.

35510.G.jpg is the 12x MTP adapter panel, face-on. Its faceplate must scale to
108.97 x 35.05 within a few percent, and its openings must come out as two rows
of six at a consistent pitch. If the tool cannot reproduce that, no connector
measured with it can be trusted.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG = ROOT / "working" / "intake" / "fs" / "fhd" / "photos"
sys.path.insert(0, str(ROOT / "spec/tools/intake"))


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
