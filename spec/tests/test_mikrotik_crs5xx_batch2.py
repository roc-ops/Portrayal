"""MikroTik's Cloud Router Switch CRS5xx, batch 2: the 100G switch with the front-mounted supplies.

The CRS504-4XQ-IN takes its envelope from MikroTik's dimensions drawing, whose file is named 04-4XQ-RM... but whose title
block reads "504-4XQ-IN" (printed 02.10.2023): it draws the IN's two AC supply modules, four QSFP28 cages and rack ears
and nothing of the outdoor -OUT. The brochure's 320 x 185 x 44 agrees. Its two supplies are hot-swap modules in the
brochure and the photographs, but no held document prints a part number for either, so they are drawn as part of the
chassis (two C14 inlets) and no bay is added. The device names are lower case with no +.
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
    "crs504-4xq-in": ("CRS504-4XQ-IN", "CRS504"),
    "crs520-4xs-16xq-rm": ("CRS520-4XS-16XQ-RM", "CRS520"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs504-4xq-in": (320.0, 44.0, 185.0),
    "crs520-4xs-16xq-rm": (443.0, 44.0, 367.0),
}
CRS504 = "crs504-4xq-in"
CRS520 = "crs520-4xs-16xq-rm"


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


# --- CRS504-4XQ-IN -----------------------------------------------------------------------------------------------

def test_crs504_drawing_name_difference_is_declared():
    d = load(CRS504)
    note = d["provenance"]["sources"]["note"]
    assert "04-4XQ-RMoutlineanddimensiondrawings_250851.pdf" in note
    assert '"504-4XQ-IN"' in note and "02.10.2023" in note
    assert "320 x 185 x 44" in d["provenance"]["chassis"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["drawing-name"]["reason"] == "sources-disagree"
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "60 V" in gaps["power-figures"]["note"] and "57" in gaps["power-figures"]["note"]


def test_crs504_has_four_qsfp28_cages_in_one_row_each_with_two_lamps():
    d = load(CRS504)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == [f"qsfp-{n}" for n in range(1, 5)]
    assert [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    assert len({p["at"][1] for p in cages}) == 1
    for a, b in zip(cages, cages[1:]):
        assert b["at"][0] - a["at"][0] == pytest.approx(26.0, abs=0.1)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 8  # ACT and 100G a cage
    assert not [p for p in placements(d, "front") if p["ref"].startswith("std/sfp")]


def test_crs504_front_carries_console_management_reset_dc_jack_and_three_lamps():
    d = load(CRS504)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert not refs(d, "front", "common/dc-barrel@1")  # drawn as chassis art: the barrel census wants a current
    assert [x["id"] for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "dc-jack-art"] == [
        "dc-jack-housing", "dc-jack-bore"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 5  # 3 bars, 2 supply lamps
    assert {"CONSOLE", "MGMT/PoE in", "RESET", "USER", "FAULT", "POWER", "36 - 60 V", "CRS504-4XQ-IN",
            "ACT", "100G", "1", "2", "3", "4"} <= text_of(d, "front")
    gaps = {g["what"] for g in d["gaps"]}
    assert {"dc-jack", "dc-terminal", "hot-swap-supplies", "led-states", "left-wall", "rear-face"} <= gaps
    assert not [p for p in placements(d, "front") if p["ref"].startswith("common/dc-terminal")]
    ports = [p for p in placements(d, "front") if p.get("group") in {"qsfp28", "mgmt", "console"}]
    assert len(ports) == 4 + 1 + 1  # page: 4 QSFP28 and one 100M Ethernet port; the console is on the metal


def test_crs504_supplies_are_two_front_modules_with_c14_inlets_and_no_bays():
    d = load(CRS504)
    assert not bays(d, "front") and not bays(d, "rear")
    inlets = refs(d, "front", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the quick guide: 2 AC inputs
    assert all(p["group"] == "inlets" and p["rotate"] in (90, 270, -90) for p in inlets)
    assert {"PSU 1", "PSU 2", "100-240 V 50/60 Hz"} <= text_of(d, "front")
    assert d["chassis"]["power"] == "ac"
    assert d["attrs"]["power"]["power-max-w"] == 41 and d["attrs"]["power"]["power-without-attachments-w"] == 25
    assert "fan-redundancy" not in json.dumps(d["groups"])


def test_crs504_fans_are_on_the_right_wall_and_the_other_faces_are_empty():
    d = load(CRS504)
    fans = [x["id"] for x in d["views"]["right"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1"]
    for view in ("rear", "left", "top", "bottom"):
        assert d["views"][view].get("empty"), view
    gaps = {g["what"] for g in d["gaps"]}
    assert {"fan-count", "left-wall", "rear-face", "top-and-bottom"} <= gaps


# --- CRS520-4XS-16XQ-RM ------------------------------------------------------------------------------------------

def test_crs520_drawing_and_brochure_agree_and_the_power_legend_conflict_is_declared():
    d = load(CRS520)
    assert "443 x 367 x 44" in d["provenance"]["chassis"]["note"]
    assert "CRS520-4XS_DIMENSIONS_250534.pdf" in d["provenance"]["sources"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "2,5 A" in gaps["power-figures"]["note"] and "10.25" in gaps["power-figures"]["note"]
    assert d["attrs"]["power"]["power-without-attachments-w"] == 123 and d["attrs"]["power"]["power-max-w"] == 150


def test_crs520_has_sixteen_qsfp28_cages_in_eight_stacked_pairs():
    d = load(CRS520)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == [f"qsfp-{n}" for n in range(1, 17)]
    assert [p["rel-pos"] for p in cages] == list(range(1, 17))
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in range(1, 17, 2):  # the metal prints 1 3 5 ... under the stacks and 2 4 6 ... over them
        assert by_id[f"qsfp-{n}"]["at"][1] > by_id[f"qsfp-{n + 1}"]["at"][1]
        assert by_id[f"qsfp-{n}"]["at"][0] == by_id[f"qsfp-{n + 1}"]["at"][0]
    assert by_id["qsfp-3"]["at"][0] - by_id["qsfp-1"]["at"][0] == pytest.approx(24.07, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 16 * 4  # four lamps a cage


def test_crs520_has_four_sfp28_cages_two_by_two_each_with_two_lamps():
    d = load(CRS520)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    assert by_id["cage-1"]["at"][1] > by_id["cage-2"]["at"][1] and by_id["cage-3"]["at"][1] > by_id["cage-4"]["at"][1]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(19.3, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 4 * 2


def test_crs520_front_carries_console_two_ten_gig_ports_reset_and_four_lamps():
    d = load(CRS520)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt-1", "10g"), ("mgmt-2", "10g")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    lamps = [p for p in placements(d, "front") if p.get("group") == "status-leds"]
    assert [p["id"] for p in lamps] == ["led-user", "led-power-2", "led-power-1", "led-fault"]
    assert {"CONSOLE", "RESET", "USER", "POWER 2", "POWER 1", "FAULT", "10G MGMT / BOOT", "100G QSFP28", "25G SFP28",
            "CRS520-4XS-16XQ"} <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"qsfp28", "sfp28", "mgmt", "console"}]
    assert len(ports) == 16 + 4 + 2 + 1  # page: 16 QSFP28, 4 SFP28, 2 x 10G; the console is on the metal
    gaps = {g["what"] for g in d["gaps"]}
    assert {"led-states", "left-wall", "top-and-bottom"} <= gaps


def test_crs520_supplies_and_fans_are_part_of_the_chassis_with_no_part_number():
    d = load(CRS520)
    assert not bays(d, "front") and not bays(d, "rear")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    decor = d["views"]["rear"]["panel"]["decor"]
    assert [x["id"] for x in decor if x.get("kind") == "fan-grille"] == ["fan-0", "fan-1", "fan-2", "fan-3"]
    assert {"POWER 1 / POWER 2", "1", "2", "3", "4"} <= text_of(d, "rear")
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"hot-swap-supplies", "hot-swap-fans", "optional-dc-supply"} <= set(gaps)
    assert "fan-redundancy" not in json.dumps(d["groups"])
    assert "G1483" not in json.dumps(d)  # no document prints the supply's number


def test_crs520_ears_and_the_rail_kit_are_declared_not_modelled():
    d = load(CRS520)
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"rack-rail-kit", "rear-support-ears"} <= set(gaps)
    assert "23-40 Rack Rail R0" in gaps["rack-rail-kit"]["note"] and "3-40_RACK_RAIL_R0_260621.pdf" in gaps["rack-rail-kit"]["note"]
    assert "kits" not in d["chassis"]


def test_crs520_walls():
    d = load(CRS520)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")
    assert d["views"]["top"].get("empty") and d["views"]["bottom"].get("empty")


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


def test_dcim_crs504_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS504)
    assert count(a, "100gbase-x-qsfp28") == 4
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # the two C14 inlets; the DC jack and the terminal are not placed
    assert len(a["console-ports"]) == 1


def test_dcim_crs520_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS520)
    assert count(a, "100gbase-x-qsfp28") == 16 and count(a, "25gbase-x-sfp28") == 4
    assert count(a, "10gbase-t") == 2
    assert len(a["power-ports"]) == 2  # the two C14 inlets at the rear
    assert len(a["console-ports"]) == 1


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
