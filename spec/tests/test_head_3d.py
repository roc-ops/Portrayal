"""The heads build as solids of the right size and the tab is a loop, read off
the compiled SVG's relief attributes (docs/pluggables-heads-design.md section 6
items 4 and 5). A solid is `out - summed lift`; a negative one is built inside out.

kit/relief.js is the reader every check here stands in for, so each one names
the rule of it that it mirrors:

- a raised node is built from `liftOf` (every `data-z-lift` up the ancestor
  chain, its own included) to its ABSOLUTE `data-z-out`;
- a cavity is a `[data-depth]` node with no `[data-depth]` below it, at its
  `--<data-cavity>` node's box, and it punches a raised surface only when
  `cavitySeatsOn` holds: its lift equals that surface's `out` and its box lies
  inside the surface's box (both boxes in the face frame, `mmRect`);
- the 2D drawing paints in document order, so a head drawn after its jack
  would bury it in 2D whatever the 3D build does.
"""
import re
from pathlib import Path

import pytest

from test_nested_occupants import fitted_copy, render, device_matrix

OCC = {"front-6/xg0": "generic/sfp-rj45@1", "front-6/cg0": "generic/qsfp-lc@2"}
DIST = Path(__file__).resolve().parents[2] / "library" / "dist" / "components"
EPS = 0.01          # cavitySeatsOn's own tolerance


def lift_of(parents, el):
    total = 0.0
    while el is not None:
        total += float(el.get("data-z-lift") or 0)
        el = parents.get(el)
    return total


def by_suffix(root, suffix):
    hits = [e for e in root.iter() if (e.get("id") or "").endswith(suffix)]
    assert len(hits) == 1, (suffix, [h.get("id") for h in hits])
    return hits[0]


def polygon(d):
    """The vertices of a path drawn with M/L/H/V/Z (either case) - a cavity's
    outline. Anything else is refused rather than guessed at."""
    pts, x, y = [], 0.0, 0.0
    for cmd, body in re.findall(r"([MmLlHhVvZz])([^MmLlHhVvZz]*)", d):
        nums = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", body)]
        if cmd in "Zz":
            continue
        if cmd in "MmLl":
            for i in range(0, len(nums), 2):
                dx, dy = nums[i], nums[i + 1]
                x, y = (x + dx, y + dy) if cmd.islower() else (dx, dy)
                pts.append((x, y))
        elif cmd in "Hh":
            for v in nums:
                x = x + v if cmd == "h" else v
                pts.append((x, y))
        else:
            for v in nums:
                y = y + v if cmd == "v" else v
                pts.append((x, y))
    assert pts, d
    return pts


def apply(m, pts):
    return [(m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2])
            for x, y in pts]


def box(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def rect_corners(el):
    x, y = float(el.get("x") or 0), float(el.get("y") or 0)
    w, h = float(el.get("width")), float(el.get("height"))
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def relative(parents, el, ancestor):
    """`el`'s own frame in `ancestor`'s frame: the transforms between them."""
    inv = _inverse(device_matrix(parents, ancestor))
    return _mul(inv, device_matrix(parents, el))


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _inverse(m):
    a, b, c, d, e, f = m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2]
    det = a * e - b * d
    return [[e / det, -b / det, (b * f - c * e) / det],
            [-d / det, a / det, (c * d - a * f) / det],
            [0, 0, 1]]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("h3d")
    dev = fitted_copy(tmp, "c100g", "base", {"front-6": "casa/smm-300gm@1"}, OCC)
    return render(dev, tmp / "o", "c100g", "base")


def test_no_solid_is_built_inside_out(built):
    root, parents = built
    seen = 0
    for el in root.iter():
        if el.get("data-z-out"):
            seen += 1
            assert float(el.get("data-z-out")) - lift_of(parents, el) >= -1e-6, el.get("id")
    assert seen, "measured no raised node at all"


def test_the_copper_head_overhangs_the_face_and_stands_22_70_out(built):
    root, parents = built
    head = by_suffix(root, "xg0-occupant--head")
    assert float(head.get("data-z-out")) - lift_of(parents, head) == pytest.approx(22.70, abs=0.05)
    assert float(head.get("y")) < 0, "the head's art overhangs the face in y"


def test_the_tab_is_two_arms_and_a_grip(built):
    root, _ = built
    ids = [e.get("id") or "" for e in root.iter()]
    for n in ("--tab--arm-l", "--tab--arm-r", "--tab--grip"):
        assert any(i.endswith(n) for i in ids), n
    # the brick is gone: the tab's own group carries no solid of its own,
    # only its arms and grip do
    tab = by_suffix(root, "cg0-occupant--tab")
    assert tab.get("data-z-out") is None


# --- the head does not bury the jack -----------------------------------------

def test_the_head_is_drawn_before_its_jack(built):
    """2D: document order is paint order. render.py raises an `out` node to the
    end of its instance group when the component composes parts (the defect
    class that buried the caps' bores); the head is the skin's base plate and
    is exempt, and this fails if that exemption ever stops covering it."""
    root, parents = built
    head = by_suffix(root, "xg0-occupant--head")
    jack = by_suffix(root, "xg0-occupant--jack")
    occ = parents[head]
    assert parents[jack] is occ, "head and jack are siblings in the occupant"
    kids = list(occ)
    assert kids.index(head) < kids.index(jack), "the head paints over its own jack"


def test_the_jack_cavity_punches_the_head(built):
    """3D: relief.js's cavitySeatsOn, evaluated on the compiled drawing. The
    jack's cavity is lifted onto the head's front (lift == out) and its box lies
    inside the head's box, so the kit punches the head with the cavity's art and
    builds the well into it. Either half failing leaves the well behind an
    unbroken head - buried, which is the defect this guards."""
    root, parents = built
    head = by_suffix(root, "xg0-occupant--head")
    jack = by_suffix(root, "xg0-occupant--jack")
    # it is the kit's cavity: the innermost [data-depth] and its named node
    assert jack.get("data-depth") and not jack.findall(".//*[@data-depth]")
    cav = by_suffix(root, f"xg0-occupant--jack--{jack.get('data-cavity')}")
    assert lift_of(parents, jack) == pytest.approx(float(head.get("data-z-out")), abs=EPS)
    hx0, hy0, hx1, hy1 = box(apply(device_matrix(parents, head), rect_corners(head)))
    cx0, cy0, cx1, cy1 = box(apply(device_matrix(parents, cav), polygon(cav.get("d"))))
    assert (cx0 >= hx0 - EPS and cy0 >= hy0 - EPS
            and cx1 <= hx1 + EPS and cy1 <= hy1 + EPS), ((cx0, cy0, cx1, cy1), (hx0, hy0, hx1, hy1))
    # and the well it builds stays inside the head's solid: its floor is in
    # front of the cage face, not through it
    floor = lift_of(parents, jack) - float(jack.get("data-depth"))
    assert floor > 0, floor


def test_the_latch_slot_is_in_the_upper_half_of_the_head(built):
    """The keyway is the cavity's narrow tier: of the outline's two extreme
    horizontal edges (in the module's own frame, label side up), the SHORT one is
    the slot's mouth and the long one the body's. Found from the outline, not a
    hard-coded row, so a flip of the jack's rotate moves it and fails here."""
    root, parents = built
    occ = by_suffix(root, "--xg0-occupant")
    head = by_suffix(root, "xg0-occupant--head")
    jack = by_suffix(root, "xg0-occupant--jack")
    cav = by_suffix(root, f"xg0-occupant--jack--{jack.get('data-cavity')}")
    pts = apply(relative(parents, cav, occ), polygon(cav.get("d")))
    ys = [p[1] for p in pts]

    def edge(y):
        xs = [p[0] for p in pts if abs(p[1] - y) < 1e-6]
        return max(xs) - min(xs)

    top, bottom = min(ys), max(ys)
    slot_y = top if edge(top) < edge(bottom) else bottom
    assert edge(slot_y) < 0.5 * max(edge(top), edge(bottom)), "no narrow tier found"
    hy0 = float(head.get("y"))
    mid = hy0 + float(head.get("height")) / 2
    assert hy0 <= slot_y < mid, (slot_y, hy0, mid)
    # the whole narrow tier, not only its mouth: its vertices at the slot's width
    sx = sorted(p[0] for p in pts if abs(p[1] - slot_y) < 1e-6)
    tier = [p for p in pts if sx[0] - 1e-6 <= p[0] <= sx[-1] + 1e-6]
    assert max(p[1] for p in tier) < mid, tier


# --- the tab's absolute extent ------------------------------------------------

def test_the_tab_arms_span_20_to_58_6_and_the_grip_58_6_to_69_8(built):
    """From the cage face. The tab is composed at lift 20.0; its arms are out 38.6
    and its grip lift 38.6 out 49.8 in its own frame. render.py writes `out`
    absolute (38.6 + 20 = 58.6, 49.8 + 20 = 69.8) and leaves `lift` to be summed,
    so a lift counted twice would put the grip's base at 78.6 - past its own front."""
    root, parents = built
    for n in ("--tab--arm-l", "--tab--arm-r"):
        arm = by_suffix(root, f"cg0-occupant{n}")
        assert lift_of(parents, arm) == pytest.approx(20.0, abs=1e-6), n
        assert float(arm.get("data-z-out")) == pytest.approx(58.6, abs=1e-6), n
    grip = by_suffix(root, "cg0-occupant--tab--grip")
    assert lift_of(parents, grip) == pytest.approx(58.6, abs=1e-6)
    assert float(grip.get("data-z-out")) == pytest.approx(69.8, abs=1e-6)


def test_the_risers_span_20_to_27_5_and_the_nose_is_11_3_tall(built):
    """The riser posts stand on the nose front (lift 20.0, summed from the tab's
    group) to 7.5 out of it, absolute 27.5 - a lift counted twice would build
    them inside out. The nose is the body node, extruded 0 to 20 over its
    11.3-tall outline, 1.4 past the 8.5 face at both edges (#646)."""
    root, parents = built
    for n in ("--tab--riser-l", "--tab--riser-r"):
        r = by_suffix(root, f"cg0-occupant{n}")
        assert lift_of(parents, r) == pytest.approx(20.0, abs=1e-6), n
        assert float(r.get("data-z-out")) == pytest.approx(27.5, abs=1e-6), n
    body = by_suffix(root, "cg0-occupant--body")
    assert float(body.get("data-z-out")) - lift_of(parents, body) == pytest.approx(20.0, abs=1e-6)
    assert float(body.get("y")) == pytest.approx(-1.3) and float(body.get("height")) == pytest.approx(11.1)


# --- art outside the viewBox ---------------------------------------------------

def _viewbox(svg_root):
    x, y, w, h = (float(v) for v in svg_root.get("viewBox").split())
    return x, y, x + w, y + h


def _inside(b, vb):
    return b[0] >= vb[0] - 1e-6 and b[1] >= vb[1] - 1e-6 and b[2] <= vb[2] + 1e-6 and b[3] <= vb[3] + 1e-6


def test_placed_overhangs_are_inside_the_device_viewbox(built):
    """PLACED: the head's 2.50 and the tab's 1.07 above the part's own y=0 are
    inside the device drawing, and nothing on the chain up to it clips."""
    root, parents = built
    vb = _viewbox(root)
    for suffix in ("xg0-occupant--head", "cg0-occupant--tab--grip",
                   "cg0-occupant--tab--arm-l", "cg0-occupant--tab--arm-r",
                   "cg0-occupant--tab--riser-l", "cg0-occupant--tab--riser-r",
                   "cg0-occupant--body"):
        el = by_suffix(root, suffix)
        b = box(apply(device_matrix(parents, el), rect_corners(el)))
        assert _inside(b, vb), (suffix, b, vb)
        node = el
        while node is not None:
            assert node.get("clip-path") is None and node.get("mask") is None, node.get("id")
            node = parents.get(node)


@pytest.mark.parametrize("stem, suffixes", [
    ("generic--sfp-rj45--v1--default", ("--head",)),
    ("generic--qsfp-lc--v2--default", ("--tab--grip", "--tab--arm-l", "--tab--arm-r",
                                       "--tab--riser-l", "--tab--riser-r", "--body")),
])
def test_standalone_preview_holds_its_overhangs(stem, suffixes):
    """The standalone component SVG is the Explorer's module preview. A part
    that declares `head:` gets a root viewBox that is the union of its size,
    its head and its composed parts, so the copper head's -2.50..10.70 and the
    QSFP tab's y -1.07 and x -0.325..18.675 are inside it."""
    import xml.etree.ElementTree as ET
    path = DIST / f"{stem}.svg"
    if not path.exists():
        pytest.skip(f"needs a build: {path.name}")
    root = ET.parse(path).getroot()
    parents = {c: p for p in root.iter() for c in p}
    if root.get("overflow") == "visible":
        return          # the root does not clip; every overhang is drawn
    vb = _viewbox(root)
    for s in suffixes:
        el = by_suffix(root, s)
        assert _inside(box(apply(device_matrix(parents, el), rect_corners(el))), vb), (stem, s)


@pytest.mark.parametrize("stem, ref", [
    # its head box equals its size, so the union is the size box
    ("generic--sfp-lc--v1--default", "generic/sfp-lc/v1"),
    # no `head:` at all
    ("std--rj45-ganged--v2--default", "std/rj45-ganged/v2"),
])
def test_a_preview_without_an_overhanging_head_keeps_its_size(stem, ref):
    """Only a part that declares `head:` grows its preview, and only by what it
    overhangs: every other preview keeps `0 0 w h` and mm width/height from
    `size`, byte for byte as before."""
    import xml.etree.ElementTree as ET
    import yaml
    path = DIST / f"{stem}.svg"
    if not path.exists():
        pytest.skip(f"needs a build: {path.name}")
    lib = DIST.parents[1] / "components"
    size = yaml.safe_load((lib / ref / "contract.yaml").read_text())["size"]
    root = ET.parse(path).getroot()
    assert root.get("viewBox") == f"0 0 {size['w']} {size['h']}", root.get("viewBox")
    assert root.get("width") == f"{size['w']}mm" and root.get("height") == f"{size['h']}mm"
