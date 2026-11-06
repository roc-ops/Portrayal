"""The chassis grounding screw on its washer is a place a ring lug lands.

common/ground-screw-washer@1 drew a pan head on a captive washer and offered nothing to land on. It now presents the
nominal `terminal-stud` interface, as every other single ground screw and stud of the library does:

  - its contract states `interface: terminal-stud` and a `mate` point, which stands on the screw's own relief node, so a lug
    seats at the top of the screw head;
  - the point is the centre of the screw the skin draws;
  - generic/ring-lug@1 mates the interface;
  - the part states no screw size: no document held for the devices that place it prints one.

These run against the real library and a components index built by the indexer the build runs. They read no library/dist and
render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

pytestmark = pytest.mark.heavy

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PART = "common/ground-screw-washer@1"
LUG = "generic/ring-lug@1"


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def entry():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}[PART]


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(PART)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_seat_stands_on_the_screw_the_skin_draws_at_its_centre():
    c = contract(PART)
    mate = c["connection-points"]["mate"]
    assert mate["direction"] == "front"
    assert mate["on"] == "screw"
    assert "screw" in [f["node"] for f in c["relief"]["features"]]
    box = c["elements"]["screw"]
    assert mate["at"] == [box["at"][0] + box["size"][0] / 2, box["at"][1] + box["size"][1] / 2]


def test_the_seat_says_where_it_came_from_and_claims_no_screw_size():
    c = contract(PART)
    assert len(c["provenance"]["seat"]) >= 40
    assert "size" not in c["connection-points"]["mate"]
    assert "stud-size" not in json.dumps(c)


def test_the_build_publishes_the_interface_and_its_point(entry):
    assert entry["interface"] == "terminal-stud"
    assert entry["mate"] == [5.5, 5.5]
