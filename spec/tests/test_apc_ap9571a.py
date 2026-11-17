"""The APC NetShelter AP9571A basic 1U rack PDU, and the two parts it needed.

It carries ten IEC C13 outlets in two banks of five on one face. A fixed input cord leaves the left end of that
face, and a rocker circuit breaker stands beside each bank. The other face is plain. What is true of the library
once it is in:

  - it is a device of the maker, with the width, height, depth and weight the data sheet gives, and six views;
  - the outlet face carries ten numbered C13 outlets, the input cord and two breakers, each bank behind its own;
  - the unit has no display, no network port and no switching;
  - every position read off a photograph is declared an estimate;
  - the two new parts say where each figure came from and are parts of the maker.

These read the contracts and the device source. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
ALLOWED = {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((LIB / "devices" / "apc" / "ap9571a" / "device.yaml").read_text())


def placements(dev, view):
    comps = dev["views"][view].get("components") or {}
    return {p["id"]: p for p in (comps.get("placements") or [])}


def test_it_is_a_device_of_the_maker_the_size_the_data_sheet_gives(dev):
    assert (dev["manufacturer"], dev["model"]) == ("APC", "AP9571A")
    c = dev["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (445, 44, 77, 1)
    assert c["weight-kg"] == 2.55


def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(dev):
    assert sorted(dev["views"]) == sorted(VIEWS)
    for name, v in dev["views"].items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor") or v.get("regions")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"


def test_ten_c13_outlets_and_the_fixed_cord_stand_on_the_outlet_face(dev):
    rear = placements(dev, "rear")
    outlets = {i: p for i, p in rear.items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 11)]
    assert {p["ref"] for p in outlets.values()} == {"std/c13-outlet@1"}
    assert rear["input"]["ref"] == "apc/pdu-cord-l6-30p@1"


def test_each_bank_of_five_sits_behind_its_own_breaker(dev):
    rear = placements(dev, "rear")
    assert {rear["breaker-1"]["ref"], rear["breaker-2"]["ref"]} == {"apc/pdu-breaker-rocker@1"}
    for n in range(1, 11):
        want = "breaker-1" if n <= 5 else "breaker-2"
        assert rear[f"outlet-{n}"]["through"] == want, n
    assert rear["breaker-1"]["at"][0] < rear["outlet-1"]["at"][0] < rear["outlet-5"]["at"][0]
    assert rear["outlet-5"]["at"][0] < rear["breaker-2"]["at"][0] < rear["outlet-6"]["at"][0]


def test_the_outlets_are_named_one_to_ten(dev):
    rules = {r["physical"]: r for r in dev["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-10"


def test_the_unit_has_no_display_no_network_port_and_no_switching(dev):
    mgmt = dev["attrs"]["management"]
    assert mgmt["outlet-switching"] is False
    assert mgmt["metering-scope"] == "none"
    refs = {p["ref"] for v in dev["views"] for p in placements(dev, v).values()}
    assert not any("display" in r or "rj45" in r for r in refs)


def test_every_position_read_off_a_photograph_is_declared_an_estimate(dev):
    for key in ("front", "rear", "breakers"):
        assert dev["provenance"][key]["confidence"] == "estimated", key
    assert "photograph" in dev["provenance"]["rear"]["note"]
    gaps = {g["what"] for g in dev["gaps"]}
    assert {"face-positions", "breaker-banks", "ears", "sides"} <= gaps


def test_every_view_that_draws_a_mark_declares_it_estimated(dev):
    for name, v in dev["views"].items():
        for d in (v.get("panel") or {}).get("decor") or []:
            assert d.get("confidence") == "estimated", f"{name}/{d['id']}"
            assert d.get("source"), f"{name}/{d['id']}"


def test_the_notches_along_the_lower_edge_of_the_outlet_face_are_drawn(dev):
    decor = dev["views"]["rear"]["panel"]["decor"]
    notches = sorted((d for d in decor if d["id"].startswith("notch-")), key=lambda d: d["at"][0])
    assert len(notches) == 23
    assert {d["at"][1] for d in notches} == {41.6}
    pitch = {round(b["at"][0] - a["at"][0], 1) for a, b in zip(notches, notches[1:])}
    assert pitch == {19.0}


def test_the_ten_outlets_stand_on_a_24_mm_pitch_in_two_groups_of_five(dev):
    rear = placements(dev, "rear")
    xs = [rear[f"outlet-{n}"]["at"][0] for n in range(1, 11)]
    assert {round(b - a, 1) for a, b in zip(xs[:4], xs[1:5])} == {24.0}
    assert {round(b - a, 1) for a, b in zip(xs[5:9], xs[6:10])} == {24.0}
    assert xs[5] - xs[4] > 90


@pytest.mark.parametrize("ref,plug", [("apc/pdu-cord-l6-30p@1", "nema-l6-30p"), ("apc/pdu-breaker-rocker@1", None)])
def test_the_new_parts_say_where_each_figure_came_from_and_which_are_estimates(ref, plug):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf and set(conf.values()) <= ALLOWED
    if plug:
        assert c["attrs"]["plug"] == plug
    ns, part = ref.split("@")[0].split("/")
    assert (LIB / "components" / ns / part / "v1" / "skins" / "default.svg").is_file()
