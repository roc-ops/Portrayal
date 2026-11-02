"""Every port of the Amphenol Network Solutions 300CB08 family, and of the two Open Rack v3 trays, is usable or says why not.

What the family's rear centre blocks and the bus-bar clip present, and what mates each:

  - the alarm card and the nrgSMART centre block present two three-pin wire-wrap headers each, as the composed part
    amphenol-ns/alarm-header@1 (`wire-wrap-3`), and the nrgSMART block presents its two nrgNET connectors as
    amphenol-ns/nrgnet-header@1 (`screw-terminal-5`);
  - the nrgILS centre block presents its two nrgNET RJ45 jacks as the composed part amphenol-ns/nrgnet-jack@1 (`rj45`);
  - the Open Rack v3 clip common/orv3-busbar-connector@1 presents `orv3-busbar`, the one slot of a part that composes nothing;
  - each of the three new keys has one estimated mate in the library: generic/wire-wrap-3-plug@1,
    generic/screw-terminal-5-plug@1 and generic/orv3-busbar-blade@1.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

HEADER = "amphenol-ns/alarm-header@1"
NRGNET = "amphenol-ns/nrgnet-header@1"
JACK = "amphenol-ns/nrgnet-jack@1"
WIRE_WRAP_PLUG = "generic/wire-wrap-3-plug@1"
SCREW_PLUG = "generic/screw-terminal-5-plug@1"
BLADE = "generic/orv3-busbar-blade@1"
CARD = "amphenol-ns/alarm-card-307608@1"
NRG_BLOCK = "amphenol-ns/nrg-rear-block@1"
ILS_BLOCK = "amphenol-ns/nrg-ils-rear-block@1"
CLIP = "common/orv3-busbar-connector@1"

NEW_PARTS = (HEADER, NRGNET, JACK, WIRE_WRAP_PLUG, SCREW_PLUG, BLADE)
CLOSED = {   # the six findings this change closes: part (or device) and code
    ("ds6001", "C19"), ("qfx5250-64oe-l", "C19"), (CLIP, "C20"), (CARD, "C22"), (ILS_BLOCK, "C22"), (NRG_BLOCK, "C22"),
}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def parts_of(ref):
    return {q["id"]: q for q in contract(ref).get("parts") or []}


@pytest.fixture(scope="module")
def index():
    import json
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


# --- 1. the new parts ------------------------------------------------------------------

@pytest.mark.parametrize("ref", NEW_PARTS)
def test_each_new_part_has_a_contract_and_a_skin(ref):
    assert (path_of(ref) / "contract.yaml").is_file()
    assert (path_of(ref) / "skins" / "default.svg").is_file()


def test_the_alarm_header_presents_wire_wrap_3():
    d = contract(HEADER)
    assert d["class"] == "port" and d["interface"] == "wire-wrap-3"
    assert d["size"] == {"w": 11.0, "h": 5.5}
    assert d["connection-points"]["mate"]["on"] == "shroud"


def test_the_nrgnet_header_presents_screw_terminal_5():
    d = contract(NRGNET)
    assert d["class"] == "port" and d["interface"] == "screw-terminal-5"
    assert d["size"] == {"w": 20.3, "h": 6.9}
    assert d["connection-points"]["mate"]["on"] == "body"


def test_the_nrgnet_jack_presents_rj45_as_a_serial_link_and_is_not_a_library_rj45_housing():
    d = contract(JACK)
    assert d["class"] == "port" and d["interface"] == "rj45"
    assert d["size"] == {"w": 16.0, "h": 12.8}
    assert d["attrs"] == {"media": "rj45-serial"}
    assert d["connection-points"]["mate"]["on"] == "shell"
    assert not d.get("parts")


@pytest.mark.parametrize("ref, key", [(WIRE_WRAP_PLUG, "wire-wrap-3"), (SCREW_PLUG, "screw-terminal-5"), (BLADE, "orv3-busbar")])
def test_each_new_mate_is_a_port_that_mates_its_key_and_says_it_is_estimated(ref, key):
    d = contract(ref)
    assert d["class"] == "port" and d["mates"] == key
    assert "interface" not in d and "behaviour" not in d
    assert d["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "needs-drawing" in d["provenance"]["size"]
    assert len(d["unplaced"]) >= 40


@pytest.mark.parametrize("ref, media", [(WIRE_WRAP_PLUG, "wire-wrap"), (SCREW_PLUG, "nrgnet")])
def test_the_two_terminal_mates_state_the_media_the_fibre_plug_census_leaves_out_by(ref, media):
    """spec/tests/test_fibre_plugs.py counts a part that mates a registered connector as a fibre plug unless what it IS says
    otherwise; these two say it by their media."""
    assert contract(ref)["attrs"]["media"] == media


@pytest.mark.parametrize("key", ["wire-wrap-3", "screw-terminal-5", "orv3-busbar"])
def test_each_new_key_has_exactly_one_mate_and_no_sentence(key):
    mates = []
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        d = yaml.safe_load(p.read_text())
        if d.get("mates") == key or (isinstance(d.get("mates"), list) and key in d["mates"]):
            mates.append(f"{p.parts[-4]}/{p.parts[-3]}@{p.parts[-2][1:]}")
    assert len(mates) == 1, mates
    entry = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"][key]
    assert "unmated" not in entry


# --- 2. the parts that present them ----------------------------------------------------

def test_the_alarm_card_composes_its_two_headers_and_draws_no_header_element():
    d = contract(CARD)
    assert {i: (q["ref"], q["at"]) for i, q in parts_of(CARD).items()} == {
        "alarm-b": (HEADER, [5.0, 6.5]), "alarm-a": (HEADER, [23.0, 6.5])}
    assert not d.get("elements")
    assert "interface" not in d
    assert [f["node"] for f in d["relief"]["features"]] == ["screw"]


def test_the_nrgsmart_block_composes_two_headers_and_two_nrgnet_connectors_and_keeps_its_temp_jacks_as_art():
    d = contract(NRG_BLOCK)
    assert {i: (q["ref"], q["at"]) for i, q in parts_of(NRG_BLOCK).items()} == {
        "alarm-b": (HEADER, [3.65, 2.35]), "alarm-a": (HEADER, [23.8, 2.35]),
        "nrgnet-in": (NRGNET, [1.0, 13.9]), "nrgnet-out": (NRGNET, [1.0, 27.7])}
    assert sorted(d["elements"]) == ["temp-1", "temp-2"]
    assert "interface" not in d


def test_the_nrgils_block_composes_its_two_nrgnet_jacks_and_keeps_the_rest_as_art():
    d = contract(ILS_BLOCK)
    got = parts_of(ILS_BLOCK)
    assert {i: (q["ref"], q["at"]) for i, q in got.items()} == {
        "nrgnet-in": (JACK, [2.2, 13.0]), "nrgnet-out": (JACK, [2.2, 28.4])}
    assert sorted(d["elements"]) == ["header-1", "header-2", "header-3", "probe"]
    assert "interface" not in d


def test_the_busbar_clip_presents_its_key_itself_composes_nothing_and_claims_no_lift():
    d = contract(CLIP)
    assert d["interface"] == "orv3-busbar" and not d.get("parts")
    assert "on" not in d["connection-points"]["mate"]


# --- 3. what the build publishes -------------------------------------------------------

def seats(index, ref):
    return [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in index[ref]["cages"]]


def test_the_alarm_card_publishes_two_seats_that_accept_the_wire_wrap_housing(index):
    assert seats(index, CARD) == [("alarm-b", "connector", "wire-wrap-3", [WIRE_WRAP_PLUG]),
                                  ("alarm-a", "connector", "wire-wrap-3", [WIRE_WRAP_PLUG])]


def test_the_nrgsmart_block_publishes_four_seats_each_with_its_mate(index):
    assert seats(index, NRG_BLOCK) == [
        ("alarm-b", "connector", "wire-wrap-3", [WIRE_WRAP_PLUG]), ("alarm-a", "connector", "wire-wrap-3", [WIRE_WRAP_PLUG]),
        ("nrgnet-in", "connector", "screw-terminal-5", [SCREW_PLUG]), ("nrgnet-out", "connector", "screw-terminal-5", [SCREW_PLUG])]


def test_the_nrgils_block_publishes_two_rj45_seats_that_accept_the_rj45_plug(index):
    got = seats(index, ILS_BLOCK)
    assert [(i, k, iface) for i, k, iface, _ in got] == [("nrgnet-in", "connector", "rj45"), ("nrgnet-out", "connector", "rj45")]
    assert all("generic/rj45-plug@1" in accepts for *_, accepts in got)


@pytest.mark.parametrize("ref", [HEADER, NRGNET, JACK, CLIP])
def test_a_part_that_presents_its_key_itself_has_no_seat_of_its_own_in_the_index(index, ref):
    """Its slot is published where a device places it, as every part that presents an interface is."""
    assert index[ref].get("cages", []) == []


# --- 4. the records --------------------------------------------------------------------

def test_the_six_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    left = sorted((r["part"], r["code"]) for r in rows if (r["part"], r["code"]) in CLOSED)
    assert left == []
