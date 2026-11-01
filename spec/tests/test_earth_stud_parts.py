"""The earth studs of seven devices are parts a lug lands on, not decor.

The Nokia SR-1e, SR-2e and SR-3e place a pair of 10-32 studs on 5/8 in. centres, the SR-12 places a pair on 5/8 in.
centres for a lug with 1/4 in. holes, and the MikroTik CRS309, CRS326 and CSS326 place one earth stud. Each was a
decor entry named for a connector (lint L197), so no cable or lug could be laid to it.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PAIR_10_32 = "common/ground-stud-pair-5-8-10-32@1"
PAIR_1_4 = "common/ground-stud-pair-5-8-1-4@1"
STUD = "common/ground-stud@1"

# device -> (view, placement id, ref, at, rotate, stud-size)
PLACED = {
    "nokia/sr-1e": ("rear", "ground-studs", PAIR_10_32, [3.3275, 181.715], 90, "10-32"),
    "nokia/sr-2e": ("rear", "ground-studs", PAIR_10_32, [3.3275, 346.19], 90, "10-32"),
    "nokia/sr-3e": ("rear", "ground-studs", PAIR_10_32, [3.3275, 488.365], 90, "10-32"),
    "nokia/sr-12": ("rear", "ground-studs", PAIR_1_4, [15.8625, 21.65], None, "1/4-20"),
    "mikrotik/crs309-1g-8s-plus-in": ("rear", "earth-stud", STUD, [256.15, 32.65], None, None),
    "mikrotik/crs326-24g-2s-plus-rm": ("rear", "earth-stud", STUD, [426.95, 31.65], None, None),
    "mikrotik/css326-24g-2s-plus-rm": ("rear", "earth-stud", STUD, [429.45, 34.55], None, None),
}
EACH = pytest.mark.parametrize("slug", sorted(PLACED))


def contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def test_the_ten_thirty_two_pair_is_two_screws_on_five_eighths_inch_centres():
    c = contract(PAIR_10_32)
    assert c["interface"] == "stud-pair-5-8" and c["class"] == "ground" and c["behaviour"] == "mounts"
    assert [(p["ref"], p["at"]) for p in c["parts"]] == [("common/ground-screw-10-32@1", [0, 0]),
                                                         ("common/ground-screw-10-32@1", [15.875, 0])]
    assert c["size"] == {"w": 25.345, "h": 9.47}
    assert c["connection-points"]["mate"] == {"at": [12.6725, 4.735], "direction": "front", "seat-out": 2.79}


@EACH
def test_each_stud_is_one_placement_of_a_part_that_presents_an_interface(slug):
    view, pid, ref, at, rotate, size = PLACED[slug]
    (p,) = [p for p in device(slug)["views"][view]["components"]["placements"] if p["id"] == pid]
    assert p["ref"] == ref and p["at"] == at and p.get("rotate") == rotate
    assert (p.get("attrs") or {}).get("stud-size") == size
    assert contract(ref).get("interface") in ("terminal-stud", "stud-pair-5-8")


@EACH
def test_no_decor_names_an_earth_stud_any_more(slug):
    for view, body in device(slug)["views"].items():
        for d in (body.get("panel") or {}).get("decor") or []:
            assert d.get("kind") not in ("ground-stud", "ground-nut", "earth-stud"), (view, d.get("id"), d.get("kind"))


@EACH
def test_each_stand_in_is_declared_by_a_gap(slug):
    gaps = {g["what"]: g for g in device(slug).get("gaps") or []}
    if slug.startswith("nokia/"):
        gap = gaps["ground-stud-hardware"]
        assert gap["scope"] == ["ground-studs"] and "stand-ins" in " ".join(gap["note"].split())
    else:
        gap = gaps["earth-stud-part"]
        assert "wing-nut" in gap["wanted"] and "stand-in" in " ".join(gap["note"].split())


@pytest.mark.parametrize("slug", [s for s in sorted(PLACED) if s.startswith("nokia/")])
def test_the_stud_size_is_stated_by_the_guide_it_came_from(slug):
    entry = device(slug)["provenance"]["ground-stud-size"]
    assert entry["confidence"] == "datasheet" and "`stud-size`" in entry["note"]
