"""Cisco Catalyst 1300, first batch: the C1300-24P-4G and the C1300-24T-4G.

Both come from Cisco's "Cisco Catalyst 1300 and 1300X Series Switches" data sheet (document 3659554-09)
and from NetBox's community elevations (the 24P's front, the 24T's front and rear). No held document
shows a 48-port -4G face, so those two models are not in the library.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
NAMES = ["c1300-24p-4g", "c1300-24t-4g"]
MODELS = {"c1300-24p-4g": "C1300-24P-4G", "c1300-24t-4g": "C1300-24T-4G"}
# data sheet p30-32: depth and weight per model; width 444.3 and height 43.94 for both
DEPTH = {"c1300-24p-4g": 299.0, "c1300-24t-4g": 240.0}
WEIGHT = {"c1300-24p-4g": 3.53, "c1300-24t-4g": 2.63}
MTBF = {"c1300-24p-4g": "396,413 at 25 C", "c1300-24t-4g": "664,987 at 25 C"}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_cisco_prints_it(name):
    d = load(name)
    assert d["name"] == name
    assert d["manufacturer"] == "Cisco"
    assert d["model"] == MODELS[name]
    assert d["portfolio"] == {"line": "Catalyst", "family": "Catalyst 1300"}
    assert d["version"] == "1.0.0"


@pytest.mark.parametrize("name", NAMES)
def test_envelope_matches_the_data_sheet(name):
    d = load(name)
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.3, 43.94, DEPTH[name], 1)
    assert c["weight-kg"] == WEIGHT[name]
    assert d["views"]["front"]["size"] == {"w": 444.3, "h": 43.94}
    assert d["views"]["rear"]["size"] == {"w": 444.3, "h": 43.94}
    assert d["views"]["top"]["size"] == {"w": 444.3, "h": DEPTH[name]}
    assert d["views"]["right"]["size"] == {"w": DEPTH[name], "h": 43.94}


@pytest.mark.parametrize("name", NAMES)
def test_ears_ship_in_the_box_with_no_position_figure(name):
    c = load(name)["chassis"]
    assert c["ears"]["positions"] == [{"name": "flush", "default": True}]
    assert "kits" not in c
    assert not [p for p in placements(load(name), "front") if p["ref"].startswith("common/rack-ear")]
    gaps = {g["what"] for g in load(name)["gaps"]}
    assert "ears" in gaps


@pytest.mark.parametrize("name", NAMES)
def test_twenty_four_gigabit_ports_numbered_down_the_columns(name):
    d = load(name)
    jacks = {p["id"]: p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth-plain@1"}
    assert sorted(p["rel-pos"] for p in jacks.values()) == list(range(1, 25))
    assert set(jacks) == {f"port-{n}" for n in range(1, 25)}
    # the upper jack of a column takes the odd number and is turned (key up); the lower is not
    for n in range(1, 25, 2):
        upper, lower = jacks[f"port-{n}"], jacks[f"port-{n + 1}"]
        assert upper["at"][1] < lower["at"][1]
        assert upper["at"][0] == lower["at"][0]
        assert upper["rotate"] == 180 and "rotate" not in lower
    xs = sorted({jacks[f"port-{n}"]["at"][0] for n in range(1, 25, 2)})
    assert len(xs) == 12
    assert xs[1] - xs[0] == pytest.approx(13.97, abs=0.01)
    # two blocks of six columns
    assert xs[6] - xs[5] == pytest.approx(13.97 + 20.28, abs=0.01)
    # one arrow lamp per port, up for the upper jack and down for the lower
    lamps = {p["for"]: p for p in placements(d, "front") if p["id"].startswith("led-port-") and p["for"] in jacks}
    assert set(lamps) == set(jacks)
    assert all(lamps[f"port-{n}"]["skin"] == "up" for n in range(1, 25, 2))
    assert all(lamps[f"port-{n}"]["skin"] == "down" for n in range(2, 25, 2))


@pytest.mark.parametrize("name", NAMES)
def test_four_sfp_cages_numbered_25_to_28_and_only_the_end_numerals_printed(name):
    d = load(name)
    cages = [p for p in placements(d, "front") if p["ref"] == "std/sfp@1"]
    assert [p["id"] for p in cages] == ["port-25", "port-26", "port-27", "port-28"]
    assert [p["rel-pos"] for p in cages] == [25, 26, 27, 28]
    assert d["groups"]["sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    xs = [p["at"][0] for p in cages]
    assert xs[1] - xs[0] == pytest.approx(19.0, abs=0.01)
    # only the first and last numeral of each run is printed
    printed = {s["text"]: s["for"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert printed == {"1": "port-1", "12": "port-12", "13": "port-13", "24": "port-24",
                       "25": "port-25", "28": "port-28"}


@pytest.mark.parametrize("name", NAMES)
def test_console_is_rj45_plus_usb_c_and_the_reset_button_is_placed(name):
    d = load(name)
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert by_id["console"]["ref"] == "std/rj45-ganged@2"
    assert by_id["console"]["attrs"] == {"media": "rj45-serial", "role": "console"}
    assert by_id["usb-c"]["ref"] == "std/usb-c@1"
    assert by_id["usb-c"]["attrs"] == {"role": "console", "media": "usb-c"}
    assert by_id["btn-reset"]["ref"] == "common/reset-button@1"
    assert by_id["btn-reset"]["attrs"] == {"function": "reset"}
    # the Type-A port is in the elevation and not in the data sheet: a USB port, never a console
    assert by_id["usb"]["ref"] == "std/usb-a@1"
    assert "role" not in by_id["usb"]["attrs"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["usb-type-a"]["reason"] == "sources-disagree"


@pytest.mark.parametrize("name", NAMES)
def test_no_fan_and_no_bay_because_both_models_are_fanless(name):
    d = load(name)
    assert d["attrs"]["thermal"]["cooling"] == "fanless"
    for view in ("front", "rear"):
        assert not (d["views"][view].get("components") or {}).get("bays")
    assert "fan-redundancy" not in json.dumps(d["attrs"])
    assert d["provenance"]["built-in-power-and-fans"]["confidence"] == "datasheet"


def test_the_24t_rear_places_the_inlet_with_its_rating_and_the_24p_rear_is_empty():
    t = load("c1300-24t-4g")
    inlet = [p for p in placements(t, "rear") if p["ref"] == "std/c14-inlet@1"]
    assert [p["id"] for p in inlet] == ["ac-inlet"]
    legend = [s["text"] for s in t["views"]["rear"]["silkscreen"]]
    assert legend == ["AC INPUT RATING:", "100-240V~", "700mA, 50-60Hz"]
    p = load("c1300-24p-4g")
    assert "empty" in p["views"]["rear"] and not placements(p, "rear")
    assert "rear-face" in {g["what"] for g in p["gaps"]}
    assert p["provenance"]["rear-layout"]["confidence"] == "estimated"


def test_the_attrs_are_each_models_own_row():
    p, t = load("c1300-24p-4g"), load("c1300-24t-4g")
    assert p["attrs"]["power"]["poe-budget-w"] == 195
    assert "poe-budget-w" not in t["attrs"]["power"]
    assert (p["attrs"]["power"]["power-max-w"], t["attrs"]["power"]["power-max-w"]) == (233.2, 14.8)
    assert (p["attrs"]["power"]["heat-dissipation-btu-hr"], t["attrs"]["power"]["heat-dissipation-btu-hr"]) == (795.2, 50.5)
    for name in NAMES:
        assert load(name)["attrs"]["environmental"]["mtbf-hours"] == MTBF[name]
    jacks = [x for x in placements(p, "front") if x["ref"] == "common/rj45-ganged-eth-plain@1"]
    assert all(x["attrs"]["poe"] == "802.3at" for x in jacks)
    assert not [x for x in placements(t, "front") if "poe" in (x.get("attrs") or {})]


@pytest.mark.parametrize("name", NAMES)
def test_the_configuration_part_number_is_the_models_sku(name):
    cfg = load(name)["configurations"]
    assert list(cfg) == ["base"]
    assert cfg["base"]["kind"] == "base" and cfg["base"]["default"] is True
    assert cfg["base"]["part-numbers"] == {MODELS[name]: {}}


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "cisco" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    docs = [
        yaml.safe_load(f.read_text())
        for f in (ROOT / "library/exports/netbox/device-types/Cisco").glob("*.yaml")
    ]
    mine = [d for d in docs if d["model"] == MODELS[name]]
    assert len(mine) == 1
    assert mine[0]["u_height"] == 1
    assert mine[0]["manufacturer"] == "Cisco"
    assert sum(1 for i in mine[0]["interfaces"] if i["type"] == "1000base-t") == 24
    assert sum(1 for i in mine[0]["interfaces"] if i["type"] == "1000base-x-sfp") == 4
    kinds = sorted(c["type"] for c in mine[0]["console-ports"])
    assert kinds == ["rj-45", "usb-c"]
    ports = [p["name"] for p in mine[0].get("power-ports", [])]
    assert ports == (["ac-inlet"] if name == "c1300-24t-4g" else [])


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run ./build.sh first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "Cisco" / f"{MODELS[name]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_files_match_the_devices():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("cisco/c1300")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES:
        entry = known[f"cisco/{name}"]
        assert entry["version"] == load(name)["version"] == "1.0.0"
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]
