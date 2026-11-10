"""The eight DC posts of the Casa C100G power entry module take a spade terminal, and the library holds one that lands on them.

The Casa C100G Hardware Installation Guide asks for "spade terminals for screw M4" on the power entry module (page 6-20).
A spade slides on from the side and a ring lug does not, so the posts are not `terminal-stud` seats:

  - spec/schemas/connectors.yaml registers `spade-m4`, and generic/spade-lug@1 mates it;
  - casa/pem-post@1 is one post's seat, drawn as nothing, and presents `spade-m4`; casa/pem@1 composes eight of them, each
    standing on the nut the module draws;
  - the module's drawing is as it was: its skin, its eight nuts and their relief, its breakers and its `branch-N` groups;
  - the lug states the width the guide allows, 9.3 mm, and names the 9.2 mm of the guide's chapter 6 beside it;
  - the build publishes eight seats on the module that accept the lug, and the chassis row that said no power end was
    offered is gone from the records file.

These run against the real library and a components index built by the indexer the build runs. They read no library/dist and
render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

IFACE = "spade-m4"
LUG = "generic/spade-lug@1"
POST = "casa/pem-post@1"
PEM = "casa/pem@1"
POSTS = {
    "post-b4-vdc": [21.8, 33.64], "post-b4-rtn": [21.8, 53.84], "post-b3-vdc": [45.9, 33.64], "post-b3-rtn": [45.9, 53.84],
    "post-b2-vdc": [154.5, 33.64], "post-b2-rtn": [154.5, 53.84], "post-b1-vdc": [178.6, 33.64], "post-b1-rtn": [178.6, 53.84],
}
PEM_ELEMENTS = {"breaker-1", "breaker-2", "breaker-3", "breaker-4", "branch-1", "branch-2", "branch-3", "branch-4",
                "hs", "alarm", "ok"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def skin(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return (LIB / "components" / ns / part / f"v{major}" / "skins/default.svg").read_text()


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_registry_holds_the_spade_interface_and_it_is_not_the_ring_lugs():
    reg = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    assert IFACE in reg and IFACE != "terminal-stud"
    assert reg[IFACE]["turns"] == [0, 90, 180, 270]
    assert "M4" in reg[IFACE]["note"] and "Casa" in reg[IFACE]["note"]
    assert contract("generic/ring-lug@1")["mates"] == "terminal-stud"


def test_the_spade_lug_mates_the_interface_and_is_a_port_part():
    c = contract(LUG)
    assert (c["class"], c["mates"]) == ("port", IFACE)
    assert c["attrs"] == {"media": "spade-lug", "connector": IFACE}
    assert c["connection-points"]["mate"]["direction"] == "front"
    assert c["connection-points"]["cable"]["direction"] == "down"


def test_the_lug_states_the_guides_width_estimates_the_rest_and_names_the_other_figure():
    c = contract(LUG)
    assert c["size"]["w"] == 9.3
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    size = c["provenance"]["size"]
    assert "9.3" in size and "9.2" in size and "item 8" in size and "page 6-20" in size
    for key in ("slot", "wire", "thickness"):
        assert len(c["provenance"][key]) >= 40
    assert all(f["confidence"] in ("estimated", "borrowed") for f in c["relief"]["features"])


def test_the_post_is_a_screw_seat_that_presents_the_interface_and_draws_nothing():
    c = contract(POST)
    assert (c["class"], c["interface"]) == ("screw", IFACE)
    assert "turns" not in c["connection-points"]["mate"]
    assert "relief" not in c
    svg = skin(POST)
    assert "<g" not in svg and "<path" not in svg and "<circle" not in svg
    # one rectangle of the part's box, painted with nothing: a seat with an empty skin has no box for the conformance check to read
    assert svg.count("<rect") == 1 and 'fill="none"' in svg and 'stroke="none"' in svg


def test_the_module_composes_eight_posts_one_for_each_terminal_standing_on_its_nut():
    parts = contract(PEM)["parts"]
    assert {p["id"]: p["at"] for p in parts} == POSTS
    assert {p["ref"] for p in parts} == {POST}
    assert {p["lift"] for p in parts} == {8.2}


def test_the_modules_drawing_is_as_it_was_eight_nuts_and_their_relief_and_the_branch_groups():
    c = contract(PEM)
    assert PEM_ELEMENTS <= set(c["elements"])
    nodes = {f["node"]: f for f in c["relief"]["features"]}
    nuts = {n for n in nodes if n.startswith("nut-")}
    assert len(nuts) == 8
    assert {(nodes[n].get("cyl"), nodes[n].get("lift")) for n in nuts} == {(2.2, 6.0)}
    assert {"breaker-1-off", "terminal-block-1", "terminal-block-2", "cover-screw-1", "hs-button"} <= set(nodes)
    svg = skin(PEM)
    for n in nuts:
        assert f'id="{n}"' in svg
    for i in (1, 2, 3, 4):
        assert f'id="branch-{i}"' in svg


@pytest.mark.heavy
def test_the_build_publishes_eight_seats_on_the_module_that_accept_the_lug(index):
    cages = index[PEM]["cages"]
    assert sorted((c["id"], c["kind"], c["interface"], tuple(c["accepts"])) for c in cages) == sorted(
        (i, "connector", IFACE, (LUG,)) for i in POSTS)


def test_the_chassis_row_that_said_no_power_end_was_offered_is_gone():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [(r["part"], r["code"]) for r in rows if r["part"] == "c100g"] == []
