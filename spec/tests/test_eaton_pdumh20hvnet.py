"""The Eaton Tripp Lite series switched PDU PDUMH20HVNET.

What is true of the 1U horizontal unit. Its size follows the rear photograph's proportion.
Its eight C13 outlets stand on one pitch and each has a lamp drawn off. Its input is a C20
inlet for a detachable cord. Its front carries the network card, the meter and no ear: the ears are
separate brackets. Its rear carries the ground screw and the factory port and no outlet. Read from
the real library, no build.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/eaton/pdumh20hvnet/device.yaml"
EXPORTS = ROOT / "library/exports"
FACES = ["front", "rear", "top", "bottom", "left", "right"]
MM_PER_IN = 25.4


def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(face):
    return device()["views"][face].get("components", {}).get("placements", [])


def outlets():
    return [p for p in placements("front") if p["id"].startswith("outlet-")]


def test_every_face_is_drawn_or_says_why_it_is_not():
    views = device()["views"]
    assert sorted(views) == sorted(FACES)
    for face in FACES:
        view = views[face]
        drawn = view.get("panel") or view.get("components")
        assert drawn or view.get("empty"), f"{face}: neither drawn nor an `empty` sentence"


def test_the_body_follows_the_rear_photographs_proportion():
    chassis = device()["chassis"]
    assert (chassis["height"], chassis["ru"]) == (43.7, 1)
    assert round(17.33 * MM_PER_IN, 1) == chassis["width"] == 440.2
    assert round(14.77 * MM_PER_IN, 1) == chassis["depth"] == 375.2
    # the photograph's face is 838 by 82 px; the width over the height must read about 10.2
    assert abs(chassis["width"] / chassis["height"] - 838 / 82) < 0.2


def test_eight_c13_outlets_numbered_eight_to_one_left_to_right_on_one_pitch():
    rows = sorted(outlets(), key=lambda p: p["at"][0])
    assert [p["id"] for p in rows] == [f"outlet-{n}" for n in range(8, 0, -1)]
    assert {p["ref"] for p in rows} == {"std/c13-outlet@1"}
    assert all(p["fed-by"] == "input" and p["states"] == ["on", "off"] for p in rows)
    steps = {round(b["at"][0] - a["at"][0], 2) for a, b in zip(rows, rows[1:])}
    assert steps == {35.65}
    assert not [p for p in placements("rear") if p["id"].startswith("outlet-")], "the rear has no outlet"


def test_each_outlet_has_a_lamp_drawn_off():
    dev = device()
    lamps = [p for p in placements("front") if p["id"].startswith("led-")]
    assert sorted(p["for"] for p in lamps) == sorted(p["id"] for p in outlets())
    group = dev["groups"]["outlet-leds"]
    assert group["states"] == ["on", "off"]
    drawn = dev["views"]["front"]["panel"]["decor"]
    assert not [d for d in drawn if d.get("kind") == "led"], "a lit lamp is never decor"


def test_the_input_is_a_detachable_c20_inlet():
    dev = device()
    inlet = [p for p in placements("front") if p["id"] == "input"][0]
    assert inlet["ref"] == "std/c20-inlet@1"
    assert dev["attrs"]["power"]["input-plug"] == "iec-60320-c20"
    assert dev["attrs"]["power"]["input-cord"] == "detachable"


def test_the_front_is_the_body_wide_with_the_card_the_meter_and_no_ear():
    dev = device()
    assert dev["views"]["front"]["size"]["w"] == dev["chassis"]["width"] == 440.2
    bays = dev["views"]["front"]["components"]["bays"]
    assert [(b["id"], b["default"]) for b in bays] == [("card", "eaton/webcardlx@1")]
    assert "eaton/tripplite-ammeter@1" in {p["ref"] for p in placements("front")}
    decor = {d["id"] for d in dev["views"]["front"]["panel"]["decor"]}
    assert not [i for i in decor if i.startswith("ear-")], "the ears are separate brackets, drawn by the generic ear"
    assert any(g["what"] == "ear-holes" for g in dev["gaps"])


def test_the_rear_carries_the_ground_screw_and_the_factory_port():
    refs = {p["id"]: p["ref"] for p in placements("rear")}
    assert refs == {"ground": "common/ground-screw-washer@1", "config-port": "common/db9-receptacle@1"}


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_device_type_exports_eight_c13_outlets_and_the_c20_input(target):
    path = EXPORTS / target / "device-types/Eaton/PDUMH20HVNET.yaml"
    doc = yaml.safe_load(path.read_text())
    assert [(o["name"], o["type"]) for o in doc["power-outlets"]] == [(str(n), "iec-60320-c13") for n in range(1, 9)]
    assert [p["type"] for p in doc["power-ports"]] == ["iec-60320-c20"]
