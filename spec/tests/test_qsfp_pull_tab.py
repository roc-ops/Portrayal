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
    assert C2["size"]["h"] == pytest.approx(lowest) == pytest.approx(8.3)
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
