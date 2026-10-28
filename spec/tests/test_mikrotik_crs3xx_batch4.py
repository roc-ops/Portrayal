"""MikroTik's fourth Cloud Router Switch batch: the CRS326-4C+20G+2Q+RM.

The envelope comes from MikroTik's dimensions drawing (printed 19.10.2021, title block CRS326-4C+20XG-2Q+): 443 wide,
44 high and 230 deep, where the drawing and the brochure print 258 across the power-cord loops as well. The device name
spells the + as `-plus`; `model:` keeps it as printed. The earlier batches are in their own test modules.

The CRS320-8P-8B-4S+RM, CRS418-8P-8G-2S+RM and CRS418-8P-8G-2S+5axQ2axQ-RM are not in this batch.
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
    "crs326-4c-plus-20g-plus-2q-plus-rm": ("CRS326-4C+20G+2Q+RM", "CRS326"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs326-4c-plus-20g-plus-2q-plus-rm": (443.0, 44.0, 230.0),
}
CRS326C = "crs326-4c-plus-20g-plus-2q-plus-rm"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


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


def test_the_conflicting_figures_are_declared():
    """A conflict sits in provenance or a gap, not only in the figure that won."""
    d = load(CRS326C)
    note = d["provenance"]["chassis"]["note"]
    assert "258" in note and "230" in note
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["depth-figure"]["reason"] == "sources-disagree" and "258" in gaps["depth-figure"]["note"]
    assert gaps["temperature-range"]["reason"] == "sources-disagree"
    assert "-20" in gaps["temperature-range"]["note"] and "0 to +60" in gaps["temperature-range"]["note"]
    assert "20XG" in d["provenance"]["sources"]["note"]


# --- CRS326-4C+20G+2Q+RM -----------------------------------------------------------------------------------------

def test_crs326c_has_twenty_2_5g_jacks_numbered_with_the_odd_ones_on_the_lower_row():
    d = load(CRS326C)
    jacks = [p for p in placements(d, "front") if p.get("group") == "rj45"]
    assert [p["rel-pos"] for p in jacks] == list(range(1, 21))
    assert [p["id"] for p in jacks] == [f"port-{n}" for n in range(1, 21)]
    assert all(p["ref"] == "common/rj45-eth@1" and p["attrs"] == {"media": "rj45", "speed": "2.5g"} for p in jacks)
    by_id = {p["id"]: p for p in jacks}
    for n in range(1, 21, 2):
        assert by_id[f"port-{n}"]["at"][1] > by_id[f"port-{n + 1}"]["at"][1]
        assert by_id[f"port-{n}"]["at"][0] == by_id[f"port-{n + 1}"]["at"][0]
    assert by_id["port-3"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(16.26, abs=0.01)
    assert by_id["port-9"]["at"][0] - by_id["port-1"]["at"][0] == pytest.approx(69.85, abs=0.01)  # the block step
    assert {"2.5G ETHERNET", "COMBO", "CONSOLE", "MGMT/BOOT", "RESET", "USER", "FAULT", "POWER 2", "POWER 1"} <= text_of(d, "front")


def test_crs326c_combo_pairs_share_their_numbers():
    d = load(CRS326C)
    copper = [p for p in placements(d, "front") if p.get("group") == "combo-copper"]
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp-plus"]
    assert [p["id"] for p in copper] == [f"copper-{n}" for n in range(1, 5)]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert [p["rel-pos"] for p in copper] == [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert all(p["ref"] == "std/sfp@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    assert all(p["attrs"] == {"media": "rj45", "speed": "2.5g"} for p in copper)
    assert "one of the pair can be used at a time" in d["groups"]["combo-copper"]["description"]
    assert "one of the pair can be used at a time" in d["groups"]["sfp-plus"]["description"]
    assert {"1T", "4T", "1F", "4F"} <= text_of(d, "front")
    at = {p["id"]: p["at"] for p in cages}
    assert at["cage-1"][0] == at["cage-2"][0] and at["cage-1"][1] > at["cage-2"][1]  # 1F below 2F
    assert at["cage-3"][0] > at["cage-1"][0]


def test_crs326c_has_two_stacked_40g_qsfp_plus_cages_one_management_jack_and_a_console():
    d = load(CRS326C)
    q = refs(d, "front", "std/qsfp-ganged@1")
    assert [p["id"] for p in q] == ["uplink-40g-1", "uplink-40g-2"]
    assert [p["rel-pos"] for p in q] == [1, 2]
    assert all(p["attrs"] == {"media": "qsfp", "speed": "40g"} for p in q)
    assert q[0]["at"][1] > q[1]["at"][1] and q[0]["at"][0] == q[1]["at"][0]  # 1 below 2
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    assert [(p["id"], p["attrs"]["speed"]) for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"] == [("mgmt", "100m")]
    assert {"40G QSFP+"} <= text_of(d, "front")
    # 20 + 4 + 4 + 2 + 2 ports, the brochure's counts
    ports = [p for p in placements(d, "front") if p.get("group") in {"rj45", "combo-copper", "sfp-plus", "qsfp-plus", "mgmt", "console"}]
    assert len(ports) == 20 + 4 + 4 + 2 + 1 + 1


def test_crs326c_has_no_poe_out_on_any_port():
    d = load(CRS326C)
    assert not [p["id"] for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if (p.get("attrs") or {}).get("poe")]


def test_crs326c_two_built_in_supplies_are_two_inlets_and_the_fan_is_in_the_left_wall():
    d = load(CRS326C)
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert all(p["group"] == "inlets" for p in inlets)
    assert "100-240 V ~3.3 A MAX, 50/60 Hz" in text_of(d, "rear") and {"POWER 1", "POWER 2"} <= text_of(d, "rear")
    assert d["attrs"]["power"]["power-max-w"] == 70 and d["attrs"]["power"]["power-without-attachments-w"] == 51
    assert d["attrs"]["thermal"]["cooling"].startswith("2 fans")
    assert [x["id"] for x in d["views"]["left"]["panel"]["decor"] if x.get("kind") == "fan-grille"] == ["fan-0"]
    assert d["views"]["right"].get("empty")
    assert any(g["what"] == "second-fan" for g in d["gaps"])
    assert not d["groups"].get("fans") and "fan-redundancy" not in json.dumps(d["groups"])


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
    a = exported(CRS326C)
    assert count(a, "2.5gbase-t") == 24 and count(a, "10gbase-x-sfpp") == 4
    assert count(a, "40gbase-x-qsfpp") == 2 and count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2
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
