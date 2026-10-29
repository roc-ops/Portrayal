"""MikroTik's Cloud Core Routers CCR2xxx, batch 1: the CCR2116-12G-4S+ and the CCR2004-1G-12S+2XS.

Each takes its envelope from the brochure and the product page, which agree (no dimensions drawing is held):
443 x 199 x 44 mm and 443 x 224 x 44 mm. Each has two fixed AC inlets and no supply bay: the rear photographs show a
plain C14 inlet with a wire clip and no module, and no held document prints a supply part number. The CCR2004-16G-2S+
is not in this batch: its rear photograph shows two removable supply modules. The device names are lower case with
-plus for each +.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
CCR2116 = "ccr2116-12g-4s-plus"
CCR2004 = "ccr2004-1g-12s-plus-2xs"
MODELS = {
    CCR2116: ("CCR2116-12G-4S+", "CCR2116"),
    CCR2004: ("CCR2004-1G-12S+2XS", "CCR2004"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth: the brochure and the page agree
    CCR2116: (443.0, 44.0, 199.0),
    CCR2004: (443.0, 44.0, 224.0),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return (d["views"][view].get("components") or {}).get("bays") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def group(d, view, name):
    return [p for p in placements(d, view) if p.get("group") == name]


def text_of(d, view):
    return {s.get("text") for s in d["views"][view]["silkscreen"]}


def decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"]["decor"] if "id" in x}


def gaps(d):
    return {g["what"]: g for g in d["gaps"]}


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    model, series = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "Routers", "family": "Cloud Core Router", "series": series}
    assert "+" not in name
    assert d["version"] == "1.0.0"
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_brochures_and_the_pages(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}
    note = d["provenance"]["chassis"]["note"]
    assert f"443 x {int(depth)} x 44" in note  # brochure and page agree; no drawing is held
    assert "retaining clips" in note


def test_the_ccr2004_16g_2s_plus_is_left_out_whole():
    """Its rear photograph (2095) shows two removable supply modules with handles, which this batch does not model."""
    assert not (DEVICES / "ccr2004-16g-2s-plus").exists()


# --- CCR2116-12G-4S+ ---------------------------------------------------------------------------------------------

def test_ccr2116_has_twelve_lamped_gigabit_jacks_in_three_blocks_of_four():
    d = load(CCR2116)
    jacks = group(d, "front", "rj45")
    assert [p["id"] for p in jacks] == [f"port-{n}" for n in range(1, 13)]
    assert [p["rel-pos"] for p in jacks] == list(range(1, 13))
    assert all(p["ref"] == "common/rj45-ganged-eth@1" and p["attrs"] == {"media": "rj45", "speed": "1g"}
               for p in jacks)
    xs = [p["at"][0] for p in jacks]
    assert xs == sorted(xs) and len({p["at"][1] for p in jacks}) == 1
    step = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert step == [17.0, 17.0, 17.0, 21.2, 17.0, 17.0, 17.0, 21.2, 17.0, 17.0, 17.0]  # four to a gang, a gutter
    assert {"GIGABIT ETHERNET"} <= text_of(d, "front")
    assert {str(n) for n in range(1, 13)} <= text_of(d, "front")


def test_ccr2116_has_four_sfp_plus_cages_numbered_by_column_and_eight_arrow_lamps():
    d = load(CCR2116)
    cages = group(d, "front", "sfp-plus")
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in (1, 3):  # the metal prints 1 and 3 under the stacks and 2 and 4 over them
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert len(group(d, "front", "sfp-leds")) == 8
    assert "SFP+" in text_of(d, "front")


def test_ccr2116_has_console_management_usb_two_buttons_and_four_lamps():
    d = load(CCR2116)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]  # the brochure's 13th gigabit port
    assert [p["id"] for p in refs(d, "front", "std/usb-a@1")] == ["usb"]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-mode", "btn-reset"]
    assert len(group(d, "front", "status-leds")) == 4
    assert {"CONSOLE", "ETH/BOOT", "USB", "MODE", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "CCR2116-12G-4S+"} \
        <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"rj45", "sfp-plus", "mgmt", "console", "usb"}]
    assert len(ports) == 12 + 4 + 1 + 1 + 1


def test_ccr2116_m2_slot_is_a_gap_and_exports_no_port():
    d = load(CCR2116)
    g = gaps(d)["m2-slot"]
    assert "Number of M.2 slots" in g["note"]
    assert not [p for v in d["views"] for p in placements(d, v) if "m2" in p["ref"].lower() or "m.2" in str(p.get("attrs"))]
    assert "m2" not in json.dumps(exported(CCR2116)["interfaces"]).lower()


def test_ccr2116_rear_has_two_inlets_four_fans_and_one_more_round_opening():
    d = load(CCR2116)
    assert not bays(d, "rear") and d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page and the brochure: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    r = decor(d, "rear")
    assert [k for k, x in r.items() if x["kind"] == "fan-grille"] == ["fan-0", "fan-1", "fan-2", "fan-3"]  # page: 4 fans
    assert r["psu-opening"]["kind"] == "round-vent"  # the fifth opening, between the inlets, is a vent
    assert {"POWER 1", "POWER 2"} <= text_of(d, "rear")
    assert "100-240 V ~2 A MAX, 50/60 Hz" in text_of(d, "rear")
    assert {"psu-slots", "fan-count"} <= set(gaps(d))


def test_ccr2116_power_figures_conflict_is_declared():
    d = load(CCR2116)
    g = gaps(d)["power-figures"]
    assert g["reason"] == "sources-disagree"
    assert all(x in g["note"] for x in ("72", "83", "60", "12 V", "10.8"))
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 72 and p["power-without-attachments-w"] == 60
    assert p["power-max-w-page"] == 83
    assert "adapter" in p["power-adapter-nominal"]


def test_ccr2116_right_wall_shows_a_vent_and_left_wall_is_plain():
    d = load(CCR2116)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")


# --- CCR2004-1G-12S+2XS ----------------------------------------------------------------------------------------

def test_ccr2004_has_two_sfp28_cages_stacked_and_twelve_sfp_plus_cages_with_lamps():
    d = load(CCR2004)
    x28 = group(d, "front", "sfp28")
    assert [p["id"] for p in x28] == ["cage-28-1", "cage-28-2"]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in x28)
    assert x28[0]["at"][1] > x28[1]["at"][1] and x28[0]["at"][0] == x28[1]["at"][0]  # 1 lower, 2 upper, as printed
    assert len(group(d, "front", "sfp28-leds")) == 4
    cages = group(d, "front", "sfp-plus")
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 13)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    xs = [p["at"][0] for p in cages]
    assert all(round(b - a, 2) == 19.8 for a, b in zip(xs, xs[1:]))
    assert len(group(d, "front", "sfp-leds")) == 24  # ACT and 10G over each cage
    assert {f"SFP+ {n}" for n in range(1, 13)} <= text_of(d, "front")
    assert {"ACT", "10G", "25G SFP28"} <= text_of(d, "front")


def test_ccr2004_has_console_over_management_reset_and_four_lamps():
    d = load(CCR2004)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert len(group(d, "front", "status-leds")) == 4
    assert {"CONSOLE", "MGMT/BOOT", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "CCR2004-1G-12S+2XS"} \
        <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "sfp-plus", "mgmt", "console"}]
    assert len(ports) == 2 + 12 + 1 + 1
    assert not refs(d, "front", "std/usb-a@1")  # no USB jack on this face


def test_ccr2004_rear_has_two_inlets_two_fans_and_a_finned_heatsink():
    d = load(CCR2004)
    assert not bays(d, "rear") and d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    r = decor(d, "rear")
    assert [k for k, x in r.items() if x["kind"] == "fan-grille"] == ["fan-0", "fan-1"]  # page: 2 fans
    assert r["heatsink"]["kind"] == "heatsink"  # chassis art, not a third fan
    assert "100-240 V ~1 A MAX 50/60 Hz" in text_of(d, "rear")
    assert {"psu-slots", "fan-count", "right-wall"} <= set(gaps(d))


def test_ccr2004_power_figures_conflict_is_declared():
    d = load(CCR2004)
    g = gaps(d)["power-figures"]
    assert g["reason"] == "sources-disagree"
    assert all(x in g["note"] for x in ("49", "60", "31"))
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 49 and p["power-max-w-page"] == 60 and p["power-without-attachments-w"] == 31


def test_ccr2004_left_wall_is_plain_and_the_right_is_not_shown():
    d = load(CCR2004)
    assert d["views"]["left"].get("empty") and d["views"]["right"].get("empty")


# --- every device ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", NAMES)
def test_the_front_vent_band_is_the_nearest_pattern_and_the_zigzag_is_a_gap(name):
    """`chevrons` is not on main: the band takes `vent` and the gap says the metal's band is a zigzag."""
    d = load(name)
    band = decor(d, "front")["vent-field"]
    assert band["pattern"] == "vent" and band["vent"]
    assert "chevrons" not in json.dumps(d["views"])
    g = gaps(d)["vent-pattern"]
    assert "zigzag" in g["note"] and "chevrons" in g["note"]


@pytest.mark.parametrize("name", NAMES)
def test_no_dc_input_and_no_barrel_plug(name):
    d = load(name)
    assert d["chassis"]["power"] == "ac"
    assert not [p for v in d["views"] for p in placements(d, v) if p["ref"] == "common/dc-barrel@1"]


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


@pytest.mark.parametrize("name", NAMES)
def test_the_common_gaps_are_declared(name):
    g = gaps(load(name))
    assert g["led-states"]["reason"] == "vendor-silent"
    assert g["weight"]["reason"] == g["eol"]["reason"] == "vendor-silent"
    assert g["top-and-bottom"]["reason"] == "needs-drawing"
    assert "fan-redundancy" not in json.dumps(load(name)["groups"])


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
    assert len(doc["power-ports"]) == 2  # two C14 inlets
    assert len(doc["console-ports"]) == 1


def test_dcim_ccr2116_interfaces_follow_the_front():
    a = exported(CCR2116)
    assert count(a, "1000base-t") == 13 and count(a, "10gbase-x-sfpp") == 4
    assert len(a["interfaces"]) == 17


def test_dcim_ccr2004_interfaces_follow_the_front():
    a = exported(CCR2004)
    assert count(a, "1000base-t") == 1 and count(a, "10gbase-x-sfpp") == 12 and count(a, "25gbase-x-sfp28") == 2
    assert len(a["interfaces"]) == 15


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
