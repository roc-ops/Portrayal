"""The redundant power system (RPS) ports: which part presents which key, and what mates it.

Two registered keys (spec/schemas/connectors.yaml) name an RPS connector: `ex3300-rps`, the port of
the Juniper EX3300, and `cisco-rps2300`, the connector of a Catalyst 2960-S that takes a Cisco RPS
2300. This change gives the EX3300 port its interface and a mate point, adds the cable end that
mates each key, adds the Cisco connector as a part, and turns the EX2200's RPS decor into a placed
part that presents nothing: the EX2200 guide names no connector type, and `ex3300-rps` covers the
EX3300 only.

These run against the real library and a components index built by the indexer the build runs
(through onebuild), never a possibly stale dist.
"""
import json
import subprocess
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/juniper"

EX3300_PORT = "juniper/ex3300-rps-port@1"
EX3300_PLUG = "juniper/ex3300-rps-plug@1"
CISCO_CONNECTOR = "cisco/rps2300-connector@1"
CISCO_PLUG = "cisco/rps2300-plug@1"
EX2200_PORT = "juniper/ex2200-rps-port@1"

EX3300 = ["ex3300-24p", "ex3300-24t", "ex3300-48p", "ex3300-48t"]
EX2200 = ["ex2200-24p", "ex2200-24t", "ex2200-48p", "ex2200-48t"]
EIGHT = EX3300 + EX2200

PLUG_SENTENCE = ("seated by configurations downstream of this library; "
                 "see docs/pluggables-design.md decision 2")


def contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    path = LIB / f"components/{ns}/{name}/v{major}/contract.yaml"
    assert path.exists(), f"{ref} has no contract at {path.relative_to(ROOT)}"
    return yaml.safe_load(path.read_text())


def layout(name, text=None):
    if text is None:
        text = (DEVICES / name / "layout.yaml").read_text()
    return yaml.safe_load(text)


def origin_layout(name):
    out = subprocess.run(["git", "show", f"origin/main:library/devices/juniper/{name}/layout.yaml"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return layout(name, out)


def placements(doc):
    """{(view, id): placement} over every view of a layout."""
    got = {}
    for view, v in (doc.get("views") or {}).items():
        for n, p in enumerate(((v or {}).get("components") or {}).get("placements") or []):
            got[(view, p.get("id") or f"#{n}")] = p     # a placement with no id is held by its place in the list
    return got


def decor(doc):
    """{(view, id): entry} of every panel decor entry."""
    got = {}
    for view, v in (doc.get("views") or {}).items():
        for d in ((v or {}).get("panel") or {}).get("decor") or []:
            got[(view, d.get("id"))] = d
    return got


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


@pytest.fixture(scope="module")
def comps():
    """components.json by ref, from the indexer the build runs over this tree (onebuild)."""
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}


# --- 1. the EX3300 port presents its key ------------------------------------------------------

def test_the_ex3300_port_presents_its_key_with_a_mate_and_nothing_else_moved():
    c = contract(EX3300_PORT)
    assert c["interface"] == "ex3300-rps"
    assert c["version"] == "1.1.0"
    assert c["connection-points"]["mate"] == {"at": [33.1, 7.1], "direction": "front"}
    # the mate is the centre of the opening
    el = c["elements"]["opening"]
    assert [el["at"][i] + el["size"][i] / 2 for i in (0, 1)] == pytest.approx([33.1, 7.1], abs=1e-6)
    # what 1.0.0 drew is unchanged
    assert c["size"] == {"w": 67.8, "h": 14.1, "d": 20.0}
    assert el == {"at": [10.9, 2.7], "size": [44.4, 8.8], "class": "slot"}
    assert c["class"] == "inlet" and c["behaviour"] == "mounts" and c["attrs"] == {"media": "rps"}
    assert "interface" in c["provenance"]
    assert "Redundant power system (RPS) port" in c["provenance"]["interface"]


@pytest.mark.parametrize("name", EX3300)
def test_each_ex3300_keeps_the_rps_gap_and_places_the_port_where_it_did(name):
    doc = layout(name)
    assert "rps-port-connector" in {g["what"] for g in doc["gaps"]}
    p = placements(doc)[("rear", "rps")]
    assert p["ref"] == EX3300_PORT and p["group"] == "mgmt" and p["rel-pos"] == 3


# --- 2. the port is a slot that takes its cable end ---------------------------------------------

@pytest.mark.parametrize("name", EX3300)
def test_each_ex3300_rps_placement_is_a_connector_slot_that_accepts_its_cable_end(name):
    d = device(name)
    lib = render_mod.Library([str(LIB)])
    slots = render_mod.cage_entries(d, "rear", lib, render_mod._pluggable_families(),
                                    render_mod._pluggable_candidates([str(LIB)]), {},
                                    render_mod._connector_registry())
    slot = next(s for s in slots if s["id"] == "rps")
    assert slot["kind"] == "connector" and slot["interface"] == "ex3300-rps"
    assert slot["mate"] is not None
    assert EX3300_PLUG in slot["accepts"]


# --- 3. the two cable ends ----------------------------------------------------------------------

@pytest.mark.parametrize("ref,key", [(EX3300_PLUG, "ex3300-rps"), (CISCO_PLUG, "cisco-rps2300")])
def test_a_cable_end_mates_its_key_and_is_drawn_estimated(comps, ref, key):
    assert ref in comps, f"the indexer publishes no {ref}"
    c = contract(ref)
    assert c["class"] == "port" and c["kind"] == "component" and c["mates"] == key
    assert "behaviour" not in c and "interface" not in c
    assert c["unplaced"] == PLUG_SENTENCE
    # no drawing of the plug is held: every dimension is an estimate, and the part says which drawing it wants
    assert set(c["size-confidence"]) == set(c["size"]) == {"w", "h"}
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert all(f["confidence"] == "estimated" for f in c["relief"]["features"])
    assert "needs-drawing" in c["provenance"]
    assert set(c["fields"]) == {"cable-od", "jacket-color"}
    assert set(c["connection-points"]) == {"mate", "cable"}
    assert c["connection-points"]["cable"]["on"] == "stub"


def test_the_ex3300_plug_takes_the_ports_opening_and_the_cisco_plug_takes_the_connectors():
    assert contract(EX3300_PLUG)["size"] == {"w": 44.4, "h": 8.8}
    shroud = contract(CISCO_CONNECTOR)["elements"]["opening"]["size"]
    assert contract(CISCO_PLUG)["size"] == {"w": shroud[0], "h": shroud[1]}


# --- 4. the Cisco RPS 2300 connector ------------------------------------------------------------

def test_the_rps2300_connector_presents_its_key_and_says_what_will_seat_it():
    c = contract(CISCO_CONNECTOR)
    assert c["interface"] == "cisco-rps2300" and c["class"] == "inlet"
    assert "connection-points" in c and "mate" in c["connection-points"]
    assert "2960-S" in c["unplaced"] and "#1322" in c["unplaced"]
    assert c["unplaced"].strip() != PLUG_SENTENCE


def test_the_rps2300_connector_figures_equal_what_its_provenance_reads():
    c = contract(CISCO_CONNECTOR)
    prov = "\n".join(str(v) for v in c["provenance"].values())
    # the plate and the shroud as the Catalyst 2960-S rear art draws them
    assert c["size"]["w"] == 72.8 and c["size"]["h"] == 22.6
    assert c["elements"]["opening"] == {"at": [13.4, 2.6], "size": [48.2, 11.3], "class": "slot"}
    for figure in ("72.8", "22.6", "48.2", "11.3", "13.4", "2.6", "3.41", "Figure 1-10", "Figure 1-12"):
        assert figure in prov, figure
    mate = c["connection-points"]["mate"]["at"]
    assert mate == pytest.approx([13.4 + 48.2 / 2, 2.6 + 11.3 / 2], abs=1e-6)
    # every figure no source gives is declared estimated
    assert c["size-confidence"]["d"] == "estimated"
    assert "estimated" in prov


def test_the_rps2300_connector_provenance_says_the_cover_is_not_modelled():
    prov = "\n".join(str(v) for v in contract(CISCO_CONNECTOR)["provenance"].values())
    assert "Figure 1-15" in prov and "not modelled" in prov.lower()


# --- 5. the EX2200 RPS port is a placed part that presents nothing ------------------------------

# the rears that drew the plate as decor: the EX2200-24T has a second one for its DC supply
EX2200_REARS = {"ex2200-24p": ["rear"], "ex2200-24t": ["rear", "rear-dc"],
                "ex2200-48p": ["rear"], "ex2200-48t": ["rear"]}


@pytest.mark.parametrize("name", EX2200)
def test_no_ex2200_view_draws_the_rps_port_as_decor_and_each_places_the_part(name):
    doc = layout(name)
    assert not [k for k in decor(doc) if k[1] in ("rps-plate", "rps-opening")]
    assert not [k for k, d in decor(doc).items() if d.get("kind") in ("rps-plate", "rps-opening")]
    got = {v: p for (v, i), p in placements(doc).items() if i == "rps"}
    assert sorted(got) == sorted(EX2200_REARS[name])
    for view, p in got.items():
        # the plate's own place, in the group the EX3300 puts its RPS port in, after its three members
        assert p["ref"] == EX2200_PORT and p["at"] == [50.1, 25.1]
        assert p["group"] == "mgmt" and p["rel-pos"] == 4
        members = {q["id"]: q["rel-pos"] for (v, i), q in placements(doc).items()
                   if v == view and q.get("group") == "mgmt" and i != "rps"}
        assert members == {"mgmt": 1, "usb": 2, "console-rj45": 3}


def test_the_ex2200_part_presents_no_interface_and_is_not_the_ex3300_part():
    c = contract(EX2200_PORT)
    assert "interface" not in c and "mates" not in c
    assert "connection-points" not in c
    assert c["class"] == "inlet" and c["behaviour"] == "mounts"
    assert c["size"] == {"w": 67.9, "h": 14.6, "d": 20.0}
    assert c["elements"]["opening"] == {"at": [11.7, 2.9], "size": [44.5, 8.9], "class": "slot"}
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert EX2200_PORT != EX3300_PORT
    prov = "\n".join(str(v) for v in c["provenance"].values())
    assert "connector type" in prov and "ex3300-rps" in prov


@pytest.mark.parametrize("name", EX2200)
def test_the_ex2200_screws_stay_placed_as_they_were(name):
    new, old = placements(layout(name)), placements(origin_layout(name))
    for key, p in old.items():
        if key[1].startswith("rps-screw-"):
            # the only change is `for: rps`, which says the screw belongs to the plate it stands on
            # (the overlap rule, L13, skips a part and the part it is for)
            assert new[key] == {**p, "for": "rps"}


# --- 6. nothing else moved ----------------------------------------------------------------------

@pytest.mark.parametrize("name", EIGHT)
def test_no_other_placement_changed_its_id_group_position_or_turn(name):
    """A guard: it passes before the change and after it."""
    new, old = placements(layout(name)), placements(origin_layout(name))
    added = set(new) - set(old)
    assert added <= {(v, "rps") for v in ("rear", "rear-dc")} if name in EX2200 else not added
    assert not set(old) - set(new)
    for key, p in old.items():
        q = new[key]
        for field in ("ref", "group", "rel-pos", "at", "rotate"):
            assert q.get(field) == p.get(field), (key, field)
