"""The Enlogic EN2951 and EN6952 Advantage Series PDUs and the parts they bring.

What is true of the library: each device places the 42 combination outlets its data sheet counts, in six breakered
banks (four-column groups J1 to J3, three-column groups J4 to J6), states one fixed input cord and the network
module's ports, declares what no document gives, and the new parts say where their figures come from.
Reads the contracts and the device sources; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

DEVICES = {
    "en2951": dict(length=1826, cord="enlogic/pdu-cord-cs8365@1", plug="cs8365c", scope="branch", button=129.7),
    "en6952": dict(length=1780, cord="enlogic/pdu-cord-60309-3pe-9h@1", plug="other",
                   scope="outlet", button=40.5),
}
UPPER = "enlogic/combo-outlet-c13-c15@1"
LOWER = "enlogic/combo-outlet-c13-c15-c19@1"
BREAKER = "enlogic/en-breaker-20a-2p@1"


def _contract(part):
    return yaml.safe_load((LIB / "components" / "enlogic" / part / "v1" / "contract.yaml").read_text())


def _device(slug):
    return yaml.safe_load((LIB / "devices" / "enlogic" / slug / "device.yaml").read_text())


def _placements(slug, view):
    return _device(slug)["views"][view]["components"]["placements"]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_chassis_is_the_drawn_strip(slug):
    device = _device(slug)
    chassis = device["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (56, DEVICES[slug]["length"], 75)
    assert chassis["mount"] == "rack-side"
    assert device["manufacturer"] == "Enlogic" and device["model"] == slug.upper()
    assert set(device["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("slug", DEVICES)
def test_the_outlets_are_the_ones_the_data_sheet_counts(slug):
    outlets = [p for p in _placements(slug, "front") if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == {UPPER: 21, LOWER: 21}
    assert all(p["states"] == ["on", "off"] for p in outlets)


@pytest.mark.parametrize("slug", DEVICES)
def test_each_bank_is_behind_its_own_breaker(slug):
    placed = _placements(slug, "front")
    outlets = [p for p in placed if p["id"].startswith("outlet-")]
    breakers = {p["id"]: p for p in placed if p["ref"] == BREAKER}
    assert sorted(breakers) == [f"breaker-b{n}" for n in range(1, 7)]
    for n, size in ((1, 8), (2, 8), (3, 8), (4, 6), (5, 6), (6, 6)):
        bank = [p for p in outlets if p["group"] == f"outlets-b{n}"]
        assert len(bank) == size
        assert Counter(p["ref"] for p in bank) == {UPPER: size // 2, LOWER: size // 2}
        assert all(p["through"] == f"breaker-b{n}" and p["fed-by"] == "input" for p in bank)
        assert breakers[f"breaker-b{n}"]["attrs"]["bank"] == f"B{n}"
    assert [breakers[f"breaker-b{n}"]["lines"] for n in (1, 2, 3)] == [["L1", "L2"], ["L2", "L3"], ["L3", "L1"]]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_outlets_stay_on_the_strip_and_clear_of_each_other(slug):
    length = DEVICES[slug]["length"]
    sizes = {UPPER: (22.8, 34.4), LOWER: (22.1, 34.4)}
    boxes = []
    for p in _placements(slug, "front"):
        if p["id"].startswith("outlet-"):
            w, h = sizes[p["ref"]]
            x, y = p["at"]
            assert 0 <= x and x + w <= 56 and 0 <= y and y + h <= length
            boxes.append((x, y, x + w, y + h))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] + 0.01 or b[2] <= a[0] + 0.01 or a[3] <= b[1] + 0.01 or b[3] <= a[1] + 0.01


@pytest.mark.parametrize("slug", DEVICES)
def test_the_cord_is_the_one_input(slug):
    want = DEVICES[slug]
    inputs = [p for p in _placements(slug, "top") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == [want["cord"]]
    power = _device(slug)["attrs"]["power"]
    assert power["input-cord"] == "fixed" and power["input-plug"] == want["plug"]
    assert power["input-phase"] == "three" and power["input-wiring"] == "delta"
    management = _device(slug)["attrs"]["management"]
    assert management == {"metering-scope": want["scope"], "outlet-switching": True}


@pytest.mark.parametrize("slug", DEVICES)
def test_the_network_module_places_its_ports(slug):
    placed = {p["id"]: p for p in _placements(slug, "front")}
    assert placed["network-1"]["ref"] == placed["network-2"]["ref"] == "common/rj45-eth@1"
    assert placed["network-1"]["attrs"]["speed"] == "1g" and placed["network-2"]["attrs"]["speed"] == "100m"
    assert placed["usb-c"]["ref"] == "std/usb-c@1"
    sensors = [d for d in _device(slug)["views"]["front"]["panel"]["decor"] if d["id"].startswith("sensor-")]
    assert len(sensors) == 2


@pytest.mark.parametrize("slug", DEVICES)
def test_the_two_buttons_are_the_dimensioned_span_apart(slug):
    buttons = [p for p in _placements(slug, "rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - 1555.0) < 0.1
    assert abs(buttons[0]["at"][1] + 9.2 - DEVICES[slug]["button"]) < 0.1


@pytest.mark.parametrize("slug", DEVICES)
def test_the_device_says_what_it_does_not_know(slug):
    device = _device(slug)
    assert "weight-kg" not in device["attrs"]["physical"]
    gaps = {g["what"] for g in device["gaps"]}
    assert {"weight", "colour", "module-ports", "sensor-count", "input-plug", "ends"} <= gaps
    for side in ("bottom", "left", "right"):
        assert device["views"][side]["empty"]


def test_the_combination_outlets_say_what_they_take():
    upper, lower = _contract("combo-outlet-c13-c15"), _contract("combo-outlet-c13-c15-c19")
    assert (upper["interface"], lower["interface"]) == ("iec-c13", "enlogic-combo")
    assert upper["attrs"]["rating-a"] == 10 and lower["attrs"]["rating-a"] == 16
    for contract in (upper, lower):
        assert "estimated" in contract["size-confidence"].values() or contract["size-confidence"]["d"] == "estimated"
        assert "ESTIMATED" in contract["provenance"]["face"]


def test_the_breaker_says_where_its_figures_come_from():
    contract = _contract("en-breaker-20a-2p")
    assert contract["class"] == "breaker" and contract["attrs"]["poles"] == 2
    assert {"bank-color", "ink", "bank", "lines"} <= set(contract["fields"])
    assert "WHITE" in contract["provenance"]["colour"]


def test_the_cords_say_what_no_source_dimensions():
    for part in ("pdu-cord-cs8365", "pdu-cord-60309-3pe-9h"):
        cord = _contract(part)
        assert cord["size-confidence"] == {"w": "estimated", "h": "estimated"}
        assert "ESTIMATED" in cord["provenance"]["size"]
    assert "TWO WAYS" in _contract("pdu-cord-cs8365")["provenance"]["plug"]
