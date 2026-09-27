"""The coax plugs build as solids, and the stub is as thick as its cable (#650,
docs/connectors-coax-design.md section 5).

Read off the compiled SVG the way kit/relief.js reads it (the helpers are
test_head_3d's and test_nested_occupants'): a raised node runs from its summed
`data-z-lift` to its ABSOLUTE `data-z-out`; a `cyl` from its summed lift for
`data-z-cyl`, at a radius of half the short side of its face box (`mmRect`).

test_coax_plugs pins where each plug seats (the mate points coincide) and that
its coupling front sits on the jack's mated plane. This file is what that
leaves out:

- every seated plug's coupling, relief boot and stub are right-side-out
  solids, chained end to end, the stub ending 30 behind its own lift;
- the same holds for a plug in a port drawn at rotate 180, which also turns
  with its port;
- the stub is built at the default `cable-od`, and at a placement's own.
"""
import shutil
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_coax_plugs import EACH, LIB, NODES, PLUGS, ROOT, SEATS, SWAPS, doc, seated  # noqa: F401
from test_head_3d import apply, box, lift_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)

EPS = 1e-6
STUB = 30.0


def front(parents, el):
    """Where relief.js builds the node's face nearest the viewer."""
    if el.get("data-z-out") is not None:
        return float(el.get("data-z-out"))
    return lift_of(parents, el) + float(el.get("data-z-cyl"))


def face_box(parents, el):
    """The node's box on the face, as mmRect sees it."""
    if el.tag.endswith("circle"):
        cx, cy, r = (float(el.get(k)) for k in ("cx", "cy", "r"))
    else:
        raise AssertionError(f"{el.get('id')}: the stub is drawn as a circle")
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    return box(apply(device_matrix(parents, el), pts))


def nodes(occ):
    """The three relief nodes of a seated plug, by skin id."""
    got = {}
    for e in occ.iter():
        eid = e.get("id") or ""
        for n in NODES:
            if eid == f"{occ.get('id')}--{n}":
                assert n not in got, (n, eid)
                got[n] = e
    assert set(got) == set(NODES), sorted(got)
    return got


def features(ref):
    return {f["node"]: f for f in doc(ref)["relief"]["features"]}


def assert_solids(parents, occ, ref):
    """Right side out, end to end: coupling, then boot, then a 30 mm stub."""
    el = nodes(occ)
    seen = 0
    for e in occ.iter():
        if e.get("data-z-out") is not None:
            seen += 1
            assert float(e.get("data-z-out")) - lift_of(parents, e) > EPS, (ref, e.get("id"))
        elif e.get("data-z-cyl") is not None:
            seen += 1
            assert float(e.get("data-z-cyl")) > EPS, (ref, e.get("id"))
    assert seen >= len(NODES), (ref, seen)
    # the plug's base: where its coupling starts (no plug lifts its coupling)
    feats = features(ref)
    assert not feats["coupling"].get("lift"), ref
    base = lift_of(parents, el["coupling"])
    # each named node has a positive depth extent
    for n in NODES:
        assert front(parents, el[n]) - lift_of(parents, el[n]) > EPS, (ref, n)
    # the boot starts on the coupling's rear, the stub on the boot's
    assert lift_of(parents, el["relief-boot"]) == pytest.approx(
        front(parents, el["coupling"]), abs=EPS), ref
    assert lift_of(parents, el["stub"]) == pytest.approx(
        front(parents, el["relief-boot"]), abs=EPS), ref
    # the stub's rear is its lift plus 30, and that lift is the contract's
    stub_lift = lift_of(parents, el["stub"])
    assert front(parents, el["stub"]) == pytest.approx(stub_lift + STUB, abs=EPS), ref
    assert stub_lift - base == pytest.approx(feats["stub"]["lift"], abs=EPS), ref
    return el


def seat_of(seated, ref):
    root, parents, _ = seated[ref]
    host = SEATS[ref][4]
    occ = by_path(root, f"{host}-occupant")
    assert occ.get("data-ref", "").startswith(ref), (ref, occ.get("data-ref"))
    return parents, occ


# --- 1. solids ------------------------------------------------------------------

@EACH
def test_the_seated_plug_builds_right_side_out(seated, ref):
    parents, occ = seat_of(seated, ref)
    assert_solids(parents, occ, ref)


@EACH
def test_the_seat_carries_a_depth(seated, ref):
    """Not a flat-panel pass: every jack but SMA and SMB presents at a plane in
    front of its face, so those seats are measured at a nonzero base. SMA and
    SMB present at the jack's own face, so their coupling starts exactly at
    the jack placement's own lift (test_coax_plugs.MATED_PLANE gives 0.0)."""
    parents, occ = seat_of(seated, ref)
    base = lift_of(parents, nodes(occ)["coupling"])
    if ref in ("generic/sma-plug@1", "generic/smb-plug@1"):
        root = seated[ref][0]
        host = by_path(root, SEATS[ref][4])
        assert base == pytest.approx(lift_of(parents, host), abs=EPS), (ref, base)
    else:
        assert base > EPS, (ref, base)


# --- 2. a plug in a turned port -------------------------------------------------

# The only coax ports the library draws turned are SMB: the MX80's MIC-3D-8DS3-E3
# places its upper row (port-0-0, -2, ... -14) at rotate 180. Seated in MIC 1/0.
ROTATED = ("juniper/mx80", "base", "front", {"mic-1-0": "juniper/mic-3d-8ds3-e3@1"},
           "mic-1-0/module/port-0-0", "generic/smb-plug@1")


@pytest.fixture(scope="module")
def rotated(tmp_path_factory):
    device, config, view, bays, host, ref = ROTATED
    tmp = tmp_path_factory.mktemp("coaxrot")
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"][config]
    cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = {host.replace("/module/", "/"): ref}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / "o"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(o)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(o / f"{name}.{config}.{view}.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


def test_the_rotated_port_is_turned_in_the_library():
    """The premise: the card still draws that port at 180 and holds SMB."""
    mic = doc(ROTATED[3]["mic-1-0"])
    port = [p for p in mic["parts"] if p.get("id") == "port-0-0"]
    assert len(port) == 1 and port[0].get("rotate") == 180
    assert port[0]["ref"] == PLUGS[ROTATED[5]][2]


def test_a_plug_in_a_turned_port_seats_and_turns_with_it(rotated):
    root, parents = rotated
    host = by_path(root, ROTATED[4])
    occ = by_path(root, f"{ROTATED[4]}-occupant")
    assert occ.get("data-ref", "").startswith(ROTATED[5])
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)
    # and the port really is turned in the device frame: x runs backwards
    m = device_matrix(parents, host)
    assert m[0][0] == pytest.approx(-1) and m[1][1] == pytest.approx(-1), m


def test_a_plug_in_a_turned_port_builds_right_side_out(rotated):
    root, parents = rotated
    occ = by_path(root, f"{ROTATED[4]}-occupant")
    el = assert_solids(parents, occ, ROTATED[5])
    # the coupling front on the jack's face (SMB's mated plane is 0)
    host = by_path(root, ROTATED[4])
    assert lift_of(parents, el["coupling"]) == pytest.approx(lift_of(parents, host), abs=0.05)
    # the stub is centred on the seat
    x0, y0, x1, y1 = face_box(parents, el["stub"])
    hx, hy = device_point(parents, host, cage_mate(host))
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((hx, hy), abs=EPS)


# --- 3. the stub's diameter -----------------------------------------------------

def stub_diameter(parents, stub):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box; a circle's
    box is square, so both sides are the diameter."""
    x0, y0, x1, y1 = face_box(parents, stub)
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


@EACH
def test_the_stub_is_the_default_cable_od(seated, ref):
    parents, occ = seat_of(seated, ref)
    stub = nodes(occ)["stub"]
    want = doc(ref)["fields"]["cable-od"]["default"]
    assert stub_diameter(parents, stub) == pytest.approx(want, abs=EPS), ref
    assert float(stub.get("r")) * 2 == pytest.approx(want, abs=EPS), ref


# A placement's attrs set the field (an occupant carries only a ref): a BNC plug
# placed directly, `mate-to` the jack, on the ASR 9901's GPS 1PPS port with that
# port swapped to a BNC bezel as in test_coax_plugs' SWAPS.
OVERRIDE = ("generic/bnc-plug@1", "cisco/asr-9901", "front", "gps-1pps", 6.1)


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    ref, device, view, host, od = OVERRIDE
    tmp = tmp_path_factory.mktemp("coaxod")
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    places = d["views"][view]["components"]["placements"]
    hits = [p for p in places if p.get("id") == host]
    assert len(hits) == 1, (device, view, host)
    hits[0]["ref"] = SWAPS[ref]
    places.append({"ref": ref, "id": "coax-plug", "mate-to": host, "attrs": {"cable-od": od}})
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / "o"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(o)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(o / f"{name}.base.{view}.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


def test_the_override_is_not_the_default():
    ref, od = OVERRIDE[0], OVERRIDE[4]
    assert doc(ref)["fields"]["cable-od"]["default"] != pytest.approx(od, abs=0.1)


def test_a_placements_cable_od_sets_the_stub(overridden):
    root, parents = overridden
    ref, _, _, host_id, od = OVERRIDE
    occ = by_path(root, "coax-plug")
    assert occ.get("data-ref", "").startswith(ref)
    assert float(occ.get("data-cable-od")) == pytest.approx(od)
    # it is seated, not merely placed
    host = by_path(root, host_id)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    el = assert_solids(parents, occ, ref)
    stub = el["stub"]
    # the compiled circle and the cyl the kit builds from it
    assert float(stub.get("r")) * 2 == pytest.approx(od, abs=EPS)
    assert stub_diameter(parents, stub) == pytest.approx(od, abs=EPS)
    # only the stub follows the cable: the boot keeps its drawn size
    boot = el["relief-boot"]
    assert boot.tag.endswith("circle"), (
        f"{ref} relief-boot is a {boot.tag}; this check reads a circle's r")
    assert float(boot.get("r")) * 2 != pytest.approx(od, abs=0.01)
