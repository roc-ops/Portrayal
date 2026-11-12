"""What the B097-016's two larger photographs show on its faces.

The Eaton Tripp Lite series B097-016 was first drawn from two 500 pixel photographs. The maker's page also
loads two 1000 pixel ones, the rear straight on and the front at an angle, which show the rocker switch above
each inlet, the number printed over and under each serial jack, the four lamp legends, the erase pinhole and
its label, and the maker's mark and model line. Every position is still read off a photograph and estimated.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/eaton/b097-016/device.yaml"
ROCKER = "eaton/b097-power-rocker"


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def of(d, view, part):
    return [p for p in placements(d, view) if p["ref"].split("@")[0] == part]


def legends(d, view):
    return [s for s in d["views"][view].get("silkscreen") or [] if "text" in s]


def serial(d):
    return sorted((p for p in placements(d, "rear") if p.get("group") == "serial"),
                  key=lambda p: p["rel-pos"])


def test_each_inlet_has_a_rocker_switch_above_it(device):
    inlets = {p["id"]: p for p in of(device, "rear", "std/c14-inlet")}
    switches = of(device, "rear", ROCKER)
    assert len(inlets) == 2 and len(switches) == 2
    assert sorted(p["for"] for p in switches) == sorted(inlets)
    for s in switches:
        inlet = inlets[s["for"]]
        assert s["at"][1] + 5.6 <= 11.75
        assert abs((s["at"][0] + 8.25) - (inlet["at"][0] + 14.0)) < 2.0
    assert {p["group"] for p in switches} == {"switches"}
    assert device["groups"]["switches"]["term"] == "Switch"


def test_the_rocker_is_the_part_the_larger_sibling_draws_not_a_second_one(device):
    refs = {p["ref"] for p in of(device, "rear", ROCKER)}
    assert refs == {f"{ROCKER}@1"}
    cutouts = {c["id"] for c in device["views"]["rear"]["panel"]["cutouts"] if "id" in c}
    assert {p["id"] for p in of(device, "rear", ROCKER)} <= cutouts


def test_the_serial_jacks_are_numbered_odd_above_and_even_below(device):
    marks = [s for s in legends(device, "rear") if s["text"].isdigit()]
    assert sorted(int(s["text"]) for s in marks) == list(range(1, 17))
    ports = serial(device)
    top = min(p["at"][1] for p in ports)
    bottom = max(p["at"][1] for p in ports)
    for s in marks:
        n = int(s["text"])
        assert (s["at"][1] < top) if n % 2 else (s["at"][1] > bottom)
    columns = {p["rel-pos"]: p["at"][0] for p in ports}
    for s in marks:
        n = int(s["text"])
        assert abs(s["at"][0] - columns[n]) < 8.0


def test_the_four_lamps_carry_the_legends_the_photograph_prints(device):
    leds = sorted(of(device, "front", "common/led-dot"), key=lambda p: p["rel-pos"])
    assert len(leds) == 4
    by_led = {s["for"]: s for s in legends(device, "front") if str(s.get("for", "")).startswith("led-")}
    assert [by_led[p["id"]]["text"] for p in leds] == ["PWR", "H/B", "SER", "NET"]
    for p in leds:
        assert abs(by_led[p["id"]]["at"][0] - p["at"][0]) < 3.0
        assert by_led[p["id"]]["at"][1] < p["at"][1]


def test_the_erase_pinhole_stands_right_of_the_console_jack_under_its_label(device):
    holes = of(device, "front", "common/reset-button")
    assert [h["id"] for h in holes] == ["erase"]
    console = [p for p in placements(device, "front") if p["id"] == "console"][0]
    assert holes[0]["at"][0] > console["at"][0] and holes[0]["group"] == "controls"
    label = [s for s in legends(device, "front") if s["text"] == "ERASE"]
    assert len(label) == 1 and label[0]["for"] == "erase"
    assert label[0]["at"][1] < holes[0]["at"][1] + 2.0


def test_the_front_carries_the_makers_mark_and_the_model_line(device):
    texts = {s["text"] for s in legends(device, "front")}
    assert {"EATON", "TRIPP LITE", "SERIES", "Model: B097-016"} <= texts
    assert not [r for r in device["views"]["front"].get("regions") or [] if "not drawn" in r.get("label", "")]


def test_what_is_now_drawn_is_no_longer_a_gap_and_what_is_not_stays_one(device):
    gaps = {g["what"]: g for g in device["gaps"]}
    assert "jack-numbering" not in gaps
    assert "not legible" not in gaps["lamps"]["note"]
    assert {"ear-positions", "sides-top-bottom", "photo-skew"} <= set(gaps)
    assert gaps["photo-skew"]["scope"] == ["rear"]


def test_no_document_held_for_this_model_names_the_inlet_type_so_it_is_declared_from_the_photograph(device):
    gap = {g["what"]: g for g in device["gaps"]}["inlet-type"]
    assert gap["reason"] == "vendor-silent" and "rear" in gap["scope"]
    for words in ("owner's manual", "IEC", "specifications page", "photograph"):
        assert words in gap["note"]
    prov = device["provenance"]["inlet"]
    assert prov["confidence"] == "estimated" and "photograph" in prov["note"]
    assert "owner's manual)" not in device["attrs"]["power"]["power-input"]
