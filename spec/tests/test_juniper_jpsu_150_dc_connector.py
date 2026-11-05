"""The DC power connector of the Juniper JPSU-150-DC-AFO supplies is a place a cable lands.

The EX3400 and EX4100 supplies drew their three-terminal DC connector as art in the skin, so each offered no cable end. Both
now compose one connector part, the pluggable three-terminal connector of the two hardware guides (a block with three cells in
a column, printed "+", "-" and an earth symbol, and a hole at each end), standing inside the block their skins already draw.
The guides name no maker or part number for the connector (the EX3400 guide names the wire pins only), so the key
`juniper-dc-block-3` claims none, the header and the cable connector that mates it are declared stand-ins, and the place and
size are estimates; each contract says so.

  - the two supplies share one key, one header part and one cable connector, each a minor;
  - each supply states the roles of the three cells (`rtn`, `batt`, `gnd`) in its provenance and states no DC port, because a
    port whose poles are the cells of one pluggable connector is offered only where that part is itself the connector;
  - no skin is edited and no supply's description is changed;
  - the four devices that seat the supplies take a patch, and the two records of the supplies are gone.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

HEADER, PLUG = "juniper/jpsu-150-dc-header@1", "juniper/jpsu-150-dc-plug@1"
KEY = "juniper-dc-block-3"
# supply -> (the block its skin draws as x, y, w, h, where the header stands, the sha256 of its skin and of its description)
SUPPLIES = {
    "juniper/ex3400-jpsu-150-dc-afo@1": (
        (47.5, 7.6, 10.1, 25.8), [47.6, 8.0],
        "2190eb520846a51e0831a0b581325ab0513c8fcbc5861195dfa41aa1059df01d",
        "da525d7bfa73e73f0ccd11bd3f70edab3e35f606f37bee6e6ff9211c3635a2b6"),
    "juniper/ex4100-jpsu-150-dc-afo@1": (
        (48.2, 9.4, 12.6, 27.5), [49.5, 10.65],
        "60afeabaefda114a3b790597772b195124bf26d729b8b2dae7613284ef23deca",
        "6fb0faca81f95d7dd82a80d3f7bde2405b39c59068df5dddf01725f9465f4c57"),
}
# device -> (the supplies it seats, the version it takes: a patch)
DEVICES = {"ex3400-24t": ("0.2.1", "juniper/ex3400-jpsu-150-dc-afo@1"), "ex3400-48t": ("0.2.1", "juniper/ex3400-jpsu-150-dc-afo@1"),
           "ex4100-24t": ("1.0.2", "juniper/ex4100-jpsu-150-dc-afo@1"), "ex4100-48t": ("1.0.2", "juniper/ex4100-jpsu-150-dc-afo@1")}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_key_is_registered_and_claims_no_maker_or_standard():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    note = reg[KEY]["note"]
    assert "standard" not in reg[KEY], "the guides name no standard"
    assert "claims none" in note and HEADER in note and PLUG in note
    assert "EX3400" in note and "EX4100" in note


def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point():
    header, plug = contract(HEADER), contract(PLUG)
    assert (header["class"], header["interface"]) == ("inlet", KEY)
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"] == {"w": 10.0, "h": 25.0}
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]
    assert "part-numbers" not in header and "part-numbers" not in plug, "no part number is stated for the connector"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_the_one_header_inside_the_block_its_skin_draws(ref):
    block, at, _, _ = SUPPLIES[ref]
    c = contract(ref)
    assert c["version"] == "1.1.0"
    assert c["parts"] == [{"ref": HEADER, "id": "dc-header", "at": at}]
    svg = (path_of(ref) / "skins" / "default.svg").read_text()
    m = re.search(r'id="terminal-block" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    assert tuple(map(float, m.groups())) == block
    bx, by, bw, bh = block
    w, h = contract(HEADER)["size"]["w"], contract(HEADER)["size"]["h"]
    assert bx <= at[0] and at[0] + w <= bx + bw and by <= at[1] and at[1] + h <= by + bh, "inside the drawn block"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_states_the_roles_and_no_dc_port(ref):
    c = contract(ref)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    text = words(prov["roles"])
    for word in ("`rtn`", "`batt`", "`gnd`", "+RTN", "-48 V"):
        assert word in text, word
    assert "STAND-IN" in words(prov["connector"]).upper() or "declared stand-in" in words(prov["connector"])
    assert words(prov["no-dc-port"]).startswith("THE DC INPUT PORT IS NOT STATED HERE")


@pytest.mark.parametrize("ref", SUPPLIES)
def test_no_skin_is_edited_and_no_description_is_changed(ref):
    _, _, skin, description = SUPPLIES[ref]
    assert hashlib.sha256((path_of(ref) / "skins" / "default.svg").read_bytes()).hexdigest() == skin
    assert hashlib.sha256(words(contract(ref)["description"]).encode()).hexdigest() == description
    assert "dc-header" not in (path_of(ref) / "skins" / "default.svg").read_text()


def test_the_exporter_names_the_header_as_a_plain_other_connector():
    assert dx.PART_POWER["juniper/jpsu-150-dc-header"] == "other"
    assert "3-position" in dx.POWER_LABEL["juniper/jpsu-150-dc-header"]


@pytest.mark.heavy
def test_the_index_lists_the_header_with_its_key_and_mate_point_and_the_plug_as_a_port(index):
    assert (index[HEADER]["class"], index[HEADER]["interface"], index[HEADER]["mate"]) == ("inlet", KEY, [5.0, 11.9])
    assert index[PLUG]["class"] == "port" and index[PLUG]["mate"] == [5.0, 11.9]
    for ref in SUPPLIES:
        assert index[ref]["version"] == "1.1.0"
        assert not index[ref].get("dc-ports")


def test_four_devices_seat_the_supplies_and_no_others():
    seats = {}
    for ref in SUPPLIES:
        seats[ref] = sorted(p.parent.name for p in (LIB / "devices" / "juniper").glob("*/layout.yaml") if ref in p.read_text())
    assert seats["juniper/ex3400-jpsu-150-dc-afo@1"] == ["ex3400-24t", "ex3400-48t"]
    assert seats["juniper/ex4100-jpsu-150-dc-afo@1"] == ["ex4100-24t", "ex4100-48t"]


@pytest.mark.parametrize("device", DEVICES)
def test_each_device_that_seats_a_supply_takes_a_patch(device):
    version, ref = DEVICES[device]
    folder = LIB / "devices/juniper" / device
    lock = json.loads((folder / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(rf"^version: {re.escape(version)}$", (folder / fn).read_text(), re.M), fn
    assert lock["version"] == version
    assert lock["composed-refs"][ref].startswith("1.1.0+")
    assert lock["composed-refs"][HEADER].startswith("1.0.0+")
    assert not lock.get("dc-ports"), "no DC port is stated"


def test_the_records_of_the_two_supplies_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    for ref in SUPPLIES:
        assert (ref, "C19") not in rows, ref
    assert doc["cap"] == len(doc["rows"])
