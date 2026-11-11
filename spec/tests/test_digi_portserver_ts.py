"""The Digi PortServer TS 1, 2 and 4 serial servers, from Digi's product page, line art and quick start guide.

Three devices of one small desktop box (84.6 x 24.2 x 133.4). What the held sources fix, and so what these tests hold:
  the product page      the port counts, the power, the size, the weight and the three part numbers
  the line art          the position of every jack, lamp, slot and button on the two ends
  the quick start guide that the serial jack is the ten-wire RJ-45
  the photograph        the black body and the legends printed on the top

Nothing here pins a part this change does not add: the tests read the three devices.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/digi"

DEVICES = {"portserver-ts-1": (1, "70002041"), "portserver-ts-2": (2, "70002043"), "portserver-ts-4": (4, "70002045")}


def device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def placements(name, view):
    return (device(name)["views"][view].get("components") or {}).get("placements") or []


def by_id(items):
    return {i["id"]: i for i in items}


@pytest.mark.parametrize("name", DEVICES)
def test_the_chassis_is_the_pages_size(name):
    d = device(name)
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (84.6, 24.2, 133.4)
    assert c["mount"] == "desktop"
    assert d["manufacturer"] == "Digi"
    assert d["views"]["front"]["size"] == d["views"]["rear"]["size"] == {"w": 84.6, "h": 24.2}
    assert d["views"]["top"]["size"] == {"w": 84.6, "h": 133.4}


@pytest.mark.parametrize("name", DEVICES)
def test_every_face_is_there(name):
    views = device(name)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    # the top is drawn from the photograph's legends; the faces no source shows say so rather than stay bare
    assert views["top"].get("silkscreen")
    for face in ("bottom", "left", "right"):
        assert views[face].get("empty"), face


@pytest.mark.parametrize("name,spec", DEVICES.items())
def test_the_serial_jacks_are_the_ten_position_jack_in_one_row(name, spec):
    count, _ = spec
    ports = [p for p in placements(name, "rear") if p["id"].startswith("serial-")]
    assert sorted(p["id"] for p in ports) == [f"serial-{n}" for n in range(1, count + 1)]
    assert {p["ref"] for p in ports} == {"digi/serial-jack-10p@1"}
    assert {p["at"][1] for p in ports} == {2.4}
    xs = sorted(p["at"][0] for p in ports)
    assert xs[0] == 7.4
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [16.0] * (count - 1)


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_end_is_the_line_arts(name):
    p = by_id(placements(name, "front"))
    assert p["eth"]["ref"] == "common/rj45-eth@1" and p["eth"]["attrs"]["speed"] == "100m"
    assert p["dc-in"]["ref"] == "common/dc-barrel@1"
    assert p["btn-reset"]["ref"] == "common/reset-button@1"
    assert sorted(i for i in p if i.startswith("led-")) == ["led-act", "led-link", "led-pwr", "led-ready"]
    # the slot has no document that names it, so it is a cutout and not a port
    decor = {c["id"] for c in device(name)["views"]["front"]["panel"]["decor"]}
    assert "aux-slot" in decor and "aux-slot" not in p


@pytest.mark.parametrize("name,spec", DEVICES.items())
def test_each_part_number_is_in_its_one_device(name, spec):
    _, pn = spec
    cfgs = device(name)["configurations"]
    assert [list(c["part-numbers"]) for c in cfgs.values()] == [[pn]]


@pytest.mark.heavy
def test_one_part_number_is_one_component():
    seen = {}
    for path in (ROOT / "library/devices").glob("*/*/device.yaml"):
        for cfg in (yaml.safe_load(path.read_text()).get("configurations") or {}).values():
            for pn in (cfg.get("part-numbers") or {}):
                if pn in {v[1] for v in DEVICES.values()}:
                    seen.setdefault(pn, set()).add(path.parent.name)
    assert len(seen) == 3
    assert all(len(v) == 1 for v in seen.values()), seen


@pytest.mark.parametrize("name", DEVICES)
def test_the_unit_states_what_the_page_states(name):
    attrs = device(name)["attrs"]
    assert attrs["physical"]["weight-kg"] == 0.189
    assert attrs["power"]["power-typical-w"] == 4 and attrs["power"]["power-max-w"] == 6
    # the page marks the family not recommended for new designs, which is not an announced end of life
    assert "lifecycle" not in attrs
    assert "not recommended for new designs" in device(name)["description"]


@pytest.mark.parametrize("name", DEVICES)
def test_the_estimates_and_disagreements_are_declared(name):
    gaps = {g["what"] for g in device(name)["gaps"]}
    assert {"side-and-bottom-faces", "wall-and-din-mounts", "power-connector-variant",
            "unpopulated-serial-openings", "slot-function"} <= gaps
