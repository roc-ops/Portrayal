"""AC inlets are connector slots, and the cord ends that seat in them (#785,
docs/connectors-power-design.md).

The three inlets (std/c14-inlet@1, std/c20-inlet@1, std/saf-d-grid@1) each
present an interface spec/schemas/connectors.yaml now lists, so every one of
them is a slot; generic/c13-plug@1, generic/c19-plug@1 and
generic/saf-d-grid-plug@1 mate them. These run against the real library, a
components.json the indexer builds here and device copies rendered here, never
a possibly stale dist.

THE SEATED DEPTH IS A RULING, and the tests below hold the parts to it: each
plug's nose sits on the floor of the cavity its inlet MODELS, so the plug
stands its overall length less that cavity depth in front of the inlet's
face. The inlet depths for the two IEC parts are estimates; a test here fails
by design when one of them changes, because every plug figure follows it.
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
from test_coax_slots import _card_slot, _contract, _device_slot, _skin_path
from test_head_3d import apply, box, lift_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
STUB = 30.0

# interface -> (the inlet that presents it, the plug that mates it)
PAIRS = {
    "iec-c14": ("std/c14-inlet@1", "generic/c13-plug@1"),
    "iec-c20": ("std/c20-inlet@1", "generic/c19-plug@1"),
    "saf-d-grid": ("std/saf-d-grid@1", "generic/saf-d-grid-plug@1"),
}
INLET_OF = {plug: inlet for inlet, plug in PAIRS.values()}
IFACE_OF = {plug: iface for iface, (_inlet, plug) in PAIRS.items()}
PLUGS = sorted(INLET_OF)
EACH = pytest.mark.parametrize("ref", PLUGS)

# plug -> (overall length, insertion nose, the cavity depth its inlet models,
# default cable-od). The first two are the plug drawing's; the third is the
# INLET's own `size.d`, pinned here so a change to it fails and is carried
# through the plug. The nose is longer than the cavity on all three.
FIGURES = {
    "generic/c13-plug@1": (64.0, 18.0, 13.0, 8.33),
    "generic/c19-plug@1": (76.0, 20.0, 15.0, 9.65),
    "generic/saf-d-grid-plug@1": (80.5, 25.5, 17.0, 9.65),
}
# plug -> its strain relief: a `cyl` where the section is round, a box where
# it is not (the Saf-D-Grid strain relief is taller than it is wide).
ROUND_BOOT = {"generic/c13-plug@1": True, "generic/c19-plug@1": True,
              "generic/saf-d-grid-plug@1": False}


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def feats(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


def rear(f):
    """Where a relief feature ends, from the part's own face: an `out` is
    absolute, a `cyl` runs its length from its `lift`."""
    if f.get("out") is not None:
        return float(f["out"])
    return float(f.get("lift") or 0.0) + float(f["cyl"])


# --- 1. the registry -----------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_inlet_interface_is_a_connector_citing_its_standard(iface):
    reg = render_mod._connector_registry()
    assert iface in reg, iface
    inlet = _contract(PAIRS[iface][0])
    assert reg[iface]["standard"] in std(), reg[iface]
    assert reg[iface]["standard"] == inlet["conforms"]


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_inlet_presents_its_interface_at_its_face(iface):
    inlet = _contract(PAIRS[iface][0])
    assert inlet["class"] == "inlet" and inlet["interface"] == iface
    got, at, lift = presented_interface(inlet, lambda r: _contract(r))
    assert got == iface
    w, h = inlet["size"]["w"], inlet["size"]["h"]
    assert at == pytest.approx([w / 2, h / 2])
    # the slot is the inlet's own face: the ruling stands the plug off by its
    # own relief, not by a lift the inlet states
    assert lift == 0.0
    assert inlet["relief"]["cavity"] == "inlet-face"


# --- 2. the slots --------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


# A chassis-mounted inlet: a device placement of the bare std part.
CHASSIS = {
    "iec-c14": ("readylinks/gl-12xb-240d", "rear", "inlet-1"),
    "iec-c20": ("juniper/mx960", "rear", "inlet-0"),
}
# An inlet on a supply that seats in a bay: a nested slot in the PSU's own
# components.json entry. Saf-D-Grid is placed on no chassis in the library;
# its three placements are all on supplies.
PSU = {
    "iec-c14": ("ufispace/psu-401-ac@1", "inlet"),
    "iec-c20": ("ufispace/psu-162-ac@1", "inlet"),
    "saf-d-grid": ("cisco/a9k-1600w-ac@1", "inlet"),
}


@pytest.mark.parametrize("iface", sorted(CHASSIS))
def test_a_chassis_inlet_publishes_a_slot_that_offers_its_plug(iface, tmp_path):
    device, view, pid = CHASSIS[iface]
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    hits = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == pid]
    assert len(hits) == 1 and hits[0]["ref"] == PAIRS[iface][0], hits
    slot = _device_slot(device, view, pid, tmp_path)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert slot["accepts"] == [PAIRS[iface][1]], slot
    assert slot["lift"] == 0.0 and slot["default"] is None, slot


def test_no_chassis_places_a_saf_d_grid_inlet():
    """Why CHASSIS has no Saf-D-Grid row: the premise, so the gap is a fact of
    the library and not of this file."""
    hits = [f for f in (LIB / "devices").glob("*/*/device.yaml")
            if "ref: std/saf-d-grid@1" in f.read_text()]
    assert hits == []


@pytest.mark.parametrize("iface", sorted(PSU))
def test_a_psu_inlet_is_a_nested_slot_that_offers_its_plug(iface, comps):
    ref, part_id = PSU[iface]
    psu = _contract(ref)
    assert psu["kind"] == "module" and psu["class"] == "psu", ref
    part = [p for p in psu["parts"] if p["id"] == part_id]
    assert len(part) == 1 and part[0]["ref"] == PAIRS[iface][0], part
    slot = _card_slot(comps, ref, part_id)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert slot["accepts"] == [PAIRS[iface][1]], slot
    assert slot["lift"] == 0.0, slot


def test_a_panel_of_inlets_publishes_one_slot_each(comps):
    """casa/c40g-ac-inlet-panel@1 composes four inlets and forwards none of
    them (a wrapper forwards only a lone aperture), so each is its own slot
    under the panel's key."""
    slots = [c for c in comps["casa/c40g-ac-inlet-panel@1"]["cages"]
             if c["interface"] == "iec-c14"]
    assert sorted(c["id"] for c in slots) == [f"inlet-psu{n}" for n in (1, 2, 3, 4)]
    assert all(c["accepts"] == ["generic/c13-plug@1"] for c in slots)


def test_a_placed_supply_with_one_inlet_is_the_slot(tmp_path):
    """common/psu-550w@2 is PLACED on a face, not seated in a bay, and composes
    one inlet: it presents that inlet as its own, so the slot is published at
    the supply's placement in the device and not a second time on the part."""
    psu = _contract("common/psu-550w@2")
    got, _at, _lift = presented_interface(psu, lambda r: _contract(r))
    assert got == "iec-c14" and "interface" not in psu
    slot = _device_slot("smartoptics/dcp-r-9d-cs", "rear", "psu-1", tmp_path)
    assert slot["kind"] == "connector" and slot["interface"] == "iec-c14", slot
    assert "generic/c13-plug@1" in slot["accepts"], slot


def test_every_composed_inlet_is_a_slot_or_is_forwarded(comps):
    """The census: each `parts:` entry that is one of the three inlets is
    either published as a slot of the component that composes it, or is that
    component's one forwarded aperture (published where the component is
    placed). Nothing hides an inlet."""
    inlet_iface = {inlet: iface for iface, (inlet, _plug) in PAIRS.items()}
    seen = {iface: 0 for iface in PAIRS}
    forwarded = []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        for p in c.get("parts") or []:
            iface = inlet_iface.get(p.get("ref"))
            if iface is None:
                continue
            seen[iface] += 1
            cages = {x["id"]: x for x in comps[ref].get("cages") or []}
            if p["id"] in cages:
                assert cages[p["id"]]["interface"] == iface, (ref, p["id"])
                assert cages[p["id"]]["accepts"] == [PAIRS[iface][1]], (ref, p["id"])
            else:
                got, _at, _lift = presented_interface(c, lambda r: _contract(r))
                assert got == iface and not c.get("interface"), (ref, p["id"])
                forwarded.append(ref)
    # the scan measured something: the counts the issue was filed on, at least
    assert seen["iec-c14"] >= 58 and seen["iec-c20"] >= 13 and seen["saf-d-grid"] >= 3, seen
    assert "common/psu-550w@2" in forwarded


# --- 3. the plugs --------------------------------------------------------------

@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = _contract(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE_OF[ref] and "interface" not in d
    name = ref.split("/")[1].split("@")[0]
    assert d["conforms"] == name and name in std()


@EACH
def test_it_states_no_depth_and_its_length_is_in_the_registry(ref):
    d = _contract(ref)
    assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
    entry = std()[d["conforms"]]
    assert entry["depth"] == pytest.approx(FIGURES[ref][0])
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"])


@EACH
def test_its_fields_are_the_cord(ref):
    f = _contract(ref)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(FIGURES[ref][3])
    assert f["jacket-color"]["default"] == "#1c1c1c"


@EACH
def test_the_stub_is_30_long_from_the_end_of_the_strain_relief(ref):
    f = feats(ref)
    boot, stub = f["relief-boot"], f["stub"]
    assert stub["cyl"] == pytest.approx(STUB)
    assert stub["lift"] == pytest.approx(rear(boot))
    assert ("cyl" in boot) == ROUND_BOOT[ref], boot


@EACH
def test_the_solids_chain_from_the_inlet_face_to_the_stub(ref):
    """nose, then the body (in one or two steps), then the strain relief:
    each starts where the one before it ends, with no gap and no overlap. A
    grip lug is a side branch off the nose's end and is not in the chain."""
    f = feats(ref)
    chain = [n for n in ("nose", "body", "body-rear", "relief-boot", "stub") if n in f]
    assert chain[0] == "nose" and not f["nose"].get("lift")
    for a, b in zip(chain, chain[1:]):
        assert float(f[b]["lift"]) == pytest.approx(rear(f[a])), (ref, a, b)
    if "lugs" in f:
        assert float(f["lugs"]["lift"]) == pytest.approx(rear(f["nose"]))
        assert rear(f["lugs"]) < rear(f["body"])
    assert set(f) == set(chain) | ({"lugs"} if "lugs" in f else set())


@EACH
def test_the_cable_leaves_from_the_stub(ref):
    cps = _contract(ref)["connection-points"]
    assert cps["cable"]["on"] == "stub"
    assert cps["cable"]["at"] == cps["mate"]["at"]
    d = _contract(ref)
    assert cps["mate"]["at"] == pytest.approx([d["size"]["w"] / 2, d["size"]["h"] / 2])


@EACH
def test_the_stub_circle_is_bound_to_the_fields(ref):
    s = _skin_path(ref).read_text()
    for node in feats(ref):
        assert f'id="{node}"' in s, node
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub
    assert 'data-fill-from="jacket-color"' in stub
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(FIGURES[ref][3] / 2, abs=0.005)
    # L73: the node a field paints states no relief colour
    assert "color" not in feats(ref)["stub"]


# --- 4. the seated depth, in the contracts --------------------------------------

@EACH
def test_the_inlet_models_the_cavity_the_plug_was_seated_to(ref):
    """Fails by design when an inlet's depth is revised: the plug's relief
    follows it (provenance.seated-depth), so both change together."""
    inlet = _contract(INLET_OF[ref])
    assert inlet["size"]["d"] == pytest.approx(FIGURES[ref][2])


@EACH
def test_the_plug_stands_its_length_less_the_modelled_cavity(ref):
    overall, nose, cavity, _od = FIGURES[ref]
    f = feats(ref)
    # the strain relief ends at the plug's rear, overall - cavity in front of
    # the inlet face
    assert rear(f["relief-boot"]) == pytest.approx(overall - cavity)
    # and what is left of the nose in front of the face is nose - cavity: the
    # nose is longer than the cavity it is seated in
    assert nose > cavity
    assert rear(f["nose"]) == pytest.approx(nose - cavity)


@EACH
def test_the_ruling_is_recorded_in_provenance(ref):
    text = " ".join(_contract(ref)["provenance"]["seated-depth"].split())
    overall, _nose, cavity, _od = FIGURES[ref]
    assert "MODELLED CAVITY FLOOR" in text
    assert "LONGER THAN THE MODELLED CAVITY" in text
    assert "REVISIT" in text
    assert f"{overall:g} - {cavity:.1f} = {overall - cavity:.1f}" in text, text


# --- 5. seated in real inlets ----------------------------------------------------

# (plug, device, configuration, view, the host's data-path). Each plug seats
# in a chassis inlet where the library has one and in a supply's inlet in a
# bay; the two supplies in the turned bays below also turn the plug.
SEATS = [
    ("generic/c13-plug@1", "readylinks/gl-12xb-240d", "base", "rear", "inlet-1"),
    ("generic/c13-plug@1", "ufispace/s9500-30xs", "ac", "front", "psu-0/module/inlet"),
    ("generic/c19-plug@1", "juniper/mx960", "base", "rear", "inlet-0"),
    ("generic/c19-plug@1", "ufispace/s9600-32x", "ac", "rear", "psu-0/module/inlet"),
    ("generic/saf-d-grid-plug@1", "cisco/asr-9901", "ac", "rear", "pm-0/module/inlet"),
]
SEAT_IDS = [f"{s[0].split('/')[1].split('@')[0]}-in-{s[1].split('/')[1]}" for s in SEATS]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=SEAT_IDS)


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


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """Every seat in SEATS, each in a copy of its device.

    Returns {(plug, device): (svg root, parent map, configs.json)}."""
    tmp = tmp_path_factory.mktemp("accords")
    out = {}
    for ref, device, config, view, host in SEATS:
        def edit(d, config=config, host=host, ref=ref):
            cfg = d["configurations"][config]
            cfg["occupants"] = {host.replace("/module/", "/"): ref}
        name, o = _render(tmp, device, edit)
        root = ET.parse(face_file(o, name, config, view)).getroot()
        configs = json.loads((o / f"{name}.configs.json").read_text())
        out[(ref, device)] = (root, {c: p for p in root.iter() for c in p}, configs)
    assert len(out) == len(SEATS)
    return out


def _seat(seated, seat):
    ref, device, _config, _view, host_path = seat
    root, parents, configs = seated[(ref, device)]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    assert occ.get("data-ref", "").startswith(ref), occ.get("data-ref")
    assert host.get("data-ref", "").startswith(INLET_OF[ref]), host.get("data-ref")
    return parents, host, occ, configs


def _nodes(occ, ref):
    got = {}
    for e in occ.iter():
        eid = e.get("id") or ""
        for n in feats(ref):
            if eid == f"{occ.get('id')}--{n}":
                assert n not in got, eid
                got[n] = e
    assert set(got) == set(feats(ref)), sorted(got)
    return got


def _front(parents, el):
    """Where relief.js builds the node's face nearest the viewer: an ABSOLUTE
    `data-z-out`, or a `cyl`'s summed lift plus its length."""
    if el.get("data-z-out") is not None:
        return float(el.get("data-z-out"))
    return lift_of(parents, el) + float(el.get("data-z-cyl"))


@EACH_SEAT
def test_it_seats_with_its_mate_on_the_inlets_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def test_one_seat_is_in_a_turned_inlet(seated):
    """Not a flat pass: a supply's inlet is drawn turned on at least one of
    the seats above, so the turn is measured and not assumed."""
    turned = 0
    for seat in SEATS:
        parents, host, _occ, _ = _seat(seated, seat)
        m = device_matrix(parents, host)
        if abs(m[0][0] - 1) > EPS or abs(m[1][1] - 1) > EPS:
            turned += 1
    assert turned >= 2, turned


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_ruling(seated, seat):
    """The compiled depths, in the device frame: the nose starts on the
    inlet's face (the published slot lift), the strain relief ends overall -
    cavity in front of it, and the stub 30 beyond that. The cavity depth is
    read off the COMPILED inlet, not the table."""
    ref = seat[0]
    parents, host, occ, configs = _seat(seated, seat)
    overall, nose, _cavity, _od = FIGURES[ref]
    cavity = float(host.get("data-depth"))
    assert host.get("data-cavity") == "inlet-face"
    el = _nodes(occ, ref)
    base = lift_of(parents, el["nose"])
    assert base == pytest.approx(lift_of(parents, host), abs=EPS)
    assert _front(parents, el["nose"]) - base == pytest.approx(nose - cavity, abs=EPS)
    assert _front(parents, el["relief-boot"]) - base == pytest.approx(overall - cavity, abs=EPS)
    assert _front(parents, el["stub"]) - base == pytest.approx(overall - cavity + STUB, abs=EPS)


@pytest.mark.parametrize("iface", sorted(CHASSIS))
def test_the_published_slot_lift_is_where_the_build_seats_the_plug(seated, iface):
    device, view, pid = CHASSIS[iface]
    plug = PAIRS[iface][1]
    seat = next(s for s in SEATS if s[0] == plug and s[1] == device)
    parents, host, occ, configs = _seat(seated, seat)
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["occupant"] == plug
    base = lift_of(parents, _nodes(occ, plug)["nose"])
    assert slot["lift"] == pytest.approx(base, abs=EPS)
    assert tuple(slot["mate"]) == pytest.approx(
        device_point(parents, host, cage_mate(host)), abs=1e-3)


# --- 6. 3D solids ----------------------------------------------------------------

@EACH_SEAT
def test_the_seated_plug_builds_right_side_out(seated, seat):
    ref = seat[0]
    parents, _host, occ, _ = _seat(seated, seat)
    el = _nodes(occ, ref)
    raised = 0
    for e in occ.iter():
        if e.get("data-z-out") is not None:
            raised += 1
            assert float(e.get("data-z-out")) - lift_of(parents, e) > EPS, e.get("id")
        elif e.get("data-z-cyl") is not None:
            raised += 1
            assert float(e.get("data-z-cyl")) > EPS, e.get("id")
    assert raised == len(el), (raised, sorted(el))
    # nothing of the plug is a pit or a cavity
    for e in occ.iter():
        assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")
    # end to end in the compiled drawing, as in the contract
    chain = [n for n in ("nose", "body", "body-rear", "relief-boot", "stub") if n in el]
    for a, b in zip(chain, chain[1:]):
        assert lift_of(parents, el[b]) == pytest.approx(_front(parents, el[a]), abs=EPS), (a, b)


# --- 7. the stub's diameter -------------------------------------------------------

def _stub_diameter(parents, stub):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box."""
    assert stub.tag.endswith("circle"), stub.tag
    cx, cy, r = (float(stub.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, stub), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


@EACH_SEAT
def test_the_stub_is_the_default_cable_od(seated, seat):
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    stub = _nodes(occ, ref)["stub"]
    assert _stub_diameter(parents, stub) == pytest.approx(FIGURES[ref][3], abs=EPS)
    # and it is centred on the seat
    cx, cy = device_point(parents, stub, (float(stub.get("cx")), float(stub.get("cy"))))
    assert (cx, cy) == pytest.approx(device_point(parents, host, cage_mate(host)), abs=EPS)


# A placement's attrs set the field (an occupant carries only a ref): each
# plug placed directly, `mate-to` a real inlet, with a cable-od of its own.
OVERRIDES = [
    ("generic/c13-plug@1", "readylinks/gl-12xb-240d", "rear", "inlet-2", 6.6),
    ("generic/c19-plug@1", "juniper/mx960", "rear", "inlet-1", 10.9),
]


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("accordod")
    out = {}
    for ref, device, view, host, od in OVERRIDES:
        def edit(d, view=view, host=host, ref=ref, od=od):
            places = d["views"][view]["components"]["placements"]
            hits = [p for p in places if p.get("id") == host]
            assert len(hits) == 1 and hits[0]["ref"] == INLET_OF[ref], hits
            places.append({"ref": ref, "id": "cord", "mate-to": host,
                           "attrs": {"cable-od": od}})
        name, o = _render(tmp, device, edit)
        root = ET.parse(o / f"{name}.base.{view}.svg").getroot()
        out[ref] = (root, {c: p for p in root.iter() for c in p})
    return out


@pytest.mark.parametrize("case", OVERRIDES, ids=[c[0].split("/")[1] for c in OVERRIDES])
def test_a_placements_cable_od_sets_the_stub(overridden, case):
    ref, _device, _view, host_id, od = case
    assert FIGURES[ref][3] != pytest.approx(od, abs=0.1)
    root, parents = overridden[ref]
    occ, host = by_path(root, "cord"), by_path(root, host_id)
    assert occ.get("data-ref", "").startswith(ref)
    assert float(occ.get("data-cable-od")) == pytest.approx(od)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    el = _nodes(occ, ref)
    assert float(el["stub"].get("r")) * 2 == pytest.approx(od, abs=EPS)
    assert _stub_diameter(parents, el["stub"]) == pytest.approx(od, abs=EPS)
    # only the stub follows the cord: the strain relief keeps its drawn size
    boot = el["relief-boot"]
    assert boot.tag.endswith("circle")
    assert float(boot.get("r")) * 2 != pytest.approx(od, abs=0.01)
