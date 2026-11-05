"""The SR-12 PEM-3 offers two DC feeds a lug lands on, and two Nokia covers name their screws for what they are.

The 175A DC PEM-3 of the 7750 SR-12 and 7450 ESS-12 drew its two terminal wells as art in the skin, so it offered no place for a
DC feed. It now composes each row of each well as a pair of studs a single two-hole lug lands across, and states two DC input
ports, one for the upper row of each well and one for the lower:

  - nokia/sr-12-dc-pole@1 is a pair of studs on the 3/4 in. pitch of the lug the installation guide names, and generic
    two-hole-lug-3-4@1 mates it;
  - nokia/sr-12-pem-3@1 composes four of them, `pole-batt-a`, `pole-batt-b`, `pole-rtn-a` and `pole-rtn-b`, and its ports
    `feed-a` and `feed-b` carry the guide's roles on them, with no nominal voltage, no current and no wire size, because the guide
    prints none for one feed;
  - the two screws that hold the SR-7 power filter safety panel and the two D-ring screws of the MF-8 front cover hold a part
    on and take no cable, so they are class `fastener`, not `screw`.

These run against the real library, a components index built by the indexer the build runs, the registry and the records file.
They read no library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

STUD = "common/terminal-screw-34@1"
POLE = "nokia/sr-12-dc-pole@1"
LUG = "generic/two-hole-lug-3-4@1"
PEM = "nokia/sr-12-pem-3@1"
COVERS = {"nokia/sr-7-psf-safety-panel@1": ["screw-left", "screw-right"],
          "nokia/mf8-horizontal-front-cover@1": ["d-ring-1", "d-ring-2"]}
FEEDS = [("feed-a", [("batt", "pole-batt-a"), ("rtn", "pole-rtn-a")]),
         ("feed-b", [("batt", "pole-batt-b"), ("rtn", "pole-rtn-b")])]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_pole_is_a_pair_of_studs_on_the_lug_pitch_and_says_the_pitch_is_inferred():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "stud-pair-3-4" in registry
    assert contract(LUG)["mates"] == "stud-pair-3-4"
    d = contract(POLE)
    assert d["interface"] == "stud-pair-3-4"
    assert [(q["ref"], q["at"]) for q in d["parts"]] == [(STUD, [0, 0]), (STUD, [19.05, 0])]
    assert "THE PITCH IS INFERRED, NOT STATED" in d["provenance"]["pitch"]
    assert "0.250-20" in d["provenance"]["thread"]


def test_the_pem_composes_one_pole_for_each_row_of_each_well():
    got = {q["id"]: (q["ref"], q["at"]) for q in contract(PEM)["parts"] if q["ref"] == POLE}
    assert got == {"pole-batt-a": (POLE, [79.015, 16.09]), "pole-batt-b": (POLE, [79.015, 37.62]),
                   "pole-rtn-a": (POLE, [315.815, 16.09]), "pole-rtn-b": (POLE, [315.815, 37.62])}


def test_each_feed_is_a_port_of_the_guides_two_roles_and_states_no_figure_the_guide_does_not_print():
    d = contract(PEM)
    ports = d["dc"]["ports"]
    assert [p["id"] for p in ports] == [f for f, _ in FEEDS]
    for port, (_, poles) in zip(ports, FEEDS):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
        assert not {"voltage", "rating-a", "awg"} & set(port)
        for key in port["source"].values():
            assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    for key in ("pairing", "rating", "voltage", "awg"):
        assert d["provenance"][key].startswith("NOT STATED")


def test_the_pem_keeps_its_drawing_and_every_id():
    d = contract(PEM)
    assert sorted(d["elements"]) == ["handle", "logo-zone", "power-switch", "screw-left", "screw-right",
                                     "terminal-neg", "terminal-rtn", "warning-marks"]
    assert d["elements"]["terminal-neg"]["class"] == d["elements"]["terminal-rtn"]["class"] == "terminal"
    assert sorted(d["connection-points"]) == ["feed-a", "feed-b", "mate"]


def test_the_build_publishes_four_pairs_a_two_hole_lug_lands_across_and_two_dc_ports(index):
    entry = index[PEM]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for _, poles in FEEDS:
        for _, slot in poles:
            assert seats[slot] == ("connector", "stud-pair-3-4", [LUG])
    assert [(p["id"], p["direction"], [(q["role"], q["slot"]) for q in p["poles"]]) for p in entry["dc-ports"]] == [
        (f, "input", poles) for f, poles in FEEDS]


@pytest.mark.parametrize("ref", sorted(COVERS))
def test_the_screws_that_hold_a_cover_on_are_fasteners_not_places_a_lug_lands(ref):
    d = contract(ref)
    assert [d["elements"][i]["class"] for i in COVERS[ref]] == ["fastener", "fastener"]
    assert d["provenance"]["fasteners"].startswith("datasheet")


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    have = {(r["part"], r["code"]) for r in rows}
    assert not have & {("sr-12", "C19"), ("sr-7", "C20"), ("lmfs-f", "C20")}
