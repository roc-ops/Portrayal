"""common/qsfp-pull-tab@2: a flat U-loop, arms at the sides and a grip that
rises above the module top, coloured by the host's latch-color
(docs/pluggables-heads-design.md section 4.5)."""
import pathlib
import xml.etree.ElementTree as ET

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


def test_every_relief_figure_says_where_it_came_from():
    for f in C2["relief"]["features"]:
        assert f.get("confidence") in {"drawing", "measured", "estimated"}, f
        assert f.get("source", "").strip(), f
