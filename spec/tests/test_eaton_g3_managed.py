"""The Eaton ePDU G3 managed EMAU07-10: what is true of its device file.

No build is needed: each test reads the device and its contract from the library folder.
"""
import pathlib

import yaml

LIB = pathlib.Path(__file__).resolve().parents[2] / "library"
DEVICE = yaml.safe_load((LIB / "devices/eaton/emau07-10/device.yaml").read_text())
CORD = yaml.safe_load((LIB / "components/eaton/g3-cord-l6-30p-front/v1/contract.yaml").read_text())


def _placements(view):
    return DEVICE["views"][view]["components"]["placements"]


def test_sixteen_c13_outlets_in_two_sections():
    outlets = [p for p in _placements("front") if p["ref"] == "std/c13-outlet@1"]
    assert len(outlets) == 16
    assert {p["through"] for p in outlets} == {"breaker-a", "breaker-b"}
    assert sum(1 for p in outlets if p["through"] == "breaker-a") == 8


def test_body_is_the_drawings_size():
    chassis = DEVICE["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (444.5, 87.1, 213.2, 2)


def test_every_outlet_is_named_as_printed():
    names = {rule["name"] for rule in DEVICE["interfaces"]}
    assert names == {"A{n}", "B{n}"}


def test_the_cord_part_is_the_round_gland():
    assert CORD["size"] == {"w": 27.2, "h": 39.1}
    assert CORD["attrs"]["plug"] == "nema-l6-30p"


def test_the_module_has_its_ports_and_buttons():
    ids = {p["id"] for p in _placements("front")}
    assert {"serial", "daisy-chain", "network", "usb", "reset", "display"} <= ids
    assert {"button-up", "button-down", "button-esc", "button-enter"} <= ids


def test_each_end_carries_the_four_holes_the_perspective_shows():
    for side in ("left", "right"):
        holes = [d for d in DEVICE["views"][side]["panel"]["decor"] if d["kind"] == "hole"]
        assert len(holes) == 4


def test_sixteen_lamps_two_tiles_of_eight():
    lamps = [p for p in _placements("front") if p["ref"] == "common/led-dot@1"]
    assert len(lamps) == 16
