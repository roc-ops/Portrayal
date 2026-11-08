"""The APC NetShelter 1U rack PDUs AP7821B (metered) and AP7921B (switched), and the two parts they needed.

Both carry eight IEC C13 outlets in a row on one face, a C20 inlet at the left end of that face and, at the right end, a
two-digit display, a round button and two jacks; the other face is plain. What is true of the library once they are in:

  - each is a device of the maker, with the width, height, depth and weight the data sheet gives, and six views;
  - the outlet face carries eight numbered C13 outlets, the inlet and every part the data sheet photograph shows;
  - the outlets are named as the unit prints them and the metered unit states metering without switching;
  - every position read off a photograph is declared an estimate;
  - the two new parts say where each figure came from.

These read the contracts and the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKUS = {
    "ap7821b": dict(model="AP7821B", size=(444, 44, 102), kg=1.74, switched=False),
    "ap7921b": dict(model="AP7921B", size=(445, 44, 108), kg=2.27, switched=True),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = ["apc/ap78-display@1", "apc/ap78-button@1"]
ALLOWED = {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(sku):
    return yaml.safe_load((LIB / "devices" / "apc" / sku / "device.yaml").read_text())


def placements(sku, view):
    comps = device(sku)["views"][view].get("components") or {}
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_sku_is_a_device_of_the_maker_the_size_the_data_sheet_gives(sku):
    d = device(sku)
    assert (d["manufacturer"], d["model"]) == ("APC", SKUS[sku]["model"])
    assert (d["chassis"]["width"], d["chassis"]["height"], d["chassis"]["depth"]) == SKUS[sku]["size"]
    assert d["chassis"]["weight-kg"] == SKUS[sku]["kg"]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(sku):
    views = device(sku)["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{sku} {name}: neither drawn nor an `empty:` sentence"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_eight_c13_outlets_and_a_c20_inlet_stand_on_the_outlet_face(sku):
    rear = placements(sku, "rear")
    outlets = {i: p for i, p in rear.items() if i.startswith("outlet-")}
    assert sorted(outlets) == [f"outlet-{n}" for n in range(1, 9)]
    assert {p["ref"] for p in outlets.values()} == {"std/c13-outlet@1"}
    assert rear["input"]["ref"] == "std/c20-inlet@1"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_right_end_of_the_outlet_face_carries_what_the_photograph_shows(sku):
    rear = placements(sku, "rear")
    refs = {i: p["ref"] for i, p in rear.items()}
    assert refs["display"] == "apc/ap78-display@1"
    assert refs["button"] == "apc/ap78-button@1"
    assert {refs["jack-1"], refs["jack-2"]} == {"std/rj45@2"}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_outlets_are_named_as_the_unit_prints_them(sku):
    rules = {r["physical"]: r for r in device(sku)["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-8"
    marks = sorted(device(sku)["views"]["rear"]["silkscreen"], key=lambda s: s["at"][0])
    numerals = [m for m in marks if m.get("for", "").startswith("outlet-")]
    assert [m["text"] for m in numerals] == [str(n) for n in range(1, 9)]
    for m in numerals:
        assert m["for"] == f"outlet-{m['text']}"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_switching_is_stated_only_for_the_switched_unit(sku):
    mgmt = device(sku)["attrs"]["management"]
    assert mgmt["outlet-switching"] is SKUS[sku]["switched"]
    assert mgmt["metering-scope"] == "input"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_every_position_read_off_a_photograph_is_declared_an_estimate(sku):
    prov = device(sku)["provenance"]
    for key in ("front", "rear"):
        assert prov[key]["confidence"] == "estimated", f"{sku} {key}"
        assert "photograph" in prov[key]["note"]


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_a_new_part_says_where_each_figure_came_from_and_which_are_estimates(ref):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf, f"{ref}: no size-confidence"
    assert set(conf.values()) <= ALLOWED
