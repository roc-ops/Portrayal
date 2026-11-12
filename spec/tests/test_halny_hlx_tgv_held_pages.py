"""halny/hlx-tgv carries what its leaflet, its quick installation guide and its
photographs state, and names what they disagree on.

The leaflet (3 pages) and the HALNy HLX-TGV Quick Installation Guide (Rev1.4,
11 pages) are the only vendor documents; eight photographs of the unit are the
rest. The device reads each fact from the page or photograph that gives it.
Only this device's own file is read: nothing here depends on a build.
"""
from pathlib import Path

import pytest
import yaml

DEVICE = Path(__file__).resolve().parents[2] / "library/devices/halny/hlx-tgv/device.yaml"


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def _placement(device, view, pid):
    placements = device["views"][view]["components"]["placements"]
    return next(p for p in placements if p["id"] == pid)


def test_the_weight_is_carried_as_the_guide_prints_it(device):
    note = device["attrs"]["physical"]["weight-note"]
    assert "500 g" in note and "Quick Installation Guide" in note


def test_the_rated_environment_is_the_two_documents_common_figures(device):
    env = device["attrs"]["environmental"]
    assert env["operating-temp"].startswith("0 to 45 C")
    assert env["storage-temp"].startswith("-20 to 70 C")
    # the leaflet says 10 to 95 percent and the guide 10 to 90: neither is carried
    assert "humidity" not in env


def test_the_adapter_input_and_the_memory_are_stated(device):
    power = device["attrs"]["power"]
    assert power["power-input"].startswith("100 to 240 V AC, 50 to 60 Hz")
    platform = device["attrs"]["platform"]
    assert platform["system-memory"] == "256 MB"
    assert platform["onboard-storage"].startswith("128 MB")


def test_the_pon_figures_are_the_leaflets_and_the_guides(device):
    perf = device["attrs"]["performance"]
    assert "9.953 Gbps" in perf["pon-rate"]
    assert "20 km" in perf["pon-reach"]
    assert perf["pon-tx-power"].startswith("4 to 9 dBm")
    assert perf["pon-rx-power"].startswith("-10 to -27 dBm")


def test_the_lan_jack_is_yellow_and_the_10g_jack_black(device):
    lan = _placement(device, "rear", "eth-lan")["attrs"]["finish"]
    ten = _placement(device, "rear", "eth-10g")["attrs"]["finish"]
    assert lan.lower() == "#ccb339"
    assert ten.lower() == "#2b2f33"


def test_the_rear_prints_pon_beside_the_fibre_notch_and_the_underside_does_not(device):
    rear = [s["text"] for s in device["views"]["rear"]["silkscreen"]]
    assert "PON" in rear
    assert "ON/OFF" in rear and "POWER" in rear
    bottom = device["views"]["bottom"].get("silkscreen", [])
    assert not [s for s in bottom if "PON" in s["text"]]


def test_the_right_face_draws_its_two_screws_and_the_left_none(device):
    right = device["views"]["right"]["panel"]["decor"]
    left = device["views"]["left"]["panel"]["decor"]
    # a decor entry with an id or a stroke is drawn as an outline, so the screws carry neither
    named = [d for d in right if d.get("fill") and d.get("size", [0])[0] <= 5]
    screws = [d for d in named if d.get("rx") == 2.5]
    assert len(screws) == 2 and len(named) == 6  # each head has a cross of two slots
    assert not [d for d in left if d.get("fill")]
    for d in named:
        x, y = d["at"]
        w, h = d["size"]
        assert 0 <= x and x + w <= 115 and 0 <= y and y + h <= 40


def test_the_disagreements_are_named_gaps_and_the_leaflet_figures_stay(device):
    gaps = {g["what"]: g for g in device["gaps"]}
    for name in ("dimensions-disagree", "dc-in-current-disagrees",
                 "humidity-disagrees", "left-face-unphotographed",
                 "right-face-vents"):
        assert name in gaps, name
        assert gaps[name]["note"]
    assert device["chassis"]["width"] == 172.0
    assert device["chassis"]["depth"] == 115.0
    assert device["chassis"]["height"] == 40.0
    dc = _placement(device, "rear", "dc-in")["attrs"]
    assert dc["input-voltage"] == "12 VDC" and dc["current-max-a"] == 1.0
    assert "112mm" in gaps["dimensions-disagree"]["note"]
    current = gaps["dc-in-current-disagrees"]["note"]
    assert "1.0A" in current and "1.5A" in current and "2A" in current
