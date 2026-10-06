"""The DC barrel jack is a connector slot, and the barrel plug that seats in it
(#789, docs/connectors-dc-terminal-design.md).

ONE SIZE, BY RULING. The library treats the DC barrel jack as one nominal
connector, `dc-barrel`: barrel diameters vary by product and no document held
for any of the four devices that place common/dc-barrel@1 states one. What a
jack is fed is carried as attributes of its placement, `input-voltage` and
`current-max-a`, from that device's own documents, and neither the interface
nor the plug states a rating. generic/dc-barrel-plug@1 is drawn at the common
5.5 mm barrel from one manufacturer's drawing; that it is the right plug for
a given device is not claimed, and its provenance says so.

These run against the real library, a components.json the indexer builds here
and device copies rendered here, never a possibly stale dist.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from portrayal import render as render_mod
from portrayal.artifacts import face_file
from portrayal.manifest import presented_interface
from test_coax_slots import _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
STUB = 30.0
JACK, PLUG, IFACE = "common/dc-barrel@1", "generic/dc-barrel-plug@1", "dc-barrel"
BARREL, FLANGE, OVERALL, CABLE_OD = 9.5, 3.0, 33.5, 4.0
CHAIN = ["flange", "grip", "stub"]

# device -> (view, placement, configuration seated in, input-voltage,
# current-max-a, the words of the device's own document its provenance quotes)
PLACED = {
    "halny/hlx-tgv": ("rear", "dc-in", None, "12 VDC", 1.0, "DC +12V/1.0A"),
    "nokia/xs-010x-r": ("rear", "dc-in", None, "12 VDC", 1.0, "Table 2-2"),
    "nokia/xs-010xr-p": ("rear", "dc-in", None, "12 VDC", 1.0, "Table 4-2"),
    "telco-systems/tm-280": ("front", "dc-in", None, "5 VDC", 3.0, "5VDC @3A (max)"),
}
EACH_DEVICE = pytest.mark.parametrize("device", sorted(PLACED))


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def feats():
    return {f["node"]: f for f in _contract(PLUG)["relief"]["features"]}


def rear(f):
    return float(f.get("lift") or 0.0) + float(f["cyl"])


def _device(device):
    return yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())


def _placement(device):
    view, pid = PLACED[device][:2]
    hits = [(v, p) for v, body in _device(device)["views"].items()
            for p in ((body or {}).get("components") or {}).get("placements") or []
            if p.get("ref") == JACK]
    assert len(hits) == 1, (device, hits)
    assert hits[0][0] == view and hits[0][1]["id"] == pid, (device, hits)
    return hits[0][1]


# --- 1. the registry, and the ruling ------------------------------------------

def test_dc_barrel_is_one_connector_and_claims_no_size_or_rating():
    reg = render_mod._connector_registry()
    assert [k for k in reg if "barrel" in k] == [IFACE]
    entry = reg[IFACE]
    assert entry["standard"] in std()
    note = entry["note"]
    assert "ONE nominal connector" in note
    assert "diameters vary by product" in note
    assert "none of the documents" in note and "four devices" in note
    assert "input-voltage" in note and "current-max-a" in note
    assert "not by the interface" in note and PLUG in note
    for key in ("barrel-jack", "barrel-plug"):
        assert "a nominal size chosen for the library" in std()[key]["registry"]
        assert "NOT A FIGURE FROM ANY PLACING DEVICE" in " ".join(std()[key]["notes"].split())


def test_the_jack_gained_its_interface_and_kept_its_drawing():
    jack = _contract(JACK)
    assert jack["interface"] == IFACE and jack["class"] == "inlet"
    assert jack["size"] == {"w": 12.0, "h": 13.0}
    assert jack["attrs"] == {"input": "dc"}
    assert jack["elements"] == {"inlet": {"at": [1.5, 2.0], "size": [9.0, 9.0],
                                          "class": "inlet"}}
    assert "relief" not in jack and "conforms" not in jack
    cps = jack["connection-points"]
    # `power` is kept, and `mate` is the same point
    assert cps["power"] == {"at": [6.0, 6.5], "direction": "front"}
    assert cps["mate"] == cps["power"]
    got, at, lift = presented_interface(jack, lambda r: _contract(r))
    assert (got, at, lift) == (IFACE, [6.0, 6.5], 0.0)
    # the point is the centre of the bore the skin draws
    bore = next(e for e in ET.parse(_skin_path(JACK)).getroot().iter()
                if e.get("id") == "inlet-bore")
    assert [float(bore.get("cx")), float(bore.get("cy"))] == at


def test_the_jack_states_no_rating_of_its_own():
    """Four devices feed it two different voltages; the part carries neither."""
    attrs = _contract(JACK)["attrs"]
    assert not {"input-voltage", "current-max-a", "voltage"} & set(attrs)


# --- 2. the four placements, and their ratings ----------------------------------

def test_the_jack_is_placed_on_exactly_these_four_devices():
    """The census: every placement of the jack in the library, and nothing
    composes it inside another part."""
    found = set()
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for view in (d.get("views") or {}).values():
            for p in ((view or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") == JACK:
                    found.add(f"{f.parts[-3]}/{f.parts[-2]}")
    assert found == set(PLACED) and len(found) == 4
    composed = []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        composed += [p for p in c.get("parts") or [] if p.get("ref") == JACK]
    assert composed == []


@EACH_DEVICE
def test_each_placement_states_what_its_device_is_fed(device):
    _view, _pid, _cfg, volts, amps, quoted = PLACED[device]
    attrs = _placement(device).get("attrs") or {}
    assert attrs == {"input-voltage": volts, "current-max-a": amps}
    prov = _device(device)["provenance"]["dc-in-rating"]
    assert prov["confidence"] == "datasheet"
    note = " ".join(prov["note"].split())
    assert quoted in note, note
    assert "`input-voltage`" in note and "`current-max-a`" in note
    assert "no barrel size" in note


def test_the_ratings_differ_which_is_why_they_are_not_the_parts():
    volts = {PLACED[d][3] for d in PLACED}
    amps = {PLACED[d][4] for d in PLACED}
    assert volts == {"12 VDC", "5 VDC"} and amps == {1.0, 3.0}


def test_the_attribute_names_are_ones_the_library_already_used():
    """`input-voltage` and `current-max-a` are not new vocabulary: a DC power
    entry module already states both, in these forms."""
    attrs = _contract("nokia/lpwr-f@1")["attrs"]
    assert isinstance(attrs["input-voltage"], str) and attrs["input-voltage"].endswith("VDC")
    assert isinstance(attrs["current-max-a"], (int, float))


# --- 3. the slots -----------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def test_the_barrel_plug_is_the_one_part_that_mates_dc_barrel(comps):
    assert sorted(r for r in comps if _contract(r).get("mates") == IFACE) == [PLUG]
    assert [r for r in comps if _contract(r).get("interface") == IFACE] == [JACK]


@EACH_DEVICE
def test_each_device_publishes_a_slot_that_offers_exactly_the_barrel_plug(device):
    view, pid = PLACED[device][:2]
    d = _device(device)
    lib = render_mod.Library([str(LIB)])
    cages = render_mod.cage_entries(d, view, lib, render_mod._pluggable_families(),
                                    render_mod._pluggable_candidates([LIB]), {})
    slot = [c for c in cages if c["id"] == pid]
    assert len(slot) == 1, (device, [c["id"] for c in cages])
    slot = slot[0]
    assert slot["kind"] == "connector" and slot["interface"] == IFACE
    assert slot["accepts"] == [PLUG]
    assert slot["lift"] == 0.0 and slot["default"] is None


# --- 4. the plug --------------------------------------------------------------------

def test_it_is_a_plug_that_mates_dc_barrel():
    d = _contract(PLUG)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE and "interface" not in d
    assert d["conforms"] == "barrel-plug" and d["unplaced"]
    assert d["attrs"] == {"media": "barrel", "connector": IFACE}
    assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
    entry = std()[d["conforms"]]
    assert entry["depth"] == pytest.approx(OVERALL)
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"]) == (8.2, 8.2)
    assert d["size-confidence"] == {"w": "drawing", "h": "drawing"} and d["size-notes"]


def test_it_states_no_voltage_and_no_current_and_claims_no_device():
    d = _contract(PLUG)
    assert not {"input-voltage", "current-max-a", "voltage", "current"} & set(d["attrs"])
    p = d["provenance"]
    assert " ".join(p["rating"].split()).startswith("NONE STATED")
    nominal = " ".join(p["nominal"].split())
    assert "A NOMINAL SIZE CHOSEN FOR THE LIBRARY" in nominal
    assert "THE RIGHT PLUG FOR A GIVEN DEVICE IS NOT CLAIMED" in nominal


def test_its_fields_are_the_cable():
    f = _contract(PLUG)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(CABLE_OD)
    assert f["jacket-color"]["default"] == "#1c1c1c"


def test_the_solids_chain_from_the_jack_face_to_the_stub():
    """The flange sits on the face of the jack, the grip starts where it ends,
    and the stub where the grip ends: no gap, no overlap, nothing else."""
    f = feats()
    assert list(f) == CHAIN
    assert not f["flange"].get("lift") and rear(f["flange"]) == pytest.approx(FLANGE)
    for a, b in zip(CHAIN, CHAIN[1:]):
        assert float(f[b]["lift"]) == pytest.approx(rear(f[a])), (a, b)
    assert f["stub"]["cyl"] == pytest.approx(STUB)
    # the whole barrel is in the jack: what stands in front is overall less it
    assert rear(f["grip"]) == pytest.approx(OVERALL - BARREL)
    assert "color" not in f["stub"]


def test_the_cable_leaves_from_the_stub():
    d = _contract(PLUG)
    cps = d["connection-points"]
    assert cps["cable"]["on"] == "stub" and cps["cable"]["at"] == cps["mate"]["at"]
    assert cps["mate"]["at"] == pytest.approx([d["size"]["w"] / 2, d["size"]["h"] / 2])


def test_the_skin_is_three_circles_and_the_stub_is_bound_to_the_fields():
    root = ET.parse(_skin_path(PLUG)).getroot()
    drawn = [e for e in root.iter() if e is not root]
    assert [e.get("id") for e in drawn] == CHAIN
    assert all(e.tag.endswith("circle") for e in drawn)
    stub = drawn[-1]
    assert stub.get("data-r-from") == "cable-od"
    assert stub.get("data-fill-from") == "jacket-color"
    assert float(stub.get("r")) == pytest.approx(CABLE_OD / 2)
    # the grip is the 8.2 box; the flange, 7.8, is inside it
    assert float(drawn[1].get("r")) * 2 == pytest.approx(8.2)
    assert float(drawn[0].get("r")) * 2 == pytest.approx(7.8)


def test_the_seated_depth_ruling_is_recorded_and_the_jack_models_no_depth():
    """Fails by design when common/dc-barrel@1 gains a depth or a relief: the
    plug's provenance says it has neither."""
    jack = _contract(JACK)
    assert "d" not in jack["size"] and "relief" not in jack
    text = " ".join(_contract(PLUG)["provenance"]["seated-depth"].split())
    assert "MEASURED FROM THE FACE THE JACK PRESENTS" in text
    assert "33.5 - 9.5 = 24" in text
    assert "THE JACK AS MODELLED STATES NO DEPTH" in text and JACK in text


# --- 5. seated on a real device ----------------------------------------------------

def _render(tmp, device, edit):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    edit(d)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / name / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(o)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return name, o


def _config(d):
    return next(k for k, v in d["configurations"].items() if v.get("default")) \
        if any(v.get("default") for v in d["configurations"].values()) \
        else next(iter(d["configurations"]))


SEATED_ON = ["telco-systems/tm-280", "nokia/xs-010x-r"]


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("barrelplug")
    out = {}
    for device in SEATED_ON:
        view, pid = PLACED[device][:2]
        chosen = {}

        def edit(d, chosen=chosen, pid=pid):
            chosen["config"] = _config(d)
            d["configurations"][chosen["config"]]["occupants"] = {pid: PLUG}
        name, o = _render(tmp, device, edit)
        configs = json.loads((o / f"{name}.configs.json").read_text())
        root = ET.parse(face_file(o, name, chosen["config"], view)).getroot()
        out[device] = (root, {c: p for p in root.iter() for c in p}, configs)
    assert set(out) == set(SEATED_ON)
    return out


def _seat(seated, device):
    root, parents, configs = seated[device]
    pid = PLACED[device][1]
    host, occ = by_path(root, pid), by_path(root, f"{pid}-occupant")
    assert occ.get("data-ref", "").startswith(PLUG), occ.get("data-ref")
    assert host.get("data-ref", "").startswith(JACK), host.get("data-ref")
    return parents, host, occ, configs


def _nodes(occ):
    got = {}
    for e in occ.iter():
        for n in CHAIN:
            if (e.get("id") or "") == f"{occ.get('id')}--{n}":
                assert n not in got
                got[n] = e
    assert list(got) == CHAIN, sorted(got)
    return got


def _front(parents, el):
    return lift_of(parents, el) + float(el.get("data-z-cyl"))


def _diameter(parents, c):
    cx, cy, r = (float(c.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, c), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return x1 - x0


@pytest.mark.parametrize("device", SEATED_ON)
def test_it_seats_on_the_centre_of_the_bore(seated, device):
    parents, host, occ, configs = _seat(seated, device)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    assert device_point(parents, host, (6.0, 6.5)) == pytest.approx((hx, hy), abs=EPS)
    assert_same_turn(parents, occ, host)
    view, pid = PLACED[device][:2]
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["accepts"] == [PLUG] and slot["occupant"] == PLUG
    assert tuple(slot["mate"]) == pytest.approx((hx, hy), abs=1e-3)


@pytest.mark.parametrize("device", SEATED_ON)
def test_the_seated_plug_stands_off_by_the_ruling(seated, device):
    """The flange starts on the face of the jack; the grip ends overall less
    the barrel in front of it, and the stub 30 beyond that. Nothing is a pit."""
    parents, host, occ, _ = _seat(seated, device)
    el = _nodes(occ)
    base = lift_of(parents, el["flange"])
    assert base == pytest.approx(lift_of(parents, host), abs=EPS)
    assert _front(parents, el["flange"]) - base == pytest.approx(FLANGE, abs=EPS)
    assert _front(parents, el["grip"]) - base == pytest.approx(OVERALL - BARREL, abs=EPS)
    assert _front(parents, el["stub"]) - base == pytest.approx(OVERALL - BARREL + STUB, abs=EPS)
    for a, b in zip(CHAIN, CHAIN[1:]):
        assert lift_of(parents, el[b]) == pytest.approx(_front(parents, el[a]), abs=EPS)
    for e in occ.iter():
        assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")
    assert _diameter(parents, el["stub"]) == pytest.approx(CABLE_OD, abs=EPS)


def test_a_placements_cable_od_sets_the_stub(tmp_path):
    device = "halny/hlx-tgv"
    view, pid = PLACED[device][:2]
    od = 3.2
    chosen = {}

    def edit(d):
        chosen["config"] = _config(d)
        d["views"][view]["components"]["placements"].append(
            {"ref": PLUG, "id": "adaptor-cord", "mate-to": pid,
             "attrs": {"cable-od": od, "jacket-color": "#e8e8e8"}})
    name, o = _render(tmp_path, device, edit)
    root = ET.parse(face_file(o, name, chosen["config"], view)).getroot()
    parents = {c: p for p in root.iter() for c in p}
    occ, host = by_path(root, "adaptor-cord"), by_path(root, pid)
    assert occ.get("data-ref", "").startswith(PLUG)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    el = _nodes(occ)
    assert _diameter(parents, el["stub"]) == pytest.approx(od, abs=EPS)
    assert el["stub"].get("fill") == "#e8e8e8"
    # only the stub follows the cable
    assert float(el["grip"].get("r")) * 2 == pytest.approx(8.2)
