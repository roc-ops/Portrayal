"""The earth studs of seven devices are parts a lug lands on, not decor, and each is drawn as the hardware looks.

The Nokia SR-1e, SR-2e and SR-3e place a pair of bare brass-coloured 10-32 studs on 5/8 in. centres, the SR-12 places a pair of
bare 1/4-20 receptacles on 5/8 in. centres for a lug with 1/4 in. holes, and the MikroTik CRS309, CRS326 and CSS326 place one
earth stud drawn as a plain disc until a wing-nut part is drawn. Each was a decor entry named for a connector (lint L197), so no
cable or lug could be laid to it.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PAIR_STUDS = "common/ground-stud-pair-5-8-10-32@1"
STUD = "common/ground-stud-10-32@1"
PAIR_HOLES = "common/ground-hole-pair-5-8-1-4@1"
HOLE = "common/ground-hole-1-4@1"
DISC = "mikrotik/earth-stud-disc@1"
# the parts the first drawing used, which no device of the seven composes any more
SCREWS = ("common/ground-screw-10-32@1", "common/ground-stud-pair-5-8-1-4@1", "common/ground-stud@1")

# device -> (view, placement id, ref, at, rotate, stud-size, the centre the part's box keeps on the face)
PLACED = {
    "nokia/sr-1e": ("rear", "ground-studs", PAIR_STUDS, [5.6495, 184.037], 90, "10-32", (16.0, 186.45)),
    "nokia/sr-2e": ("rear", "ground-studs", PAIR_STUDS, [5.6495, 348.512], 90, "10-32", (16.0, 350.925)),
    "nokia/sr-3e": ("rear", "ground-studs", PAIR_STUDS, [5.6495, 490.687], 90, "10-32", (16.0, 493.1)),
    "nokia/sr-12": ("rear", "ground-studs", PAIR_HOLES, [18.9375, 24.725], None, "1/4-20", (30.05, 27.9)),
    "mikrotik/crs309-1g-8s-plus-in": ("rear", "earth-stud", DISC, [256.2, 32.7], None, None, (260.2, 36.7)),
    "mikrotik/crs326-24g-2s-plus-rm": ("rear", "earth-stud", DISC, [427.0, 31.7], None, None, (431.0, 35.7)),
    "mikrotik/css326-24g-2s-plus-rm": ("rear", "earth-stud", DISC, [429.5, 34.6], None, None, (433.5, 38.6)),
}
EACH = pytest.mark.parametrize("slug", sorted(PLACED))
NOKIA = pytest.mark.parametrize("slug", [s for s in sorted(PLACED) if s.startswith("nokia/")])
SRE = pytest.mark.parametrize("slug", ["nokia/sr-1e", "nokia/sr-2e", "nokia/sr-3e"])
MIKROTIK = pytest.mark.parametrize("slug", [s for s in sorted(PLACED) if s.startswith("mikrotik/")])


def folder(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return LIB / "components" / ns / name / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def skin(ref):
    return (folder(ref) / "skins" / "default.svg").read_text()


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def gaps(slug):
    return {g["what"]: g for g in device(slug).get("gaps") or []}


def flat(text):
    return " ".join(text.split())


def test_the_stud_is_a_bare_brass_end_that_presents_terminal_stud():
    c = contract(STUD)
    assert c["interface"] == "terminal-stud" and c["class"] == "ground" and c["size"] == {"w": 4.826, "h": 4.826}
    assert c["size-confidence"] == {"w": "registry", "h": "registry"}
    assert c["connection-points"]["mate"] == {"at": [2.413, 2.413], "direction": "front", "on": "stud"}
    (feature,) = c["relief"]["features"]
    assert feature["node"] == "stud" and feature["cyl"] == 12.0 and feature["color"] == "#b8a06a"
    assert feature["confidence"] == "estimated"
    # one brass disc, as the chassis drew its stud ends; no nut, no washer, no screw head
    assert re.findall(r'fill="(#[0-9a-fA-F]{6})"', skin(STUD)) == ["#b8a06a"]
    assert "ESTIMATED" in c["provenance"]["colour"]


def test_the_ten_thirty_two_pair_is_two_studs_on_five_eighths_inch_centres():
    c = contract(PAIR_STUDS)
    assert c["interface"] == "stud-pair-5-8" and c["class"] == "ground" and c["behaviour"] == "mounts"
    assert [(p["ref"], p["at"]) for p in c["parts"]] == [(STUD, [0, 0]), (STUD, [15.875, 0])]
    assert c["size"] == {"w": 20.701, "h": 4.826}
    assert c["connection-points"]["mate"] == {"at": [10.3505, 2.413], "direction": "front", "seat-out": 12}


def test_the_quarter_twenty_hole_is_a_bare_dark_opening_at_the_threads_size():
    c = contract(HOLE)
    assert c["interface"] == "terminal-stud" and c["class"] == "ground" and c["size"] == {"w": 6.35, "h": 6.35}
    assert c["size-confidence"] == {"w": "registry", "h": "registry"}
    assert c["connection-points"]["mate"] == {"at": [3.175, 3.175], "direction": "front"}
    assert "relief" not in c
    svg = skin(HOLE)
    assert re.findall(r'<circle[^>]*\sr="([\d.]+)"[^>]*fill="(#[0-9a-fA-F]{6})"', svg) == [("3.175", "#2a2d31")]
    assert "screw" in flat(c["description"]) and "No screw is drawn" in flat(c["description"])


def test_the_quarter_twenty_pair_is_two_holes_on_five_eighths_inch_centres():
    c = contract(PAIR_HOLES)
    assert c["interface"] == "stud-pair-5-8" and c["class"] == "ground" and c["behaviour"] == "mounts"
    assert [(p["ref"], p["at"]) for p in c["parts"]] == [(HOLE, [0, 0]), (HOLE, [15.875, 0])]
    assert c["size"] == {"w": 22.225, "h": 6.35}
    assert c["connection-points"]["mate"] == {"at": [11.1125, 3.175], "direction": "front"}


def test_the_disc_is_the_two_circles_the_three_switches_drew_and_says_it_stands_in():
    c = contract(DISC)
    assert c["interface"] == "terminal-stud" and c["class"] == "ground" and c["size"] == {"w": 8.0, "h": 8.0}
    assert c["connection-points"]["mate"] == {"at": [4.0, 4.0], "direction": "front"}
    assert "relief" not in c
    circles = re.findall(r'<circle id="(\w+)" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="(#[0-9a-fA-F]{6})"', skin(DISC))
    assert circles == [("base", "4", "4", "4", "#b4b8bc"), ("nut", "4", "4", "2", "#8d9298")]
    assert "STAND-IN" in c["provenance"]["stand-in"] and "wing nut" in flat(c["description"])


@EACH
def test_each_stud_is_one_placement_of_a_part_that_presents_an_interface(slug):
    view, pid, ref, at, rotate, size, centre = PLACED[slug]
    (p,) = [p for p in device(slug)["views"][view]["components"]["placements"] if p["id"] == pid]
    assert p["ref"] == ref and p["at"] == at and p.get("rotate") == rotate
    assert (p.get("attrs") or {}).get("stud-size") == size
    assert contract(ref).get("interface") in ("terminal-stud", "stud-pair-5-8")


@EACH
def test_the_part_keeps_the_centre_the_studs_were_drawn_about(slug):
    view, pid, ref, at, rotate, size, centre = PLACED[slug]
    (p,) = [p for p in device(slug)["views"][view]["components"]["placements"] if p["id"] == pid]
    w, h = contract(ref)["size"]["w"], contract(ref)["size"]["h"]
    cx, cy = p["at"][0] + w / 2, p["at"][1] + h / 2
    assert (round(cx, 3), round(cy, 3)) == centre


@EACH
def test_no_decor_names_an_earth_stud_any_more(slug):
    for view, body in device(slug)["views"].items():
        for d in (body.get("panel") or {}).get("decor") or []:
            assert d.get("kind") not in ("ground-stud", "ground-nut", "earth-stud"), (view, d.get("id"), d.get("kind"))


@EACH
def test_no_screw_or_hex_nut_part_stands_in_for_the_hardware(slug):
    refs = {p["ref"] for body in device(slug)["views"].values() for p in (body.get("components") or {}).get("placements") or []}
    assert not refs & set(SCREWS)
    text = (LIB / "devices" / slug / "device.yaml").read_text()
    assert "pan-head screws where" not in text and "stand-in (gap ground-stud-hardware)" not in text


@SRE
def test_the_sr_e_gap_says_the_colour_and_length_are_estimates_and_no_photograph_is_held(slug):
    assert "ground-stud-hardware" not in gaps(slug)
    gap = gaps(slug)["ground-stud-appearance"]
    assert gap["scope"] == ["ground-studs"] and gap["reason"] == "needs-photo"
    text = flat(gap["note"])
    assert "brass-coloured" in text and "estimates" in text and "no photograph" in text
    assert "photograph" in gap["wanted"]


def test_the_sr_12_says_its_receptacle_thread_and_pitch_are_inferred_not_stated():
    slug = "nokia/sr-12"
    assert "ground-stud-hardware" not in gaps(slug)
    gap = gaps(slug)["ground-receptacle-size"]
    assert gap["scope"] == ["ground-studs"] and gap["reason"] == "vendor-silent"
    assert "INFERRED, NOT STATED" in flat(gap["note"]) and "15.1" in gap["note"]
    note = flat(device(slug)["provenance"]["ground"]["note"])
    assert "INFERRED, NOT STATED" in note and "bare 1/4-20 receptacles" in note


@MIKROTIK
def test_each_mikrotik_disc_is_declared_a_stand_in_for_the_wing_nut_by_its_gap(slug):
    gap = gaps(slug)["earth-stud-part"]
    assert gap["scope"] == ["rear"]
    assert "wing-nut" in gap["wanted"] and "disc" in gap["wanted"]
    assert "mikrotik/earth-stud-disc" in flat(gap["note"]) and "stands in for the wing nut" in flat(gap["note"])


@NOKIA
def test_the_stud_size_is_stated_by_the_guide_it_came_from(slug):
    entry = device(slug)["provenance"]["ground-stud-size"]
    assert entry["confidence"] == "datasheet" and "`stud-size`" in entry["note"]
