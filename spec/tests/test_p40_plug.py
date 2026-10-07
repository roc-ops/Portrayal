"""The P40 output receptacle is a connector slot, and the plug that seats in it
(docs/connectors-dc-terminal-design.md section 14).

amphenol-ns/output-p40@1, the two-pole output of the Amphenol Network
Solutions connectorized power panels, presents interface `p40`;
amphenol-ns/p40-plug@1, the Amphenol PRM0400 plug drawn from its maker's
customer drawing, mates it. These run against the real library and device
copies rendered here, never a possibly stale dist.

The plug follows generic/terminal-508-2-plug@1 part for part: ONE WIRE PER
POLE, a stub and a named point for each, every stub sized by `wire-od` and
painted by `wire-color`. ITS SEATED DEPTH IS AN ESTIMATE: 22.3 in front of
the mouth of the receptacle's shroud, the drawing's 35.1 less the 12.8 of
nose it draws. The receptacle's shroud, 6.0, is an estimate too.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import render as render_mod
from portrayal.artifacts import face_file
from test_coax_slots import _contract, _skin_path
from test_dc_terminal_plugs import _front, _nodes, _render, feats
from test_head_3d import lift_of
from test_nested_occupants import assert_same_turn, by_path, cage_mate, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
EPS = 1e-6
IFACE = "p40"
RECEPTACLE = "amphenol-ns/output-p40@1"
PLUG = "amphenol-ns/p40-plug@1"
SHROUD = 6.0        # the receptacle presents at the mouth of its shroud
STANDS = 22.3       # 35.1 - 12.8: the plug in front of that mouth
STUB = 30.0
WIRE_OD = 8.0       # the largest insulation the housing takes (drawing note 2)
POLE_Y = (12.0, 21.8)
MATE = (4.85, 16.9)
WIRES = ("wire-1", "wire-2")

# Every device that places the receptacle, and how many it places.
PLACERS = {
    "amphenol-ns/300cb08-c": 16, "amphenol-ns/300cb08-sc": 16,
    "amphenol-ns/nrg300cb08-ctrl-c": 16, "amphenol-ns/nrg300cb08-ctrl-sc": 16,
    "amphenol-ns/nrg300cb08-sens-c": 16, "amphenol-ns/nrg300cb08-sens-sc": 16,
}
# (device, config, view, host): one at each end of each bank, on two panels
SEATS = [
    ("amphenol-ns/300cb08-sc", "base", "rear", "output-b8"),
    ("amphenol-ns/300cb08-sc", "base", "rear", "output-a1"),
    ("amphenol-ns/nrg300cb08-ctrl-c", "base", "rear", "output-a8"),
]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=[f"{s[0].split('/')[1]}-{s[3]}" for s in SEATS])


# --- 1. the interface and the receptacle ---------------------------------------------

def test_the_interface_is_a_vendor_connector_citing_no_standard():
    reg = render_mod._connector_registry()
    entry = reg[IFACE]
    assert "standard" not in entry and not entry.get("cover"), entry
    assert RECEPTACLE in entry["note"] and PLUG in entry["note"]


def test_the_receptacle_presents_it_between_its_cavities_on_its_shroud():
    c = _contract(RECEPTACLE)
    assert c["interface"] == IFACE and c["version"] == "1.1.0"
    mate = c["connection-points"]["mate"]
    assert mate["on"] == "shell" and mate["direction"] == "front"
    batt, rtn = c["elements"]["batt"], c["elements"]["rtn"]
    mid = [(batt["at"][i] + batt["size"][i] / 2 + rtn["at"][i] + rtn["size"][i] / 2) / 2 for i in (0, 1)]
    assert mate["at"] == pytest.approx(mid, abs=EPS)
    shell = next(f for f in c["relief"]["features"] if f["node"] == "shell")
    assert shell["out"] == SHROUD


def test_the_receptacle_kept_its_drawing():
    c = _contract(RECEPTACLE)
    assert c["size"] == {"w": 10.5, "h": 29.8} and c["class"] == "inlet"
    assert c["elements"] == {"batt": {"at": [0.7, 2.9], "size": [9.1, 9.1], "class": "inlet"},
                             "rtn": {"at": [0.7, 13.9], "size": [9.1, 9.1], "class": "inlet"}}


def test_only_the_receptacle_presents_the_interface_and_every_placement_is_counted():
    presenters = []
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        if yaml.safe_load(p.read_text()).get("interface") == IFACE:
            presenters.append(p.relative_to(LIB / "components").parts[:2])
    assert presenters == [("amphenol-ns", "output-p40")]
    got = {}
    for dev in (LIB / "devices").glob("*/*/device.yaml"):
        n = dev.read_text().count(f"ref: {RECEPTACLE}")
        if n:
            got[f"{dev.parent.parent.name}/{dev.parent.name}"] = n
    assert got == PLACERS


def test_the_plug_is_the_only_part_that_mates_it():
    mates = []
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        if yaml.safe_load(p.read_text()).get("mates") == IFACE:
            mates.append(p.relative_to(LIB / "components").parts[:2])
    assert mates == [("amphenol-ns", "p40-plug")]


# --- 2. the plug ----------------------------------------------------------------------

def test_it_is_a_plug_with_no_depth_at_the_drawings_size():
    c = _contract(PLUG)
    assert c["class"] == "port" and c["mates"] == IFACE and c["kind"] == "component"
    assert c["size"] == {"w": 9.7, "h": 34.2} and "d" not in c["size"]
    assert "behaviour" not in c
    assert c["attrs"]["positions"] == 2 and c["attrs"]["contact-mm"] == 4


def test_its_fields_are_the_wire_and_the_body():
    f = _contract(PLUG)["fields"]
    assert set(f) == {"wire-od", "wire-color", "body-color"}
    assert f["wire-od"]["default"] == WIRE_OD


def test_one_stub_and_one_point_per_pole_centred_on_the_mate():
    c = _contract(PLUG)
    cp = c["connection-points"]
    assert tuple(cp["mate"]["at"]) == MATE
    for w, y in zip(WIRES, POLE_Y):
        assert cp[w]["on"] == w and cp[w]["at"] == [MATE[0], y]
    assert (POLE_Y[0] + POLE_Y[1]) / 2 == pytest.approx(MATE[1], abs=EPS)
    nodes = {e.get("id"): e for e in ET.parse(_skin_path(PLUG)).getroot().iter()}
    for w, y in zip(WIRES, POLE_Y):
        e = nodes[w]
        assert (float(e.get("cx")), float(e.get("cy"))) == (MATE[0], y)
        assert float(e.get("r")) == WIRE_OD / 2
        assert e.get("data-r-from") == "wire-od" and e.get("data-fill-from") == "wire-color"


def test_the_relief_stands_the_estimate_and_the_stubs_run_from_it():
    f = feats(PLUG)
    for n in ("body", "latch-top", "latch-bottom"):
        assert f[n]["out"] == STANDS and f[n]["confidence"] == "estimated"
    for w in WIRES:
        assert f[w]["lift"] == STANDS and f[w]["cyl"] == STUB


def test_the_estimate_is_recorded_in_provenance():
    prov = _contract(PLUG)["provenance"]
    assert "ESTIMATED" in prov["seated-depth"] and "12.8" in prov["seated-depth"]
    assert "9.8" in prov["axis"] and "11.0" in prov["axis"]


# --- 3. seated in real panels -----------------------------------------------------------

@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p40plug")
    jobs = {}
    for device, config, _view, host in SEATS:
        jobs.setdefault((device, config), []).append(host)
    out = {}
    for (device, config), hosts in jobs.items():
        def edit(d, config=config, hosts=hosts):
            d["configurations"][config]["occupants"] = {h: PLUG for h in hosts}
        name, o = _render(tmp, device, edit)
        configs = json.loads((o / f"{name}.configs.json").read_text())
        root = ET.parse(face_file(o, name, config, "rear")).getroot()
        out[(device, config)] = (root, {c: p for p in root.iter() for c in p}, configs)
    return out


def _seat(seated, seat):
    device, config, _view, host_path = seat
    root, parents, configs = seated[(device, config)]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    assert occ.get("data-ref", "").startswith(PLUG), occ.get("data-ref")
    assert host.get("data-ref", "").startswith(RECEPTACLE), host.get("data-ref")
    return parents, host, occ, configs


@EACH_SEAT
def test_it_seats_with_its_mate_on_the_receptacles_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


@EACH_SEAT
def test_the_slot_offers_exactly_the_plug_and_ships_empty(seated, seat):
    _device, _config, view, pid = seat
    parents, host, occ, configs = _seat(seated, seat)
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["kind"] == "connector" and slot["interface"] == IFACE, slot
    assert slot["accepts"] == [PLUG] and slot["default"] is None, slot
    assert slot["lift"] == pytest.approx(SHROUD, abs=EPS)


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_estimate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    el = _nodes(occ, PLUG)
    base = lift_of(parents, el["body"])
    assert base - lift_of(parents, host) == pytest.approx(SHROUD, abs=EPS)
    assert _front(parents, el["body"]) - base == pytest.approx(STANDS, abs=EPS)
    for w in WIRES:
        assert _front(parents, el[w]) - base == pytest.approx(STANDS + STUB, abs=EPS)


@EACH_SEAT
def test_the_seated_plug_builds_right_side_out(seated, seat):
    parents, _host, occ, _ = _seat(seated, seat)
    raised = 0
    for e in occ.iter():
        if e.get("data-z-out") is not None:
            raised += 1
            assert float(e.get("data-z-out")) - lift_of(parents, e) > EPS, e.get("id")
        elif e.get("data-z-cyl") is not None:
            raised += 1
            assert float(e.get("data-z-cyl")) > EPS, e.get("id")
        assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")
    assert raised == len(feats(PLUG))


def test_every_output_of_a_panel_is_a_p40_slot(seated):
    _root, _parents, configs = seated[("amphenol-ns/300cb08-sc", "base")]
    slots = [c for c in configs["cages"]["rear"] if c.get("interface") == IFACE]
    assert sorted(c["id"] for c in slots) == sorted(
        f"output-{s}{n}" for s in "ab" for n in range(1, 9))
    assert all(c["accepts"] == [PLUG] for c in slots)
