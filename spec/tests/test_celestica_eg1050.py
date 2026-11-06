"""The Celestica EG1050-48CP gateway is drawn from its hardware guide and datasheet.

Read-only checks of the device file: the folder and its lock exist, the port counts and speeds are
the guide's (32 x 1GbE, 16 x 2.5GbE, 4 x SFP28, the management pair, the console, two USB-A), the
PoE class is the one the guide prints for every data port, the six antenna connectors the guide
lists exist as placements with their part numbers declared, the supplies are the shared CRPS 1600 W
component and nothing the guide leaves out is stated as known.
"""
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
FOLDER = LIB / "devices/celestica/eg1050-48cp"
DEVICE = FOLDER / "device.yaml"


@pytest.fixture(scope="module")
def dev():
    assert DEVICE.is_file(), f"{DEVICE.relative_to(LIB.parent)} does not exist"
    return yaml.safe_load(DEVICE.read_text())


def _placements(dev, view):
    return dev["views"][view]["components"].get("placements", [])


def _by_group(dev, view, group):
    return [p for p in _placements(dev, view) if p.get("group") == group]


def test_folder_has_device_and_lock():
    assert DEVICE.is_file(), "device.yaml is missing"
    assert (FOLDER / "device.lock.json").is_file(), "device.lock.json is missing"


def test_identity_and_chassis(dev):
    assert dev["manufacturer"] == "Celestica" and dev["model"] == "EG1050-48CP"
    ch = dev["chassis"]
    assert (ch["width"], ch["height"], ch["depth"], ch["ru"]) == (438.2, 43.4, 371.6, 1)


def test_data_port_counts_and_speeds(dev):
    groups = dev["groups"]
    two5 = _by_group(dev, "front", "rj45-2p5g")
    one = _by_group(dev, "front", "rj45-1g")
    assert groups["rj45-2p5g"]["attrs"]["speed"] == "2.5g" and len(two5) == 16
    assert groups["rj45-1g"]["attrs"]["speed"] == "1g" and len(one) == 32
    ids = sorted(int(p["id"].split("-")[1]) for p in two5 + one)
    assert ids == list(range(1, 49))
    assert sorted(int(p["id"].split("-")[1]) for p in two5) == list(range(1, 17))
    sfp28 = _by_group(dev, "front", "sfp28")
    assert len(sfp28) == 4 and groups["sfp28"]["attrs"]["speed"] == "25g"


def test_poe_class_on_every_data_port(dev):
    for g in ("rj45-2p5g", "rj45-1g"):
        poe = dev["groups"][g]["attrs"]["poe"]
        assert "802.3bt" in poe and "Type 4" in poe and "Class 8" in poe and "90 W" in poe, poe


def test_management_console_and_usb(dev):
    ids = {p["id"] for p in _placements(dev, "front")}
    assert {"mgmt", "mgmt-sfp", "console", "usb-1", "usb-2"} <= ids
    assert [p for p in _placements(dev, "front") if p["id"] == "console"][0]["ref"] == "std/rj45-ganged@2"


def test_antenna_connectors(dev):
    wifi = _by_group(dev, "front", "wifi-antenna")
    cell = _by_group(dev, "front", "cellular-antenna")
    assert len(wifi) == 2 and len(cell) == 4
    for p in wifi + cell:
        assert p["ref"] == "std/sma@1"
    gaps = {g["what"]: g for g in dev["gaps"]}
    note = " ".join(str(g.get("wanted", "")) for g in dev["gaps"])
    assert "Y0RGK0MA0AA" in note and "YECN009AA" in note, "the guide's antenna part numbers are not recorded"
    assert "antenna-connector-positions" in gaps


def test_supplies_are_the_shared_crps_1600(dev):
    bays = dev["views"]["rear"]["components"]["bays"]
    assert [b["id"] for b in bays] == ["psu-1", "psu-2"]
    for b in bays:
        assert b["accepts"] == ["celestica/psu-crps-1600-ac@1"]
        assert b["default"] == "celestica/psu-crps-1600-ac@1"
        ref = b["default"].split("@")[0]
        assert (LIB / "components" / ref / "v1/contract.yaml").is_file()
    cfgs = dev["configurations"]
    parts = {k: list(v["part-numbers"]) for k, v in cfgs.items()}
    assert sorted(sum(parts.values(), [])) == ["R4048-F90F4-A1", "R4048-F91F4-A1"]
    assert {v["airflow"] for v in cfgs.values()} == {"front-to-back", "back-to-front"}


def test_every_figure_not_printed_is_a_gap(dev):
    gaps = {g["what"] for g in dev["gaps"]}
    assert {"antenna-connector-positions", "antennas"} <= gaps
    assert dev["maturity"] in ("draft", "modelled")


FACES = ("front", "rear", "top", "bottom", "left", "right")


def test_all_six_faces_are_present_and_drawn_or_declared_empty(dev):
    views = dev["views"]
    assert [f for f in FACES if f not in views] == []
    for f in FACES:
        v = views[f]
        drawn = any(
            v.get(k)
            for k in ("components", "regions")
        ) or any((v.get("panel") or {}).get(k) for k in ("decor", "cutouts")) or v.get("silkscreen")
        assert drawn or str(v.get("empty") or "").strip(), f"{f} is neither drawn nor declared empty"


def test_the_six_faces_describe_the_chassis_box(dev):
    ch = dev["chassis"]
    sizes = {f: (dev["views"][f]["size"]["w"], dev["views"][f]["size"]["h"]) for f in FACES}
    for f in ("front", "rear"):
        assert sizes[f] == (ch["width"], ch["height"])
    for f in ("left", "right"):
        assert sizes[f] == (ch["depth"], ch["height"])
    for f in ("top", "bottom"):
        assert sizes[f] == (ch["width"], ch["depth"])


def test_the_device_is_addressable():
    import sys
    sys.path.insert(0, str(SPEC / "tools"))
    from portrayal import capability as C

    data = yaml.safe_load(DEVICE.read_text())
    cap, _ = C.assess(data, profiles=C.load_profiles(SPEC / "schemas"))
    assert cap["level"] == 4, cap.get("blocked")
