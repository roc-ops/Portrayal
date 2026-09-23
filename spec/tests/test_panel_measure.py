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
    # THE PACKAGE NAME, and getting it wrong here is silent. This said
    # `panel_measure` and relied on a `sys.path.insert` above it; removing
    # that hack in #178 turned nine tests into skips and nothing failed.
    # The skip allow-list (#183) is what showed the count moving.
    return pytest.importorskip("portrayal_intake.panel_measure")


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
    """A plate declared as the wrong face must not validate.

    This is the whole safety property: the width scales ANYTHING, and only the
    height check can tell you the scale was taken off the wrong object.

    ON A DRAWN PLATE RATHER THAN THE STAGED PHOTOGRAPH, deliberately. The
    reference imagery lives in `working/` and is never committed, so this test
    skipped on CI - the one test in the file that proves the tool refuses,
    running only on the machine that already has the corpus. A rectangle with
    the FHD module's aspect ratio exercises the identical path: the same image
    passes as the face it is and is refused as the face it is not.
    """
    Image = pytest.importorskip("PIL.Image")
    w, h = 311, 100                      # 311/100 is 108.97/35.05 to a tenth of a px
    im = Image.new("RGB", (w + 40, h + 40), (255, 255, 255))
    for y in range(20, 20 + h):
        for x in range(20, 20 + w):
            im.putpixel((x, y), (10, 10, 10))

    assert pm.measure(im)[1] < 3.0, "the drawn plate is not a good FHD stand-in"

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


# --- the plate's left edge is its edge, not its corner -------------------------

def _rounded_plate(Image, *, left=30, top=25, w=311, h=100, r=12):
    """A dark plate with rounded corners on a light ground, as FS draws one.

    Rows inside a corner's radius start inboard of the true edge, by `r` px on
    the very first row. The outermost of them fall under 97% of the widest row
    and stay out of the band `plate()` finds, but the next ones in do not: with
    these defaults the band's first row starts 4 px inboard, which is the error
    the first-row x0 made. Change `r`, `w` or the 97% threshold and re-check
    that the band still opens on an inset row, or the tests below stop
    measuring anything.
    """
    im = Image.new("RGB", (left + w + 40, top + h + 40), (255, 255, 255))
    for y in range(h):
        # how far a quarter-circle of radius r pulls this row in
        dy = max(r - y, y - (h - 1 - r), 0)
        inset = r - int(round((r * r - dy * dy) ** 0.5)) if dy else 0
        for x in range(inset, w - inset):
            im.putpixel((left + x, top + y), (10, 10, 10))
    return im


def test_a_rounded_plate_reports_its_true_left_edge(pm):
    """x0 IS THE PLATE'S EDGE, NOT ITS CORNER.

    `plate()` took x0 from the FIRST row of the band, and on every FS FHD render
    that row lies on the plate's rounded top corner: 1.25-1.53 mm right of the
    true edge on the seven cassette renders measured in 2026-09. `openings()`
    counts from x0, so every adapter measured with it came out ~1.45 mm too far
    left and nothing noticed, because the check that "proved" the method compared
    it with a skin the same tool had produced. A drawn plate knows its edge.
    """
    Image = pytest.importorskip("PIL.Image")
    im = _rounded_plate(Image)
    x0, _y0, x1, _y1, _mm = pm.plate(im)
    # The band's first row, found as `plate()` finds it. Not y0: that is the
    # plate's solid top edge now, and on a rounded plate it is always inset.
    spans = []
    for y in range(im.size[1]):
        xs = [x for x in range(im.size[0]) if pm._dark(im.getpixel((x, y)))]
        spans.append((xs[0], xs[-1] - xs[0] + 1) if xs else (0, 0))
    widest = max(w for _x, w in spans)
    first = next(x for x, w in spans if w > widest * 0.97)
    assert first > 30, (
        "the band opens on a full-width row, so a first-row x0 would pass too - "
        "this plate no longer tests the corner; see _rounded_plate")
    assert x0 == 30, f"x0 {x0} is {x0 - 30} px inboard of the drawn edge at 30"
    assert x1 == 30 + 311 - 1


def test_openings_count_from_the_true_edge(pm):
    """A feature a known distance in from the edge reads that distance."""
    Image = pytest.importorskip("PIL.Image")
    im = _rounded_plate(Image)
    for y in range(25 + 30, 25 + 70):          # a pale opening at x 80..119
        for x in range(30 + 80, 30 + 120):
            im.putpixel((x, y), (200, 205, 210))
    box = pm.plate(im)
    (a, b, _c), = pm.openings(im, box)
    px = 311 / 108.97
    assert abs(a * px - 80) < 0.5 and abs(b * px - 120) < 0.5, (a * px, b * px)


def test_the_cassette_renders_frame_on_the_plate_edge(pm):
    """On FS's own render the frame is the edge at the plate's centre row.

    57016.main.jpg's centre row starts at x 86; the band's first row, on the
    corner, starts at 94 - the 1.38 mm every 12-fibre adapter was placed short by.
    """
    im = _im(pm, "57016.main.jpg")
    x0, y0, _x1, y1, _mm = pm.plate(im)
    yc = (y0 + y1) // 2
    edge = next(x for x in range(im.size[0]) if pm._dark(im.getpixel((x, yc))))
    assert abs(x0 - edge) <= 1, (x0, edge)


# --- the scale is the plate's width, and its height ends where the plate does -----

def _shadowed_plate(Image):
    """The rounded plate, with the two shadows FS renders under one.

    A HALO: a pale grey band (sum 675, inside `_dark`) 3 px outside BOTH edges
    over the plate's lower quarter, the way FS's drop shadow widens the rows
    near the lip. It makes those rows the widest in the image.

    A SHADOW BELOW: rows fading from grey to white under the plate, as wide as
    its rounded corners, so the first of them are wide enough to join the band.
    """
    im = _rounded_plate(Image)
    for y in range(25 + 75, 25 + 100):
        for x in list(range(27, 30)) + list(range(341, 344)):
            im.putpixel((x, y), (225, 225, 225))
    for k in range(12):
        g = 150 + 7 * k                   # sums 450..681: dark, never solid
        for x in range(30 + k, 341 - k):
            im.putpixel((x, 125 + k), (g, g, g))
    return im


def test_the_scale_is_the_plate_not_its_widest_shadowed_row(pm):
    """x1 IS THE PLATE'S RIGHT EDGE, AND THE SCALE IS ITS WIDTH.

    The widest row in an FS render is its drop shadow, not its plate: 1.4% wider
    on 35510.G and 0.16-0.48% on the FHD cassette renders. Scaling on that row
    put every measured position short in proportion to its distance from x0.
    """
    Image = pytest.importorskip("PIL.Image")
    x0, _y0, x1, _y1, mm = pm.plate(_shadowed_plate(Image))
    assert (x0, x1) == (30, 30 + 311 - 1), (x0, x1)
    assert abs(mm - 108.97 / 311) < 1e-9, (mm, 108.97 / 311)


def test_the_plate_ends_where_it_is_solid_not_where_its_shadow_does(pm):
    """y0 AND y1 ARE THE PLATE'S TOP AND BOTTOM EDGES.

    The band is cut on width, so it dropped a rounded corner's rows at the top and
    kept the shadow's first rows below the plate - on 35510.G one row lost at
    the top and four gained below, which with the scale corrected would have
    read 3.1% on the height check. The shadow is dark, but it is not solid.
    """
    Image = pytest.importorskip("PIL.Image")
    _x0, y0, _x1, y1, _mm = pm.plate(_shadowed_plate(Image))
    assert (y0, y1) == (25, 25 + 100 - 1), (y0, y1)


def test_the_mtp_panel_scales_on_its_centre_row(pm):
    """On FS's own render the scale is the plate's width at its centre row.

    35510.G.jpg's widest dark row is its lower halo, 645 px against the plate's
    636, and that is the 1.4% every figure measured on it was short by.
    """
    im = _im(pm, "35510.G.jpg")
    x0, y0, x1, y1, mm = pm.plate(im)
    yc = (y0 + y1) // 2
    xs = [x for x in range(im.size[0]) if pm._dark(im.getpixel((x, yc)))]
    assert abs(x0 - xs[0]) <= 1 and abs(x1 - xs[-1]) <= 1, (x0, x1, xs[0], xs[-1])
    assert abs((x1 - x0 + 1) * mm - 108.97) < 0.01
