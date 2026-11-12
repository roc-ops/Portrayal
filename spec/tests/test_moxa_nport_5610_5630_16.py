"""The Moxa NPort 5610-16 and NPort 5630-16 serial device servers are in the library, with all six faces and their ears.

Both share the body, the front and the AC rear of the NPort 5650-16 and differ from it in what the data sheet lists per model: the
serial standard, the weight and the input current. They place no part of their own: every part they use is one the NPort 5650-16
already places. The sides, the underside and the ears are the ones the maker's CAD sheet draws; each position on them is read
off the sheet and declared as an estimate in the provenance that carries it.

These read the library and render nothing; they read no library/dist, except the device-type exports.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEPTH = 198.25

MODELS = {
    "nport-5610-16": {"model": "NPort 5610-16", "standard": "RS-232", "kg": 2.49, "ma": "141 mA @ 100 VAC"},
    "nport-5630-16": {"model": "NPort 5630-16", "standard": "RS-422, RS-485", "kg": 2.56, "ma": "152 mA @ 100 VAC"},
}


def device(slug):
    return yaml.safe_load((LIB / "devices" / "moxa" / slug / "device.yaml").read_text())


def placements(dev, view):
    return {p["id"]: p for p in dev["views"][view]["components"].get("placements", [])}


def decor(dev, view):
    return {e["id"]: e for e in dev["views"][view]["panel"]["decor"]}


def centre(e):
    return e["at"][0] + e["size"][0] / 2, e["at"][1] + e["size"][1] / 2


@pytest.mark.parametrize("slug,want", MODELS.items())
def test_the_body_is_the_one_the_data_sheet_dimensions(slug, want):
    d = device(slug)
    assert d["manufacturer"] == "Moxa" and d["model"] == want["model"]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (440, 45.5, DEPTH)
    sizes = {"front": (440, 45.5), "rear": (440, 45.5), "top": (440, DEPTH), "bottom": (440, DEPTH),
             "left": (DEPTH, 45.5), "right": (DEPTH, 45.5)}
    for face, size in sizes.items():
        assert (d["views"][face]["size"]["w"], d["views"][face]["size"]["h"]) == size, face


@pytest.mark.parametrize("slug,want", MODELS.items())
def test_each_model_states_its_own_serial_standard_weight_and_current(slug, want):
    d = device(slug)
    assert d["attrs"]["performance"]["serial-standards"] == want["standard"]
    assert d["attrs"]["physical"]["weight-kg"] == want["kg"]
    assert d["attrs"]["power"]["power-input-current"] == want["ma"]
    assert list(d["configurations"]["base"]["part-numbers"]) == [want["model"]]


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_has_sixteen_numbered_serial_ports_and_one_lan_jack(slug):
    d = device(slug)
    rear = placements(d, "rear")
    ports = [p for p in rear.values() if p.get("group") == "serial"]
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 17))
    assert {p["attrs"]["role"] for p in ports} == {"console-server"}
    assert rear["lan"]["group"] == "lan" and d["groups"]["lan"]["role"] == "management"
    assert rear["inlet"]["ref"] == "std/c14-inlet@1" and "ground" in rear


@pytest.mark.parametrize("slug,want", MODELS.items())
def test_the_front_has_the_lcd_keys_lamps_and_the_models_own_nameplate(slug, want):
    front = placements(device(slug), "front")
    assert front["lcm"]["ref"] == "moxa/nport-5600-lcm@1" and front["keys"]["ref"] == "moxa/nport-5600-keys@1"
    assert {i for i in front if i.startswith(("led-tx-", "led-rx-"))} == (
        {f"led-tx-{n}" for n in range(1, 17)} | {f"led-rx-{n}" for n in range(1, 17)})
    text = {s["id"]: s.get("text") for s in device(slug)["views"]["front"]["silkscreen"]}
    assert text["silk-model-number"] == want["model"].split()[1]


@pytest.mark.parametrize("slug", MODELS)
def test_all_six_faces_are_drawn_and_none_is_left_empty(slug):
    d = device(slug)
    for face in ("front", "rear", "top", "bottom", "left", "right"):
        view = d["views"][face]
        assert "empty" not in view, face
        assert view["panel"]["decor"], face


@pytest.mark.parametrize("slug", MODELS)
def test_each_side_has_the_ear_leg_with_six_holes_and_the_right_is_the_left_mirrored_in_depth(slug):
    d = device(slug)
    left, right = decor(d, "left"), decor(d, "right")
    for face in (left, right):
        assert [n for n in range(1, 7) if f"ear-hole-{n}" in face] == list(range(1, 7))
        assert {"ear-leg", "body-dot", "body-hole-1", "body-hole-4", "rear-hole-1", "rear-hole-2"} <= set(face)
    for i, e in left.items():
        if e["kind"] in ("hole", "plate", "seam", "fold") and i in right:
            lx, ly = centre(e)
            rx, ry = centre(right[i])
            assert lx + rx == pytest.approx(DEPTH, abs=0.02), i
            assert ly == pytest.approx(ry, abs=0.01), i
    # the six ear holes are two rows of three, one pitch apart along the depth
    xs = sorted({round(centre(left[f"ear-hole-{n}"])[0], 1) for n in range(1, 7)})
    assert len(xs) == 3 and xs[1] - xs[0] == pytest.approx(20.1, abs=0.2)


@pytest.mark.parametrize("slug", MODELS)
def test_the_underside_has_four_round_holes_six_tabs_and_a_plate(slug):
    bottom = decor(device(slug), "bottom")
    holes = [e for i, e in bottom.items() if i.startswith("round-hole-")]
    assert len(holes) == 4 and all(e["size"] == [14.8, 14.8] for e in holes)
    assert sorted(i for i in bottom if i.startswith("tab-") and not i.endswith("-bar")) == [f"tab-{n}" for n in range(1, 7)]
    plate = bottom["rear-plate"]
    assert plate["size"][0] > 250 and plate["at"][0] + plate["size"][0] <= 440
    # the sheet draws the underside with the front at the top; the library's has the rear at the top and left and right mirrored,
    # so the plate sits on the right half, nearer the top (rear) edge, and the tabs on the bottom (front) edge below every hole
    assert centre(plate)[0] > 440 / 2 and centre(plate)[1] < DEPTH / 2
    hole_ys = sorted(centre(e)[1] for e in holes)
    assert hole_ys[1] < DEPTH / 2 < hole_ys[2]
    assert all(centre(bottom[f"tab-{n}"])[1] > hole_ys[-1] for n in range(1, 7))


@pytest.mark.parametrize("slug", MODELS)
def test_the_ears_are_stated_as_a_position_and_never_placed_on_a_face(slug):
    d = device(slug)
    ears = d["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["proud"] and ears["positions"][0]["default"] is True
    assert "h" not in ears  # the sheet's ear is the full height of the body
    for view in d["views"].values():
        for p in view.get("components", {}).get("placements", []):
            assert p["ref"] != "common/rack-ear@1" and p["id"] not in ("ear-left", "ear-right")


@pytest.mark.parametrize("slug", MODELS)
def test_the_gaps_say_what_no_page_shows_and_not_that_the_sides_are_undrawn(slug):
    d = device(slug)
    gaps = {g["what"]: g for g in d["gaps"]}
    assert "rack-ears-and-kit" not in gaps and gaps["rack-kit"]["reason"] == "vendor-silent"
    assert gaps["depth-figures-differ"]["reason"] == "sources-disagree"
    assert set(gaps["depth-figures-differ"]["scope"]) == {"top", "bottom", "left", "right"}
    assert ("dip-switches" in gaps) == (slug == "nport-5630-16")
    for key in ("sides", "bottom", "ears"):
        assert d["provenance"][key]["confidence"] == "estimated", key
    text = yaml.safe_dump(d["gaps"])
    assert "No held document draws a side" not in text


def test_the_two_models_place_no_part_the_nport_5650_16_does_not():
    base = {p["ref"] for v in device("nport-5650-16")["views"].values() for p in v.get("components", {}).get("placements", [])}
    for slug in MODELS:
        refs = {p["ref"] for v in device(slug)["views"].values() for p in v.get("components", {}).get("placements", [])}
        assert refs <= base, slug


@pytest.mark.parametrize("slug,want", MODELS.items())
@pytest.mark.parametrize("export", ["netbox", "nautobot"])
def test_each_device_type_is_exported_under_the_model_name(slug, want, export):
    path = LIB / "exports" / export / "device-types" / "Moxa" / f"{want['model']}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["model"] == want["model"]
    assert [p["name"] for p in doc["console-server-ports"]] == [f"port-{n}" for n in range(1, 17)]
