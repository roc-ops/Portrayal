"""Eaton Tripp Lite series SmartRack SRCABLEDUCTVRT, the vertical finger duct (roc-ops/Portrayal#1094).

The figures are those the maker's submittal drawing dimensions on its views, in inches as printed and
converted here: 1.91 x 33.96 in for the plate, 2.47 in from the plate to the cover and 2.83 in over the
button, with the buttons 24.49 in apart. The specification sheet's 2.04 x 4.06 in and the drawing's own
millimetre row match no view and are not used. The slot count is read off the side view and the first
hole, the hole size and the sheet are estimates, so they are not pinned here.

The device and component files are read as they are; the one test of a compiled face reads the build
and fails by naming the missing file when there is none.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
MM = 25.4
NAME = "srcableductvrt"
PARTS = ("base", "fingers", "cover", "cover-end", "cover-side")


def device():
    return yaml.safe_load((LIB / "devices" / "eaton" / NAME / "device.yaml").read_text())


def contract(part):
    return yaml.safe_load((LIB / "components/eaton" / f"tripplite-duct-vrt-{part}" / "v1/contract.yaml").read_text())


def placements(view):
    return device()["views"][view].get("components", {}).get("placements", [])


def decor(view):
    return device()["views"][view].get("panel", {}).get("decor", [])


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def test_the_duct_is_the_size_the_drawing_dimensions():
    c = device()["chassis"]
    assert close(c["width"], 1.91 * MM, 0.1)
    assert close(c["height"], 33.96 * MM, 0.1)
    assert close(c["depth"], 2.83 * MM, 0.1)
    assert (c["mount"], c["shell"]) == ("rack-side", "sheet")
    assert c["ru"] * 44.45 >= c["height"] > (c["ru"] - 1) * 44.45
    assert close(c["weight-kg"], 4 * 0.4536, 0.05)


def test_it_is_one_device_of_one_part_number():
    d = device()
    assert (d["manufacturer"], d["model"], d["maturity"]) == ("Eaton", "SRCABLEDUCTVRT", "modelled")
    assert list(d["configurations"]["base"]["part-numbers"]) == ["SRCABLEDUCTVRT"]
    assert d["configurations"]["cover-off"]["kind"] == "example"


def test_it_draws_every_one_of_its_six_faces():
    v = device()["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    c = device()["chassis"]
    for face in ("front", "rear"):
        assert (v[face]["size"]["w"], v[face]["size"]["h"]) == (c["width"], c["height"])
    for face in ("left", "right"):
        assert (v[face]["size"]["w"], v[face]["size"]["h"]) == (c["depth"], c["height"])
    for face in ("top", "bottom"):
        assert (v[face]["size"]["w"], v[face]["size"]["h"]) == (c["width"], c["depth"])


def test_the_duct_guide_runs_down_the_channel_at_the_dimensioned_pitch():
    (g,) = device()["views"]["front"]["guides"]
    assert (g["kind"], g["run"]) == ("duct", "y")
    assert close(g["finger-pitch"], 0.71 * MM, 0.05)
    assert close(g["size"][1], 33.96 * MM, 0.1)
    assert close(g["size"][0], 40.0 - 2 * 1.1, 0.1)


@pytest.mark.parametrize("face", ["left", "right"])
def test_each_side_face_draws_the_same_row_of_slots_at_the_dimensioned_pitch(face):
    slots = [d for d in decor(face) if d.get("kind") == "finger-gap"]
    assert len(slots) == 48
    ys = [d["at"][1] for d in slots]
    assert all(close(b - a, 18.0, 0.02) for a, b in zip(ys, ys[1:]))
    assert all(close(d["size"][0], 1.77 * MM, 0.05) for d in slots)


def test_the_two_buttons_are_the_pdu_button_and_sit_where_the_rear_view_puts_them():
    btn = [p for p in placements("rear") if p["ref"] == "eaton/tripplite-mounting-button@1"]
    assert len(btn) == 2
    size = contract_of_button()["size"]
    centres = [p["at"][1] + size["h"] / 2 for p in btn]
    assert close(centres[0], 4.86 * MM, 0.1)
    assert close(centres[1] - centres[0], 24.49 * MM, 0.1)
    assert close(device()["chassis"]["height"] - centres[1], 4.61 * MM, 0.1)
    for p in btn:
        assert close(p["at"][0] + size["w"] / 2, device()["chassis"]["width"] / 2, 0.02)


def contract_of_button():
    return yaml.safe_load((LIB / "components/eaton/tripplite-mounting-button/v1/contract.yaml").read_text())


def test_the_button_is_reused_not_twinned():
    assert contract_of_button()["mates"] == "pdu-button"
    assert not [p for p in PARTS if "button" in p]
    assert not list((LIB / "components/eaton").glob("tripplite-duct-vrt-*button*"))


def test_the_holes_down_the_rear_plate_are_the_dimensioned_200_mm_apart():
    holes = sorted(d["at"][1] for d in decor("rear") if d.get("kind") == "hole")
    assert len(holes) == 5
    assert all(close(b - a, 200.0, 0.02) for a, b in zip(holes, holes[1:]))


def test_the_cover_is_a_lid_that_the_base_configuration_ships_fitted():
    assert contract("cover")["lid"] is True
    for view in ("front", "top", "bottom", "left", "right"):
        covers = [p for p in placements(view) if "cover" in p["ref"]]
        assert covers and all(p["only-in"] == ["base"] for p in covers), view


def test_every_part_has_a_contract_and_a_skin_and_none_is_a_twin_of_a_1u_part():
    for part in PARTS:
        d = LIB / "components/eaton" / f"tripplite-duct-vrt-{part}" / "v1"
        assert (d / "contract.yaml").is_file() and (d / "skins/default.svg").is_file(), part
        assert contract(part)["version"] == "1.0.0"
    assert contract("fingers")["size"]["h"] > 800 > contract("cover-side")["size"]["w"]


def test_the_cable_capacity_is_a_named_gap_and_no_figure_is_recorded():
    d = device()
    assert "cable-capacity" in [g["what"] for g in d["gaps"]]
    assert "cable-capacity" not in d["attrs"].get("performance", {})


@pytest.mark.parametrize("config", ["base", "cover-off"])
def test_the_compiled_left_face_has_all_its_slots(config):
    path = DIST / f"{NAME}.{config}.left.svg"
    assert path.is_file(), f"{path} is missing - run build.sh"
    root = ET.parse(path).getroot()
    assert sum(1 for e in root.iter() if e.get("data-kind") == "finger-gap") == 48
