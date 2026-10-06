"""Ground studs seat a ring lug (#789, third part).

docs/connectors-dc-terminal-design.md section 13. The three single-stud
ground parts - common/ground-lug@1, common/ground-stud@1 and
juniper/mx-ground-stud@1 - each present the nominal `terminal-stud`
interface on the stud axis, at the top of what the part builds, so every
placement of one is a slot of its device. casa/c40g-ground-studs@1 draws three
studs: each is now casa/shelf-ground-stud@1, composed once per stud, so that
terminal publishes three nested slots. generic/ring-lug@1 seats in all of
them, unchanged. Where a device's documents state the size of the stud or
screw, the placement carries it as `stud-size`.

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

import warmrender
from portrayal import manifest
from portrayal import render as render_mod
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

# part -> what it was before it became a slot, and where a lug lands on it.
#   axis   the stud axis in the part's own frame
#   on     the relief feature `mate` sits on
#   top    how far off the panel that feature ends, which is where a lug starts
SINGLE = {
    "common/ground-lug@1": dict(
        axis=(3.5, 9.8), on="screw-cap", top=4.7, size={"w": 7.0, "h": 14.0},
        elements={"stud": [0.7, 7.0], "symbol": [1.5, 1.0]},
        solids={"stud": (0.0, 3.2), "washer": (3.2, 3.7), "screw-cap": (3.7, 4.7)}),
    "common/ground-stud@1": dict(
        axis=(4.05, 4.05), on="stud", top=6.0, size={"w": 8.1, "h": 8.1},
        elements={"nut": [0.0, 0.5]},
        solids={"nut": (0.0, 3.2), "stud": (0.0, 6.0)}),
    "juniper/mx-ground-stud@1": dict(
        axis=(3.5, 3.5), on="stud", top=8.0, size={"w": 7.0, "h": 7.0},
        elements={},
        solids={"stud": (3.0, 8.0)}),
}
CASA, CASA_STUD = "casa/c40g-ground-studs@1", "casa/shelf-ground-stud@1"
# the three studs of the Casa terminal: seat id -> stud axis in the terminal's frame
CASA_SEATS = {"stud-tr": (21.45, 6.15), "stud-bl": (6.15, 21.45), "stud-br": (21.45, 21.45)}
CASA_TOP = 3.5
FOUR = (*SINGLE, CASA)

# WHAT THE CASA TERMINAL DREW FOR ITS UPPER RIGHT STUD BEFORE THE STUDS BECAME
# PARTS, in the terminal's own frame. The other two are the same art moved by
# the 15.3 grid. The composed terminal must still compile to exactly these.
OLD_WASHER_TR = ("21.45,0.75 22.46,2.38 24.15,1.47 24.21,3.39 26.13,3.45 25.22,5.14 26.85,6.15 "
                 "25.22,7.16 26.13,8.85 24.21,8.91 24.15,10.83 22.46,9.92 21.45,11.55 20.44,9.92 "
                 "18.75,10.83 18.69,8.91 16.77,8.85 17.68,7.16 16.05,6.15 17.68,5.14 16.77,3.45 "
                 "18.69,3.39 18.75,1.47 20.44,2.38")
OLD_NUT_TR = "25.35,6.15 23.4,9.53 19.5,9.53 17.55,6.15 19.5,2.77 23.4,2.77"
OLD_SHIFT = {"stud-tr": (0.0, 0.0), "stud-bl": (-15.3, 15.3), "stud-br": (0.0, 15.3)}

# The census, counted off the library by walking every device view and every
# component's `parts:`: part -> (placements, devices).
CENSUS = {
    "common/ground-lug@1": (63, 40),
    "common/ground-stud@1": (23, 7),
    "juniper/mx-ground-stud@1": (10, 5),
    CASA: (1, 1),
}

UFI2 = {"ground-1": "M4", "ground-2": "M4"}
# device -> {placement: the size its own documents state}. Every other
# placement of the four parts states none.
# THE THREE AMPHENOL PANELS STATE THE SAME SIZE FROM THE SAME DOCUMENT. The
# 300CB08-SC and 300CB08-C share the 300CB08's sides and bottom, and one
# installation guide covers every version: its grounding specification, 1/4-20
# threaded holes on 5/8 inch centres, is not limited to a version the way its
# input rows are.
AMPHENOL6 = {f"ground-{side}-{i}": "1/4-20"
             for side in ("bottom", "left", "right") for i in (1, 2)}
STUD_SIZE = {
    "amphenol-ns/300cb08": AMPHENOL6,
    "amphenol-ns/300cb08-sc": AMPHENOL6,
    "amphenol-ns/300cb08-c": AMPHENOL6,
    "casa/c40g": {"ground-studs-rear": "M6"},
    "edgecore/agr110": {"ground-right": "M5"},
    "edgecore/agr130": {"ground-right": "M5"},
    "edgecore/dcs500": {"ground-0": "M5", "ground-1": "M5"},
    "edgecore/ais800-64d": {"ground-screw-1": "M6", "ground-screw-2": "M6"},
    "edgecore/ais800-64o": {"ground-screw-1": "M6", "ground-screw-2": "M6"},
    "juniper/mx104": {"ground-stud-0": "10-32", "ground-stud-1": "10-32"},
    "juniper/mx150": {"ground-stud-0": "10-32", "ground-stud-1": "10-32"},
    "juniper/mx80": {"ground-stud-0": "10-32", "ground-stud-1": "10-32"},
    "juniper/mx240": {"ground-stud-0": "1/4-20", "ground-stud-1": "1/4-20"},
    "juniper/mx480": {"ground-stud-0": "1/4-20", "ground-stud-1": "1/4-20"},
    "nokia/nfxs-d-ba": {"ground-left": "1/4 in", "ground-right": "1/4 in"},
    "nokia/nfxs-e-bb": {"ground": "1/4 in"},
    "nokia/nfxs-f-bb": {"ground": "1/4 in"},
    "nokia/lmfs-f": {"ground-stud-1": "M6", "ground-stud-2": "M6"},
    "ufispace/m3000-14xc": UFI2,
    "ufispace/s9500-22xst": UFI2,
    "ufispace/s9500-30xs": {"ground-lug": "M4"},
    "ufispace/s9501-18smt": {f"ground-{i}": "M4" for i in (1, 2, 3, 4)},
    "ufispace/s9501-28smt": UFI2,
    "ufispace/s9502-16smt": UFI2,
    "ufispace/s9510-28dc": UFI2,
    "ufispace/s9510-30xc": UFI2,
    "ufispace/s9511-20ct": UFI2,
    "ufispace/s9600-102xc": UFI2,
    "ufispace/s9600-28dx": {"ground-1": "M4"},
    "ufispace/s9601-102xc": UFI2,
    "ufispace/s9601-104bc": {"ground-1": "M4"},
}

# One real device per case: (configuration, view, the part, the slots a lug
# goes on). A slot is keyed by its placement, or `<placement>/<stud>` on the
# Casa terminal.
BUILT = {
    # each of the four parts
    "edgecore/agr110": ("ac", "rear", "common/ground-lug@1", ["ground-right"]),
    "readylinks/gl-12xb-240d": ("base", "rear", "common/ground-stud@1", ["ground-stud"]),
    "casa/c40g": ("base", "rear", CASA, ["ground-studs-rear/stud-tr"]),
    # a pair, one stud above the other, both seated
    "juniper/mx240": ("base", "rear", "juniper/mx-ground-stud@1",
                      ["ground-stud-0", "ground-stud-1"]),
    # a pair side by side, both seated
    "ufispace/s9500-22xst": ("dc", "right", "common/ground-lug@1", ["ground-1", "ground-2"]),
    # a placement turned 90
    "edgecore/dcs500": ("base", "rear", "common/ground-lug@1", ["ground-1"]),
    # a pair on a side panel, on the 5/8 inch centres its guide states
    "amphenol-ns/300cb08": ("base", "left", "common/ground-stud@1",
                            ["ground-left-1", "ground-left-2"]),
}
EACH_BUILT = pytest.mark.parametrize("device", sorted(BUILT))
EACH_SINGLE = pytest.mark.parametrize("part", sorted(SINGLE))


def _yaml(path):
    return yaml.safe_load(Path(path).read_text())


def _device(device):
    return _yaml(LIB / "devices" / device / "device.yaml")


def feats(ref):
    return {f["node"]: f for f in (_contract(ref).get("relief") or {}).get("features") or []}


def _span(feat):
    """Where a relief feature starts and ends, off the face of its part."""
    if "out" in feat:
        return 0.0, float(feat["out"])
    lo = float(feat.get("lift", 0.0))
    return lo, lo + float(feat["cyl"])


def placements_of(parts):
    """Every placement of `parts` in the library, by walking device views and
    component `parts:`. -> [(where, view-or-None, placement)]"""
    out = []
    for f in sorted((LIB / "devices").rglob("device.yaml")):
        d = _yaml(f)
        slug = f"{f.parents[1].name}/{f.parent.name}"
        for view, body in (d.get("views") or {}).items():
            comps = (body or {}).get("components") or {}
            for kind in ("placements", "bays"):
                for p in comps.get(kind) or []:
                    if p.get("ref") in parts:
                        out.append((slug, view, p))
                    refs = {p.get("default"), *(p.get("accepts") or [])}
                    assert not refs & set(parts), (slug, p.get("id"))
    for f in sorted((LIB / "components").rglob("v*/contract.yaml")):
        c = _yaml(f)
        ref = f"{f.parents[2].name}/{c['name']}@{c['version'].split('.')[0]}"
        for p in c.get("parts") or []:
            if p.get("ref") in parts:
                out.append((ref, None, p))
    return out


# --- 1. the four parts ------------------------------------------------------------

@EACH_SINGLE
def test_a_single_stud_part_presents_terminal_stud_on_its_stud_axis(part):
    s = SINGLE[part]
    c = _contract(part)
    assert c["interface"] == IFACE and "mates" not in c
    assert c["connection-points"] == {
        "mate": {"at": list(s["axis"]), "direction": "front", "on": s["on"]}}
    # and nothing else about it moved
    assert c["class"] == "ground" and c["behaviour"] == "mounts"
    assert c["size"] == s["size"]
    assert {k: v["at"] for k, v in (c.get("elements") or {}).items()} == s["elements"]
    assert not c.get("parts") and c["skins"] == ["default"]
    assert "terminal-stud" in c["provenance"]["seat"]


@EACH_SINGLE
def test_a_lug_lands_on_top_of_everything_the_part_builds(part):
    """`mate` sits `on:` the feature that stands highest, so the seat's lift
    is the top of the part and no solid of it reaches the lug."""
    s = SINGLE[part]
    f = feats(part)
    spans = {n: _span(x) for n, x in f.items()}
    assert spans == {n: pytest.approx(v) for n, v in s["solids"].items()}
    assert spans[s["on"]][1] == pytest.approx(s["top"]) == max(hi for _, hi in spans.values())
    iface, at, lift = manifest.presented_interface(_contract(part), _contract)
    assert (iface, at) == (IFACE, list(s["axis"])) and lift == pytest.approx(s["top"])
    # the axis IS the stud the skin draws
    root = ET.parse(_skin_path(part)).getroot()
    stud = next(e for e in root.iter() if e.get("id") == "stud")
    circle = stud if stud.tag == f"{SVG}circle" else stud.find(f"{SVG}circle")
    assert (float(circle.get("cx")), float(circle.get("cy"))) == s["axis"]


def test_the_casa_terminal_composes_a_seat_on_each_of_its_three_studs():
    c = _contract(CASA)
    assert "interface" not in c and "mates" not in c and "connection-points" not in c
    assert c["class"] == "ground" and c["behaviour"] == "mounts"
    assert c["size"] == {"w": 27.6, "h": 27.6}
    assert c["attrs"] == {"model": "C40G Shelf Ground Terminal"}
    parts = c["parts"]
    assert [p["id"] for p in parts] == list(CASA_SEATS)
    for p in parts:
        x, y = CASA_SEATS[p["id"]]
        assert p["ref"] == CASA_STUD and p["at"] == pytest.approx([x - 5.4, y - 5.4])
        assert "rotate" not in p and "lift" not in p
    # the studs' art and relief are in the stud part now, and only there
    assert "relief" not in c
    skin = _skin_path(CASA).read_text()
    assert "earth-mark" in skin and "polygon" not in skin and "circle" not in skin
    assert "ALL THREE ARE SEATS" in c["provenance"]["seats"]
    assert "two M6 screws" in c["provenance"]["stud-count"]


def test_the_casa_stud_is_the_art_and_the_relief_the_terminal_drew():
    c = _contract(CASA_STUD)
    assert c["class"] == "ground" and c["interface"] == IFACE
    assert "mates" not in c and "conforms" not in c and "behaviour" not in c
    assert c["size"] == {"w": 10.8, "h": 10.8}
    assert c["connection-points"] == {
        "mate": {"at": [5.4, 5.4], "direction": "front", "on": "stud-top"}}
    f = feats(CASA_STUD)
    assert {n: _span(x) for n, x in f.items()} == {
        "stud-top": (0.0, 3.5), "washer": (0.0, 0.7), "nut": (0.7, pytest.approx(2.9))}
    assert f["stud-top"]["thread"] == 1.0 and c["relief"]["wall"] == "#4a4f55"
    assert manifest.presented_interface(c, _contract)[2] == CASA_TOP == \
        max(hi for _, hi in map(_span, f.values()))
    root = ET.parse(_skin_path(CASA_STUD)).getroot()
    assert [e.get("id") for e in root if e.get("id")] == ["washer", "nut", "stud-top"]
    # the same polygons, moved to the part's own origin
    for node, old in (("washer", OLD_WASHER_TR), ("nut", OLD_NUT_TR)):
        got = [tuple(map(float, p.split(","))) for p in
               root.find(f"{SVG}polygon[@id='{node}']").get("points").split()]
        want = [(float(a) - 16.05, float(b) - 0.75) for a, b in
                (p.split(",") for p in old.split())]
        assert got == [pytest.approx(w, abs=EPS) for w in want], node
    top = root.find(f"{SVG}circle[@id='stud-top']")
    assert [float(top.get(k)) for k in ("cx", "cy", "r")] == [5.4, 5.4, 1.55]


def test_the_parts_that_present_terminal_stud_and_the_one_lug_that_mates_it():
    """Read off the library: the two terminal screws of the barrier blocks,
    the three single ground studs and the Casa stud present the interface, and
    one part mates it. The lug is the one #815 added, untouched."""
    presents, mates = [], []
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = _yaml(f)
        ref = f"{f.parents[2].name}/{c['name']}@{c['version'].split('.')[0]}"
        if c.get("interface") == IFACE:
            presents.append(ref)
        if c.get("mates") == IFACE:
            mates.append(ref)
    assert sorted(presents) == sorted([*SINGLE, CASA_STUD, "common/terminal-screw-34@1",
                                       "common/terminal-screw-38@1"])
    assert mates == [LUG]
    lug = _contract(LUG)
    assert lug["version"] == "1.0.0" and lug["size"] == {"w": 5.5, "h": 27.4}
    assert sorted(lug["fields"]) == ["barrel-color", "wire-color"]


def test_what_is_out_of_scope_is_still_not_a_seat():
    for ref in ("cisco/a9k-ground-pad@1", "common/ground-screw-washer@1", "casa/ground-bolts@1",
                "edgecore/agr-ground-plate@1", "juniper/mx204-ground-plate@1",
                "juniper/mx304-ground-plate@1", "common/ground-symbol@1",
                "nokia/sr-1-dc-terminal-block@1"):
        c = _contract(ref)
        assert "interface" not in c, ref
        assert not [p for p in c.get("parts") or []
                    if _contract(p["ref"]).get("interface") == IFACE], ref


# --- 2. the census, and every placement is a slot ----------------------------------

@pytest.fixture(scope="module")
def placed():
    got = placements_of(FOUR)
    assert got, "the walk found no placement of any ground stud part"
    return got


def test_the_census_of_ground_stud_placements(placed):
    """Counted by walking every device view and every component's `parts:`.
    All four parts are placed straight on a chassis face and no component
    composes one."""
    counts = {}
    for where, view, p in placed:
        assert view is not None, f"{where} composes {p['ref']}: a seat this census does not count"
        n, devs = counts.setdefault(p["ref"], [0, set()])
        counts[p["ref"]][0] = n + 1
        devs.add(where)
    got = {ref: (n, len(devs)) for ref, (n, devs) in counts.items()}
    assert got == CENSUS
    assert all(n > 0 and d > 0 for n, d in got.values())
    assert sum(n for n, _ in got.values()) == 97
    assert len({where for where, _, _ in placed}) == 53


@pytest.fixture(scope="module")
def slots(placed):
    """The device `cages[]` entry of every placement, built by the same
    `cage_entries` the build publishes, keyed (device, view, id)."""
    lib = render_mod.Library([str(LIB)])
    families = render_mod._pluggable_families()
    candidates = render_mod._pluggable_candidates([LIB])
    got = {}
    for device in sorted({where for where, _, _ in placed}):
        d = _device(device)
        for view in d.get("views") or {}:
            for c in render_mod.cage_entries(d, view, lib, families, candidates, {}):
                got[(device, view, c["id"])] = c
    assert got
    return got


def test_every_single_stud_placement_is_a_slot_of_its_device_offering_the_lug(placed, slots):
    """A ground stud placed on a chassis face is a DEVICE cage, keyed by the
    placement's own id, and it offers exactly the ring lug and ships empty."""
    seen = 0
    for device, view, p in placed:
        if p["ref"] == CASA:
            continue
        s = SINGLE[p["ref"]]
        c = slots[(device, view, p["id"])]
        assert c["kind"] == "connector" and c["interface"] == IFACE, (device, p["id"])
        assert c["accepts"] == [LUG] and c["default"] is None and c["occupant"] is None
        assert c["media"] is None and c["mirror"] is False and c["group-states"] is False
        assert c["lift"] == pytest.approx(s["top"])
        assert c["rotate"] == p.get("rotate")
        # the mate is the stud axis, through the placement's own turn
        want = render_mod.seat_point(p["at"], s["size"], p.get("rotate"), list(s["axis"]))
        assert c["mate"] == pytest.approx(want, abs=EPS)
        seen += 1
    assert seen == 96


def test_the_only_turned_placements_are_turned_90(placed):
    turned = sorted((device, p["id"], p["rotate"]) for device, _, p in placed if p.get("rotate"))
    assert turned == [("edgecore/dcs500", "ground-0", 90), ("edgecore/dcs500", "ground-1", 90),
                      ("nokia/nfxs-d-ba", "ground-left", 90),
                      ("nokia/nfxs-d-ba", "ground-right", 90)]


@pytest.fixture(scope="module")
def comps():
    import onebuild
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def test_the_casa_terminal_publishes_exactly_its_three_studs_as_slots(comps, slots, placed):
    cages = comps[CASA]["cages"]
    assert [c["id"] for c in cages] == list(CASA_SEATS)
    for c in cages:
        assert c["kind"] == "connector" and c["interface"] == IFACE
        assert c["accepts"] == [LUG] and c["default"] is None
        assert c["mate"] == pytest.approx(list(CASA_SEATS[c["id"]]), abs=EPS)
        assert c["lift"] == pytest.approx(CASA_TOP)
        assert not c["rotate"] and c["media"] is None
    # the terminal itself is a plain placement, not a cage of its device
    (device, view, p), = [x for x in placed if x[2]["ref"] == CASA]
    assert (device, view, p["id"]) == ("casa/c40g", "rear", "ground-studs-rear")
    assert (device, view, p["id"]) not in slots
    # a single-stud part publishes no nested slot: it is the slot
    for part in SINGLE:
        assert not comps[part].get("cages"), part


# --- 3. stud-size ------------------------------------------------------------------

def test_stud_size_is_stated_where_a_document_states_it_and_nowhere_else(placed):
    got = {}
    for device, view, p in placed:
        size = (p.get("attrs") or {}).get("stud-size")
        if size is not None:
            got.setdefault(device, {})[p["id"]] = size
    assert got == STUD_SIZE
    assert sum(len(v) for v in got.values()) == 68 and len(got) == 31
    # every device that states one says where it read it
    for device in STUD_SIZE:
        entry = _device(device)["provenance"]["ground-stud-size"]
        assert "`stud-size`" in entry["note"] and entry["confidence"] == "datasheet", device
    # and no other file in the library states the attribute at all
    stated = [f for f in [*(LIB / "components").rglob("v*/contract.yaml"),
                          *(LIB / "devices").rglob("device.yaml")]
              if re.search(r"\bstud-size\s*:", f.read_text())]
    assert sorted(f"{f.parents[1].name}/{f.parent.name}" for f in stated) == sorted(STUD_SIZE)


def test_stud_size_is_text_and_changes_no_part():
    """The interface claims no size and the lug is one nominal lug: a
    placement's `stud-size` is a fact carried beside the slot."""
    assert {v for sizes in STUD_SIZE.values() for v in sizes.values()} == \
        {"M4", "M5", "M6", "10-32", "1/4-20", "1/4 in"}
    for ref in (*SINGLE, CASA_STUD, LUG):
        assert "stud-size" not in (_contract(ref).get("fields") or {}), ref
        assert "stud-size" not in (_contract(ref).get("attrs") or {}), ref


# --- 4. built: bare, and with a lug seated ------------------------------------------

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
    config, view = BUILT[device][:2]
    root = ET.parse(face_file(o, name, config, view)).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Each device twice: as the library holds it, and with a lug on the
    slots BUILT names. Also the device index of the bare build."""
    out = {}
    for device, (config, view, part, keys) in BUILT.items():
        name, o = _render(tmp_path_factory.mktemp("bare"), device, lambda d: None)
        bare = _face(o, name, device)
        index = json.loads((o / f"{name}.configs.json").read_text())

        def edit(d, config=config, keys=keys):
            occ = d["configurations"][config].setdefault("occupants", {})
            for k in keys:
                occ[k] = LUG
        name, o = _render(tmp_path_factory.mktemp("seated"), device, edit)
        out[device] = (bare, _face(o, name, device), index)
    assert set(out) == set(BUILT)
    return out


def _stud_path(key):
    """The drawing path of the stud a slot key names: the same string."""
    return key


def _geometry(el):
    """What an element draws: its tag and every attribute but the ones the
    build adds to address it."""
    return (el.tag, {k: v for k, v in el.attrib.items()
                     if k != "id" and not k.startswith("data-")})


@EACH_BUILT
def test_with_nothing_seated_the_part_compiles_to_the_drawing_it_always_was(built, device):
    """No lug anywhere, and each stud's compiled nodes are its skin's nodes:
    the same shapes, in the same order, with the same paint."""
    (root, parents), _, _ = built[device]
    config, view, part, keys = BUILT[device]
    assert not [e for e in root.iter() if (e.get("data-ref") or "").startswith(LUG)]
    assert not [e for e in root.iter() if (e.get("data-path") or "").endswith("-occupant")
                and e.get("data-for") in keys]
    for key in keys:
        host = by_path(root, _stud_path(key))
        ref = host.get("data-ref").rsplit(":", 1)[0]
        assert ref == (CASA_STUD if part == CASA else part)
        skin = ET.parse(_skin_path(ref)).getroot()
        want = [_geometry(e) for e in skin.iter() if e is not skin and isinstance(e.tag, str)]
        got = [_geometry(e) for e in host.iter()
               if e is not host and e.tag != f"{SVG}title" and e.get("data-cp") is None]
        assert got == want, key
        # one connection point was added, and it is the only thing that was
        cps = [e for e in host if e.get("data-cp")]
        assert [e.get("data-cp") for e in cps] == ["mate"]
        # the relief the part compiled to is the relief its contract states
        z = {e.get("id").rsplit("--", 1)[1]: e for e in host.iter()
             if e.get("id") and any(k.startswith("data-z-") for k in e.attrib)}
        f = feats(ref)
        assert sorted(z) == sorted(f)
        for node, feat in f.items():
            lo, hi = _span(feat)
            e = z[node]
            assert lift_of(parents, e) - lift_of(parents, host) == pytest.approx(lo), node
            depth = e.get("data-z-out") or e.get("data-z-cyl")
            assert float(depth) - (lift_of(parents, host) if e.get("data-z-out") else 0) == \
                pytest.approx(hi - (0 if e.get("data-z-out") else lo)), node


def test_the_bare_casa_terminal_compiles_to_the_three_studs_it_always_drew(built):
    """Each stud's washer, nut and stud end land, in the terminal's frame,
    on exactly the points the terminal's own skin drew them at, painted after
    the earth mark as the mark was painted clear of them before."""
    (root, parents), _, _ = built["casa/c40g"]
    host = by_path(root, "ground-studs-rear")
    assert host.get("data-ref", "").startswith(CASA)
    inv = _inverse(device_matrix(parents, host))
    order = [e.get("id").rsplit("--", 1)[1] for e in host if e.get("id")]
    assert order == ["silkscreen", *CASA_SEATS], order
    for seat, (dx, dy) in OLD_SHIFT.items():
        stud = by_path(root, f"ground-studs-rear/{seat}")
        assert stud.get("id") == f"{host.get('id')}--{seat}"
        m = _mul(inv, device_matrix(parents, stud))
        for node, old in (("washer", OLD_WASHER_TR), ("nut", OLD_NUT_TR)):
            poly = next(e for e in stud.iter() if e.get("id") == f"{stud.get('id')}--{node}")
            got = apply(m, [tuple(map(float, p.split(","))) for p in poly.get("points").split()])
            want = [(float(a) + dx, float(b) + dy) for a, b in
                    (p.split(",") for p in old.split())]
            assert len(got) == len(want)
            for g, w in zip(got, want):
                assert g == pytest.approx(w, abs=EPS), (seat, node)
            assert (poly.get("fill"), poly.get("stroke")) == ("#ffffff", "#231f20")
            assert poly.get("stroke-width") == ("0.3" if node == "washer" else "0.45")
        top = next(e for e in stud.iter() if e.get("id") == f"{stud.get('id')}--stud-top")
        cx, cy = apply(m, [(float(top.get("cx")), float(top.get("cy")))])[0]
        assert (cx, cy) == pytest.approx((21.45 + dx, 6.15 + dy), abs=EPS)
        assert (cx, cy) == pytest.approx(CASA_SEATS[seat], abs=EPS)
        assert (top.get("r"), top.get("fill"), top.get("stroke"), top.get("stroke-width")) == \
            ("1.55", "#c9cbcd", "#231f20", "0.3")


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _inverse(m):
    (a, b, tx), (c, d, ty), _ = m
    det = a * d - b * c
    return [[d / det, -b / det, (b * ty - d * tx) / det],
            [-c / det, a / det, (c * tx - a * ty) / det], [0, 0, 1]]


def _lug(built, device, key):
    _, (root, parents), _ = built[device]
    host = by_path(root, _stud_path(key))
    occ = by_path(root, f"{key}-occupant")
    assert occ.get("data-ref", "").startswith(LUG) and occ.get("data-for") == key
    return root, parents, host, occ


def _node(occ, name):
    hits = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--{name}"]
    assert len(hits) == 1, name
    return hits[0]


def _axis_and_top(host):
    ref = host.get("data-ref").rsplit(":", 1)[0]
    if ref == CASA_STUD:
        return (5.4, 5.4), CASA_TOP
    return SINGLE[ref]["axis"], SINGLE[ref]["top"]


def _lug_box(parents, occ):
    return box(apply(device_matrix(parents, occ), [(0, 0), (5.5, 0), (5.5, 27.4), (0, 27.4)]))


def _wire_box(parents, occ):
    wire = _node(occ, "wire")
    x, y, w, h = (float(wire.get(k)) for k in ("x", "y", "width", "height"))
    return box(apply(device_matrix(parents, wire),
                     [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]))


@EACH_BUILT
def test_a_lug_seats_with_its_mate_on_the_stud_axis(built, device):
    keys = BUILT[device][3]
    root = built[device][1][0]
    lugs = [e for e in root.iter() if (e.get("data-ref") or "").startswith(LUG)]
    assert len(lugs) == len(keys)
    for key in keys:
        root, parents, host, occ = _lug(built, device, key)
        axis, _ = _axis_and_top(host)
        hx, hy = device_point(parents, host, axis)
        ox, oy = device_point(parents, occ, own_mate(occ))
        assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, key
        assert_same_turn(parents, occ, host)


@EACH_BUILT
def test_the_seated_lugs_solids_start_above_everything_its_stud_builds(built, device):
    """Read off the compiled depths. The top of what the stud builds is the
    highest end of any solid in it; the lug's group is lifted to exactly
    that, and no solid of the lug starts below it."""
    for key in BUILT[device][3]:
        root, parents, host, occ = _lug(built, device, key)
        _, top = _axis_and_top(host)
        base = lift_of(parents, host)
        ends = []
        for e in host.iter():
            if e.get("data-z-cyl"):
                ends.append(lift_of(parents, e) + float(e.get("data-z-cyl")) - base)
            if e.get("data-z-out"):
                ends.append(float(e.get("data-z-out")) - base)
        assert ends and max(ends) == pytest.approx(top), key
        zero = lift_of(parents, occ) - base
        assert zero == pytest.approx(top)
        tongue, head = _node(occ, "tongue"), _node(occ, "head")
        sleeve, wire = _node(occ, "sleeve"), _node(occ, "wire")
        spans = {
            "tongue": (zero, float(tongue.get("data-z-out")) - base),
            "head": (lift_of(parents, head) - base,
                     lift_of(parents, head) - base + float(head.get("data-z-cyl"))),
            "sleeve": (lift_of(parents, sleeve) - base,
                       lift_of(parents, sleeve) - base + float(sleeve.get("data-z-bar"))),
            "wire": (lift_of(parents, wire) - base,
                     lift_of(parents, wire) - base + float(wire.get("data-z-bar"))),
        }
        assert spans["tongue"] == pytest.approx((top, top + 0.8))
        assert spans["head"] == pytest.approx((top + 0.8, top + 2.2))
        assert spans["sleeve"] == pytest.approx((top, top + 4.5))
        assert spans["wire"] == pytest.approx((top + 0.75, top + 3.75))
        for name, (lo, hi) in spans.items():
            assert lo >= max(ends) - EPS and hi > lo, (key, name)
        for e in occ.iter():
            assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")


def test_the_wire_leaves_downward_on_an_unturned_stud(built):
    for device, key in (("edgecore/agr110", "ground-right"),
                        ("readylinks/gl-12xb-240d", "ground-stud"),
                        ("casa/c40g", "ground-studs-rear/stud-tr")):
        root, parents, host, occ = _lug(built, device, key)
        axis, _ = _axis_and_top(host)
        hx, hy = device_point(parents, host, axis)
        x0, y0, x1, y1 = _wire_box(parents, occ)
        assert (x0 + x1) / 2 == pytest.approx(hx, abs=EPS)
        assert y0 == pytest.approx(hy + 14.65) and y1 == pytest.approx(hy + 24.65)
        assert x1 - x0 == pytest.approx(3.0)


def test_on_a_1ru_rear_the_wire_runs_past_the_lower_edge_of_the_face(built):
    """Recorded, not wanted: the lug is 24.65 long below the stud axis and a
    1RU face is 44 high. On the AGR110 the wire ends 6.75 below the face."""
    root, parents, host, occ = _lug(built, "edgecore/agr110", "ground-right")
    face = _device("edgecore/agr110")["views"]["rear"]["size"]
    _, _, _, y1 = _wire_box(parents, occ)
    assert y1 - face["h"] == pytest.approx(6.75)


def test_a_stud_turned_90_turns_its_lug_and_the_wire_leaves_to_the_left(built):
    """A seat applies its host's turn and nothing else. The DCS500's two
    ground points are placed at `rotate: 90`, so the lug's own down is the
    face's left: the wire runs level, away from the stud toward x = 0."""
    device, key = "edgecore/dcs500", "ground-1"
    p = next(q for q in _device(device)["views"]["rear"]["components"]["placements"]
             if q["id"] == key)
    assert p["rotate"] == 90
    root, parents, host, occ = _lug(built, device, key)
    axis, _ = _axis_and_top(host)
    hx, hy = device_point(parents, host, axis)
    x0, y0, x1, y1 = _wire_box(parents, occ)
    assert (y0 + y1) / 2 == pytest.approx(hy, abs=EPS) and y1 - y0 == pytest.approx(3.0)
    assert x1 == pytest.approx(hx - 14.65) and x0 == pytest.approx(hx - 24.65)
    cable = [e for e in occ if e.get("data-cp") == "cable"]
    assert len(cable) == 1 and cable[0].get("data-cp-dir") == "down"
    cx, cy = device_point(parents, occ, [float(v) for v in cable[0].get("data-cp-at").split()])
    assert (cx, cy) == pytest.approx((x0, hy), abs=EPS)


def _overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > EPS and min(a[3], b[3]) - max(a[1], b[1]) > EPS


def test_two_lugs_on_a_pair_drawn_one_above_the_other_overlap(built):
    """A RECORDED FACT, NOT A WANTED ONE. The MX240's two grounding points
    take ONE two-hole lug; they are drawn 13.2 apart, one above the other. A
    one-hole lug on each is 24.65 long below its axis, so the upper lug lies
    across the lower stud and the lower lug's ring. A two-hole lug is later
    work (docs/connectors-dc-terminal-design.md section 13)."""
    device = "juniper/mx240"
    upper = _lug(built, device, "ground-stud-0")
    lower = _lug(built, device, "ground-stud-1")
    parents = upper[1]
    (ux, uy), (lx, ly) = (device_point(parents, h, (3.5, 3.5)) for h in (upper[2], lower[2]))
    assert ux == pytest.approx(lx) and ly - uy == pytest.approx(13.2)
    a, b = _lug_box(parents, upper[3]), _lug_box(parents, lower[3])
    assert _overlap(a, b)
    assert a[3] - b[1] == pytest.approx(27.4 - 13.2)        # 14.2 of the upper lug's length
    # the upper lug's sleeve, 5.65 to 14.65 below its axis, is over the lower stud's axis
    assert uy + 5.65 < ly < uy + 14.65


def test_two_lugs_on_a_pair_at_its_documented_pitch_still_overlap(built):
    """A RECORDED FACT. The Amphenol 300CB08 draws each ground landing on the
    5/8 inch centres its guide states, 15.9, one stud above the other on a
    side panel 43.9 high. The guide allows a single-hole lug on a stud; two
    of this one overlap by 11.5 of their length, and the lower one runs
    12.45 past the lower edge of the face."""
    device = "amphenol-ns/300cb08"
    upper = _lug(built, device, "ground-left-1")
    lower = _lug(built, device, "ground-left-2")
    parents = upper[1]
    (ux, uy), (lx, ly) = (device_point(parents, h, (4.05, 4.05)) for h in (upper[2], lower[2]))
    assert ux == pytest.approx(lx) and ly - uy == pytest.approx(15.9)
    a, b = _lug_box(parents, upper[3]), _lug_box(parents, lower[3])
    assert _overlap(a, b) and a[3] - b[1] == pytest.approx(27.4 - 15.9)
    face = _device(device)["views"]["left"]["size"]
    assert a[3] < face["h"] and b[3] - face["h"] == pytest.approx(12.45)


def test_two_lugs_on_a_pair_drawn_side_by_side_do_not_overlap(built):
    """The other pairs are drawn side by side. The S9500-22XST's two holes
    are 11 apart and a lug is 5.5 wide, so two one-hole lugs lie beside each
    other with 5.5 between them, both wires leaving downward."""
    device = "ufispace/s9500-22xst"
    one = _lug(built, device, "ground-1")
    two = _lug(built, device, "ground-2")
    parents = one[1]
    (ax, ay), (bx, by) = (device_point(parents, h, (3.5, 9.8)) for h in (one[2], two[2]))
    assert ay == pytest.approx(by) and bx - ax == pytest.approx(11.0)
    a, b = _lug_box(parents, one[3]), _lug_box(parents, two[3])
    assert not _overlap(a, b)
    assert b[0] - a[2] == pytest.approx(11.0 - 5.5)


@EACH_BUILT
def test_the_device_index_publishes_the_slot(built, device):
    """A single stud is a cage of its device's view, id = the placement id.
    The Casa terminal is not; its three studs are read off components.json."""
    config, view, part, keys = BUILT[device]
    index = built[device][2]
    ids = {c["id"]: c for c in index["cages"][view]}
    for key in keys:
        if part == CASA:
            assert key not in ids and key.split("/")[0] not in ids
            continue
        c = ids[key]
        assert c["kind"] == "connector" and c["interface"] == IFACE
        assert c["accepts"] == [LUG] and c["lift"] == pytest.approx(SINGLE[part]["top"])
    # and on no other view
    for other, cages in index["cages"].items():
        if other != view:
            assert not [c for c in cages if c["id"] in keys], other


# --- 5. the kit: it offers the studs, and seats a lug as the build does -------------

KIT_SCRIPT = ROOT / "spec/tests/js/ground-stud-lugs.mjs"
# device -> the slot the kit is asked to fill
KIT_ASKS = {"edgecore/agr110": "ground-right", "edgecore/dcs500": "ground-1",
            "casa/c40g": "ground-studs-rear/stud-tr"}


@pytest.fixture(scope="module")
def kit(built, tmp_path_factory):
    """kit/swap.js run under node against the BARE compiled faces, with the
    device index of the same build and the component index and skins built
    here. No skip: a machine without node fails."""
    assert shutil.which("node"), "node is needed to run the kit's slot walk"
    dist = tmp_path_factory.mktemp("ground-dist")
    comps = build_components(dist)
    cases = {}
    for device, slot in KIT_ASKS.items():
        config, view, part, keys = BUILT[device]
        (root, _), _, index = built[device]
        cases[device] = {"face": spec_of(root), "view": view, "slot": slot, "ref": LUG,
                         "bays": index["bays"], "cages": index["cages"]}
    payload = {"components": list(comps.values()), "cases": cases,
               "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                         for r in (LUG, *SINGLE, CASA, CASA_STUD)}}
    p = subprocess.run(["node", str(KIT_SCRIPT)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(KIT_SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    assert set(got) == set(KIT_ASKS)
    for name, g in got.items():
        assert "error" not in g, g.get("error")
    return got


@pytest.mark.parametrize("device", sorted(KIT_ASKS))
def test_the_kit_offers_every_ground_stud_on_the_face(kit, built, device):
    config, view, part, keys = BUILT[device]
    (root, parents), _, index = built[device]
    slot = KIT_ASKS[device]
    studs = {e["id"]: e for e in kit[device]["studs"]}
    if part == CASA:
        want = [f"ground-studs-rear/{s}" for s in CASA_SEATS]
    else:
        want = [c["id"] for c in index["cages"][view] if c["interface"] == IFACE]
    assert want and sorted(studs) == sorted(want)
    assert sorted(kit[device]["offered"]) == sorted(want)
    one = studs[slot]
    assert one["kind"] == "connector" and one["interface"] == IFACE
    assert one["accepts"] == [LUG] and one["default"] is None
    host = by_path(root, slot)
    _, top = _axis_and_top(host)
    if part == CASA:
        # a nested slot: read off the drawing and components.json
        assert one["modulePath"] == "ground-studs-rear" and one["carrier"] == CASA
        assert one["key"] == slot
        assert one["mate"] == pytest.approx(list(CASA_SEATS[slot.split("/")[1]]))
        assert one["lift"] == pytest.approx(top)
    else:
        # a device cage: exactly the entry the device index published
        assert one["modulePath"] is None and one["carrier"] is None
        pub = next(c for c in index["cages"][view] if c["id"] == slot)
        assert one["mate"] == pytest.approx(pub["mate"]) and one["lift"] == pytest.approx(top)
        assert one["rotate"] == pub["rotate"]


@pytest.mark.parametrize("device", sorted(KIT_ASKS))
def test_the_kit_seats_a_lug_exactly_as_the_build_does(kit, built, device):
    slot = KIT_ASKS[device]
    _, (seated, _), _ = built[device]
    want = built_occupant(seated, slot)
    assert want["ref"] == LUG
    bad = mismatches([{"name": device, "built": {slot: want}}],
                     [{"name": device, "seated": {slot: kit[device]["lug"]}}])
    assert not bad, "\n".join(bad)
    g = kit[device]
    assert g["occRef"] and g["occRef"].startswith(LUG)
    assert g["again"] == 1, "a second swap stacked a second lug"
    assert set(g["others"]) <= {0}, "another stud was given a lug"
    assert g["left"] == 0, "emptying the stud left a lug"


@pytest.mark.parametrize("device", sorted(KIT_ASKS))
def test_the_kit_seated_lug_is_lifted_to_the_top_of_its_stud(kit, built, device):
    slot = KIT_ASKS[device]
    (root, parents), _, _ = built[device]
    host = by_path(root, slot)
    _, top = _axis_and_top(host)
    lug = kit[device]["lug"]
    # a nested seat is lifted inside its carrier; a device cage from the face
    assert float(lug["attrs"]["data-z-lift"]) == pytest.approx(top)
    z = {c["a"]["id"].rsplit("--", 1)[1]: c["a"] for c in lug["children"]
         if c["a"].get("id") and any(k.startswith("data-z-") for k in c["a"])}
    assert sorted(z) == ["head", "sleeve", "tongue", "wire"]
    assert float(z["tongue"]["data-z-out"]) == pytest.approx(lift_of(parents, host) + top + 0.8)
    assert (float(z["head"]["data-z-lift"]), float(z["head"]["data-z-cyl"])) == (0.8, 1.4)
    assert float(z["sleeve"]["data-z-bar"]) == 4.5
    assert (float(z["wire"]["data-z-lift"]), float(z["wire"]["data-z-bar"])) == (0.75, 3.0)


def test_the_3d_pass_names_the_one_view_that_holds_a_ground_stud(kit, built):
    """A stud placed on the chassis is a device cage, so viewsToRewrite
    (kit/swap.js) names exactly the view whose `cages[]` holds it, and
    seatViews seats the lug on that face."""
    for device in ("edgecore/agr110", "edgecore/dcs500"):
        t = kit[device]["threeD"]
        view = BUILT[device][1]
        index = built[device][2]
        assert len(index["cages"]) == 6 and len(t["views"]) == 6
        assert t["named"] == [view], device
        assert t["viewsApplied"] == 1 and t["viewsSeated"] == 1
        assert t["faceApplied"] == 1 and t["faceSeated"] == 1
        assert not t["faceRefused"] and not t["faceFailed"]


def test_the_3d_pass_seats_a_lug_on_a_stud_of_the_casa_terminal(kit):
    """`ground-studs-rear/stud-tr` is claimed by no bay and no cage of any
    view: the terminal is a plain placement that publishes slots. Every view
    is named for such a key (#814) and the rear face seats the lug."""
    t = kit["casa/c40g"]["threeD"]
    assert sorted(t["named"]) == sorted(t["views"]) and "rear" in t["named"]
    assert t["viewsApplied"] == 1 and t["viewsSeated"] == 1
    assert t["faceApplied"] == 1 and t["faceSeated"] == 1
    assert not t["faceRefused"] and not t["faceFailed"]
