"""The Panduit P42G20G (G6 intelligent PDU) and P24B32M (basic, half-height, two-sided PDU).

Each test reads the device source and the contracts it names. None reads a build.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "panduit"
COMPONENTS = ROOT / "library" / "components" / "panduit"


def _device(name: str) -> dict:
    path = DEVICES / name / "device.yaml"
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    return yaml.safe_load(path.read_text())


def _refs(node, found=None):
    """Every `ref:` string under a node, in document order."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "ref" and isinstance(value, str):
                found.append(value)
            else:
                _refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _refs(item, found)
    return found


def _count(device: dict, ref: str, view: str | None = None) -> int:
    node = device["views"][view] if view else device["views"]
    return _refs(node).count(ref)


def _decor(device: dict, view: str) -> dict:
    """The panel decor of one view, by id. Empty when the view has no panel decor."""
    items = device["views"][view].get("panel", {}).get("decor", [])
    return {item["id"]: item for item in items if "id" in item}


def _centre(item: dict) -> tuple[float, float]:
    """The centre of a decor rectangle or a placement, in the face's millimetres."""
    width, height = item.get("size", [0, 0])
    return round(item["at"][0] + width / 2, 2), round(item["at"][1] + height / 2, 2)


def _contract(name: str) -> dict:
    path = COMPONENTS / name / "v1" / "contract.yaml"
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    return yaml.safe_load(path.read_text())


# ---- P42G20G -------------------------------------------------------------------------

def test_p42g20g_body_is_the_drawn_strip():
    chassis = _device("p42g20g")["chassis"]
    assert chassis["height"] == 1780
    assert (chassis["width"], chassis["depth"]) == (56, 75)
    assert chassis["weight-kg"] == 11.5
    assert chassis["mount"] == "rack-side"


def test_p42g20g_places_the_two_kinds_of_combination_socket():
    device = _device("p42g20g")
    assert _count(device, "panduit/g5-outlet-c13-c15@1", "front") == 21
    assert _count(device, "panduit/g5-outlet-c13-c15-c19@1", "front") == 21


def test_p42g20g_has_six_breakers_and_two_buttons_and_a_cord():
    device = _device("p42g20g")
    assert _count(device, "panduit/g5-breaker-20a@1", "front") == 6
    assert _count(device, "panduit/g5-mounting-button@1", "rear") == 2
    assert _count(device, "panduit/g5-cord-60309-3pe-9h@1") == 1


def test_p42g20g_controller_bay_takes_the_g6_controller():
    device = _device("p42g20g")
    bays = device["views"]["front"]["components"]["bays"]
    assert [bay["default"] for bay in bays] == ["panduit/g6-controller@1"]
    assert bays[0]["accepts"] == ["panduit/g6-controller@1"]


def test_g6_controller_draws_the_jacks_its_drawing_labels():
    contract = _contract("g6-controller")
    refs = _refs(contract["parts"])
    assert refs.count("std/rj45@2") == 5
    assert refs.count("std/usb-a@1") == 1
    text = yaml.safe_dump(contract)
    for label in ("Serial", "Ethernet/PDU In", "PDU Out", "Sensor-1", "Sensor-2"):
        assert label in text, f"the contract does not carry the printed label {label!r}"


def test_g6_controller_is_its_own_part():
    contract = _contract("g6-controller")
    assert contract["name"] == "g6-controller"
    assert contract["version"] == "1.0.0"


# ---- P24B32M -------------------------------------------------------------------------

def test_p24b32m_body_is_the_drawn_strip():
    chassis = _device("p24b32m")["chassis"]
    assert chassis["height"] == 915
    assert chassis["depth"] == 112
    assert chassis["weight-kg"] == 9.6
    assert chassis["mount"] == "rack-side"


def test_p24b32m_places_eighteen_c13_and_six_c19():
    device = _device("p24b32m")
    assert _count(device, "std/c13-outlet@1", "front") == 18
    assert _count(device, "std/c19-outlet@1", "front") == 6


def test_p24b32m_breakers_and_ground_are_on_the_rear_and_not_the_front():
    device = _device("p24b32m")
    assert _count(device, "panduit/g5-breaker-20a@1", "rear") == 6
    assert _count(device, "panduit/g5-breaker-20a@1", "front") == 0
    assert _count(device, "common/ground-screw@1", "rear") == 1


def test_p24b32m_has_two_buttons_and_the_60a_cord():
    device = _device("p24b32m")
    assert _count(device, "panduit/g5-mounting-button@1") == 2
    assert _count(device, "panduit/g5-cord-60309-3pe-9h@1") == 1


def test_p24b32m_states_no_metering_and_no_switching():
    management = _device("p24b32m")["attrs"]["management"]
    assert management["metering-scope"] == "none"
    assert management["outlet-switching"] is False


# ---- the shapes the drawings show, counted from their vector paths -------------------

def test_p42g20g_blank_plate_draws_five_hexagon_heads_in_2_1_2_and_one_ring():
    # Sheet 1 front view, at 2.918 mm to the point, the scale of the printed 1780.0.
    # Five hexagon heads, 4.82 along by 5.52 across. Two sit at 816.10, one at 849.58 and two at 918.21 along the face.
    # One ring, 5.87 across, has an inner circle of 4.47.
    decor = _decor(_device("p42g20g"), "front")
    assert not [name for name in decor if name.startswith("blank-plate-screw")], "the six round dots are gone"
    hexes = {name: item for name, item in decor.items() if name.startswith("blank-plate-hex-")}
    assert len(hexes) == 5
    for item in hexes.values():
        assert item["pattern"] == "motif" and item["size"] == [5.52, 4.82]
        assert len(item["pattern-cells"]) == 1 and len(item["pattern-cells"][0]) == 6, "one six-sided cell"
    centres = sorted(_centre(item) for item in hexes.values())
    assert centres == [(8.88, 816.10), (8.88, 918.21), (46.09, 849.58), (47.05, 816.10), (47.05, 918.21)]
    along = sorted(y for _, y in centres)
    assert along == [816.10, 816.10, 849.58, 918.21, 918.21], "a 2, 1, 2 layout along the strip"
    rings = [name for name in decor if name.startswith("blank-plate-ring")]
    assert sorted(rings) == ["blank-plate-ring", "blank-plate-ring-inner"]
    assert decor["blank-plate-ring"]["size"] == [5.87, 5.87]
    assert decor["blank-plate-ring-inner"]["size"] == [4.47, 4.47]
    assert _centre(decor["blank-plate-ring"]) == _centre(decor["blank-plate-ring-inner"]) == (12.82, 941.59)


def test_p24b32m_cord_end_face_draws_two_torx_screws_and_a_rectangle():
    # SIDE VIEW, at 2.039 mm to the point, the scale of the printed 52.0.
    # Two Torx screws, 6.9 across, sit at 6.79 and 44.93 across and 67.75 deep.
    # A rectangle of 19.09 by 19.09 has its corner at 16.34 across and 92.32 deep.
    device = _device("p24b32m")
    decor = _decor(device, "bottom")
    for name in ("end-screw-1", "end-screw-2", "end-screw-torx-1", "end-screw-torx-2", "cord-window"):
        assert name in decor, f"the cord-end face does not draw {name}"
    assert [decor[n]["size"] for n in ("end-screw-1", "end-screw-2")] == [[6.9, 6.9]] * 2
    assert [_centre(decor[n]) for n in ("end-screw-1", "end-screw-2")] == [(6.79, 67.75), (44.93, 67.75)]
    for name in ("end-screw-torx-1", "end-screw-torx-2"):
        assert decor[name]["pattern"] == "motif" and decor[name]["size"] == [3.74, 4.96]
        assert len(decor[name]["pattern-cells"][0]) == 12, "a six-lobed recess has twelve corners"
    assert [_centre(decor[n]) for n in ("end-screw-torx-1", "end-screw-torx-2")] == [(6.79, 67.72), (44.93, 67.72)]
    assert decor["cord-window"]["at"] == [16.34, 92.32] and decor["cord-window"]["size"] == [19.09, 19.09]
    assert "stroke" in decor["cord-window"] and "fill" not in decor["cord-window"], "an outline, as the drawing has it"
    assert "gland alone" not in yaml.safe_dump(device["provenance"]), "no note still says the face is the gland alone"


def test_p24b32m_earth_screw_has_one_slot_along_the_strip():
    # Rear view, at 2.039 mm to the point. A head 12.04 across carries one slot, 7.95 long and 0.98 wide, along the strip.
    device = _device("p24b32m")
    decor = _decor(device, "rear")
    assert "earth-screw-head" in decor and "earth-screw-slot" in decor, "the rear does not draw the slot"
    assert decor["earth-screw-head"]["size"] == [12.04, 12.04]
    assert decor["earth-screw-slot"]["size"] == [1.0, 7.95], "taller than wide: along the strip, which stands upright"
    ground = next(p for p in device["views"]["rear"]["components"]["placements"] if p["id"] == "ground")
    centre = (round(ground["at"][0] + 2.8, 2), round(ground["at"][1] + 2.8, 2))
    assert _centre(decor["earth-screw-head"]) == _centre(decor["earth-screw-slot"]) == centre


@pytest.mark.parametrize("name", ["p42g20g", "p24b32m"])
def test_each_device_names_its_estimates_and_gaps(name):
    device = _device(name)
    assert device["maturity"] == "modelled"
    gap_names = {gap["what"] for gap in device["gaps"]}
    assert {"photographs", "outlet-pitch"} <= gap_names
