"""MikroTik's batch 4b: the models of batch 4 that its first PR did not reach.

The CRS320-8P-8B-4S+RM takes its envelope from MikroTik's dimensions drawing (printed 13.07.2023): 444.5 wide, 44.4
high and 235 deep, where the brochure prints 444 x 235 x 44. Its two supply slots take the hot-swap G1483-0600WNB,
which is its own component; the shipped supply is a module in a slot that no held document names. The device name
spells the + as `-plus`; `model:` keeps it as printed. The earlier batches are in their own test modules.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
MODELS = {
    "crs320-8p-8b-4s-plus-rm": ("CRS320-8P-8B-4S+RM", "CRS320"),
    "crs418-8p-8g-2s-plus-rm": ("CRS418-8P-8G-2S+RM", "CRS418"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs320-8p-8b-4s-plus-rm": (444.5, 44.4, 235.0),
    "crs418-8p-8g-2s-plus-rm": (443.0, 44.0, 230.0),
}
CRS320 = "crs320-8p-8b-4s-plus-rm"
CRS418 = "crs418-8p-8g-2s-plus-rm"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return (d["views"][view].get("components") or {}).get("bays") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def text_of(d, view):
    return {s.get("text") for s in d["views"][view]["silkscreen"]}


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    model, series = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "Switches", "family": "Cloud Router Switch", "series": series}
    assert "+" not in name
    assert d["version"] == "1.0.0"
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_drawings(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}


# --- CRS320-8P-8B-4S+RM ------------------------------------------------------------------------------------------

def test_crs320_brochure_and_drawing_differences_are_declared():
    d = load(CRS320)
    note = d["provenance"]["chassis"]["note"]
    assert "444.5" in note and "444 x 235 x 44" in note and "44.4" in note
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["size-figures"]["reason"] == "sources-disagree"
    assert "444" in gaps["size-figures"]["note"]


def test_crs320_has_sixteen_poe_out_jacks_in_two_classes():
    d = load(CRS320)
    jacks = [p for p in placements(d, "front") if p.get("group") == "rj45"]
    assert [p["rel-pos"] for p in jacks] == list(range(1, 17))
    assert [p["id"] for p in jacks] == [f"port-{n}" for n in range(1, 17)]
    assert all(p["ref"] == "common/rj45-eth@1" and p["attrs"]["media"] == "rj45" and p["attrs"]["speed"] == "1g"
               for p in jacks)
    for p in jacks:
        assert p["attrs"]["poe"] == ("802.3af/at (out)" if p["rel-pos"] <= 8 else "802.3bt (out)"), p["id"]
    by_id = {p["id"]: p for p in jacks}
    for n in range(1, 17, 2):  # the lower jack of a column takes the odd number
        assert by_id[f"port-{n}"]["at"][1] > by_id[f"port-{n + 1}"]["at"][1]
        assert by_id[f"port-{n}"]["at"][0] == by_id[f"port-{n + 1}"]["at"][0]
    assert by_id["port-3"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(16.24, abs=0.01)
    assert by_id["port-9"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(70.0, abs=0.01)  # the block step
    assert {"PoE out af / at", "PoE out af / at / bt", "GIGABIT ETHERNET", "RESET", "CONSOLE", "ETH / BOOT",
            "SFP+"} <= text_of(d, "front")
    assert "1▼" in text_of(d, "front") and "▲16" in text_of(d, "front")


def test_crs320_poe_markings_are_printed_not_lamps():
    """The photograph shows grey unlit bars over the jacks: printed marks, as on the CRS354-48P, not lit lamps."""
    d = load(CRS320)
    decor = d["views"]["front"]["panel"]["decor"]
    assert len([x for x in decor if x.get("kind") == "poe-bar"]) == 8  # one over each column of two jacks
    assert not [p for p in placements(d, "front") if "poe-lamp" in p["id"] or "poe-out" in p["id"]]
    assert "poe-lamps" in {g["what"] for g in d["gaps"]}
    assert d["attrs"]["power"]["poe-budget-w"] == 963


def test_crs320_has_four_sfp_plus_cages_a_console_a_management_jack_and_reset():
    d = load(CRS320)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp-plus"]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert all(p["ref"] == "std/sfp@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    at = {p["id"]: p["at"] for p in cages}
    assert at["cage-1"][0] == at["cage-2"][0] and at["cage-1"][1] > at["cage-2"][1]  # 1 below 2
    assert at["cage-3"][0] > at["cage-1"][0]
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    ports = [p for p in placements(d, "front") if p.get("group") in {"rj45", "sfp-plus", "mgmt", "console"}]
    assert len(ports) == 16 + 4 + 1 + 1  # brochure: 17 x 1G (16 PoE out and one management), 4 SFP+, one console
    assert not [p for p in placements(d, "front") if (p.get("attrs") or {}).get("media") == "qsfp"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 4


def test_crs320_supplies_are_two_slots_that_take_the_hot_swap_g1483_and_seat_none_by_default():
    d = load(CRS320)
    b = bays(d, "rear")
    assert [x["id"] for x in b] == ["psu-1", "psu-2"]
    assert all(x["group"] == "supply-slots" and x["accepts"] == ["mikrotik/g1483-0600wnb@1"] for x in b)
    assert not [x for x in b if x.get("default")]  # no held document names the shipped supply
    assert d["configurations"]["base"]["bays"] == {"psu-1": "", "psu-2": ""}  # both explicitly unseated
    assert d["chassis"]["power"] == "ac"
    gaps = {g["what"]: g for g in d["gaps"]}
    assert "shipped-supply-part" in gaps and "G1483-0600WNB" in gaps["shipped-supply-part"]["note"]
    assert "slot-2-cover" in gaps
    assert {"POWER 2 / POWER 1", "100-240 V ~9 A MAX, 50/60 Hz"} <= text_of(d, "rear")
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 600 and "1150" in p["power-max-with-additional-psu"]
    assert p["power-without-attachments-w"] == 36
    assert d["attrs"]["thermal"]["cooling"].startswith("3 fans")
    assert "fan-redundancy" not in json.dumps(d["groups"])


def test_g1483_0600wnb_is_one_module_with_its_own_c14_inlet():
    base = ROOT / "library/components/mikrotik/g1483-0600wnb/v1"
    c = yaml.safe_load((base / "contract.yaml").read_text())
    assert c["name"] == "g1483-0600wnb" and c["version"] == "1.0.0" and c["class"] == "psu"
    assert c["attrs"]["model"] == "G1483-0600WNB" and c["attrs"]["power-output-w"] == 600
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert [p["ref"] for p in c["parts"]] == ["std/c14-inlet@1"]
    assert (base / "skins/default.svg").exists()


def test_crs320_fans_are_openings_in_the_right_wall_and_the_rear():
    d = load(CRS320)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"] if x.get("kind") == "fan-grille"] == ["fan-0"]
    assert [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "vent-field"] == ["rear-vent"]
    assert any(g["what"] == "fan-count" for g in d["gaps"])
    assert d["views"]["left"].get("empty")


# --- CRS418-8P-8G-2S+RM ------------------------------------------------------------------------------------------

def test_crs418_has_sixteen_jacks_and_poe_out_on_ether9_to_16_only():
    d = load(CRS418)
    jacks = [p for p in placements(d, "front") if p.get("group") == "rj45"]
    assert [p["id"] for p in jacks] == [f"port-{n}" for n in range(1, 17)]
    assert [p["rel-pos"] for p in jacks] == list(range(1, 17))
    assert all(p["ref"] == "common/rj45-ganged-eth-plain@1" and p["attrs"]["speed"] == "1g" for p in jacks)
    with_poe = [p["rel-pos"] for p in jacks if "poe" in p["attrs"]]
    assert with_poe == list(range(9, 17))  # the brochure's PoE-out ports are Ether9 - Ether16
    assert all(p["attrs"]["poe"] == "802.3af/at, or 24 V passive (out)" for p in jacks if p["rel-pos"] >= 9)
    by_id = {p["id"]: p for p in jacks}
    for n in range(1, 17, 2):  # the lower jack of a column takes the odd number
        assert by_id[f"port-{n}"]["at"][1] > by_id[f"port-{n + 1}"]["at"][1]
        assert by_id[f"port-{n}"]["at"][0] == by_id[f"port-{n + 1}"]["at"][0]
    assert by_id["port-3"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(13.97, abs=0.01)
    assert by_id["port-9"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(70.5, abs=0.01)  # the block step
    assert d["attrs"]["power"]["poe-budget-w"] == 150
    assert not [p for p in placements(d, "front") if "poe-lamp" in p["id"]]


def test_crs418_poe_lamps_carry_the_photographs_lit_colours_and_the_bars_are_printed():
    d = load(CRS418)
    lit = {p["id"]: p["states"] for p in placements(d, "front") if p["id"] in {"led-poe-red", "led-poe-green"}}
    assert lit["led-poe-red"][1]["color"] == "#ef4444" and lit["led-poe-green"][1]["color"] == "#22c55e"
    assert len([x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "poe-bar"]) == 2
    assert {"28 V", "PoE out▲", "SFP+ 1", "SFP+ 2", "CONSOLE", "MGMT/BOOT", "RESET", "MODE", "USB", "USER", "FAULT",
            "PWR 2", "PWR 1", "ACT", "10G"} <= text_of(d, "front")
    assert "poe-lamps" in {g["what"] for g in d["gaps"]}


def test_crs418_has_two_sfp_plus_cages_usb_console_management_and_two_buttons():
    d = load(CRS418)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp-plus"]
    assert [p["id"] for p in cages] == ["cage-1", "cage-2"]
    assert all(p["ref"] == "std/sfp@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    assert cages[1]["at"][0] - cages[0]["at"][0] == pytest.approx(17.6, abs=0.01)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]
    usb = refs(d, "front", "std/usb-a@1")
    assert [(p["id"], p.get("rotate"), p.get("skin")) for p in usb] == [("usb", 90, "usb2")]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["usb-generation"]["reason"] == "sources-disagree" and "USB 3.0" in gaps["usb-generation"]["note"]
    assert [(p["id"], p["attrs"]["function"]) for p in refs(d, "front", "common/reset-button@1")] == [
        ("btn-reset", "reset"), ("btn-mode", "mode")]
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 4
    ports = [p for p in placements(d, "front") if p.get("group") in {"rj45", "sfp-plus", "mgmt", "console", "usb"}]
    assert len(ports) == 16 + 2 + 1 + 1 + 1  # brochure: 17 x 1G, two SFP+, one USB, one console
    assert not [p for p in placements(d, "front") if (p.get("attrs") or {}).get("media") == "qsfp"]


def test_crs418_two_built_in_supplies_are_two_inlets_and_four_fans_are_openings():
    d = load(CRS418)
    assert not (d["views"]["rear"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert all(p["group"] == "inlets" for p in inlets)  # the page: 2 AC inputs
    assert {"POWER 1", "POWER 2", "100-240 V ~1 A MAX 50/60 Hz"} <= text_of(d, "rear")
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 215 and p["power-without-attachments-w"] == 28
    assert d["attrs"]["thermal"]["cooling"].startswith("4 fans")
    fans = [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1", "fan-2", "fan-3"]
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")
    assert "fan-redundancy" not in json.dumps(d["groups"])
    assert not d["groups"].get("fans")


# --- every device ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", NAMES)
def test_the_ears_are_shipped_flush_and_never_placed(name):
    d = load(name)
    default = [p for p in d["chassis"]["ears"]["positions"] if p.get("default")]
    assert [p["name"] for p in default] == ["flush"]
    assert not [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "common/rack-ear@1"]
    assert "kits" not in d["chassis"]


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_every_legend_is_readable_at_the_device_pages_scale(name):
    d = load(name)
    for view in d["views"].values():
        for s in view.get("silkscreen") or []:
            if s.get("text"):
                assert s["font-size"] >= 1.5, s


# --- the DCIM export --------------------------------------------------------------------------------------------

def exported(name):
    model = MODELS[name][0]
    docs = [yaml.safe_load(f.read_text()) for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")]
    mine = [x for x in docs if x["model"] == model]
    assert len(mine) == 1
    return mine[0]


def count(doc, kind):
    return sum(1 for i in doc["interfaces"] if i["type"] == kind)


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    doc = exported(name)
    assert doc["u_height"] == 1 and doc["manufacturer"] == "MikroTik"


def test_dcim_crs320_interfaces_follow_the_front():
    a = exported(CRS320)
    assert count(a, "1000base-t") == 17 and count(a, "10gbase-x-sfpp") == 4
    assert len(a["console-ports"]) == 1


def test_dcim_crs418_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS418)
    assert count(a, "1000base-t") == 17 and count(a, "10gbase-x-sfpp") == 2
    assert len(a["power-ports"]) == 2
    assert len(a["console-ports"]) == 1


def test_dcim_g1483_module_type_is_exported():
    docs = [yaml.safe_load(f.read_text()) for f in (ROOT / "library/exports/netbox/module-types").rglob("*.yaml")]
    mine = [x for x in docs if x.get("model") == "G1483-0600WNB"]
    assert len(mine) == 1
    assert len(mine[0]["power-ports"]) == 1


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run the build first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS[name][0]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_files_match_the_devices():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("mikrotik/")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES:
        entry = known[f"mikrotik/{name}"]
        assert entry["version"] == load(name)["version"] == "1.0.0"
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]
