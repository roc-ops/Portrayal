"""The end caps, feet, base plate and hinge tabs of the Chatsworth Motive single-sided managers.

The data sheet's photograph shows two caps on the top end. It also shows two feet with a base
plate and two small holes on the bottom end. The installation instructions draw four hinge tabs
on the corners of the door's back. Each device draws them on the faces where a plate does not
hide them.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = {"0": 150, "1": 200, "2": 250, "3": 300, "4": 380}
MODELS = [f"3261{n}-{c}" for n in "01234" for c in ("703", "e03")]


def load(model):
    path = ROOT / "library" / "devices" / "chatsworth" / model / "device.yaml"
    return yaml.safe_load(path.read_text())


def decor(dev, view):
    return {d["id"]: d for d in dev["views"][view]["panel"]["decor"]}


@pytest.mark.parametrize("model", MODELS)
def test_rear_draws_two_caps_two_feet_the_rim_and_four_tabs(model):
    dev = load(model)
    d = decor(dev, "rear")
    width = dev["chassis"]["width"]
    height = dev["chassis"]["height"]
    assert width == WIDTHS[model[4]]
    caps = [v for v in d.values() if v["kind"] == "end-cap"]
    feet = [v for v in d.values() if v["kind"] == "foot"]
    tabs = [v for v in d.values() if v["kind"] == "hinge-tab"]
    assert (len(caps), len(feet), len(tabs)) == (2, 2, 4)
    plates = [v for v in d.values() if v["kind"] == "cross-plate"]
    assert len(plates) == 2 and [v["kind"] for v in d.values()].count("door-rib") == 1
    assert plates[0]["at"][1] + plates[0]["size"][1] < d["door-rib"]["at"][1] + 1e-6
    assert d["door-rib"]["at"][1] + d["door-rib"]["size"][1] < plates[1]["at"][1] + 1e-6
    assert abs(d["door-rib"]["at"][0] + d["door-rib"]["size"][0] / 2 - width / 2) < 0.06 * width
    assert all(v["at"][1] == 0 for v in caps)
    assert all(abs(v["size"][0] - 0.425 * width) < 0.06 for v in caps)
    assert all(abs(v["size"][0] - 0.19 * width) < 0.06 for v in feet)
    assert all(abs(v["at"][1] + v["size"][1] - height) < 1e-6 for v in feet)
    assert sorted(v["at"][1] for v in tabs) == [0, 0, height - 50, height - 50]
    left = [v["at"][0] for v in tabs if v["at"][0] < width / 2]
    right = [v["at"][0] + v["size"][0] for v in tabs if v["at"][0] >= width / 2]
    assert len(left) == len(right) == 2
    assert all(abs(a + b - width) < 0.15 for a, b in zip(sorted(left), sorted(right, reverse=True)))


@pytest.mark.parametrize("model", MODELS)
def test_top_draws_two_round_pads_on_two_caps(model):
    d = decor(load(model), "top")
    pads = [v for v in d.values() if v["kind"] == "cap-pad"]
    caps = [v for v in d.values() if v["kind"] == "end-cap"]
    assert (len(caps), len(pads)) == (2, 2)
    for pad in pads:
        assert pad["size"][0] == pad["size"][1]
        assert pad["rx"] == pytest.approx(pad["size"][0] / 2, abs=0.06)
        assert any(c["at"][0] < pad["at"][0] and pad["at"][0] + pad["size"][0] < c["at"][0] + c["size"][0] for c in caps)


@pytest.mark.parametrize("model", MODELS)
def test_bottom_draws_feet_plate_and_two_holes(model):
    dev = load(model)
    d = decor(dev, "bottom")
    width = dev["chassis"]["width"]
    holes = [v for v in d.values() if v["kind"] == "hole"]
    feet = [v for v in d.values() if v["kind"] == "foot"]
    assert (len(holes), len(feet)) == (2, 2)
    centres = sorted(h["at"][0] + h["size"][0] / 2 for h in holes)
    assert centres[0] + centres[1] == pytest.approx(width, abs=0.15)
    assert "base-bar" in d and "base-rim" in d


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("view", ["left", "right"])
def test_sides_draw_cap_foot_and_base_at_the_door_end(model, view):
    dev = load(model)
    d = decor(dev, view)
    depth = dev["chassis"]["depth"]
    for key in ("end-cap", "foot", "base-rim"):
        assert key in d
    door_end = depth - 3 if view == "left" else 3
    cap = d["end-cap"]
    edge = cap["at"][0] + cap["size"][0] if view == "left" else cap["at"][0]
    assert edge == pytest.approx(door_end, abs=0.06)
    assert d["base-rim"]["at"][1] + d["base-rim"]["size"][1] == pytest.approx(dev["chassis"]["height"])


@pytest.mark.parametrize("model", MODELS)
def test_every_new_item_is_estimated_and_the_notes_and_gap_say_so(model):
    dev = load(model)
    for view in ("rear", "top", "bottom", "left", "right"):
        for item in dev["views"][view]["panel"]["decor"]:
            if item["id"].startswith(("end-cap", "foot", "base-", "hinge-tab", "cap-pad", "cross-plate", "door-rib")):
                assert item.get("confidence") == "estimated"
    assert dev["provenance"]["ends"]["confidence"] == "estimated"
    assert "2.804" in dev["provenance"]["ends"]["note"]
    gap = [g for g in dev["gaps"] if g["what"] == "end-fittings-front"]
    assert len(gap) == 1 and gap[0]["scope"] == ["front"]
    assert gap[0]["reason"] == "vendor-silent"


@pytest.mark.parametrize("model", MODELS)
def test_the_shared_parts_are_the_ones_the_device_already_placed(model):
    """Nothing is drawn as a new component: the guide, the base well and the frame stay what they were."""
    dev = load(model)
    refs = {p["ref"] for p in dev["views"]["front"]["components"]["placements"]}
    assert "chatsworth/motive-vcm-guide@1" in refs
    assert not any("end-cap" in r or "foot" in r or "hinge" in r for r in refs)
