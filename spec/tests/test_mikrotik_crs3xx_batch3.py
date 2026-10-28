"""MikroTik's third Cloud Router Switch batch: the CRS317-1G-16S+RM, CRS309-1G-8S+IN, CRS312-4C+8XG-RM and
CRS328-4C-20S-4S+RM.

The CRS312 and CRS328-4C envelopes come from MikroTik's dimensions drawings (printed 20.09.2023). The CRS317 and CRS309
have no drawing, so theirs are the brochure's and the product page's figures. The device name spells the + as `-plus`;
`model:` keeps it as printed. The pilot and the earlier batches are in their own test modules.
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
    "crs317-1g-16s-plus-rm": ("CRS317-1G-16S+RM", "CRS317"),
    "crs309-1g-8s-plus-in": ("CRS309-1G-8S+IN", "CRS309"),
    "crs312-4c-plus-8xg-rm": ("CRS312-4C+8XG-RM", "CRS312"),
    "crs328-4c-20s-4s-plus-rm": ("CRS328-4C-20S-4S+RM", "CRS328"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs317-1g-16s-plus-rm": (443.0, 44.0, 224.0),
    "crs309-1g-8s-plus-in": (272.0, 44.0, 191.0),
    "crs312-4c-plus-8xg-rm": (443.0, 44.0, 183.0),
    "crs328-4c-20s-4s-plus-rm": (443.0, 44.0, 193.0),
}
POE_IN = "802.3af/at or passive PoE (in), 18 - 57 V"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


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
def test_the_envelope_is_the_drawings_or_the_brochures(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}


def test_the_conflicting_figures_are_declared():
    """A conflict sits in provenance or a gap, not only in the figure that won."""
    crs328 = load("crs328-4c-20s-4s-plus-rm")
    assert "194" in crs328["provenance"]["chassis"]["note"] and "193" in crs328["provenance"]["chassis"]["note"]
    assert any(g["what"] == "depth-figure" and g["reason"] == "sources-disagree" for g in crs328["gaps"])
    crs309 = load("crs309-1g-8s-plus-in")
    gaps = {g["what"]: g for g in crs309["gaps"]}
    assert gaps["power-max-w"]["reason"] == gaps["dc-input-range"]["reason"] == "sources-disagree"
    assert "23 W" in gaps["power-max-w"]["note"] and "17 W" in gaps["power-max-w"]["note"]
    assert "11-57" in gaps["dc-input-range"]["note"] and "12 - 57" in gaps["dc-input-range"]["note"]
    p = crs309["attrs"]["power"]
    assert p["power-max-w"] == 23 and "17 W" in p["power-without-attachments"]
    crs317 = load("crs317-1g-16s-plus-rm")
    assert "-40" in crs317["provenance"]["datasheet"]["note"] and "-20" in crs317["provenance"]["datasheet"]["note"]


# --- CRS317 ---------------------------------------------------------------------------------------------------

def test_crs317_has_sixteen_sfp_plus_cages_one_ethernet_and_a_console():
    d = load("crs317-1g-16s-plus-rm")
    cages = refs(d, "front", "std/sfp-ganged@1")
    assert [p["rel-pos"] for p in cages] == list(range(1, 17))
    assert all(p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    xs = [p["at"][0] for p in cages]
    assert xs[1] - xs[0] == pytest.approx(14.25, abs=0.01)  # the cages abut inside a block of four
    assert xs[4] - xs[0] == pytest.approx(63.5, abs=0.01)   # the block step
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    assert [p["id"] for p in refs(d, "front", "common/rj45-eth@1")] == ["eth-1"]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"SFP+ 1", "SFP+ 16", "ACT", "10G", "CONSOLE", "ETH/BOOT", "RESET", "USR", "FAULT", "PWR 1", "PWR 2"} <= texts


def test_crs317_has_two_lamps_per_cage_and_the_brochures_38_lamps():
    d = load("crs317-1g-16s-plus-rm")
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-sfp-")]
    assert len(lamps) == 32
    assert sorted(p["rel-pos"] for p in lamps) == list(range(1, 33))
    status = [p for p in refs(d, "front", "common/led-dot@1")]
    assert [p["id"] for p in status] == ["led-usr", "led-fault", "led-pwr2", "led-pwr1"]
    # 32 + 4 + the two lamps of the ETH/BOOT jack: the brochure's "LEDs: 38"
    assert len(lamps) + len(status) + 2 == 38


def test_crs317_two_built_in_supplies_are_two_inlets_and_two_fans():
    d = load("crs317-1g-16s-plus-rm")
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert all(p["group"] == "inlets" for p in inlets)
    assert [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"] == ["fan-0", "fan-1"]
    texts = {s.get("text") for s in d["views"]["rear"]["silkscreen"]}
    assert {"POWER 1", "POWER 2", "100-240V~2A MAX 50/60Hz"} <= texts
    assert d["attrs"]["power"]["power-max-w"] == 44


# --- CRS309 ---------------------------------------------------------------------------------------------------

def test_crs309_has_eight_sfp_plus_cages_one_poe_in_port_and_a_de9_console():
    d = load("crs309-1g-8s-plus-in")
    cages = refs(d, "front", "std/sfp@1")
    assert [p["rel-pos"] for p in cages] == list(range(1, 9))
    xs = [p["at"][0] for p in cages]
    assert xs[1] - xs[0] == pytest.approx(19.76, abs=0.01)
    assert [p["id"] for p in refs(d, "front", "common/db9-receptacle@1")] == ["console"]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"POE/BOOT", "CONSOLE", "RESET", "USER", "PWR", "SFP+ 8"} <= texts


def test_crs309_poe_in_is_on_ethernet_1_and_on_no_other_port():
    d = load("crs309-1g-8s-plus-in")
    with_poe = [(v, p["id"]) for v, body in d["views"].items()
                for p in (body.get("components") or {}).get("placements") or []
                if (p.get("attrs") or {}).get("poe")]
    assert with_poe == [("front", "eth-1")]
    eth = next(p for p in placements(d, "front") if p["id"] == "eth-1")
    assert eth["attrs"]["poe"] == POE_IN and eth["rel-pos"] == 1


def test_crs309_dc_jack_is_the_barrel_jack_with_the_rating_the_metal_prints():
    d = load("crs309-1g-8s-plus-in")
    jacks = refs(d, "rear", "common/dc-barrel@1")
    assert [p["id"] for p in jacks] == ["dc-in"]
    assert jacks[0]["group"] == "inlets"
    assert jacks[0]["attrs"] == {"input-voltage": "12-57 VDC", "current-max-a": 1.2}
    assert d["provenance"]["dc-in-rating"]["confidence"] == "datasheet"
    assert d["chassis"]["power"] == "dc"
    assert "DC 12-57 V" in {s.get("text") for s in d["views"]["rear"]["silkscreen"]}


def test_crs309_is_passive_with_a_chassis_art_earth_stud_and_a_narrow_body():
    d = load("crs309-1g-8s-plus-in")
    rear = d["views"]["rear"]
    assert not [x for x in rear["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert d["attrs"]["thermal"]["cooling"].startswith("passive")
    assert [g["what"] for g in d["gaps"] if g["what"] == "earth-stud-part"] == ["earth-stud-part"]
    assert d["chassis"]["width"] == 272.0 < 443.0
    assert not [p for p in placements(d, "rear") if "ground-stud" in p["ref"]]


# --- CRS312 ---------------------------------------------------------------------------------------------------

def test_crs312_ports_are_eight_ten_gig_jacks_four_combo_pairs_a_management_jack_and_usb():
    d = load("crs312-4c-plus-8xg-rm")
    xg = [p for p in placements(d, "front") if p.get("group") == "xg"]
    assert [p["rel-pos"] for p in xg] == list(range(1, 9))
    assert all(p["attrs"]["speed"] == "10g" for p in xg)
    assert xg[1]["at"][0] - xg[0]["at"][0] == pytest.approx(15.9, abs=0.01)
    copper = [p for p in placements(d, "front") if p.get("group") == "combo-copper"]
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp-plus"]
    # a combo pair shares its number: copper-N and cage-N are one port at a time
    assert [p["rel-pos"] for p in copper] == [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert [p["id"] for p in copper] == [f"copper-{n}" for n in range(1, 5)]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert "share" in d["groups"]["combo-copper"]["description"] and "share" in d["groups"]["sfp-plus"]["description"]
    assert [p["attrs"]["speed"] for p in placements(d, "front") if p.get("group") == "mgmt"] == ["100m"]
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    assert [p["id"] for p in refs(d, "front", "common/usb-a@2")] == ["usb"]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"1T", "4T", "1F", "4F", "2F", "3F", "CONSOLE", "MGMT/BOOT", "RESET", "USER", "FAULT", "POWER 1", "POWER 2"} <= texts


def test_crs312_lower_left_cage_is_1f_as_printed():
    d = load("crs312-4c-plus-8xg-rm")
    at = {p["id"]: p["at"] for p in placements(d, "front") if p["ref"] == "std/sfp@1"}
    assert at["cage-1"][0] == at["cage-2"][0] and at["cage-1"][1] > at["cage-2"][1]
    assert at["cage-3"][0] == at["cage-4"][0] and at["cage-3"][1] > at["cage-4"][1]
    assert at["cage-3"][0] > at["cage-1"][0]


def test_crs312_power_is_built_in_and_the_rear_is_empty_with_a_gap():
    d = load("crs312-4c-plus-8xg-rm")
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert d["views"]["rear"].get("empty") and not placements(d, "rear")
    assert not [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "std/c14-inlet@1"]
    gap = [g for g in d["gaps"] if g["what"] == "rear-face"]
    assert len(gap) == 1 and gap[0]["scope"] == ["rear"]
    assert d["attrs"]["power"]["power-max-w"] == 60
    assert "four built-in fans" in d["attrs"]["thermal"]["cooling"]
    assert d["views"]["left"].get("empty")
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["vent-field"]


# --- CRS328-4C ------------------------------------------------------------------------------------------------

def test_crs328_4c_has_twenty_sfp_cages_numbered_with_the_odd_ones_on_the_lower_row():
    d = load("crs328-4c-20s-4s-plus-rm")
    sfp = [p for p in placements(d, "front") if p.get("group") == "sfp"]
    assert [p["rel-pos"] for p in sfp] == list(range(1, 21))
    by_id = {p["id"]: p for p in sfp}
    for n in range(1, 21, 2):
        assert by_id[f"port-{n}"]["at"][1] > by_id[f"port-{n + 1}"]["at"][1]
        assert by_id[f"port-{n}"]["at"][0] == by_id[f"port-{n + 1}"]["at"][0]
    assert by_id["port-9"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(70.2, abs=0.01)


def test_crs328_4c_has_four_sfp_plus_cages_and_one_console_and_two_buttons():
    d = load("crs328-4c-20s-4s-plus-rm")
    plus = [p for p in placements(d, "front") if p.get("group") == "sfp-plus"]
    assert [p["rel-pos"] for p in plus] == [1, 2, 3, 4]
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    buttons = {p["id"]: p["attrs"]["function"] for p in refs(d, "front", "common/reset-button@1")}
    assert buttons == {"btn-reset": "reset", "btn-mode": "mode"}
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"CONSOLE", "RESET", "MODE", "USER", "FAULT", "PWR 1", "PWR 2", "COMBO", "SFP+"} <= texts


def test_crs328_4c_combo_pairs_share_their_numbers():
    d = load("crs328-4c-20s-4s-plus-rm")
    copper = [p for p in placements(d, "front") if p.get("group") == "combo-copper"]
    cages = [p for p in placements(d, "front") if p.get("group") == "combo-sfp"]
    assert [p["id"] for p in copper] == [f"copper-{n}" for n in range(1, 5)]
    assert [p["id"] for p in cages] == [f"combo-sfp-{n}" for n in range(1, 5)]
    assert [p["rel-pos"] for p in copper] == [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert "share" in d["groups"]["combo-copper"]["description"] and "share" in d["groups"]["combo-sfp"]["description"]
    by = {p["id"]: p["at"] for p in copper}
    assert by["copper-1"][1] > by["copper-2"][1] and by["copper-3"][1] > by["copper-4"][1]


def test_crs328_4c_two_built_in_supplies_are_two_inlets_and_two_fans():
    d = load("crs328-4c-20s-4s-plus-rm")
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"] == ["fan-0", "fan-1"]
    assert d["attrs"]["power"]["power-max-w"] == 43
    assert d["views"]["left"].get("empty")
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["vent-field"]


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


def test_dcim_interfaces_and_power_ports_follow_the_faces():
    a = exported("crs317-1g-16s-plus-rm")
    assert count(a, "10gbase-x-sfpp") == 16 and count(a, "1000base-t") == 1
    assert len(a["power-ports"]) == 2
    b = exported("crs309-1g-8s-plus-in")
    assert count(b, "10gbase-x-sfpp") == 8 and count(b, "1000base-t") == 1
    assert len(b.get("power-ports") or []) == 1
    c = exported("crs312-4c-plus-8xg-rm")
    assert count(c, "10gbase-x-sfpp") == 4 and count(c, "10gbase-t") == 12 and count(c, "100base-tx") == 1
    assert not c.get("power-ports")
    e = exported("crs328-4c-20s-4s-plus-rm")
    assert count(e, "10gbase-x-sfpp") == 4 and count(e, "1000base-x-sfp") == 24 and count(e, "1000base-t") == 4
    assert len(e["power-ports"]) == 2


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
