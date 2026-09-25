"""Slots on a module's BACK: the FHD cassette rears' MPO bulkheads (B3, Task 7i).

common/mpo-flange-adapter@2 and common/mpo24-flange-adapter@2 present `mpo`
with a `mate` at the centre of their opening, `on:` the housing, so a dust cap
or an MPO plug seats in front of the housing. They sit on the BACK of every
FHD MTP cassette - the component a cassette names as `faces.rear` - and no
back had ever seated an occupant. Three things here could each go wrong
without a sound:

  - THE OPENING IS THE STANDARD ONE. The adapters drew a 13.1 x 7.0 opening
    that a 12.5 x 7.6 plug overhangs; @2 draws std/mpo@2's 12.9 x 8.0, centred
    on the mate, keyed where @1 was keyed. Read off the skin, not the contract,
    because the skin is what is drawn.
  - EVERY BACK PUBLISHES ITS SLOTS. A back composing ONE bulkhead looked like a
    wrapper forwarding its aperture (P2), whose slot is published by whatever
    places it - and nothing places a back. So the six single-MTP backs
    published nothing while the multi-MTP ones did. The census below counts
    every component publishing an `mpo` slot.
  - A KEY ON THE BACK SEATS ON THE BACK. `bay-1/mtp1` - the module-less path
    the drawing already publishes as `bay-1/module/mtp1` - is seated by the
    rear drawing, lands on the bulkhead's mate, and is not drawn on the front,
    where the same bay's `bay-1/lc01` is.

Every seating is a configured occupant on a tmp_path copy of the real device.
Each bulkhead SHIPS its cap (B3 task 8, test_shipped_caps.py), so an unkeyed
bulkhead holds the cap and a configured one holds what it names.
"""
import re
import shutil
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_nested_occupants import LIB, SPEC, device_point, effective_lift, is_inside

from portrayal import lint
from portrayal import render as R
from portrayal.components_index import named_as_faces
from portrayal.manifest import (back_parts, key_on_back, nested_key_host,
                                presented_interface, seat_point)

FLANGES = {"common/mpo-flange-adapter@2": 12, "common/mpo24-flange-adapter@2": 24}
APERTURE = "std/mpo@2"
CAP = "common/mpo-dust-cap@2"
MPO12 = "generic/mpo12-plug@1"
MPO24 = "generic/mpo24-plug@1"
PLUGS = (MPO12, MPO24)
FHD = "fs/fhd-1ufce"
CASSETTE = "fs/fhd-2mtp12-lc-os2-a@4"        # the 2 x MTP-12 LC cassette
BACK = "fs/fhd-2mtp12-lc-rear@2"             # what it names as faces.rear
MATE = [15.0, 5.5]                           # the opening's centre
HOUSING = 3.5                                # the housing's absolute `out`

# THE CENSUS: every component publishing an `mpo` slot, with its slot ids. A
# new one needs its own line here - that is the point. Ten FHD cassette backs,
# one slot per flanged bulkhead. The SIX SINGLE-MTP BACKS publish theirs only
# because a face forwards nothing (render.component_cages, `face`); the
# forwarding wrapper common/mpo-adapter@2 publishes none of its own (P2), and
# nothing composes it.
MPO_SLOTS = {
    "fs/fhd-1mtp12-sc-rear@3": ["mtp"],
    "fs/fhd-1mtp24-lc-af-rear@2": ["mtp"],
    "fs/fhd-1mtp24-lc-rear@3": ["mtp"],
    "fs/fhd-1mtp6lcd-af-rear@2": ["mtp"],
    "fs/fhd-1mtp6lcd-rear@3": ["mtp"],
    "fs/fhd-1mtp6lcd-u-rear@2": ["mtp"],
    "fs/fhd-2mtp12-lc-af-rear@1": ["mtp1", "mtp2"],
    "fs/fhd-2mtp12-lc-rear@2": ["mtp1", "mtp2"],
    "fs/fhd-2mtp12-lc-u-rear@1": ["mtp1", "mtp2"],
    "fs/fhd-3mtp18-lc-rear@1": ["mtp1", "mtp2", "mtp3"],
}

# THE FHD MTP ADAPTER PANELS (2026-09-25) publish `mpo` slots too, from a
# different part: each opening is common/mpo-adapter@2, the panel tile, not a
# cassette's flanged bulkhead, and an adapter panel has an opening on BOTH
# faces - the front and the same adapters seen from behind. Their own census,
# because the flange checks below are about bulkheads and do not apply. The
# MTP-16 panel is not here: its tile presents `mpo16`.
_T12 = [f"{i:02d}" for i in range(1, 13)]
_T8 = _T12[:8]
PANEL_MPO_SLOTS = {
    "fs/fhd-fap12mtp-a@1": ["mtp" + i for i in _T12],
    "fs/fhd-fap12mtp-a-rear@1": ["b" + i for i in _T12],
    "fs/fhd-fap12mtp-b@1": ["mtp" + i for i in _T12],
    "fs/fhd-fap12mtp-b-rear@1": ["b" + i for i in _T12],
    "fs/fhd-fap8mtp-b@1": ["mtp" + i for i in _T8],
    "fs/fhd-fap8mtp-b-rear@1": ["b" + i for i in _T8],
}

# what the real build test seats: the cap and both plugs, on two cassettes
SEATS = {"bay-1/mtp1": CAP, "bay-1/mtp2": MPO12, "bay-2/mtp1": MPO24}

_lib = R.Library([str(LIB)])


def contract(ref):
    return _lib.resolve(ref)[0]


def skin(ref):
    return ET.parse(_lib.resolve(ref)[1] / "default.svg").getroot()


def node(root, nid):
    hits = [n for n in root.iter() if n.get("id") == nid]
    assert len(hits) == 1, (nid, len(hits))
    return hits[0]


def _vertices(d):
    """The corners of a path made of M/H/V/Z only - the opening's shape."""
    toks = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", d)
    assert set(t for t in toks if t.isalpha()) <= set("MHVZ"), d
    pts, x, y, i = [], 0.0, 0.0, 0
    while i < len(toks):
        t = toks[i]
        if t == "M":
            x, y = float(toks[i + 1]), float(toks[i + 2]); i += 3
        elif t == "H":
            x = float(toks[i + 1]); i += 2
        elif t == "V":
            y = float(toks[i + 1]); i += 2
        else:
            i += 1
            continue
        pts.append((x, y))
    return pts


def opening(ref):
    """(x0, y0, x1, y1) of the opening's rectangle and (x0, y0, x1, y1) of the
    key slot above it, off the skin's `opening` node."""
    pts = _vertices(node(skin(ref), "opening").get("d"))
    xs = sorted({x for x, _ in pts})
    ys = sorted({y for _, y in pts})
    assert len(ys) == 3, ("a rectangle with a slot on one edge", ys)
    key_x = sorted(x for x, y in pts if y == ys[0])
    return (xs[0], ys[1], xs[-1], ys[2]), (key_x[0], ys[0], key_x[-1], ys[1])


# --- the part -----------------------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(FLANGES))
def test_the_flange_adapter_presents_mpo_at_its_opening_on_the_housing(ref):
    c = contract(ref)
    assert c["interface"] == "mpo"
    assert presented_interface(c, contract) == ("mpo", MATE, HOUSING)
    housing = next(f for f in c["relief"]["features"] if f["node"] == "housing")
    assert housing["out"] == HOUSING
    assert c["connection-points"]["optical"]["at"] == MATE
    assert c["optical"]["positions"] == FLANGES[ref]
    # FS SHIPS THE PORT CAPPED (B3 task 8, test_shipped_caps.py)
    assert c["default"] == CAP
    # the internal end face stays the floor of the empty port, and the part
    # still composes no std/mpo: it presents the slot itself
    art = skin(ref)
    assert len(list(node(art, "fibres"))) == FLANGES[ref]
    assert not any(q["ref"] == APERTURE for q in c.get("parts") or [])


@pytest.mark.parametrize("ref", sorted(FLANGES))
def test_the_opening_is_std_mpos_estimate_centred_on_the_mate_and_keyed(ref):
    (x0, y0, x1, y1), (kx0, ky0, kx1, ky1) = opening(ref)
    std = contract(APERTURE)["size"]
    assert (round(x1 - x0, 6), round(y1 - y0, 6)) == (std["w"], std["h"])
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx(tuple(MATE), abs=1e-9)
    # the key slot @1 drew, kept: 3.0 x 0.7 on the middle of the top edge
    assert (round(kx1 - kx0, 6), round(ky1 - ky0, 6)) == (3.0, 0.7)
    assert (kx0 + kx1) / 2 == pytest.approx(MATE[0], abs=1e-9) and ky1 == y0
    # the housing's hole is the same shape, so the end face shows through it
    hole = node(skin(ref), "housing").get("d").split("M")[-1]
    assert _vertices("M" + hole) == _vertices(node(skin(ref), "opening").get("d"))
    # and the figure is cited as the estimate it is, not re-measured
    prov = " ".join(contract(ref)["provenance"]["opening"].split())
    assert "std/mpo@2" in prov and "ESTIMATED" in prov


@pytest.mark.parametrize("plug", PLUGS)
def test_a_seated_plugs_key_faces_the_key_slot_and_enters_without_it(plug):
    """THE KEY CHECK. The plug's key is on its top long face and so is the
    opening's key slot, so the polarity agrees; the widths do not (4.39
    against 3.0), and the flange adapter's provenance records that. What
    keeps the plug entering is that its key sits inside its own envelope, so
    it is inside the opening when seated and never reaches the slot."""
    (x0, y0, x1, y1), (kx0, _ky0, kx1, _ky1) = opening(next(iter(FLANGES)))
    key = node(skin(plug), "key")
    pm = contract(plug)["connection-points"]["mate"]["at"]
    dx, dy = MATE[0] - pm[0], MATE[1] - pm[1]
    k = [float(key.get(a)) for a in ("x", "y", "width", "height")]
    box = (k[0] + dx, k[1] + dy, k[0] + k[2] + dx, k[1] + k[3] + dy)
    assert (box[0] + box[2]) / 2 == pytest.approx((kx0 + kx1) / 2, abs=1e-6)
    assert (box[1] + box[3]) / 2 < MATE[1], "the key is not on the slot's side"
    assert x0 < box[0] and box[2] < x1 and y0 < box[1] and box[3] < y1
    for ref in FLANGES:
        note = " ".join(contract(ref)["provenance"]["key"].split())
        assert "4.39" in note and "3.0" in note


# --- the published slots ------------------------------------------------------------

def _mpo_slots():
    faces = named_as_faces([str(LIB)])
    families, connectors = R._pluggable_families(), R._connector_registry()
    candidates = R._pluggable_candidates([str(LIB)])
    out = {}
    for cf in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        ref = f"{cf.parts[-4]}/{cf.parts[-3]}@{cf.parts[-2][1:]}"
        for s in R.component_cages(contract(ref), _lib, families, candidates,
                                   connectors, face=ref in faces):
            if s["interface"] == "mpo":
                out.setdefault(ref, []).append(s)
    return out


def test_every_cassette_back_publishes_one_mpo_slot_per_bulkhead():
    got = _mpo_slots()
    assert len(got) > 0, "no component publishes an mpo slot - nothing was measured"
    assert {r: [s["id"] for s in ss] for r, ss in got.items()} == {**MPO_SLOTS, **PANEL_MPO_SLOTS}
    for ref in PANEL_MPO_SLOTS:
        parts = {q["id"]: q for q in contract(ref)["parts"]}
        for s in got[ref]:
            assert parts[s["id"]]["ref"] == "common/mpo-adapter@2", (ref, s["id"])
            assert s["kind"] == "connector" and s["default"] == CAP, (ref, s["id"])
    for ref, slots in ((r, ss) for r, ss in got.items() if r in MPO_SLOTS):
        parts = {q["id"]: q for q in contract(ref)["parts"]}
        for s in slots:
            q = parts[s["id"]]
            assert q["ref"] in FLANGES, (ref, q["ref"])
            assert s["kind"] == "connector" and s["lift"] == HOUSING
            assert s["mate"] == seat_point(q["at"], contract(q["ref"])["size"],
                                           q.get("rotate"), MATE)
            assert {CAP, MPO12, MPO24} <= set(s["accepts"]), s["accepts"]
            assert s["default"] in (None, CAP)


def test_no_module_uses_one_id_on_its_front_and_its_back():
    """A key is looked up on the front first (manifest.back_parts), so a back
    part sharing a front id could not be addressed."""
    backs = 0
    for cf in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(cf.read_text()) or {}
        back = back_parts(c, contract)
        if not back:
            continue
        backs += 1
        front = {q.get("id") for q in c.get("parts") or []} | set(c.get("bays") or {})
        assert not front & set(back), (cf, front & set(back))
    assert backs > 0


# --- seating on a real cassette's back ----------------------------------------------

def fhd_with(tmp_path, bays, occupants, without_rear=()):
    dev = shutil.copytree(LIB / "devices" / FHD, tmp_path / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["base"]
    cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = occupants
    for b in d["views"]["front"]["components"]["bays"]:
        if b["id"] in without_rear:
            b.pop("rear")
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def run(dev, out):
    return warmrender.run([sys.executable, str(SPEC / "tools/portrayal/render.py"),
                           str(dev), "--library", str(LIB), "--out", str(out)],
                          capture_output=True, text=True)


def drawn(dev, out, view):
    r = run(dev, out)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / f"fhd-1ufce.base.{view}.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


def of(root, path):
    hits = [n for n in root.iter() if n.get("data-of") == path]
    assert len(hits) == 1, (path, len(hits))
    return hits[0]


def l12(dev):
    data = yaml.safe_load(dev.read_text())
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


def published(ref, slot_id):
    return next(s for s in _mpo_slots()[ref] if s["id"] == slot_id)


def test_the_cap_and_both_plugs_seat_on_a_real_cassette_back(tmp_path):
    dev = fhd_with(tmp_path, {"bay-1": CASSETTE, "bay-2": CASSETTE}, SEATS)
    rear, parents = drawn(dev, tmp_path / "o", "rear")
    front, _ = drawn(dev, tmp_path / "o", "front")
    seated = 0
    for key, ref in SEATS.items():
        bay, mtp = key.split("/")
        host_path = f"{bay}/module/{mtp}"
        host, occ = of(rear, host_path), of(rear, f"{host_path}-occupant")
        back = node(rear, f"{bay}-rear")
        # ON THE REAR FACE: inside the bay's back, inside the hole it is seen
        # through, naming its host - and nowhere on the front
        assert is_inside(parents, occ, back)
        assert is_inside(parents, occ, node(rear, f"cutout--back-{bay[-1]}"))
        assert occ.get("data-for") == host_path
        assert occ.get("data-class") == contract(ref)["class"]
        assert not any(host_path + "-occupant" in (n.get("data-path") or "")
                       + (n.get("data-of") or "") for n in front.iter())
        # AND ITS MATE LANDS ON THE BULKHEAD'S, to 1e-6, in the device frame
        hx, hy = device_point(parents, host, MATE)
        ox, oy = device_point(parents, occ, contract(ref)["connection-points"]["mate"]["at"])
        assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, (key, (hx, hy), (ox, oy))
        # which is where the back's own published slot says, through the back
        px, py = device_point(parents, back, published(BACK, mtp)["mate"])
        assert abs(px - hx) < 1e-6 and abs(py - hy) < 1e-6, (key, (px, py))
        seated += 1
    assert seated == len(SEATS) > 0
    # the slot nobody keyed holds what it ships: the cap, seated on its host
    shipped = [n for n in rear.iter()
               if n.get("data-of") == "bay-2/module/mtp2-occupant"]
    assert len(shipped) == 1 and shipped[0].get("data-class") == "cap"
    assert shipped[0].get("data-for") == "bay-2/module/mtp2"
    assert l12(dev) == []


@pytest.mark.parametrize("key", sorted(SEATS))
def test_each_stands_in_front_of_the_housing(key):
    """SUMMED LIFT, ABSOLUTE OUT, on the group the rear drawing draws.

    The rear drawing is a projection and strips relief, because nothing in 3D
    is built from it - the kit builds a cassette's back from the back's own
    drawing. So the figures are read where the build makes them: the back
    drawn at the module's path, the way draw_placement draws it, before the
    strip. That is what the kit's back has to reproduce."""
    ref = SEATS[key]
    bay, mtp = key.split("/")
    used = set()
    g, _ = R.instance_group(_lib, BACK, f"{bay}-rear", [0, 0], None, None, None,
                            None, path=f"{bay}/module", occupants=SEATS,
                            occ_used=used)
    parents = {c: p for p in g.iter() for c in p}
    occ = next(n for n in g.iter() if n.get("data-path") == f"{bay}/module/{mtp}-occupant")
    assert occ.get("data-ref").rsplit(":", 1)[0] == ref
    assert key in used
    assert effective_lift(parents, occ) == pytest.approx(HOUSING, abs=1e-9)
    assert published(BACK, mtp)["lift"] == HOUSING
    feats = contract(ref)["relief"]["features"]
    assert feats
    for f in feats:
        n = next(x for x in occ.iter() if x.get("id") == f"{occ.get('id')}--{f['node']}")
        # `out` is absolute from the occupant's face, which is the housing's front
        assert float(n.get("data-z-out")) == pytest.approx(f["out"] + HOUSING, abs=1e-9)
        # `lift` is summed: the node starts where its own lift puts it, off the housing
        assert effective_lift(parents, n) == pytest.approx(
            HOUSING + float(f.get("lift") or 0), abs=1e-9)
        assert float(n.get("data-z-out")) > HOUSING


def test_a_front_key_and_a_back_key_on_one_cassette_each_seat_on_their_own_face(tmp_path):
    occupants = {"bay-1/lc01": "generic/lc-duplex-plug@2", "bay-1/mtp1": CAP}
    dev = fhd_with(tmp_path, {"bay-1": CASSETTE}, occupants)
    rear, _ = drawn(dev, tmp_path / "o", "rear")
    front, _ = drawn(dev, tmp_path / "o", "front")
    paths = lambda root, attr: {n.get(attr) for n in root.iter()}
    assert "bay-1/module/lc01-occupant" in paths(front, "data-path")
    assert "bay-1/module/lc01-occupant" not in paths(rear, "data-of")
    assert "bay-1/module/mtp1-occupant" in paths(rear, "data-of")
    assert "bay-1/module/mtp1-occupant" not in paths(front, "data-path")
    data = yaml.safe_load(dev.read_text())
    cfg = data["configurations"]["base"]
    assert key_on_back("bay-1/mtp1", data, cfg, contract)
    assert not key_on_back("bay-1/lc01", data, cfg, contract)
    assert nested_key_host("bay-1/mtp1", data, cfg, contract) == (
        "common/mpo-flange-adapter@2", BACK, "bay-1/module")
    assert l12(dev) == []


def test_a_back_key_on_a_bay_that_shows_no_back_is_an_error(tmp_path):
    """The front drawing hands a back key on; with no `rear:` there is nothing
    to hand it to, so both the build and L12 say so rather than drop it."""
    dev = fhd_with(tmp_path, {"bay-1": CASSETTE}, {"bay-1/mtp1": CAP},
                   without_rear=("bay-1",))
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0 and "shows no back" in r.stderr, r.stderr[-600:]
    errs = l12(dev)
    assert len(errs) == 1 and "shows no back" in errs[0], errs


def test_a_back_key_naming_no_bulkhead_is_still_an_error(tmp_path):
    dev = fhd_with(tmp_path, {"bay-1": CASSETTE}, {"bay-1/mtp9": CAP})
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0 and "occupants/bay-1/mtp9" in r.stderr, r.stderr[-600:]
    errs = l12(dev)
    assert len(errs) == 1 and "occupants/bay-1/mtp9" in errs[0], errs
