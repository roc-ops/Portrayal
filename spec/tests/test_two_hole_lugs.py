"""A two-hole lug across a pair of studs (#828), and the sized ground screws
the pairs are made of (#830).

docs/connectors-dc-terminal-design.md section 13.7. Three interfaces in
spec/schemas/connectors.yaml - `stud-pair-5-8`, `stud-pair-3-4`, `stud-pair-1` -
each SPAN two `terminal-stud` seats, the mechanism `lc-duplex` uses for two LC
bores: a pair host composes two studs at the interface's pitch and presents the
pair at their midpoint, at the height the studs present; one lug part per pitch
mates it, drawn across, and the order the host composes its studs in is the
axis the lug's wire leaves along.

Held to the real library and to builds made here, on a tmp copy of the Edgecore
AGR110 with every pair host placed twice on its rear - side by side and stood on
end - and a lug on each. Nothing reads library/dist.
"""
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import lint, manifest
from portrayal import render as render_mod
from test_coax_slots import _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_lifted_seat_js import build_components, mismatches, skin_file, spec_of
from test_nested_occupants import assert_same_turn, by_path, device_matrix, device_point
from test_nested_slots_js import built_occupant

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SPEC = ROOT / "spec"
RENDER = SPEC / "tools/portrayal/render.py"
EPS = 1e-6
RING = "generic/ring-lug@1"

# interface -> (pitch, the lug that mates it)
PAIRS = {
    "stud-pair-5-8": (15.875, "generic/two-hole-lug-5-8@1"),
    "stud-pair-3-4": (19.05, "generic/two-hole-lug-3-4@1"),
    "stud-pair-1": (25.4, "generic/two-hole-lug-1@1"),
}
# host -> (interface, stud part, the height the studs present at)
HOSTS = {
    "common/ground-stud-pair-5-8-m6@1": ("stud-pair-5-8", "common/ground-screw-m6@1", 4.6),
    "common/ground-stud-pair-5-8-1-4@1": ("stud-pair-5-8", "common/ground-screw-1-4@1", 3.66),
    "common/ground-stud-pair-3-4-1-4@1": ("stud-pair-3-4", "common/ground-screw-1-4@1", 3.66),
    "common/ground-stud-pair-1-1-4@1": ("stud-pair-1", "common/ground-screw-1-4@1", 3.66),
    "juniper/mx-ground-stud-pair-5-8@1": ("stud-pair-5-8", "juniper/mx-ground-stud@1", 8.0),
    "juniper/mx-ground-stud-pair-3-4@1": ("stud-pair-3-4", "juniper/mx-ground-stud@1", 8.0),
}
# screw -> (head diameter, head height) from the standard each cites
SCREWS = {"common/ground-screw-m6@1": (12.0, 4.6),
          "common/ground-screw-1-4@1": (12.5, 3.66)}
# lug -> (tongue width, overall length without the stub, tab thickness, barrel OD)
LUGS = {"generic/two-hole-lug-5-8@1": (11.68, 54.61, 2.03, 7.87),
        "generic/two-hole-lug-3-4@1": (10.67, 52.32, 1.27, 5.59),
        "generic/two-hole-lug-1@1": (12.19, 66.29, 2.03, 7.87)}

lint.STANDARDS.update(lint.load_yaml(SPEC / "schemas/standards.yaml")["standards"])


def _yaml(path):
    return yaml.safe_load(Path(path).read_text())


def _file(ref, root=LIB):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return root / "components" / ns / name / f"v{major}" / "contract.yaml"


def _errors(fn, ref, code, root=LIB):
    f = _file(ref, root)
    with lint.collecting() as got:
        fn(f, _yaml(f), [str(root), str(LIB)])
    return [e for e in got.errors if f"[{code}]" in e]


def _mates(ref):
    """{stud id: its composed mate point} in the host's own frame."""
    c = _contract(ref)
    out = {}
    for q in c["parts"]:
        core = _contract(q["ref"])
        out[q["id"]] = manifest.seat_point(q["at"], core["size"], q.get("rotate"),
                                           core["connection-points"]["mate"]["at"])
    return out


# --- 1. the vocabulary -------------------------------------------------------------

def test_the_registry_is_loaded():
    """Every pitch assertion below is vacuous on an empty registry."""
    assert lint.STANDARDS.get("two-hole-lug-5-8", {}).get("pitch")


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_a_pair_interface_spans_two_studs_at_its_pitch(iface):
    reg = _yaml(SPEC / "schemas/connectors.yaml")["interfaces"]
    std = _yaml(SPEC / "schemas/standards.yaml")["standards"]
    e = reg[iface]
    assert e["spans"] == {"interface": "terminal-stud", "count": 2}
    # the interface cites the lug's entry, which carries the pitch, as
    # `lc-duplex` cites the bore's
    lug = PAIRS[iface][1]
    assert e["standard"] == lug.split("/")[1].split("@")[0] and lug in e["note"]
    assert _contract(lug)["conforms"] == e["standard"]
    assert float(std[e["standard"]]["pitch"]) == PAIRS[iface][0]
    assert std[e["standard"]]["pitch-kind"] == "target"
    # #829 gives these `turns`; this change does not
    assert "turns" not in e


# --- 2. the sized screws -----------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(SCREWS))
def test_a_sized_screw_presents_a_stud_on_top_of_its_head(ref):
    dk, k = SCREWS[ref]
    c = _contract(ref)
    assert c["interface"] == "terminal-stud" and c["class"] == "ground"
    assert c["size"] == {"w": dk, "h": dk}
    assert manifest.presented_interface(c, _contract) == (
        "terminal-stud", [dk / 2, dk / 2], pytest.approx(k))
    assert "behaviour" not in c and "registry" in c["provenance"]["size"]


def test_the_nominal_ground_screw_is_untouched():
    """#830: the owner kept common/ground-lug@1 unsized; the sized parts sit
    beside it and nothing that placed it changed."""
    c = _contract("common/ground-lug@1")
    assert c["version"] == "1.4.1" and c["size"] == {"w": 7.0, "h": 14.0}


# --- 3. the pair hosts -------------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(HOSTS))
def test_a_pair_host_composes_two_studs_at_the_interface_pitch(ref):
    iface, stud, top = HOSTS[ref]
    pitch = PAIRS[iface][0]
    c = _contract(ref)
    assert c["interface"] == iface and c["class"] == "ground"
    assert [(q["id"], q["ref"]) for q in c["parts"]] == [("1", stud), ("2", stud)]
    assert manifest.spanned_slots(c, _contract, render_mod._connector_registry()) == ["1", "2"]
    m = _mates(ref)
    assert math.dist(m["1"], m["2"]) == pytest.approx(pitch, abs=1e-9)
    assert m["1"][1] == m["2"][1] and m["1"][0] < m["2"][0]       # left to right
    _, at, lift = manifest.presented_interface(c, _contract)
    assert at == pytest.approx([(m["1"][0] + m["2"][0]) / 2, m["1"][1]])
    assert lift == pytest.approx(top)
    # each stud presents at that same height, on its own
    assert manifest.presented_interface(_contract(stud), _contract)[2] == pytest.approx(top)
    assert manifest.spanning_axis(c, _contract, render_mod._connector_registry()) == 0


@pytest.mark.parametrize("ref", sorted(HOSTS))
def test_l116_is_clean_for_every_pair_host(ref):
    assert _errors(lint.lint_component_spanned_geometry, ref, "L116") == []
    assert _errors(lint.lint_component_spanned_exclusion, ref, "L115") == []


def _copy(root, ref, name, edit):
    dst = root / "components" / "test" / name / "v1"
    shutil.copytree(_file(ref).parent, dst)
    f = dst / "contract.yaml"
    c = _yaml(f)
    c["name"], c["version"] = name, "1.0.0"
    c.pop("unplaced", None)
    edit(c)
    f.write_text(yaml.safe_dump(c, sort_keys=False, allow_unicode=True))
    return f"test/{name}@1"


def test_l116_refuses_a_pair_off_its_pitch(tmp_path):
    """The MX chassis were drawn at 13.2 and 14.0 against 5/8 in.: a host at
    such a pitch presents no pair a lug fits."""
    def drawn(c):
        c["parts"][1]["at"] = [13.2, 0]
        c["connection-points"]["mate"]["at"] = [3.5 + 6.6, 3.5]
    ref = _copy(tmp_path, "juniper/mx-ground-stud-pair-5-8@1", "close-pair", drawn)
    got = _errors(lint.lint_component_spanned_geometry, ref, "L116", tmp_path)
    assert got and "13.2" in got[0] and "15.875" in got[0], got


def test_l116_refuses_a_pair_presenting_below_its_studs(tmp_path):
    """The depth arm reads what each stud PRESENTS, the top of the stud, not
    only where the stud is placed. A pair presenting at the panel would seat
    its lug inside the studs."""
    def sunk(c):
        c["connection-points"]["mate"].pop("seat-out")
    ref = _copy(tmp_path, "juniper/mx-ground-stud-pair-5-8@1", "sunk-pair", sunk)
    got = _errors(lint.lint_component_spanned_geometry, ref, "L116", tmp_path)
    assert len(got) == 2 and "presents at 8" in got[0], got


def test_l116_still_reads_an_lc_bore_at_its_placed_lift():
    """The LC adapters' bores present at their own face, so the generalised
    depth arm reads them exactly as before."""
    for ref in ("common/lc-duplex-adapter@6", "common/lc-duplex-v-adapter@6"):
        assert _errors(lint.lint_component_spanned_geometry, ref, "L116") == []


# --- 4. the lugs -------------------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_a_two_hole_lug_mates_its_pair_drawn_across(iface):
    pitch, ref = PAIRS[iface]
    W, L, T, OD = LUGS[ref]
    c = _contract(ref)
    assert c["mates"] == iface and c["class"] == "port" and "behaviour" not in c
    assert c["size"] == {"w": pytest.approx(L + 10), "h": W} and "d" not in c["size"]
    assert c["conforms"] == ref.split("/")[1].split("@")[0]
    assert sorted(c["fields"]) == ["barrel-color", "wire-color"]
    mate = c["connection-points"]["mate"]["at"]
    assert mate == pytest.approx([W / 2 + pitch / 2, W / 2])
    assert c["connection-points"]["cable"] == {"at": [pytest.approx(L + 10), W / 2],
                                               "direction": "right"}
    assert _errors(lint.lint_component_spanned_geometry, ref, "L116") == []
    # the two heads the skin draws over the holes are the pair, either side of `mate`
    skin = ET.parse(_skin_path(ref)).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    for i, x in ((1, mate[0] - pitch / 2), (2, mate[0] + pitch / 2)):
        circle = skin.find(f"{ns}g[@id='head-{i}']/{ns}circle")
        assert (float(circle.get("cx")), float(circle.get("cy"))) == \
            pytest.approx((x, W / 2), abs=1e-4), i
    feats = {f["node"]: f for f in c["relief"]["features"]}
    assert feats["tongue"]["out"] == T and feats["barrel"]["bar"] == OD
    assert feats["head-1"]["lift"] == feats["head-2"]["lift"] == T


def test_l116_refuses_a_lug_drawn_on_end():
    """The canonical axis is ACROSS; a lug stood on end would be wrong on
    every host, because each host's own axis arrives with the seat."""
    c = _contract("generic/two-hole-lug-5-8@1")
    on_end = {**c, "size": {"w": c["size"]["h"], "h": c["size"]["w"]},
              "connection-points": {"mate": {"at": [5.84, 13.7775]}}}
    with lint.collecting() as got:
        lint.lint_component_spanned_geometry(Path("x/contract.yaml"), on_end, [str(LIB)])
    assert [e for e in got.errors if "[L116]" in e]


# --- 5. a device: every host placed twice, a lug on each ----------------------------

# placement id -> (host, rotate). Spread along the AGR110's rear, below the
# top edge; they cross its supplies and fans, which a render does not mind.
PLACED = {}
_x = 20.0
for _i, _host in enumerate(sorted(HOSTS)):
    for _rot in (0, 90):
        PLACED[f"pair-{_i}-{_rot}"] = (_host, _rot, [_x, 5.0])
        _x += 35.0
CONFIG, VIEW = "ac", "rear"


def _device_with(tmp, occupants):
    dev = shutil.copytree(LIB / "devices/edgecore/agr110", tmp / "agr110") / "device.yaml"
    d = _yaml(dev)
    pl = d["views"][VIEW]["components"]["placements"]
    for n, (pid, (host, rot, at)) in enumerate(PLACED.items()):
        p = {"ref": host, "id": pid, "at": at, "group": "grounding", "rel-pos": 10 + n}
        if rot:
            p["rotate"] = rot
        pl.append(p)
    d["configurations"][CONFIG]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def _render(dev, out):
    return warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                           "--out", str(out)], capture_output=True, text=True)


def _lug_of(pid):
    return PAIRS[HOSTS[PLACED[pid][0]][0]][1]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = {}
    for name, occ in (("bare", {}), ("seated", {p: _lug_of(p) for p in PLACED})):
        tmp = tmp_path_factory.mktemp(name)
        dev = _device_with(tmp, occ)
        r = _render(dev, tmp / "o")
        assert r.returncode == 0, r.stderr[-800:]
        root = ET.parse(tmp / "o" / f"agr110.{CONFIG}.{VIEW}.svg").getroot()
        out[name] = (root, {c: p for p in root.iter() for c in p},
                     json.loads((tmp / "o" / "agr110.configs.json").read_text()))
    return out


def test_each_pair_is_a_slot_of_the_device_with_its_studs_as_bores(built):
    _, _, index = built["bare"]
    cages = {c["id"]: c for c in index["cages"][VIEW]}
    for pid, (host, rot, at) in PLACED.items():
        iface = HOSTS[host][0]
        c = cages[pid]
        assert c["kind"] == "connector" and c["interface"] == iface
        assert c["accepts"] == [PAIRS[iface][1]] and c["default"] is None
        assert c["bores"] == ["1", "2"]
        assert c["lift"] == pytest.approx(HOSTS[host][2])
        # the placement's own turn plus the axis the studs lie on (0)
        assert (c["rotate"] or 0) == rot


def test_the_ring_lug_is_still_offered_on_each_stud_of_a_pair():
    lib_ = render_mod.Library([str(LIB)])
    for host in HOSTS:
        cages = {c["id"]: c for c in render_mod.component_cages(
            lib_.resolve(host)[0], lib_, render_mod._pluggable_families(),
            render_mod._pluggable_candidates([str(LIB)]), render_mod._connector_registry())}
        assert sorted(cages) == ["1", "2"], host
        for c in cages.values():
            assert c["interface"] == "terminal-stud" and c["accepts"] == [RING], host


def _lug(built, pid):
    root, parents, _ = built["seated"]
    host = by_path(root, pid)
    occ = by_path(root, f"{pid}-occupant")
    assert occ.get("data-ref", "").startswith(_lug_of(pid)) and occ.get("data-for") == pid
    return parents, host, occ


@pytest.mark.parametrize("pid", sorted(PLACED))
def test_the_lugs_holes_land_on_the_two_studs(built, pid):
    """Read off the drawing: each hole of the seated lug, carried into the
    device frame, is the axis of one stud, first hole on the first stud."""
    parents, host, occ = _lug(built, pid)
    iface = HOSTS[PLACED[pid][0]][0]
    pitch, ref = PAIRS[iface]
    W = LUGS[ref][0]
    holes = [device_point(parents, occ, (W / 2 + i * pitch, W / 2)) for i in (0, 1)]
    for sid, hole in zip(("1", "2"), holes):
        stud = by_path(_root(built), f"{pid}/{sid}")
        ref_s = stud.get("data-ref").rsplit(":", 1)[0]
        axis = _contract(ref_s)["connection-points"]["mate"]["at"]
        assert device_point(parents, stud, axis) == pytest.approx(hole, abs=EPS), sid


def _root(built):
    return built["seated"][0]


def _wire_box(parents, occ):
    wire = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--wire")
    x, y, w, h = (float(wire.get(k)) for k in ("x", "y", "width", "height"))
    return box(apply(device_matrix(parents, wire),
                     [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]))


@pytest.mark.parametrize("pid", sorted(PLACED))
def test_the_wire_leaves_along_the_pair_right_or_down(built, pid):
    """Side by side, the wire leaves to the right of the second stud; stood on
    end (rotate 90), the first stud is on top and the wire leaves downward."""
    parents, host, occ = _lug(built, pid)
    second = by_path(_root(built), f"{pid}/2")
    sx, sy = device_point(parents, second, _contract(
        second.get("data-ref").rsplit(":", 1)[0])["connection-points"]["mate"]["at"])
    x0, y0, x1, y1 = _wire_box(parents, occ)
    if PLACED[pid][1] == 0:
        assert x0 > sx and (y0 + y1) / 2 == pytest.approx(sy, abs=EPS)
    else:
        assert y0 > sy and (x0 + x1) / 2 == pytest.approx(sx, abs=EPS)
    # the lug takes its host's turn: the pair's axis is 0 in the host's frame
    assert_same_turn(parents, occ, host)


@pytest.mark.parametrize("pid", sorted(PLACED))
def test_the_lugs_solids_start_on_top_of_the_studs(built, pid):
    """3D: the occupant group is lifted to the height the studs present, and
    no solid of the lug starts below the top of either stud."""
    parents, host, occ = _lug(built, pid)
    top = HOSTS[PLACED[pid][0]][2]
    base = lift_of(parents, host)
    ends = []
    for e in host.iter():
        if e is occ or occ in [parents.get(e)]:
            continue
        if e.get("data-z-cyl") and not _inside(parents, e, occ):
            ends.append(lift_of(parents, e) + float(e.get("data-z-cyl")) - base)
    assert ends and max(ends) == pytest.approx(top)
    assert lift_of(parents, occ) - base == pytest.approx(top)
    T = LUGS[_lug_of(pid)][2]
    tongue = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--tongue")
    assert float(tongue.get("data-z-out")) - base == pytest.approx(top + T)
    for e in occ.iter():
        assert e.get("data-depth") is None and e.get("data-cavity") is None


def _inside(parents, el, anc):
    n = parents.get(el)
    while n is not None:
        if n is anc:
            return True
        n = parents.get(n)
    return False


# --- 6. L115: a pair and its studs are one level or the other ----------------------

def test_l115_refuses_a_lug_on_a_pair_and_a_ring_lug_on_one_of_its_studs(tmp_path):
    pid = next(iter(PLACED))
    dev = _device_with(tmp_path, {pid: _lug_of(pid), f"{pid}/2": RING})
    with lint.collecting() as got:
        lint.lint_device_spanned_exclusion(dev, _yaml(dev), [str(LIB)])
    errs = [e for e in got.errors if "[L115]" in e]
    assert errs and f"{pid}/2" in errs[0], errs
    r = _render(dev, tmp_path / "o")
    assert r.returncode != 0 and f"occupants/{pid}:" in r.stderr, r.stderr[-600:]


def test_l115_is_clean_for_one_level_at_a_time(tmp_path):
    pid = next(iter(PLACED))
    for n, occ in enumerate(({pid: _lug_of(pid)}, {f"{pid}/1": RING, f"{pid}/2": RING})):
        dev = _device_with(tmp_path / str(n), occ)
        with lint.collecting() as got:
            lint.lint_device_spanned_exclusion(dev, _yaml(dev), [str(LIB)])
        assert not [e for e in got.errors if "[L115]" in e], occ


# --- 7. the kit seats a lug on a pair as the build does ----------------------------

KIT_SCRIPT = SPEC / "tests/js/ground-stud-lugs.mjs"
KIT_ASKS = ("pair-4-0", "pair-4-90", "pair-0-0")


@pytest.fixture(scope="module")
def kit(built, tmp_path_factory):
    assert shutil.which("node"), "node is needed to run the kit's slot walk"
    for pid in KIT_ASKS:
        assert pid in PLACED
    dist = tmp_path_factory.mktemp("pair-dist")
    comps = build_components(dist)
    root, _, index = built["bare"]
    cases = {pid: {"face": spec_of(root), "view": VIEW, "slot": pid, "ref": _lug_of(pid),
                   "bays": index["bays"], "cages": index["cages"],
                   "ifaces": ["terminal-stud", *PAIRS]} for pid in KIT_ASKS}
    refs = {_lug_of(p) for p in KIT_ASKS} | set(HOSTS) | {h[1] for h in HOSTS.values()}
    payload = {"components": list(comps.values()), "cases": cases,
               "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                         for r in refs}}
    p = subprocess.run(["node", str(KIT_SCRIPT)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(KIT_SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    for name, g in got.items():
        assert "error" not in g, g.get("error")
    return got


@pytest.mark.parametrize("pid", KIT_ASKS)
def test_the_kit_offers_the_pair_and_its_studs(kit, pid):
    ids = {e["id"] for e in kit[pid]["studs"]}
    assert {pid, f"{pid}/1", f"{pid}/2"} <= ids
    entry = next(e for e in kit[pid]["studs"] if e["id"] == pid)
    assert entry["accepts"] == [_lug_of(pid)]


@pytest.mark.parametrize("pid", KIT_ASKS)
def test_the_kit_seats_a_two_hole_lug_exactly_as_the_build_does(kit, built, pid):
    want = built_occupant(_root(built), pid)
    bad = mismatches([{"name": pid, "built": {pid: want}}],
                     [{"name": pid, "seated": {pid: kit[pid]["lug"]}}])
    assert not bad, "\n".join(bad)
    g = kit[pid]
    assert g["again"] == 1 and g["left"] == 0
    t = g["threeD"]
    assert t["named"] == [VIEW] and t["viewsSeated"] == 1 and t["faceSeated"] == 1
    assert not t["faceRefused"] and not t["faceFailed"]
