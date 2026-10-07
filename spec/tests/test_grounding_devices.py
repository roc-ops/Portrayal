"""The devices whose ground points became pair hosts (#828, #830).

docs/connectors-dc-terminal-design.md section 13.7 adds the two-hole lug and
the hosts that present a pair of studs at the pitch of one; this file holds
the devices that place them. Each landing is one placement of a host, at the
pitch its documents give, centred where its source puts it, and a slot of
its device that offers the two-hole lug of that pitch. The SR-1 DC terminal
block composes one host per pole. The Casa C40G terminal is not converted:
its pitch is read only off a lug's part number, and its gap says so.

Held to the real library: nothing is rendered and nothing reads library/dist.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import render as render_mod
from test_coax_slots import _contract

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
EPS = 1e-6
LUG = {"stud-pair-5-8": "generic/two-hole-lug-5-8@1",
       "stud-pair-3-4": "generic/two-hole-lug-3-4@1",
       "stud-pair-1": "generic/two-hole-lug-1@1"}

AMPHENOL = ("300cb08", "300cb08-c", "300cb08-sc", "nrg300cb08-ctrl", "nrg300cb08-ctrl-c",
            "nrg300cb08-ctrl-sc", "nrg300cb08-sens", "nrg300cb08-sens-c", "nrg300cb08-sens-sc",
            "nrgils300cb08", "nrgils300cb08-sc")
H58_14 = "common/ground-stud-pair-5-8-1-4@1"


def _amphenol(model):
    """The 300CB08 panels' three landings, at the old studs' midpoints; the
    nrgILS chassis is deeper and its bottom and right landings sit further on.

    THE THREE -C PANELS are 367.0 deep and were re-read on main (#867): the
    bottom is read off their own bottom view, guide Fig. 3-13 (upper), which
    puts the two ground bolts at 216.0 across, one 5/8 in. pair whose screws
    sit 15.875 apart about 49.0 (main read them at 41.05 and 56.95, 15.9
    apart, before the pair); the side landing is placed from the
    REAR, 62 from it as on the stud panel, so 305.0 from the front (device
    provenance `envelope-faces`). The left view runs from the rear, so its
    62.0 is the same on every version."""
    ils = model.startswith("nrgils")
    if model.endswith("-c"):
        return {("bottom", "ground-bottom"): (216.0, 49.0),
                ("left", "ground-left"): (62.0, 23.75),
                ("right", "ground-right"): (305.0, 23.75)}
    return {("bottom", "ground-bottom"): (216.2 if ils else 214.95, 68.0),
            ("left", "ground-left"): (62.0, 23.75),
            ("right", "ground-right"): (311.2 if ils else 268.8, 23.75)}


# device -> {(view, placement): (host, rotate, the pair's centre on the face, stud-size)}
PAIRS = {f"amphenol-ns/{m}": {k: (H58_14, 90, c, "1/4-20") for k, c in _amphenol(m).items()}
         for m in AMPHENOL}
PAIRS.update({
    # the photographed holes' midpoint; the 5/8 in. is the named lug's
    "edgecore/ais800-64d": {("rear", "ground-screws"):
                            ("common/ground-stud-pair-5-8-m6@1", 90, (7.3, 47.9), "M6")},
    "edgecore/ais800-64o": {("rear", "ground-screws"):
                            ("common/ground-stud-pair-5-8-m6@1", 90, (7.3, 47.9), "M6")},
    # the side elevation's pair, 210.5 and 235.85 from the rear, and its mirror
    "nokia/nfxs-d-ba": {("left", "ground-left"):
                        ("common/ground-stud-pair-1-1-4@1", None, (223.175, 586.85), "1/4 in"),
                        ("right", "ground-right"):
                        ("common/ground-stud-pair-1-1-4@1", None, (56.8, 586.85), "1/4 in")},
    "nokia/nfxs-e-bb": {("right", "ground"):
                        ("common/ground-stud-pair-3-4-1-4@1", 90, (22.0, 227.0), "1/4 in")},
    "nokia/nfxs-f-bb": {("right", "ground"):
                        ("common/ground-stud-pair-3-4-1-4@1", 90, (22.0, 111.0), "1/4 in")},
    # the rendered studs' midpoint; 16 mm (0.63 in.) is 5/8 in. rounded
    "nokia/lmfs-f": {("front", "ground-studs"):
                     ("common/ground-stud-pair-5-8-m6@1", 90, (7.7, 247.55), "M6")},
})
CASES = [(d, v, i) for d, pairs in sorted(PAIRS.items()) for (v, i) in sorted(pairs)]


def _device(device):
    return yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())


def _placement(device, view, pid):
    comps = _device(device)["views"][view]["components"]
    return next(p for p in comps.get("placements") or [] if p["id"] == pid)


def _pitch(host):
    a, b = (p["at"] for p in _contract(host)["parts"])
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5


@pytest.fixture(scope="module")
def slots():
    lib = render_mod.Library([str(LIB)])
    families = render_mod._pluggable_families()
    candidates = render_mod._pluggable_candidates([LIB])
    got = {}
    for device in PAIRS:
        d = _device(device)
        for view in {v for v, _ in PAIRS[device]}:
            for c in render_mod.cage_entries(d, view, lib, families, candidates, {}):
                got[(device, view, c["id"])] = c
    assert got
    return got


@pytest.mark.parametrize("device,view,pid", CASES)
def test_the_landing_is_one_pair_host_centred_where_its_source_puts_it(device, view, pid):
    host, rot, centre, size = PAIRS[device][(view, pid)]
    p = _placement(device, view, pid)
    assert p["ref"] == host and p.get("rotate") == rot
    assert p["attrs"]["stud-size"] == size
    c = _contract(host)
    mate = c["connection-points"]["mate"]["at"]
    want = render_mod.seat_point(p["at"], c["size"], rot, mate)
    assert want == pytest.approx(list(centre), abs=1e-3)
    # and the studs are at the interface's pitch, one above the other when turned
    pitch = {"stud-pair-5-8": 15.875, "stud-pair-3-4": 19.05, "stud-pair-1": 25.4}[c["interface"]]
    assert _pitch(host) == pytest.approx(pitch, abs=EPS)


@pytest.mark.parametrize("device", sorted(PAIRS))
def test_no_single_stud_is_left_where_a_pair_now_lands(device):
    """The old placements are gone, not kept beside the pair."""
    for view, body in _device(device)["views"].items():
        for p in ((body or {}).get("components") or {}).get("placements") or []:
            assert p["ref"] not in ("common/ground-lug@1", "common/ground-stud@1"), (view, p["id"])


@pytest.mark.parametrize("device,view,pid", CASES)
def test_each_pair_is_a_slot_offering_the_two_hole_lug_of_its_pitch(slots, device, view, pid):
    host = PAIRS[device][(view, pid)][0]
    c = slots[(device, view, pid)]
    iface = _contract(host)["interface"]
    assert c["interface"] == iface and c["accepts"] == [LUG[iface]]
    assert c["default"] is None and c["occupant"] is None


def test_the_ground_marks_follow_their_pair():
    for model in AMPHENOL:
        d = _device(f"amphenol-ns/{model}")
        for side in ("left", "right"):
            mark = _placement(f"amphenol-ns/{model}", side, f"ground-{side}-mark")
            assert mark["for"] == f"ground-{side}"
            # centred on the pair, 6.0 tall
            assert mark["at"][1] + 3.0 == pytest.approx(23.75)
        assert "ground-pairs" in d["provenance"]
    for device, pid in (("edgecore/ais800-64d", "ground-screws"),
                        ("edgecore/ais800-64o", "ground-screws"),
                        ("nokia/lmfs-f", "ground-studs")):
        view = "front" if device == "nokia/lmfs-f" else "rear"
        assert _placement(device, view, "ground-symbol")["for"] == pid


def test_the_inferred_pitches_say_they_are_inferred():
    for device in ("edgecore/ais800-64d", "edgecore/ais800-64o"):
        d = _device(device)
        note = d["provenance"]["ground-pair"]["note"]
        assert "INFERRED" in note and "LCDXN2-14AF-E" in note
        assert d["provenance"]["ground-pair"]["confidence"] == "estimated"
        assert "ground-pair-pitch" in [g["what"] for g in d["gaps"]]
    note = _device("nokia/lmfs-f")["provenance"]["ground-pair"]["note"]
    assert "16 mm (0.63 in.)" in note and "15.875" in note


def test_the_lmfs_f_esd_point_has_a_group_of_its_own():
    d = _device("nokia/lmfs-f")
    assert d["groups"]["esd"]["term"] == "Point" and d["groups"]["esd"]["role"] == "furniture"
    assert _placement("nokia/lmfs-f", "front", "esd-point")["group"] == "esd"
    assert "ESD" not in d["groups"]["grounding"]["description"]


def test_each_pole_of_the_sr_1_dc_block_is_a_pair_of_10_32_studs():
    block = _contract("nokia/sr-1-dc-terminal-block@1")
    poles = {p["id"]: p for p in block["parts"]}
    assert sorted(poles) == ["a-neg", "a-rtn", "b-neg", "b-rtn"]
    assert {p["ref"] for p in poles.values()} == {"nokia/sr-1-dc-pole@1"}
    # each pole on its barrier's centre, upper stud at y 31.4
    for pid, cx in (("a-neg", 11.6), ("a-rtn", 28.7), ("b-neg", 45.9), ("b-rtn", 62.8)):
        assert poles[pid]["at"] == pytest.approx([cx - 5.6, 31.4 - 5.6])
    pole = _contract("nokia/sr-1-dc-pole@1")
    assert pole["interface"] == "stud-pair-5-8" and _pitch("nokia/sr-1-dc-pole@1") == 15.875
    # stacked: first stud on top, so the wire leaves down
    (a, b) = (p["at"] for p in pole["parts"])
    assert a[0] == b[0] and b[1] > a[1]
    stud = _contract("nokia/sr-1-dc-stud@1")
    assert stud["interface"] == "terminal-stud" and "10-32" in stud["provenance"]["thread"]
    assert "LCD6-10AH-L" in pole["provenance"]["lug"]
    # the device keeps its placement and its id
    assert _placement("nokia/sr-1-dc", "rear", "dc-input")["ref"] == "nokia/sr-1-dc-terminal-block@1"


def test_the_casa_terminal_waits_for_a_pitch():
    """Not converted: the C40G's 5/8 in. is read only off the lug's part number,
    and a pair across stud-bl and stud-br would re-key two nested slots."""
    parts = [p["id"] for p in _contract("casa/c40g-ground-studs@1")["parts"]]
    assert parts == ["stud-tr", "stud-bl", "stud-br"]
    gap = next(g for g in _device("casa/c40g")["gaps"] if g["what"] == "ground-stud-count")
    assert "LCD6-14AH-L" in gap["note"] and "waits" in gap["note"]
