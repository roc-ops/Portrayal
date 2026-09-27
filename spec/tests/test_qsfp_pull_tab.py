"""common/qsfp-pull-tab@2: a flat U-loop, arms at the sides and a grip that
rises above the module top, coloured by the host's latch-color
(docs/pluggables-heads-design.md section 4.5)."""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "library/components/common/qsfp-pull-tab"
C2 = yaml.safe_load((D / "v2/contract.yaml").read_text())
SVG = ET.parse(D / "v2/skins/default.svg").getroot()
NODES = {e.get("id"): e for e in SVG.iter() if e.get("id")}


def test_v1_points_at_v2():
    assert yaml.safe_load((D / "v1/contract.yaml").read_text())["superseded-by"] == \
        "common/qsfp-pull-tab@2"


def test_the_loop_is_two_arms_and_a_grip_with_nothing_between():
    feats = {f["node"]: f for f in C2["relief"]["features"]}
    assert set(feats) >= {"arm-l", "arm-r", "grip"}
    xs = sorted(float(NODES[n].get("x")) for n in ("arm-l", "arm-r"))
    w = float(NODES["arm-l"].get("width"))
    assert xs[1] - (xs[0] + w) > 10.0, "the arms must leave the middle open"


def test_the_grip_is_at_the_far_end_and_higher_than_the_arms():
    feats = {f["node"]: f for f in C2["relief"]["features"]}
    assert feats["grip"]["out"] > feats["arm-l"]["out"] - 0.01
    assert float(NODES["grip"].get("y")) < float(NODES["arm-l"].get("y"))


def test_the_colour_is_the_field_and_no_rate_is_drawn():
    assert "latch-color" in C2["fields"]
    for n in ("arm-l", "arm-r", "grip"):
        assert NODES[n].get("data-fill-from") == "latch-color", n
        assert NODES[n].get("data-stroke-derive") == "latch-color", n
    assert "".join(SVG.itertext()).strip() == "", "a generic tab carries no lettering"


def test_photograph_readings_say_photo_measured():
    """The vocabulary keeps `measured` for readings off the part itself; a
    photograph is `photo-measured` (component.schema.json $defs.confidence).
    Drawing-sourced features remain drawing, even when corroborated by photos."""
    feats = {f["node"]: f for f in C2["relief"]["features"]}
    # Photo-measured arms
    assert feats["arm-l"]["confidence"] == "photo-measured"
    assert feats["arm-r"]["confidence"] == "photo-measured"
    # Size from photos
    assert C2["size-confidence"]["h"] == "photo-measured"
    # Grip sourced to drawing, despite photograph corroboration
    assert feats["grip"]["confidence"] == "drawing"
    assert "photographs" in feats["grip"]["source"].lower()


def test_every_relief_figure_says_where_it_came_from():
    for f in C2["relief"]["features"]:
        assert f.get("confidence") in {"drawing", "measured", "photo-measured", "estimated"}, f
        assert f.get("source", "").strip(), f


# --- the riser blocks (roc-ops/Portrayal#646) ----------------------------------

def _box(n):
    e = NODES[n]
    x, y = float(e.get("x")), float(e.get("y"))
    return x, y, x + float(e.get("width")), y + float(e.get("height"))


def test_each_arm_roots_in_a_riser_7_5_long_and_7_8_tall():
    """The photographed riser: 7.5 along the axis (7.41 and 7.53 in the two side
    views) and 7.8 tall from the strap top (7.67 and 7.87), flush with the strap
    top. Drawn as the part BELOW the arm's cross-section, so the arm root is the
    post's top and the two solids share no volume."""
    feats = {f["node"]: f for f in C2["relief"]["features"]}
    for side in ("l", "r"):
        arm, riser = _box(f"arm-{side}"), _box(f"riser-{side}")
        assert riser[0] == pytest.approx(arm[0]) and riser[2] == pytest.approx(arm[2]), side
        assert riser[1] == pytest.approx(arm[3]), "the riser starts where the arm's section ends"
        assert riser[3] - arm[1] == pytest.approx(7.8), "7.8 tall from the strap top"
        f = feats[f"riser-{side}"]
        assert f["out"] == pytest.approx(7.5) and not f.get("lift")
        assert f["out"] < feats[f"arm-{side}"]["out"], "the arm runs on past its riser"
        assert f["confidence"] == "photo-measured" and f["source"].strip()
        assert C2["elements"][f"riser-{side}"]["size"] == [1.95, 4.9]


def test_the_size_box_holds_the_risers():
    """size.h is the whole part now: the grip top to the risers' lower ends."""
    lowest = max(_box(n)[3] for n in NODES if n in C2["elements"])
    assert C2["size"]["h"] == pytest.approx(lowest) == pytest.approx(8.56)
    assert SVG.get("viewBox") == f"0 0 {C2['size']['w']} {C2['size']['h']}"


def test_the_risers_paint_first_because_they_are_farthest():
    """2D paint order is depth order here: risers (7.5 out) under arms (38.6)
    under nothing - so a riser never covers its own arm's end."""
    order = [e.get("id") for e in SVG if e.get("id")]
    for side in ("l", "r"):
        assert order.index(f"riser-{side}") < order.index(f"arm-{side}")
    for n in ("riser-l", "riser-r"):
        assert NODES[n].get("data-fill-from") == "latch-color", n
        assert NODES[n].get("data-stroke-derive") == "latch-color", n


def test_the_riser_belongs_to_the_tab():
    """Ownership, stated where the next reader looks: the riser is the strap's
    own moulding, so the tab carries it and the module head does not."""
    assert "belongs to this" in C2["provenance"]["riser"]
    assert "riser" in C2["description"]


# --- the S-bend and the fitted-edge figures (roc-ops/Portrayal#647, #685) -----

# Side view IMG_2190 of the maintainer's photographs of a QSFP SR4 module, read
# on body edges fitted along the in-cage body: the strap top above the module
# top at every 2.5 of reach from the nose front (provenance.sbend), +/-0.15.
REACH = [2.5 * i for i in range(1, 20)]
SAMPLES = [0.46, 0.47, 0.46, 0.49, 0.51, 0.55, 0.55, 0.57, 0.35, -0.29,
           -0.80, -1.04, -1.05, -0.79, -0.26, 0.33, 0.78, 1.10, 1.23]
TOL = 0.15
STRAP_TOP = 0.47        # where the strap leaves the riser; was 0.57 on median edges
GRIP_TOP = 1.23         # was 1.07 on median edges
DIP = 1.53              # the curve's lowest point below STRAP_TOP, at reach 30.7
RISE = 0.76             # GRIP_TOP less STRAP_TOP
HOSTS = ("generic/qsfp-lc", "generic/qsfp-dd-lc")


def _segments(side):
    """One arm's boxes in reach order: (node, lift, out)."""
    feats = [f for f in C2["relief"]["features"]
             if f["node"] == f"arm-{side}" or f["node"].startswith(f"arm-{side}-")]
    return sorted(((f["node"], f.get("lift") or 0.0, f["out"]) for f in feats),
                  key=lambda t: t[1])


def _top_above_module(node):
    """A box top in the host face frame, as a height above the module top. The
    tab's own y 0 is the grip top, GRIP_TOP above the module."""
    return GRIP_TOP - float(NODES[node].get("y"))


def test_the_samples_are_the_recorded_provenance():
    text = " ".join(C2["provenance"]["sbend"].split())
    assert ", ".join(f"{v:.2f}" for v in SAMPLES) in text
    for word in ("photo-measured", "IMG_2190", "CALIBRATION", "UNCERTAINTY", "IMG_2192"):
        assert word in text, word


def test_each_arm_is_six_boxes_along_the_reach():
    for side in ("l", "r"):
        segs = _segments(side)
        assert len(segs) == 6, segs
        for node, _, _ in segs:
            assert C2["elements"][node]["size"] == [1.95, 2.9], node
            assert float(NODES[node].get("height")) == pytest.approx(2.9), node
            assert NODES[node].get("x") == NODES[f"arm-{side}"].get("x"), node
            assert float(NODES[node].get("width")) == pytest.approx(1.95), node
            assert C2["elements"][node]["at"] == [float(NODES[node].get("x")),
                                                  float(NODES[node].get("y"))], node


def test_the_boxes_meet_end_to_end_with_no_gap_and_no_overlap():
    """Each box's lift is where the one before it ends: the root starts on the
    nose front, the last one ends where the grip begins."""
    grip = next(f for f in C2["relief"]["features"] if f["node"] == "grip")
    for side in ("l", "r"):
        segs = _segments(side)
        assert segs[0][0] == f"arm-{side}" and segs[0][1] == 0.0
        for (_, _, out), (n, lift, _) in zip(segs, segs[1:]):
            assert lift == pytest.approx(out, abs=1e-9), n
        for n, lift, out in segs:
            assert out > lift, n
        assert segs[-1][2] == pytest.approx(grip["lift"], abs=1e-9)


def test_both_arms_step_alike():
    left, right = _segments("l"), _segments("r")
    for (nl, al, ol), (nr, ar, orr) in zip(left, right):
        assert (al, ol) == (ar, orr), (nl, nr)
        assert NODES[nl].get("y") == NODES[nr].get("y"), (nl, nr)


def _curve(u):
    pts = [(0.0, SAMPLES[0])] + list(zip(REACH, SAMPLES))
    for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
        if u0 <= u <= u1:
            return v0 + (v1 - v0) * (u - u0) / (u1 - u0)
    raise ValueError(u)


def test_every_box_follows_the_measured_curve():
    """Each box top lies inside the curve's own range over the box's span,
    widened by the reading's uncertainty - a step, not a guess."""
    for side in ("l", "r"):
        for n, lift, out in _segments(side):
            span = [_curve(lift + (out - lift) * k / 20) for k in range(21)]
            top = _top_above_module(n)
            assert min(span) - TOL <= top <= max(span) + TOL, (n, top, min(span), max(span))


def test_the_dip_and_the_rise_are_the_measured_ones():
    for side in ("l", "r"):
        segs = _segments(side)
        tops = [_top_above_module(n) for n, _, _ in segs]
        root = tops[0]
        assert root == pytest.approx(STRAP_TOP, abs=0.01)
        deepest = min(range(len(tops)), key=lambda i: tops[i])
        assert root - tops[deepest] == pytest.approx(DIP, abs=TOL)
        _, lift, out = segs[deepest]
        assert lift <= 30.7 <= out, "the deepest box holds the curve's lowest point"
        # down into the dip and back up, once: an S, not a sawtooth
        assert tops[:deepest + 1] == sorted(tops[:deepest + 1], reverse=True)
        assert tops[deepest:] == sorted(tops[deepest:])
        assert GRIP_TOP - root == pytest.approx(RISE, abs=0.01)


def test_the_grip_top_and_strap_top_are_the_fitted_edge_figures():
    """#685: read again on fitted body edges, the grip top moved beyond its
    uncertainty (1.07 to 1.23) and the strap top within it (0.57 to 0.47);
    the hosts compose the tab so the grip top lands where it was measured."""
    assert float(NODES["grip"].get("y")) == 0.0
    for ref in HOSTS:
        host = yaml.safe_load((ROOT / "library/components" / ref / "v2/contract.yaml").read_text())
        tab = next(p for p in host["parts"] if p["id"] == "tab")
        assert tab["at"][1] == pytest.approx(-GRIP_TOP), ref
        assert tab["at"][1] + float(NODES["arm-l"].get("y")) == pytest.approx(-STRAP_TOP), ref
        # the risers stay flush with the strap top and end where #646 measured
        # their lower edge, 7.33 and 7.39 below the module top
        assert tab["at"][1] + _box("riser-l")[3] == pytest.approx(7.36, abs=TOL), ref


def test_the_steps_are_drawn_under_the_arm_root_and_riser():
    """Face-on the strap is seen end-on, and every lower box lies inside the
    outline the arm root and the riser already draw, so it is painted first and
    the face looks as it did."""
    order = [e.get("id") for e in SVG if e.get("id")]
    for side in ("l", "r"):
        ax0, ay0, ax1, _ = _box(f"arm-{side}")
        _, _, _, ry1 = _box(f"riser-{side}")
        for n, _, _ in _segments(side)[1:]:
            x0, y0, x1, y1 = _box(n)
            assert (x0, x1) == (ax0, ax1) and ay0 <= y0 and y1 <= ry1, n
            assert order.index(n) < order.index(f"riser-{side}"), n
            assert NODES[n].get("data-fill-from") == "latch-color", n
            assert NODES[n].get("data-stroke-derive") == "latch-color", n
