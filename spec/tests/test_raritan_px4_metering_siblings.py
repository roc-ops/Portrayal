"""The Raritan PX4-532AWA-E7M26V2 and PX4-1551WA-E7M26V2 rack PDUs.

What is true of the library once the two devices are in it: each exists under its maker with the
printed unit size, carries the outlet mix, the breaker count and the controller its data sheet
lists, states the metering scope the data sheet gives it, draws all six sides or says why not, and
says in its provenance and in a gap that its geometry is read from the mechanical drawing of the
sibling part number, because no drawing of its own is held.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "raritan"
C13 = "std/c13-outlet"
CX = "raritan/px4-cx-outlet"
# name: (model, outlets of each type, outlets in a group, metering scope, outlet switching, sibling model)
NEW = {
    "px4-532awa-e7m26v2": ("PX4-532AWA-E7M26V2", 18, 6, "outlet", True, "PX4-132AWA"),
    "px4-1551wa-e7m26v2": ("PX4-1551WA-E7M26V2", 12, 4, "input", False, "PX4-5551WA"),
}
SIDES = {"front", "rear", "top", "bottom", "left", "right"}


def _device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text(encoding="utf-8"))


def _placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def _text(node):
    return yaml.safe_dump(node).lower()


def test_each_device_exists_under_its_maker_and_lists_its_part_number():
    for name, (model, *_rest) in NEW.items():
        dev = _device(name)
        assert dev["manufacturer"] == "Raritan", name
        assert dev["model"] == model, name
        assert dev["maturity"] == "modelled", name
        assert model in dev["configurations"]["base"]["part-numbers"], name


def test_the_outline_is_the_printed_unit_size():
    for name in NEW:
        chassis = _device(name)["chassis"]
        assert (chassis["width"], chassis["depth"], chassis["height"]) == (56, 65, 1780), name
        assert chassis["mount"] == "rack-side", name


def test_every_side_is_drawn_or_says_why_it_is_not():
    for name in NEW:
        views = _device(name)["views"]
        assert set(views) == SIDES, name
        for side, view in views.items():
            assert view.get("panel") or view.get("components") or view.get("empty"), (name, side)


def test_the_outlet_mix_is_the_one_the_data_sheet_lists():
    for name, (_, per_type, group, *_rest) in NEW.items():
        outlets = sorted(
            (p for p in _placements(_device(name), "front") if p["id"].startswith("outlet-")),
            key=lambda p: int(p["id"].split("-")[1]),
        )
        refs = [p["ref"].split("@")[0] for p in outlets]
        assert refs.count(C13) == per_type and refs.count(CX) == per_type, name
        for g in range(0, len(refs), group):
            assert refs[g:g + group] == [C13] * (group // 2) + [CX] * (group // 2), (name, g)


def test_each_has_six_breakers_a_controller_and_the_universal_input():
    for name in NEW:
        front = _placements(_device(name), "front")
        assert len([p for p in front if p["ref"].startswith("raritan/px4-breaker")]) == 6, name
        assert {"eth-1", "eth-2", "usb-a-1", "usb-a-2", "usb-b", "link", "sensor"} <= {p["id"] for p in front}, name
        assert any(p["ref"].startswith("raritan/px4-universal-input") for p in front), name


def test_each_rear_carries_two_mounting_buttons_1244_apart():
    for name in NEW:
        ys = sorted(p["at"][1] for p in _placements(_device(name), "rear") if "mounting-button" in p["ref"])
        assert len(ys) == 2 and round(ys[1] - ys[0], 2) == 1244.0, name


def test_the_metering_scope_is_the_one_the_data_sheet_gives():
    for name, (_, _, _, scope, switching, _) in NEW.items():
        management = _device(name)["attrs"]["management"]
        assert management["metering-scope"] == scope, name
        assert management["outlet-switching"] is switching, name


def test_the_geometry_borrowed_from_the_sibling_drawing_is_declared():
    for name, (_, _, _, _, _, sibling) in NEW.items():
        dev = _device(name)
        gaps = {g["what"]: g for g in dev.get("gaps", [])}
        assert "own-drawing" in gaps, name
        assert gaps["own-drawing"]["reason"] == "needs-drawing", name
        assert sibling.lower() in _text(gaps["own-drawing"]), name
        assert sibling.lower() in _text(dev["provenance"]["method"]), name


def test_every_colour_is_declared_unchecked_and_what_no_source_places_is_a_gap():
    for name in NEW:
        dev = _device(name)
        text = _text(dev["provenance"])
        assert "unchecked" in text and "colour" in text, name
        gaps = {g["what"] for g in dev.get("gaps", [])}
        assert {"breaker-feed", "controller-layout", "mount-marks", "sides"} <= gaps, (name, gaps)
