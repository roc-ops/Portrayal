"""Barrier terminal blocks seat a lug per pole (#789, second part).

docs/connectors-dc-terminal-design.md section 12. Each terminal screw of a
barrier block is a part of its own, common/terminal-screw-34@1 or
common/terminal-screw-38@1, that presents the nominal `terminal-stud`
interface; the block composes one per pole as `lug-1` to `lug-3` and so
publishes each pole as a nested slot. generic/ring-lug@1, a one-hole
insulated ring terminal on a stub of wire lying in the plane of the face,
seats there.

Held to the real library and to builds made here: nothing is rasterised and
nothing reads library/dist.
"""
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from portrayal.artifacts import face_file
from test_coax_slots import _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_lifted_seat_js import build_components, mismatches, skin_file, spec_of
from test_nested_occupants import (assert_same_turn, by_path, device_matrix,
                                   device_point, own_mate)
from test_nested_slots_js import built_occupant

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
SVG = "{http://www.w3.org/2000/svg}"
IFACE, LUG = "terminal-stud", "generic/ring-lug@1"
POLES = ("lug-1", "lug-2", "lug-3")
# a stub lying in the plane of the face is 10, not the 30 of one that points
# at the viewer (docs/connectors-dc-terminal-design.md section 12.4)
STUB = 10.0

# block -> (its seat part, head diameter, head height, pole top, lip top,
#           the three screw axes in the block's frame, the pole elements)
# The axes, the head sizes and the heights are the figures each block drew
# and built for its screws BEFORE they became parts: the block must still
# compile to them.
BLOCKS = {
    "common/dc-terminal-24@1": dict(
        seat="common/terminal-screw-34@1", head=3.4, cyl=1.2, pole=7.9, lip=9.0,
        axes=((5.5, 7.2), (13.05, 7.2), (20.6, 7.2)), slot=1.35, size=(24.6, 14.4),
        poles={"pole-1": [2.5, 3.6], "pole-2": [10.05, 3.6], "pole-3": [17.6, 3.6]}),
    "common/dc-terminal-27@1": dict(
        seat="common/terminal-screw-38@1", head=3.8, cyl=1.4, pole=9.0, lip=10.2,
        axes=((6.6, 8.0), (14.8, 8.0), (23.0, 8.0)), slot=1.55, size=(27.5, 15.9),
        poles={"pole-1": [3.2, 3.6], "pole-2": [11.4, 3.6], "pole-3": [19.6, 3.6]}),
}
SEATS = sorted(b["seat"] for b in BLOCKS.values())
PSU = "telco-systems/tm810x-psu-dc@1"

# device -> (configuration, view, drawing path of one block, its block, the
#            configuration key of that block). The Telco supply is a module in
#            a bay, so its block is three levels down and the key is the
#            module-less path.
SEATED = {
    "edgecore/csr180": ("dc", "front", "psu1-input", "common/dc-terminal-24@1", "psu1-input"),
    "edgecore/csr200": ("dc", "front", "psu1-input", "common/dc-terminal-27@1", "psu1-input"),
    "telco-systems/tm-8104": ("dc-power", "front", "psu-1/module/terminal",
                              "common/dc-terminal-24@1", "psu-1/terminal"),
}
EACH_BLOCK = pytest.mark.parametrize("block", sorted(BLOCKS))
EACH_DEVICE = pytest.mark.parametrize("device", sorted(SEATED))
WIRED = "lug-2"


def _yaml(path):
    return yaml.safe_load(Path(path).read_text())


def _device(device):
    return _yaml(LIB / "devices" / device / "device.yaml")


def feats(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


# --- 1. the registry -----------------------------------------------------------

def test_terminal_stud_is_one_nominal_connector_and_claims_no_size():
    reg = _yaml(ROOT / "spec/schemas/connectors.yaml")["interfaces"]
    std = _yaml(ROOT / "spec/schemas/standards.yaml")["standards"]
    entry = reg[IFACE]
    assert entry["standard"] == IFACE and IFACE in std
    note = entry["note"]
    for words in ("ONE nominal connector", "vary by product", "claims no size",
                  "attribute of the placement", LUG, "two-hole lug"):
        assert words in note, words
    # the registry entry claims no envelope
    assert "w" not in std[IFACE] and "h" not in std[IFACE]
    assert "NO ENVELOPE IS CLAIMED" in std[IFACE]["notes"]
    lug = std["ring-lug"]
    assert (lug["w"], lug["h"], lug["depth"]) == (5.5, 27.4, 4.5)
    assert "FV2-MS3" in lug["source"] and "NOT A FIGURE FROM ANY PLACING DEVICE" in lug["notes"]


def test_no_barrier_block_states_a_stud_size():
    """No document held for a device that places a barrier block states the
    size of its terminal screws, so none of them carries `stud-size`. The
    attribute arrived with the ground studs, whose documents do print sizes
    (test_ground_stud_lugs.py holds every placement that states one)."""
    files = [LIB / "devices" / d / "device.yaml" for d in
             ("edgecore/csr180", "edgecore/csr200", "telco-systems/tm-8104",
              "telco-systems/tm-8106")]
    files += [f for f in (LIB / "components").rglob("v*/contract.yaml")]
    assert len(files) > 4
    for f in files:
        assert not re.search(r"\bstud-size\s*:", f.read_text()), f


# --- 2. the seat parts -----------------------------------------------------------

@EACH_BLOCK
def test_the_seat_is_the_screw_itself(block):
    b = BLOCKS[block]
    c = _contract(b["seat"])
    assert c["class"] == "screw" and c["interface"] == IFACE
    assert "mates" not in c and "conforms" not in c and "behaviour" not in c
    assert "media" not in (c.get("attrs") or {})
    assert c["size"] == {"w": b["head"], "h": b["head"]}
    r = b["head"] / 2
    # the barriers fix the pole: the lug on a terminal screw does not turn (#829)
    assert c["connection-points"]["mate"] == {"at": [r, r], "direction": "front", "on": "head",
                                              "turns": [0]}
    assert feats(b["seat"])["head"]["cyl"] == b["cyl"]
    assert "lift" not in feats(b["seat"])["head"]
    root = ET.parse(_skin_path(b["seat"])).getroot()
    head = root.find(f"{SVG}circle[@id='head']")
    assert [float(head.get(k)) for k in ("cx", "cy", "r")] == [r, r, r]
    assert root.find(f"{SVG}path[@id='slot']") is not None


def test_the_screws_that_present_terminal_stud_are_these_two_and_one_lug_mates_it():
    """The `class: screw` parts that present the interface are the two
    terminal screws. The ground studs present it too (`class: ground`,
    test_ground_stud_lugs.py); they are not terminal screws and are left to
    their own census. So does the 10-32 stud of the SR-1 DC terminal block,
    which a pair host composes two to a pole (#828, test_grounding_devices.py)."""
    presents, mates = [], []
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = _yaml(f)
        ref = f"{f.parents[2].name}/{c['name']}@{c['version'].split('.')[0]}"
        if c.get("interface") == IFACE and c.get("class") == "screw":
            presents.append(ref)
        if c.get("mates") == IFACE:
            mates.append(ref)
    assert sorted(presents) == sorted([*SEATS, "nokia/sr-1-dc-stud@1"]) and len(SEATS) == 2
    assert mates == [LUG]


# --- 3. the blocks ---------------------------------------------------------------

@EACH_BLOCK
def test_the_block_composes_a_seat_on_each_screw_and_states_no_interface(block):
    b = BLOCKS[block]
    c = _contract(block)
    assert "interface" not in c and "mates" not in c
    assert c["class"] == "inlet" and c["attrs"] == {"media": "dc-terminal"}
    assert (c["size"]["w"], c["size"]["h"]) == b["size"]
    # every element id it had, where it was
    assert {k: v["at"] for k, v in c["elements"].items()} == b["poles"]
    assert "dc-in" in c["connection-points"] and "mate" not in c["connection-points"]
    parts = c["parts"]
    assert [p["id"] for p in parts] == list(POLES)
    r = b["head"] / 2
    for p, (x, y) in zip(parts, b["axes"]):
        assert p["ref"] == b["seat"] and p["lift"] == b["pole"]
        assert p["at"] == pytest.approx([x - r, y - r], abs=EPS)
        assert "rotate" not in p
    # the lift IS the pole's top face
    f = feats(block)
    assert {f[k]["out"] for k in b["poles"]} == {b["pole"]}
    assert f["lip-bottom"]["out"] == f["lip-top"]["out"] == b["lip"]
    assert not [n for n in f if n.startswith("screw")]
    assert "screw" not in _skin_path(block).read_text()


@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


@EACH_BLOCK
def test_the_block_publishes_exactly_its_three_poles_as_slots(comps, block):
    b = BLOCKS[block]
    cages = comps[block]["cages"]
    assert [c["id"] for c in cages] == list(POLES)
    for c, axis in zip(cages, b["axes"]):
        assert c["kind"] == "connector" and c["interface"] == IFACE
        assert c["accepts"] == [LUG] and c["default"] is None
        assert c["mate"] == pytest.approx(list(axis), abs=EPS)
        # a lug starts where the head ends
        assert c["lift"] == pytest.approx(b["pole"] + b["cyl"], abs=EPS)
        assert c["lift"] >= b["lip"]
        assert not c["rotate"] and c["media"] is None


def test_the_census_of_blocks_and_seats(comps):
    """Counted off the library, with non-zero counts: the devices that place
    a barrier block, the supply that composes one, and the seats they make."""
    placed = {}
    for f in sorted((LIB / "devices").rglob("device.yaml")):
        d = _yaml(f)
        for body in (d.get("views") or {}).values():
            for p in ((body or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") in BLOCKS:
                    key = f"{f.parents[1].name}/{f.parent.name}"
                    placed.setdefault(key, []).append(p["ref"])
    assert placed == {"edgecore/csr180": ["common/dc-terminal-24@1"] * 2,
                      "edgecore/csr200": ["common/dc-terminal-27@1"] * 2}
    composing = sorted(r for r in comps
                       if any(p.get("ref") in BLOCKS for p in _contract(r).get("parts") or []))
    assert composing == [PSU]
    seated_by = sorted(f"{f.parents[1].name}/{f.parent.name}"
                       for f in (LIB / "devices").rglob("device.yaml") if PSU in f.read_text())
    assert seated_by == ["telco-systems/tm-8104", "telco-systems/tm-8106"]
    seats = sum(len(comps[r]["cages"]) for refs in placed.values() for r in refs)
    assert seats == 12
    assert sum(len(comps[b]["cages"]) for b in BLOCKS) == 6


def test_the_telco_supply_says_nothing_states_what_it_takes():
    c = _contract(PSU)
    assert "NOTHING HELD STATES" in c["provenance"]["terminals"]
    assert [p["id"] for p in c["parts"] if p["ref"] in BLOCKS] == ["terminal"]


def test_the_nokia_block_lands_a_two_hole_lug_on_each_pole():
    """Not one of these blocks: each pole is a pair of studs that one two-hole
    lug spans (#828), held in test_grounding_devices.py."""
    c = _contract("nokia/sr-1-dc-terminal-block@1")
    assert "interface" not in c
    assert {p["ref"] for p in c["parts"]} == {"nokia/sr-1-dc-pole@1"}


# --- 4. the lug ------------------------------------------------------------------

def test_it_is_a_lug_that_mates_terminal_stud():
    c = _contract(LUG)
    assert c["kind"] == "component" and c["class"] == "port"
    assert c["mates"] == IFACE and c["conforms"] == "ring-lug"
    assert "behaviour" not in c and "interface" not in c
    assert c["size"] == {"w": 5.5, "h": 27.4}          # no depth
    assert c["attrs"] == {"media": "ring-lug", "connector": IFACE}
    assert c["unplaced"]
    assert c["connection-points"] == {"mate": {"at": [2.75, 2.75], "direction": "front"},
                                      "cable": {"at": [2.75, 27.4], "direction": "down"}}


def test_its_fields_are_two_colours_and_no_wire_size():
    c = _contract(LUG)
    assert sorted(c["fields"]) == ["barrel-color", "wire-color"]
    assert c["fields"]["wire-color"]["default"] == "#1c1c1c"
    assert c["fields"]["barrel-color"]["default"] == "#3250d2"
    why = c["provenance"]["wire-od"]
    assert "NOT A FIELD" in why and "data-r-from" in why and "`bar`" in why
    assert "NOT CLAIMED" in c["provenance"]["nominal"]
    assert "MAY TURN IT FURTHER" in c["provenance"]["orientation"] and "#829" in c["provenance"]["orientation"]
    assert "10 LONG" in c["provenance"]["wire"] and "#805" in c["provenance"]["cable-point"]


def test_the_skin_is_a_tongue_a_sleeve_a_wire_and_a_head():
    root = ET.parse(_skin_path(LUG)).getroot()
    ids = [e.get("id") for e in root if e.get("id")]
    assert ids == ["tongue", "sleeve", "wire", "head"]      # farthest first
    sleeve, wire = root.find(f"{SVG}rect[@id='sleeve']"), root.find(f"{SVG}rect[@id='wire']")
    num = lambda e, *ks: [float(e.get(k)) for k in ks]
    assert num(sleeve, "x", "y", "width", "height") == [0.5, 8.4, 4.5, 9.0]
    assert num(wire, "x", "y", "width", "height") == [1.25, 17.4, 3.0, STUB]
    # the wire leaves along the long axis of the part, on the hole's axis
    assert 1.25 + 3.0 / 2 == 0.5 + 4.5 / 2 == 2.75
    assert sleeve.get("data-fill-from") == "barrel-color"
    assert wire.get("data-fill-from") == "wire-color"
    assert not [e for e in root.iter() if e.get("data-r-from")]
    head = root.find(f"{SVG}g[@id='head']/{SVG}circle")
    assert num(head, "cx", "cy", "r") == [2.75, 2.75, 1.9]


def test_the_lugs_solids_stack_from_the_seat_and_nothing_is_below_it():
    f = feats(LUG)
    assert list(f) == ["tongue", "head", "sleeve", "wire"]
    assert f["tongue"]["out"] == 0.8 and f["tongue"]["shape"] is True
    assert f["head"]["lift"] == f["tongue"]["out"] and f["head"]["cyl"] == 1.4
    assert f["sleeve"]["bar"] == 4.5 and "lift" not in f["sleeve"]
    assert f["wire"]["bar"] == 3.0
    # the wire is concentric with the sleeve
    assert f["wire"]["lift"] + f["wire"]["bar"] / 2 == pytest.approx(f["sleeve"]["bar"] / 2)
    for feat in f.values():
        assert feat.get("lift", 0) >= 0 and "sink" not in feat


# --- 5. built: the bare blocks, and a lug on one pole -------------------------------

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


def _face(o, name, device):
    config, view = SEATED[device][:2]
    root = ET.parse(face_file(o, name, config, view)).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Each device twice: as the library holds it, and with a lug on the
    middle pole of one block."""
    out = {}
    for device, (config, view, path, block, key) in SEATED.items():
        name, o = _render(tmp_path_factory.mktemp("bare"), device, lambda d: None)
        bare = _face(o, name, device)

        def edit(d, config=config, key=key):
            d["configurations"][config].setdefault("occupants", {})[f"{key}/{WIRED}"] = LUG
        name, o = _render(tmp_path_factory.mktemp("wired"), device, edit)
        out[device] = (bare, _face(o, name, device))
    assert set(out) == set(SEATED)
    return out


def _centre(parents, el, local):
    return device_point(parents, el, local)


@EACH_DEVICE
def test_the_bare_block_compiles_to_the_screws_it_always_drew(built, device):
    """The compiled geometry of an empty block is what it was when the block
    drew its own screws: three slotted heads on the same axes, the same size,
    painted after the poles, standing from the pole top to the same height."""
    (root, parents), _ = built[device]
    path, block = SEATED[device][2:4]
    b = BLOCKS[block]
    host = by_path(root, path)
    assert host.get("data-ref", "").startswith(block)
    kids = [e for e in host if e.get("id")]
    order = [e.get("id").rsplit("--", 1)[1] for e in kids]
    assert order == ["body", "lip-top", "lip-bottom", "mid", "pole-1", "pole-2", "pole-3",
                     "lug-1", "lug-2", "lug-3"], order
    assert not [e for e in root.iter() if (e.get("data-ref") or "").startswith(LUG)]
    r = b["head"] / 2
    for pole, (x, y) in zip(POLES, b["axes"]):
        seat = by_path(root, f"{path}/{pole}")
        head = seat.find(f"{SVG}circle")
        cx, cy, rr = (float(head.get(k)) for k in ("cx", "cy", "r"))
        assert rr == r
        assert (head.get("fill"), head.get("stroke"), head.get("stroke-width")) == \
            ("#c3c9cf", "#5b6167", "0.2")
        assert _centre(parents, seat, (cx, cy)) == pytest.approx(
            _centre(parents, host, (x, y)), abs=EPS)
        assert lift_of(parents, head) - lift_of(parents, host) == pytest.approx(b["pole"])
        assert float(head.get("data-z-cyl")) == b["cyl"]
        slot = seat.find(f"{SVG}path")
        a = b["slot"]
        want = f"M {round(r - a, 2)} {r} H {round(r + a, 2)} M {r} {round(r - a, 2)} V {round(r + a, 2)}"
        assert slot.get("d") == want
        assert (slot.get("stroke"), slot.get("stroke-width"), slot.get("stroke-linecap")) == \
            ("#5b6167", "0.3", "round")
        assert slot.get("data-z-cyl") is None and slot.get("data-z-out") is None
    # and the rest of the block's relief is where it was
    z = {e.get("id").rsplit("--", 1)[1]: e.get("data-z-out") for e in kids if e.get("data-z-out")}
    assert float(z["lip-bottom"]) == float(z["lip-top"]) == b["lip"]
    assert {float(z[p]) for p in b["poles"]} == {b["pole"]}


def _lug(built, device):
    _, (root, parents) = built[device]
    path, block = SEATED[device][2:4]
    host = by_path(root, path)
    occ = by_path(root, f"{path}/{WIRED}-occupant")
    assert occ.get("data-ref", "").startswith(LUG)
    assert occ.get("data-for") == f"{path}/{WIRED}"
    return root, parents, host, occ, BLOCKS[block]


def _node(occ, name):
    hits = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--{name}"]
    assert len(hits) == 1, name
    return hits[0]


@EACH_DEVICE
def test_one_pole_is_wired_and_its_neighbours_are_empty(built, device):
    root, parents, host, occ, b = _lug(built, device)
    lugs = [e for e in root.iter() if (e.get("data-ref") or "").startswith(LUG)]
    assert lugs == [occ]
    path = SEATED[device][2]
    for pole in POLES:
        assert by_path(root, f"{path}/{pole}").get("data-ref", "").startswith(b["seat"])
    assert not [e for e in root.iter() if e.get("data-for") in
                (f"{path}/lug-1", f"{path}/lug-3")]


@EACH_DEVICE
def test_the_lug_seats_on_the_screw_axis_with_its_wire_leaving_downward(built, device):
    root, parents, host, occ, b = _lug(built, device)
    axis = b["axes"][POLES.index(WIRED)]
    hx, hy = device_point(parents, host, axis)
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    assert_same_turn(parents, occ, host)
    wire = _node(occ, "wire")
    x, y, w, h = (float(wire.get(k)) for k in ("x", "y", "width", "height"))
    x0, y0, x1, y1 = box(apply(device_matrix(parents, wire),
                               [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]))
    # the wire is on the screw's axis, wholly below it, and runs down the face
    assert (x0 + x1) / 2 == pytest.approx(hx, abs=EPS)
    assert y0 > hy and y1 - y0 == pytest.approx(STUB) and x1 - x0 == pytest.approx(3.0)
    # and it leaves over the block's lower edge, toward the legend
    _, _, _, by1 = box(apply(device_matrix(parents, host),
                             [(0, 0), (b["size"][0], b["size"][1])]))
    sleeve = _node(occ, "sleeve")
    sy = device_point(parents, sleeve, (float(sleeve.get("x")), float(sleeve.get("y"))))[1]
    assert hy < sy < by1 < y1 and y0 == pytest.approx(sy + 9.0)
    cable = [e for e in occ if e.get("data-cp") == "cable"]
    assert len(cable) == 1 and cable[0].get("data-cp-dir") == "down"
    cx, cy = device_point(parents, occ, [float(v) for v in cable[0].get("data-cp-at").split()])
    assert cx == pytest.approx(hx, abs=EPS) and cy == pytest.approx(y1, abs=EPS)


@EACH_DEVICE
def test_the_seated_solids_clear_the_host_screw_and_the_lips(built, device):
    """Read off the compiled depths. The host's head ends where the lug
    starts, so no solid of the lug shares its volume, and every solid of the
    lug starts at or above the lips its wire crosses."""
    root, parents, host, occ, b = _lug(built, device)
    base = lift_of(parents, host)
    seat = by_path(root, f"{SEATED[device][2]}/{WIRED}")
    head = seat.find(f"{SVG}circle")
    host_top = lift_of(parents, head) + float(head.get("data-z-cyl")) - base
    assert host_top == pytest.approx(b["pole"] + b["cyl"])
    zero = lift_of(parents, occ) - base
    assert zero == pytest.approx(host_top)
    assert zero >= b["lip"]
    tongue, lhead = _node(occ, "tongue"), _node(occ, "head")
    sleeve, wire = _node(occ, "sleeve"), _node(occ, "wire")
    # `out` is absolute from the face the block is on; the others are lifts
    assert float(tongue.get("data-z-out")) - base == pytest.approx(zero + 0.8)
    spans = {
        "tongue": (zero, float(tongue.get("data-z-out")) - base),
        "head": (lift_of(parents, lhead) - base,
                 lift_of(parents, lhead) - base + float(lhead.get("data-z-cyl"))),
        "sleeve": (lift_of(parents, sleeve) - base,
                   lift_of(parents, sleeve) - base + float(sleeve.get("data-z-bar"))),
        "wire": (lift_of(parents, wire) - base,
                 lift_of(parents, wire) - base + float(wire.get("data-z-bar"))),
    }
    assert spans["head"][0] == pytest.approx(spans["tongue"][1])
    assert spans["head"][1] - spans["head"][0] == pytest.approx(1.4)
    assert spans["sleeve"] == pytest.approx((zero, zero + 4.5))
    assert spans["wire"] == pytest.approx((zero + 0.75, zero + 3.75))
    for name, (lo, hi) in spans.items():
        assert lo >= host_top - EPS, (name, lo, host_top)      # not inside the host's head
        assert lo >= b["lip"] - EPS, (name, lo, b["lip"])      # nor inside a lip
        assert hi > lo
    for e in occ.iter():
        assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")


def test_a_placements_colours_paint_the_wire_and_the_sleeve(tmp_path):
    device = "edgecore/csr200"
    config, view, path, block, key = SEATED[device]

    def edit(d):
        d["configurations"][config].setdefault("occupants", {})[f"{key}/lug-1"] = {
            "ref": LUG, "attrs": {"wire-color": "#2e8b3d", "barrel-color": "#c62828"}}
        d["configurations"][config]["occupants"][f"{key}/lug-3"] = LUG
    name, o = _render(tmp_path, device, edit)
    root, parents = _face(o, name, device)
    one, three = (by_path(root, f"{path}/{p}-occupant") for p in ("lug-1", "lug-3"))
    assert _node(one, "wire").get("fill") == "#2e8b3d"
    assert _node(one, "sleeve").get("fill") == "#c62828"
    assert _node(three, "wire").get("fill") == "#1c1c1c"
    assert _node(three, "sleeve").get("fill") == "#3250d2"
    # a colour changes no size
    for occ in (one, three):
        assert float(_node(occ, "wire").get("width")) == 3.0
        assert _node(occ, "sleeve").get("data-z-bar") == "4.5"
    assert not [e for e in root.iter() if e.get("data-for") == f"{path}/lug-2"]


# --- 6. the kit: its own slot walk offers the seats, and seats a lug in one -------

KIT_SCRIPT = ROOT / "spec/tests/js/terminal-lugs.mjs"
KIT_FACES = ["edgecore/csr180", "telco-systems/tm-8104"]


@pytest.fixture(scope="module")
def kit(built, tmp_path_factory):
    """kit/swap.js run under node against the BARE compiled faces, with the
    index and the skins built here. No skip: a machine without node fails."""
    assert shutil.which("node"), "node is needed to run the kit's slot walk"
    dist = tmp_path_factory.mktemp("lugs-dist")
    comps = build_components(dist)
    faces, cages, asks, bays = {}, {}, {}, {}
    for device in KIT_FACES:
        config, view, path, block, key = SEATED[device]
        (root, _), _ = built[device]
        faces[device] = spec_of(root)
        cages[device] = []          # every stud seat is a NESTED slot, none is the device's
        asks[device] = {"slot": f"{path}/{WIRED}", "ref": LUG}
        d = _device(device)
        bays[device] = [{"id": b["id"]} for b in
                        (((d["views"][view] or {}).get("components") or {}).get("bays") or [])]
    payload = {"components": list(comps.values()), "faces": faces, "cages": cages, "asks": asks,
               "bays": bays,
               "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                         for r in (LUG, *SEATS)}}
    p = subprocess.run(["node", str(KIT_SCRIPT)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(KIT_SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    assert set(got) == set(KIT_FACES)
    for name, g in got.items():
        assert "error" not in g, g.get("error")
    return got


@pytest.mark.parametrize("device", KIT_FACES)
def test_the_kits_slot_walk_offers_every_pole_of_every_block(kit, built, device):
    config, view, path, block, key = SEATED[device]
    b = BLOCKS[block]
    (root, parents), _ = built[device]
    blocks = sorted(e.get("data-path") for e in root.iter()
                    if (e.get("data-ref") or "").startswith(block))
    assert len(blocks) == 2 and path in blocks
    studs = {e["id"]: e for e in kit[device]["studs"]}
    assert sorted(studs) == sorted(f"{blk}/{p}" for blk in blocks for p in POLES)
    assert sorted(kit[device]["offered"]) == sorted(studs)
    one = studs[f"{path}/{WIRED}"]
    # the configuration key is the drawing path less the bay's `module` segment
    assert one["key"] == f"{key}/{WIRED}"
    assert one["kind"] == "connector" and one["interface"] == IFACE
    assert one["accepts"] == [LUG] and one["default"] is None
    assert one["modulePath"] == path and one["carrier"] == block
    host = by_path(root, path)
    assert one["lift"] == pytest.approx(lift_of(parents, host) + b["pole"] + b["cyl"])
    assert one["mate"] == pytest.approx(list(b["axes"][POLES.index(WIRED)]))


@pytest.mark.parametrize("device", KIT_FACES)
def test_the_kit_seats_a_lug_exactly_as_the_build_does(kit, built, device):
    path = SEATED[device][2]
    slot = f"{path}/{WIRED}"
    _, (wired, _) = built[device]
    want = built_occupant(wired, slot)
    assert want["ref"] == LUG
    bad = mismatches([{"name": device, "built": {slot: want}}],
                     [{"name": device, "seated": {slot: kit[device]["lug"]}}])
    assert not bad, "\n".join(bad)
    g = kit[device]
    assert g["occRef"] and g["occRef"].startswith(LUG)
    assert g["again"] == 1, "a second swap stacked a second lug"
    assert g["others"] and set(g["others"]) == {0}, "a neighbouring pole was wired"
    assert g["left"] == 0, "emptying the pole left a lug"


@pytest.mark.parametrize("device", KIT_FACES)
def test_the_kit_seated_lug_carries_its_four_solids_at_their_depths(kit, built, device):
    """What relief.js is handed for the lug the kit seated: the tongue, the
    head, the sleeve and the wire, each with the depth figure the 3D build
    reads, on a group lifted to the top of the host screw."""
    path, block = SEATED[device][2:4]
    b = BLOCKS[block]
    lug = kit[device]["lug"]
    (root, parents), _ = built[device]
    host_lift = lift_of(parents, by_path(root, path))
    zero = b["pole"] + b["cyl"]
    assert float(lug["attrs"]["data-z-lift"]) == pytest.approx(zero)
    z = {c["a"]["id"].rsplit("--", 1)[1]: c["a"] for c in lug["children"]
         if c["a"].get("id") and any(k.startswith("data-z-") for k in c["a"])}
    assert sorted(z) == ["head", "sleeve", "tongue", "wire"]
    # `out` is absolute from the face the block is on; the rest stack on lifts
    assert float(z["tongue"]["data-z-out"]) == pytest.approx(host_lift + zero + 0.8)
    assert z["tongue"]["data-z-shape"] == "1"
    assert (float(z["head"]["data-z-lift"]), float(z["head"]["data-z-cyl"])) == (0.8, 1.4)
    assert float(z["sleeve"]["data-z-bar"]) == 4.5 and "data-z-lift" not in z["sleeve"]
    assert (float(z["wire"]["data-z-lift"]), float(z["wire"]["data-z-bar"])) == (0.75, 3.0)
    # no `data-z-color` on the two painted solids: 3D takes the fill, which is
    # the field's colour
    assert "data-z-color" not in z["sleeve"] and "data-z-color" not in z["wire"]


def test_the_3d_pass_seats_a_lug_on_a_supply_in_a_bay(kit):
    """The explorer's 3D scene is cut from faces rewritten by seatViews. A
    seat on a supply in a bay is named by its drawing path, which holds
    `/module/`, and the pass seats it."""
    t = kit["telco-systems/tm-8104"]["threeD"]
    assert t["named"] == ["front"]
    assert t["viewsApplied"] == 1 and t["viewsSeated"] == 1
    assert t["faceApplied"] == 1 and t["faceSeated"] == 1


def test_the_3d_pass_seats_a_lug_on_a_block_placed_on_the_device(kit):
    """A pole of a block placed straight on the device, `psu1-input/lug-2`, is
    claimed by no bay and no cage of any view: the block is a plain placement
    that publishes slots and is not itself a cage. viewsToRewrite (kit/swap.js)
    names every view for such a key (#814), so the pass that cuts the 3D scene
    seats the lug exactly as the per-face pass and the 2D explorer do."""
    t = kit["edgecore/csr180"]["threeD"]
    assert t["faceApplied"] == 1 and t["faceSeated"] == 1
    assert not t["faceRefused"] and not t["faceFailed"]
    assert t["named"] == ["front"]
    assert t["viewsApplied"] == 1 and t["viewsSeated"] == 1
