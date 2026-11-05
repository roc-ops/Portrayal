"""The DC input of the Cisco NCS 5000 and NCS 5700 supplies is a place a cable lands.

The NC5K-PDC-930W-BK and -FR supplies (NCS 5001, 5002 and 5011) and the NC57-1600W-DCFW supply (NCS-57C3-MOD) drew their DC input
as art in a skin, so they offered no cable end. Each now composes the three-cell DC power connector that the Cisco
NXA-PDC-930W supply already carries: a column of three cells printed "-DC", "+DC" and an earth symbol (Cisco NCS 5000 hardware
installation guide, Figure 21; Cisco NCS 5700 fixed-port guide, Figure 93; Cisco N93108TC-FX3 guide, figure 504148). The three
figures draw one connector under one key, so the cable connector that mates it is one part. The guides name no maker or part
number for it, so the key claims none and the header parts are declared stand-ins.

  - the NC57 supply composes the NXA-PDC-930W's header inside the dark block its skin draws;
  - the two NC5K supplies compose a header of their own that draws the three grey cells their skins drew before, at the same
    place, size and colours, so their face does not change; the connector is drawn about 10 by 30 mm there and about 9 by 16 mm
    on the NXA-PDC-930W, both estimates;
  - each supply states the roles of the three contacts in its provenance and states no DC port;
  - the three records are gone.

These run against the real library and the records file. They read no library/dist and render nothing.
"""
import re
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

KEY = "cisco-dc-block-3"
NXA_HEADER, PLUG = "cisco/nxa-pdc-930w-dc-header@1", "cisco/nxa-pdc-930w-dc-plug@1"
NC5K_HEADER = "cisco/nc5k-pdc-930w-dc-header@1"
NC5K = ["cisco/nc5k-pdc-930w-bk@1", "cisco/nc5k-pdc-930w-fr@1"]
NC57 = "cisco/nc57-1600w-dcfw@1"
SUPPLIES = NC5K + [NC57]
# the three grey cells the NC5K skins drew, as (x, y, w, h) on the supply's face
CELLS = [(75.6, 5.4, 9.6, 9.6), (75.6, 15.6, 9.6, 9.6), (75.6, 26.4, 9.6, 9.0)]


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def skin(ref):
    return (path_of(ref) / "skins" / "default.svg").read_text()


def header_of(ref):
    return NXA_HEADER if ref == NC57 else NC5K_HEADER


def window(ref):
    """The box the skin draws the connector's housing or block in: (x, y, w, h)."""
    svg = skin(ref)
    if ref == NC57:
        m = re.search(r'<g id="inlet">\s*<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    else:
        m = re.search(r'id="dc-housing" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    return tuple(map(float, m.groups()))


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_its_header_inside_the_window_its_skin_draws(ref):
    (part,) = contract(ref)["parts"]
    assert (part["ref"], part["id"]) == (header_of(ref), "dc-header")
    x, y = part["at"]
    w, h = contract(header_of(ref))["size"]["w"], contract(header_of(ref))["size"]["h"]
    rx, ry, rw, rh = window(ref)
    assert rx <= x and x + w <= rx + rw and ry <= y and y + h <= ry + rh, "the part stands inside the drawn window"


def test_the_two_nc5k_supplies_carry_one_face_and_so_one_header_and_one_place():
    bk, fr = (contract(r) for r in NC5K)
    assert bk["parts"] == fr["parts"]
    assert skin(NC5K[0]) == skin(NC5K[1])


def test_the_nc5k_header_draws_the_three_cells_the_skins_drew_where_they_drew_them():
    (part,) = contract(NC5K[0])["parts"]
    ox, oy = part["at"]
    svg = skin(NC5K_HEADER)
    rects = re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="0.5"/>', svg)
    placed = [(round(ox + float(x), 3), round(oy + float(y), 3), float(w), float(h)) for x, y, w, h in rects]
    assert placed == CELLS
    assert 'fill="#8d9399" stroke="#5c6167" stroke-width="0.25"' in svg
    for ref in NC5K:
        assert "#8d9399" not in skin(ref), "the supply no longer draws the cells the header draws"


def test_the_nc5k_header_is_one_connector_with_the_nxa_header_at_another_size():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    assert "standard" not in reg[KEY]
    note = reg[KEY]["note"]
    assert NC5K_HEADER in note and NXA_HEADER in note and PLUG in note and "claims none" in note
    nc5k, nxa, plug = contract(NC5K_HEADER), contract(NXA_HEADER), contract(PLUG)
    for c in (nc5k, nxa):
        assert (c["class"], c["interface"]) == ("inlet", KEY)
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert nc5k["size"] != nxa["size"]
    assert nc5k["size-confidence"] == {"w": "estimated", "h": "estimated"}
    mx, my = nc5k["connection-points"]["mate"]["at"]
    assert 0 <= mx <= nc5k["size"]["w"] and 0 <= my <= nc5k["size"]["h"]
    assert "STAND-IN" in nc5k["provenance"]["part"] and "NO MAKER" in nc5k["provenance"]["part"]
    assert "two sizes" in nc5k["size-notes"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_states_the_roles_and_no_dc_port(ref):
    c = contract(ref)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    roles = prov["roles"]
    assert all(word in roles for word in ("`neg`", "`pos`", "`gnd`"))
    assert roles.index("`neg`") < roles.index("`pos`") < roles.index("`gnd`"), "top to bottom"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_provenance_says_the_connector_is_a_stand_in_with_no_maker(ref):
    text = contract(ref)["provenance"]["connector"]
    assert header_of(ref) in text and PLUG in text and "stand-in" in text.lower()
    assert "no maker" in text.lower()


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_does_not_draw_its_connector_twice(ref):
    assert "dc-header" not in skin(ref)


def test_the_exporter_lists_the_nc5k_header_as_the_nxa_header_is_listed():
    assert dx.PART_POWER["cisco/nc5k-pdc-930w-dc-header"] == dx.PART_POWER["cisco/nxa-pdc-930w-dc-header"] == "other"
    assert dx.POWER_LABEL["cisco/nc5k-pdc-930w-dc-header"] == dx.POWER_LABEL["cisco/nxa-pdc-930w-dc-header"]


def test_the_supplies_are_seated_by_the_devices_that_listed_them():
    seats = {ref: sorted(p.parent.name for p in (LIB / "devices" / "cisco").glob("*/layout.yaml")
                         if ref in p.read_text()) for ref in SUPPLIES}
    assert {"ncs-57c3-mod-hx", "ncs-57c3-mod-s"} <= set(seats[NC57])
    for ref in NC5K:
        assert {"ncs-5001", "ncs-5002", "ncs-5011"} <= set(seats[ref])


def test_the_records_of_the_three_supplies_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    for ref in SUPPLIES:
        assert (ref, "C19") not in rows
    assert doc["cap"] == len(doc["rows"])
