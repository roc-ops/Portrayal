"""The WTI console server and PDU hybrids CPM-800-1 and CPM-1600-1, and the console server DSM-8.

The maker's dimensional drawings, data sheets and hardware guides give the outline, the order of every connector on both faces and
the bank each outlet belongs to; no photograph is held. What is true of the library once the three devices are in:

  - the maker is registered, and each model is a device of it, the size the documents give;
  - the CPM models carry their outlets and C20 inlets on the rear and the DSM-8 its C14 inlets, each connector a library part;
  - each outlet is fed by the inlet of its bank (four outlets to an inlet), as the hardware guide says;
  - the serial ports are numbered from 1 and every face the drawing shows is drawn;
  - the colours and the positions say they are not checked against a photograph.

These read the device sources and the registry. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

MODELS = {
    "cpm-800-1": dict(model="CPM-800-1", ru=1, outlets=8, inlets=2, serial=8, depth=220.98),
    "cpm-1600-1": dict(model="CPM-1600-1", ru=2, outlets=16, inlets=4, serial=16, depth=317.5),
    "dsm-8": dict(model="DSM-8", ru=1, outlets=0, inlets=2, serial=8, depth=166.37),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]


def device(name):
    return yaml.safe_load((LIB / "devices" / "wti" / name / "device.yaml").read_text())


def placements(name, view):
    comps = (device(name)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


def all_placements(name):
    out = {}
    for view in ("front", "rear"):
        out.update(placements(name, view))
    return out


def test_the_maker_is_registered():
    vendors = yaml.safe_load((SCHEMAS / "vendors.yaml").read_text())
    entry = (vendors.get("vendors") or vendors)["wti"]
    assert entry["display"] == "WTI"
    assert entry["role"] == "hardware"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_model_is_a_device_of_the_maker_at_the_size_the_documents_give(name):
    d = device(name)
    m = MODELS[name]
    assert (d["manufacturer"], d["model"]) == ("WTI", m["model"])
    ch = d["chassis"]
    assert ch["width"] == 435.6  # 17.15 inches, the drawing's top cover width
    assert ch["ru"] == m["ru"]
    assert ch["height"] == (44.45 if m["ru"] == 1 else 88.9)
    assert ch["depth"] == m["depth"]


@pytest.mark.parametrize("name", sorted(MODELS))
def test_all_six_views_are_there_and_a_bare_one_says_why(name):
    views = device(name)["views"]
    assert sorted(views) == sorted(VIEWS)
    for view, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name} {view}: neither drawn nor an `empty:` sentence"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_connectors_are_library_parts_in_the_counts_the_documents_give(name):
    m = MODELS[name]
    ps = all_placements(name)
    refs = [p["ref"] for p in ps.values()]
    assert refs.count("std/rj45-ganged@2") == m["serial"]
    assert refs.count("std/nema-5-15r@1") == m["outlets"]
    assert refs.count("std/c20-inlet@1" if name != "dsm-8" else "std/c14-inlet@1") == m["inlets"]
    assert refs.count("common/rj45-eth@1") == 2
    assert refs.count("common/rj11-jack@1") == 1
    assert refs.count("std/mini-usb@1") == 1


@pytest.mark.parametrize("name", ["cpm-800-1", "cpm-1600-1"])
def test_each_outlet_is_fed_by_an_inlet_and_each_inlet_feeds_four(name):
    ps = placements(name, "rear")
    feeds = {}
    for p in ps.values():
        if p["ref"] == "std/nema-5-15r@1":
            assert p["fed-by"] in ps and ps[p["fed-by"]]["ref"] == "std/c20-inlet@1", p["id"]
            feeds.setdefault(p["fed-by"], []).append(p["id"])
    assert sorted(len(v) for v in feeds.values()) == [4] * MODELS[name]["inlets"]


def test_the_cpm_1600_banks_are_a1_a4_a5_a8_b1_b4_b5_b8():
    ps = placements("cpm-1600-1", "rear")
    bank = {p["id"]: p["fed-by"] for p in ps.values() if p["ref"] == "std/nema-5-15r@1"}
    for row in "ab":
        for n in range(1, 9):
            assert bank[f"outlet-{row}{n}"] == f"inlet-{row}{1 if n <= 4 else 2}"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_serial_ports_are_numbered_from_one_without_a_gap(name):
    ps = [p for p in all_placements(name).values() if p["ref"] == "std/rj45-ganged@2"]
    assert sorted(p["rel-pos"] for p in ps) == list(range(1, MODELS[name]["serial"] + 1))
    assert len({tuple(p["at"]) for p in ps}) == len(ps)


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_colours_and_positions_say_no_photograph_is_held(name):
    d = device(name)
    assert "UNCHECKED" in d["provenance"]["colour"]["note"]
    assert "NO PHOTOGRAPH" in d["provenance"]["sources"]["note"]
    assert any(g["what"] == "photographs" for g in d["gaps"])


def test_no_part_number_belongs_to_two_devices():
    seen = {}
    for name in MODELS:
        for pn in device(name)["configurations"]["base"]["part-numbers"]:
            assert pn not in seen, f"{pn} is on {seen.get(pn)} and {name}"
            seen[pn] = name
