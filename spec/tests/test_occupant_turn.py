"""A configuration can turn a seated occupant (#829).

`occupants:` takes `turn:`, RELATIVE to the seat: added after the host's own
turn and any axis a spanning host's pair runs on. The turns a host allows are
its interface's `turns` (spec/schemas/connectors.yaml) narrowed by its
presented point's own (manifest.allowed_turns): a ring lug turns freely on a
ground stud, and not at all on a barrier block's terminal screw. Where a
configuration states no turn, the build computes one (render.default_seat_turn,
rule B: down, toward the nearer side edge, the other side, up - the first that
crosses no part, bay or other seat) and publishes it per view as `seat-turns`
in configs.json, so the kit never re-derives it.

Held here: the registry and the narrowing, a two-hole interface that spans a
pair (synthetic, `turns: [0, 180]`), the seating rule at every turn on every
stud part, the refusals, the expansion carrying the turn to the drawing, the
nested Casa seat, L146 and L147, the census of defaults across the library,
what configs.json publishes, the lock, and the DCIM exports.
"""
import collections
import copy
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import devicelock, dcim_export, lint, manifest
from portrayal import render as R
from portrayal.artifacts import face_file
from test_nested_occupants import by_path, device_matrix, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
LUG = "generic/ring-lug@1"
STUDS = ("common/ground-lug@1", "common/ground-stud@1", "juniper/mx-ground-stud@1",
         "casa/shelf-ground-stud@1")
SCREWS = ("common/terminal-screw-34@1", "common/terminal-screw-38@1")
EPS = 1e-6

_lib = R.Library([str(LIB)])


def _res(ref):
    try:
        return _lib.resolve(ref)[0]
    except Exception:
        return None


def _conn():
    return R._connector_registry()


# --- 1. the turns a host allows --------------------------------------------------

def test_the_registry_lets_a_lug_turn_freely_on_a_stud_and_names_no_other_turns():
    reg = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    assert reg["terminal-stud"]["turns"] == [0, 90, 180, 270]
    # a two-hole lug across a pair (#828) may lead its wire either way ALONG
    # the pair and never across it; every other interface allows 0 alone
    pairs = ("stud-pair-5-8", "stud-pair-3-4", "stud-pair-1")
    assert all(reg[k]["turns"] == [0, 180] for k in pairs)
    assert sorted(k for k, v in reg.items() if "turns" in v) == sorted(["terminal-stud", *pairs])


@pytest.mark.parametrize("ref", STUDS)
def test_a_ground_stud_allows_the_four_right_angles(ref):
    assert manifest.allowed_turns(_res(ref), _res, _conn()) == [0, 90, 180, 270]


@pytest.mark.parametrize("ref", SCREWS)
def test_a_terminal_screw_narrows_its_interface_to_0(ref):
    c = _res(ref)
    assert c["interface"] == "terminal-stud"
    assert c["connection-points"]["mate"]["turns"] == [0]
    assert manifest.allowed_turns(c, _res, _conn()) == [0]
    # and a block that composes it forwards nothing of its own
    for block in ("common/dc-terminal-24@1", "common/dc-terminal-27@1"):
        assert manifest.allowed_turns(_res(block), _res, _conn()) == [0]


def test_a_cage_and_a_contract_presenting_nothing_allow_0_alone():
    assert manifest.allowed_turns(_res("std/sfp-ganged@1"), _res, _conn()) == [0]
    assert manifest.allowed_turns(_res(LUG), _res, _conn()) == [0]
    assert manifest.allowed_turns({}, _res, _conn()) == [0]


# A SYNTHETIC PAIR, generically: an interface that spans two studs, as a
# two-hole lug's would, allowing 0 and 180 - the lug may lead its wire either
# way along the pair and never across it. The real `stud-pair-*` interfaces
# land on another branch; the rule is the interface's `turns` whatever its
# name, so this is the proof the integrator relies on.
PAIR_REG = {"terminal-stud": {"turns": [0, 90, 180, 270]},
            "stud-pair-x": {"spans": {"interface": "terminal-stud", "count": 2},
                            "turns": [0, 180]}}
STUD = {"name": "s", "interface": "terminal-stud", "size": {"w": 4, "h": 4},
        "connection-points": {"mate": {"at": [2, 2]}}}
PAIR = {"name": "pair", "interface": "stud-pair-x", "size": {"w": 4, "h": 20},
        "connection-points": {"mate": {"at": [2, 10]}},
        "parts": [{"ref": "x/s@1", "id": "1", "at": [0, 0]},
                  {"ref": "x/s@1", "id": "2", "at": [0, 16]}]}
TWO_HOLE = {"name": "two-hole", "mates": "stud-pair-x", "size": {"w": 6, "h": 30},
            "connection-points": {"mate": {"at": [3, 3]}}}
FAKE = {"x/s@1": STUD, "x/pair@1": PAIR, "x/two-hole@1": TWO_HOLE}


def test_a_spanning_pair_allows_its_own_turns_and_a_point_narrows_them():
    res = FAKE.get
    assert manifest.allowed_turns(PAIR, res, PAIR_REG) == [0, 180]
    # the axis the pair runs on is the host's; the turn is on top of it
    axis = manifest.spanning_axis(PAIR, res, PAIR_REG)
    assert axis == 90
    assert manifest.summed_rotate(manifest.summed_rotate(None, axis), 180) == 270
    narrowed = copy.deepcopy(PAIR)
    narrowed["connection-points"]["mate"]["turns"] = [180]
    assert manifest.allowed_turns(narrowed, res, PAIR_REG) == [180]
    # a turn the interface does not list cannot be added by the point
    widened = copy.deepcopy(PAIR)
    widened["connection-points"]["mate"]["turns"] = [0, 90]
    assert manifest.allowed_turns(widened, res, PAIR_REG) == [0]


def test_a_pair_publishes_its_turns_and_its_default_never_turns_across_the_pair():
    """The slot a pair presents publishes [0, 180]; the default turn takes
    only what the pair allows, whatever is in the way."""
    seat = {"mate": [50.0, 20.0], "rotate": 90.0, "turns": [0, 180],
            "interface": "stud-pair-x", "obstacles": [], "legends": [],
            "face": {"w": 400.0, "h": 44.0}}
    t = R.default_seat_turn(seat, TWO_HOLE)
    assert t in (0, 180)
    # down from a seat turned 90 is not a turn the pair allows, so the first
    # allowed direction in rule B's order is the nearer side, left: turn 0
    assert t == 0
    # something to the left of the pair, clear of its studs: the lug goes right
    x, y = seat["mate"]
    seat["obstacles"] = [(x - 25.0, y - 1.0, x - 10.0, y + 1.0)]
    assert R.default_seat_turn(seat, TWO_HOLE) == 180


# --- 2. the seating rule ----------------------------------------------------------

def _host(ref, at=(100.0, 50.0), rotate=None):
    return {"ref": ref, "at": list(at), "rotate": rotate}


@pytest.mark.parametrize("ref", STUDS)
@pytest.mark.parametrize("host_rotate", [None, 90])
@pytest.mark.parametrize("turn", [0, 90, 180, 270])
def test_a_lug_lands_on_its_stud_at_every_turn(ref, host_rotate, turn):
    hc, oc = _res(ref), _res(LUG)
    host = _host(ref, rotate=host_rotate)
    at, orot, _lift = R.solve_seat(_lib, "t", LUG, "h", host, occ_turn=turn)
    _i, m_at, _l = manifest.presented_interface(hc, _res)
    want = manifest.seat_point(host["at"], hc["size"], host_rotate, m_at)
    got = manifest.seat_point(at, oc["size"], orot, oc["connection-points"]["mate"]["at"])
    assert got == pytest.approx(want, abs=1e-4)
    assert float(orot or 0) % 360 == (float(host_rotate or 0) + turn) % 360
    # an unturned seat draws exactly what it drew before #829
    if turn == 0:
        assert orot == R.solve_seat(_lib, "t", LUG, "h", host)[1]


@pytest.mark.parametrize("ref", SCREWS)
def test_a_turn_on_a_terminal_screw_is_refused(ref):
    with pytest.raises(ValueError, match="turn 90 is not one its host"):
        R.solve_seat(_lib, "occupants/psu1-input/lug-2", LUG, "psu1-input/lug-2",
                     _host(ref), occ_turn=90)
    # 0 is the seat's own direction and always allowed
    R.solve_seat(_lib, "t", LUG, "h", _host(ref), occ_turn=0)


def test_a_turn_on_a_cage_is_refused():
    with pytest.raises(ValueError, match=r"allows \(0\)"):
        R.solve_seat(_lib, "occupants/port-1", "generic/sfp-lc@1", "port-1",
                     _host("std/sfp-ganged@1"), occ_turn=180)


# --- 3. through a build -------------------------------------------------------------

def _render(tmp, device, occupants, config=None):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    dev.parent.mkdir(parents=True)
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    cfgs = d.setdefault("configurations", {"default": {"default": True}})
    config = config or next(iter(cfgs))
    cfgs[config].setdefault("occupants", {}).update(occupants)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / name / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(o)], capture_output=True, text=True)
    return name, o, config, r


def _face(o, name, config, view):
    root = ET.parse(face_file(o, name, config, view)).getroot()
    return root, {c: p for p in root.iter() for c in p}


def _angle(parents, el):
    import math
    m = device_matrix(parents, el)
    return math.degrees(math.atan2(m[1][0], m[0][0])) % 360


@pytest.fixture(scope="module")
def mx150(tmp_path_factory):
    """mx150: a ring lug on each stud of its ground pair (#828 made the two
    studs one `juniper/mx-ground-stud-pair-3-4@1`, `ground-studs`; each stud is
    still a slot of its own, one level in), one stating `turn: 90`, one stating
    none."""
    name, o, config, r = _render(tmp_path_factory.mktemp("mx150"), "juniper/mx150", {
        "ground-studs/1": {"ref": LUG, "turn": 90}, "ground-studs/2": LUG})
    assert r.returncode == 0, r.stderr[-800:]
    return name, o, config


TWO_HOLE_34 = "generic/two-hole-lug-3-4@1"


def test_the_expansion_carries_a_turn_and_the_drawing_records_it(mx150):
    """The stud with no turn takes the default, up, because down crosses the
    ESD jack and both sides cross the other stud or a fan."""
    name, o, config = mx150
    root, parents = _face(o, name, config, "rear")
    for key, turn in (("ground-studs/1", 90), ("ground-studs/2", 180)):
        host, occ = by_path(root, key), by_path(root, f"{key}-occupant")
        assert occ.get("data-seat-turn") == str(turn)
        assert (_angle(parents, occ) - _angle(parents, host) - turn) % 360 == pytest.approx(0, abs=1e-6)
        hx, hy = device_point(parents, host, (3.5, 3.5))
        ox, oy = device_point(parents, occ, own_mate(occ))
        assert (hx, hy) == pytest.approx((ox, oy), abs=EPS)
    idx = json.loads((o / f"{name}.configs.json").read_text())
    # the pair is a seat of its own, for the two-hole lug: it leads left, the
    # nearer edge, across the ESD jack below its second stud either way (the
    # census's pinned residual)
    assert idx["seat-turns"] == {"rear": {"ground-studs": {TWO_HOLE_34: 180},
                                          "ground-studs/1": {LUG: 0},
                                          "ground-studs/2": {LUG: 180}}}
    cages = {c["id"]: c for c in idx["cages"]["rear"]}
    assert cages["ground-studs"]["turns"] == [0, 180]
    assert cages["ground-studs"]["bores"] == ["1", "2"]
    # a slot with no choice publishes none
    assert all(c["turns"] is None for v in idx["cages"].values() for c in v
               if c["interface"] != "terminal-stud" and not c["interface"].startswith("stud-pair-"))


def _node(occ, name):
    hits = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--{name}"]
    assert len(hits) == 1, name
    return hits[0]


def test_a_lug_turned_90_lies_along_x_and_its_cable_leaves_left(mx150):
    """WHAT 3D AND A CABLE LIBRARY READ, through the composed transform (the
    CTM): every solid of the lug turned 90 runs along x, to the left of its
    stud, and the `cable` point's declared `down` comes out as left. Nothing
    in relief.js changed for it - it reads the rotate() on the group."""
    name, o, config = mx150
    root, parents = _face(o, name, config, "rear")
    host, occ = by_path(root, "ground-studs/1"), by_path(root, "ground-studs/1-occupant")
    hx, hy = device_point(parents, host, (3.5, 3.5))
    for part in ("wire", "sleeve"):
        el = _node(occ, part)
        x, y, w, h = (float(el.get(k)) for k in ("x", "y", "width", "height"))
        m = device_matrix(parents, el)
        pts = [(m[0][0] * px + m[0][1] * py + m[0][2], m[1][0] * px + m[1][1] * py + m[1][2])
               for px, py in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        assert max(xs) - min(xs) > max(ys) - min(ys), part
        assert max(xs) <= hx + EPS and (min(ys) + max(ys)) / 2 == pytest.approx(hy, abs=EPS), part
        # still a 3D solid of the same depth: a turn moves no z
        assert el.get("data-z-bar") is not None
    cable = [e for e in occ if e.get("data-cp") == "cable"]
    assert len(cable) == 1 and cable[0].get("data-cp-dir") == "down"
    m = device_matrix(parents, cable[0])
    assert (m[0][1], m[1][1]) == pytest.approx((-1.0, 0.0), abs=1e-9)   # (0, 1) -> left


def test_a_nested_stud_turns_and_its_default_is_published_by_its_path(tmp_path):
    name, o, config, r = _render(tmp_path, "casa/c40g", {
        "ground-studs-rear/stud-bl": {"ref": LUG, "turn": 270},
        "ground-studs-rear/stud-tr": LUG})
    assert r.returncode == 0, r.stderr[-800:]
    root, parents = _face(o, name, config, "rear")
    for key, turn in (("ground-studs-rear/stud-bl", 270), ("ground-studs-rear/stud-tr", 90)):
        host, occ = by_path(root, key), by_path(root, f"{key}-occupant")
        assert occ.get("data-seat-turn") == str(turn)
        assert (_angle(parents, occ) - _angle(parents, host) - turn) % 360 == pytest.approx(0, abs=1e-6)
        hx, hy = device_point(parents, host, (5.4, 5.4))
        ox, oy = device_point(parents, occ, own_mate(occ))
        assert (hx, hy) == pytest.approx((ox, oy), abs=EPS)
    idx = json.loads((o / f"{name}.configs.json").read_text())
    assert idx["seat-turns"]["rear"] == {
        "ground-studs-rear/stud-bl": {LUG: 0}, "ground-studs-rear/stud-br": {LUG: 0},
        "ground-studs-rear/stud-tr": {LUG: 90}}
    # no view that holds no turning seat is published
    assert set(idx["seat-turns"]) == {"rear"}


def test_a_turn_on_a_barrier_block_pole_fails_the_build(tmp_path):
    name, o, config, r = _render(tmp_path, "edgecore/csr180",
                                 {"psu1-input/lug-2": {"ref": LUG, "turn": 90}})
    assert r.returncode != 0
    assert "turn 90 is not one its host" in r.stderr
    # and the same pole with no turn seats the lug as it always did, with no
    # data-seat-turn: the screw turns nothing
    name, o, config, r = _render(tmp_path / "again", "edgecore/csr180",
                                 {"psu1-input/lug-2": LUG})
    assert r.returncode == 0, r.stderr[-800:]
    root, _ = _face(o, name, config, "front")
    occ = by_path(root, "psu1-input/lug-2-occupant")
    assert occ.get("data-seat-turn") is None and "rotate(" not in occ.get("transform", "")
    idx = json.loads((o / f"{name}.configs.json").read_text())
    assert "seat-turns" not in idx or not idx["seat-turns"]


# --- 4. lint -----------------------------------------------------------------------

def _occupants_lint(occupants, device="juniper/mx150"):
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    d["configurations"] = {"c": {"default": True, "occupants": occupants}}
    with lint.collecting() as got:
        lint.lint_device_occupants("device.yaml", d, [str(LIB)])
    return [e for e in got.errors if "[L146]" in e]


def test_l146_passes_an_allowed_turn_and_no_turn():
    # the MX150's studs are one level into its pair host (#828)
    assert not _occupants_lint({"ground-studs/1": {"ref": LUG, "turn": 270},
                                "ground-studs/2": LUG})
    assert not _occupants_lint({"ground-studs": {"ref": TWO_HOLE_34, "turn": 180}})
    assert not _occupants_lint({"psu1-input/lug-2": {"ref": LUG, "turn": 0}},
                               device="edgecore/csr180")


def test_l146_fails_a_turn_the_host_does_not_allow():
    bad = _occupants_lint({"psu1-input/lug-2": {"ref": LUG, "turn": 180}},
                          device="edgecore/csr180")
    assert len(bad) == 1 and "turn 180 is not one common/terminal-screw-34@1 allows (0)" in bad[0]
    # a two-hole lug turned across its pair
    bad = _occupants_lint({"ground-studs": {"ref": TWO_HOLE_34, "turn": 90}})
    assert len(bad) == 1 and \
        "turn 90 is not one juniper/mx-ground-stud-pair-3-4@1 allows (0, 180)" in bad[0], bad
    # and the nested keys the pass case uses are read, not skipped
    assert _occupants_lint({"ground-studs/1": {"ref": LUG, "turn": 45}})


def _point_lint(contract):
    with lint.collecting() as got:
        lint.lint_component_point_turns("contract.yaml", contract)
    return [e for e in got.errors if "[L147]" in e]


def test_l147_passes_the_library_and_a_narrowing():
    for ref in (*STUDS, *SCREWS, LUG):
        assert not _point_lint(_res(ref)), ref


def test_l147_fails_a_widening_a_point_that_is_not_presented_and_no_interface():
    screw = copy.deepcopy(_res("common/terminal-screw-34@1"))
    screw["interface"] = "rj45"
    screw["connection-points"]["mate"]["turns"] = [0, 90]
    assert "turns [90] are not among the turns 'rj45' allows ([0])" in _point_lint(screw)[0]
    lug = copy.deepcopy(_res(LUG))
    lug["connection-points"]["mate"]["turns"] = [0]
    assert "this part presents no interface" in _point_lint(lug)[0]
    stud = copy.deepcopy(_res("common/ground-stud@1"))
    stud["connection-points"]["other"] = {"at": [0, 0], "turns": [0]}
    assert "is presented at is 'mate'" in _point_lint(stud)[0]


# --- 5. the default, across the library ---------------------------------------------

# (the way the WIRE leaves the face, as rule B chooses) -> seats, and the
# devices they are on, for each lug. 2026-10-07, after the grounding batch
# (#828, #830) joined #829.
#
# THE RING LUG: 157 seats on 65 devices since the Eaton EVMA8365X (below); 156 on 64 before it, 155 on 63 before the EVMI2130X. On main (796eb08) the same census read
# 147 on 61; the pair hosts added eight stud seats and two devices: the MX204
# and MX304 plates now compose two screws each that a ring lug lands on (+4,
# two devices), the FX-16's two single studs became two pairs (+2), and the
# FX-8's and FX-4's single stud each became a pair (+1, +1). Every other
# converted device keeps its stud count: its studs moved one level into a pair
# host and are still seats. The Eaton EVMI2130X's M6 bonding screw, the first
# common/ground-screw-m6@1 placed on a face of its own, adds one more (down), and the
# EVMA8365X's, the same screw at the same place on its sibling's face, one more (down).
WANT = {"down": 107, "left": 27, "up": 8, "right": 21}
# THE TWO-HOLE LUG on a pair host: 59 seats on 33 devices - three on each of
# the eleven Amphenol 300CB08 panels, one on each AIS800, the seven MX, the
# LMFS-F, two on the FX-16, one on the FX-8 and FX-4, the SR-1-DC block's
# four poles (one level in), and one M4 pair on each of eight UfiSpace
# chassis (#830), every one of which leads its wire left, toward the end of
# the flank its pair sits at
WANT_PAIRS = {"down": 45, "left": 12, "up": 1, "right": 1}
NAMES = {0: "right", 90: "down", 180: "left", 270: "up"}
LEADS = {"right": 0, "down": 90, "left": 180, "up": 270}
PAIR_IFACES = ("stud-pair-5-8", "stud-pair-3-4", "stud-pair-1")
# what a default still lies across: a legend, the soft preference, where every
# direction that crosses no part crosses one
RESIDUAL = {("ufispace/s9600-102xc", "rear", "ground-2"): ("down", 0, 1),
            ("ufispace/s9601-102xc", "rear", "ground-2"): ("down", 0, 1),
            # the plate's lug, down, over a legend; up crosses the ESD jack
            ("juniper/mx304", "rear", "ground-plate"): ("down", 0, 1)}
# what a two-hole lug's default still lies across a PART, either way along its
# pair - the least bad. Both are the model's geometry, not the rule's: the
# MX150's ESD jack (y 10.4) starts under the tongue of a lug 10.67 wide across
# studs at y 6.5, and the MX480's pair stands 0.34 inside the PEM3 bay's edge.
HARD_RESIDUAL = {("juniper/mx150", "rear", "ground-studs"): ("left", 1, 0),
                 ("juniper/mx480", "rear", "ground-studs"): ("down", 1, 0)}
# the crossings the seat's own direction made, which the default must not.
# The MX150's second stud is `ground-stud-1` of main, one level into its pair.
CROSSED_BEFORE = {("supermicro/sys-111e-fwtr", "front", "ground-stud"),
                  ("supermicro/sys-111e-fdwtr", "front", "ground-stud"),
                  ("juniper/mx150", "rear", "ground-studs/2"),
                  ("edgecore/dcs500", "rear", "ground-0")}


@pytest.fixture(scope="module")
def census():
    """Every turnable seat in the library, with the lug that mates it: the
    ring lug on a stud, the two-hole lug of its pitch on a pair."""
    candidates = R._pluggable_candidates([str(LIB)])
    rows = {}
    for f in sorted((LIB / "devices").rglob("device.yaml")):
        d = yaml.safe_load(f.read_text())
        slug = f"{f.parents[1].name}/{f.parent.name}"
        for v, view in (d.get("views") or {}).items():
            for key, seat in R.turnable_seats(d, view, _lib).items():
                assert seat["interface"] in ("terminal-stud", *PAIR_IFACES), (slug, key)
                [(ref, lug)] = candidates[seat["interface"]]
                assert (ref == LUG) == (seat["interface"] == "terminal-stud")
                t = R.default_seat_turn(seat, lug)
                assert t in seat["turns"], (slug, key)
                absolute = int((seat["rotate"] + t) % 360)
                lead = LEADS[lug["connection-points"]["cable"]["direction"]]
                box = R.occupant_box(seat["mate"], lug, absolute)
                box0 = R.occupant_box(seat["mate"], lug, seat["rotate"])
                rows[(slug, v, key)] = dict(
                    lug=ref, dir=NAMES[(absolute + lead) % 360], turn=t,
                    hard=sum(R._crosses(box, o) for o in seat["obstacles"]),
                    soft=sum(R._crosses(box, o) for o in seat["legends"]),
                    hard0=sum(R._crosses(box0, o) for o in seat["obstacles"]))
    return rows


def _ring(census):
    return {k: r for k, r in census.items() if r["lug"] == LUG}


def _pairs(census):
    return {k: r for k, r in census.items() if r["lug"] != LUG}


def test_the_default_distribution_is_pinned(census):
    ring, pairs = _ring(census), _pairs(census)
    assert dict(collections.Counter(r["dir"] for r in ring.values())) == WANT
    assert len({k[0] for k in ring}) == 65   # 63, and the Eaton EVMI2130X and EVMA8365X
    assert dict(collections.Counter(r["dir"] for r in pairs.values())) == WANT_PAIRS
    assert len({k[0] for k in pairs}) == 33
    # a pair is turned only along itself
    assert {r["turn"] for r in pairs.values()} == {0, 180}


def test_no_default_crosses_a_part_a_bay_or_another_seat(census):
    assert not [k for k, r in _ring(census).items() if r["hard"]]
    hard = {k: (r["dir"], r["hard"], r["soft"]) for k, r in census.items() if r["hard"]}
    assert hard == HARD_RESIDUAL
    left = {k: (r["dir"], r["hard"], r["soft"]) for k, r in census.items()
            if r["soft"] and not r["hard"]}
    assert left == RESIDUAL


def test_a_pairs_own_studs_are_not_in_its_lugs_way():
    """A two-hole lug lands on both studs of its pair, and neither holds the
    pair's midpoint: counted as obstacles they made every direction cross
    two, and every pair in the library took the "least bad" turn. The
    Amphenol 300CB08's bottom pair has nothing else near it."""
    d = yaml.safe_load((LIB / "devices/amphenol-ns/300cb08/device.yaml").read_text())
    seat = R.turnable_seats(d, d["views"]["bottom"], _lib)["ground-bottom"]
    lug = _res("generic/two-hole-lug-5-8@1")
    for t in seat["turns"]:
        box = R.occupant_box(seat["mate"], lug, (seat["rotate"] + t) % 360)
        assert not [o for o in seat["obstacles"] if R._crosses(box, o)], t
    # one level in, a ring lug's neighbour IS in its way: the other stud
    stud = R.turnable_seats(d, d["views"]["bottom"], _lib)["ground-bottom/1"]
    assert len(stud["obstacles"]) == len(seat["obstacles"]) + 1


def test_the_four_crossings_the_seat_gave_are_gone(census):
    for k in CROSSED_BEFORE:
        assert census[k]["hard0"] >= 1, k
        assert census[k]["hard"] == 0 and census[k]["dir"] != "down", k
    # main's forty-odd were pairs of single studs, the upper lug lying across
    # the lower stud; those pairs are pair hosts now, a two-hole lug's seat.
    # Seventeen ring-lug seats still cross something at their own direction -
    # the four above, both studs of the MX240's and MX480's pairs, the MX304
    # plate's first screw, Casa's top stud, the UfiSpace S9600/S9601
    # `ground-1`, and one screw of each two-screw Edgecore plate #830 drew
    # (the AGR560, EPS112 and EPS203 `ground-1`, the DCS500 `ground-0b` and
    # `ground-1b`) - and the default clears every one. Those five are a ring
    # lug at its seat's own direction lying across the plate's OTHER screw, 16
    # to 17 away; which screw draws the earth symbol does not move them.
    crossed = {k for k, r in _ring(census).items() if r["hard0"]}
    assert len(crossed) == 17 and not [k for k in crossed if census[k]["hard"]]


def test_a_barrier_block_pole_is_no_turnable_seat():
    for device in ("edgecore/csr180", "edgecore/csr200"):
        d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
        for view in d["views"].values():
            assert not R.turnable_seats(d, view, _lib)


# --- 6. the lock and the exports ------------------------------------------------------

def test_a_configuration_turn_asks_a_patch():
    d = yaml.safe_load((LIB / "devices/juniper/mx240/device.yaml").read_text())
    cfg = next(iter(d["configurations"]))
    d["configurations"][cfg].setdefault("occupants", {})["ground-studs/1"] = LUG
    turned = copy.deepcopy(d)
    turned["configurations"][cfg]["occupants"]["ground-studs/1"] = {"ref": LUG, "turn": 270}
    versions = devicelock.component_versions(LIB)
    old, new = devicelock.entry(d, versions), devicelock.entry(turned, versions)
    assert devicelock.required_bump(old, new) == "patch"


def test_the_dcim_exports_do_not_read_a_turn():
    d = yaml.safe_load((LIB / "devices/juniper/mx240/device.yaml").read_text())
    cfg_name = next(iter(d["configurations"]))
    cfg = d["configurations"][cfg_name]
    plain = copy.deepcopy(cfg)
    plain.setdefault("occupants", {})["ground-studs/1"] = LUG
    turned = copy.deepcopy(cfg)
    turned.setdefault("occupants", {})["ground-studs/1"] = {"ref": LUG, "turn": 270}
    a = dcim_export.build(d, cfg_name, plain, None)
    b = dcim_export.build(d, cfg_name, turned, None)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
