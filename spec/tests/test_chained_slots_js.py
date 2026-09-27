"""Slots on a seated occupant, in the explorer (P3 as amended 2026-09-24).

A cabled 100G uplink is built as it is racked: a QSFP28 optic in the card's
cage, and a generic/lc-plug@2 in each of the optic's `tx` and `rx` bores. The
build has always seated that - `nt-a/qsfp-2-occupant/tx` is a chained key
(manifest.nested_key_host), and render.py draws the plug inside the optic's
own group at `nt-a/module/qsfp-2-occupant/tx-occupant`. The kit did not:
nestedSlots walked no slot inside any `data-for` group, so the explorer could
show the optic and never plug it, and a `swap=` naming a plug was dropped.

HELD TO A REAL BUILD. A tmp copy of nokia/nfxs-d-ba is rendered with three
configurations - both FANT-H boards and no optic (`duplex`), an optic in each
`qsfp-2` (`optics`), and the optics with both plugs in each (`ring`) - and
what the kit seats is compared with what render.py drew, attribute for
attribute and matrix for matrix (test_lifted_seat_js's `mismatches`). The
FANT-H's `qsfp-2` stands on a 36-degree facet, so the plug inherits a tilt it
does not carry itself.
"""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_lifted_seat_js import LIB, RENDER, SPEC, build_components, skin_file, spec_of
from test_nested_slots_js import built_occupant
from test_lifted_seat_js import mismatches
from portrayal.artifacts import face_file

SCRIPT = SPEC / "tests/js/chained-slots.mjs"
DEVICE = "nokia/nfxs-d-ba"
OPTIC, PLUG, CAP = "generic/qsfp-lc@2", "generic/lc-plug@2", "common/lc-dust-cap@1"
FANT = "nokia/fant-h-bb@2"
NTS = ("nt-a", "nt-b")
BAYS = {"nt-b": FANT}
OPTICS = {f"{nt}/qsfp-2": OPTIC for nt in NTS}
PLUGS = {f"{nt}/qsfp-2-occupant/{b}": PLUG for nt in NTS for b in ("tx", "rx")}
CONFIGS = {"duplex": {}, "optics": OPTICS, "ring": {**OPTICS, **PLUGS}}
# drawing paths, as the explorer keys them
CAGE = {nt: f"{nt}/module/qsfp-2" for nt in NTS}
BORE = {(nt, b): f"{nt}/module/qsfp-2-occupant/{b}" for nt in NTS for b in ("tx", "rx")}

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def render(tmp):
    vendor, name = DEVICE.split("/")
    work = tmp / name
    dev = work / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / DEVICE, dev.parent)
    d = yaml.safe_load(dev.read_text())
    for cfg, occ in CONFIGS.items():
        d["configurations"][cfg] = {"kind": "example", "description": "P3 amended test",
                                    "bays": dict(BAYS), **({"occupants": dict(occ)} if occ else {})}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = work / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return out, name


def node(stdin, swap=None):
    env = {**os.environ, **({"SWAP_MODULE": str(swap)} if swap else {})}
    p = subprocess.run(["node", str(SCRIPT), "scenarios"], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent), env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chained-slots")
    dist = tmp / "dist"
    comps = build_components(dist)
    out, name = render(tmp)
    faces = {c: ET.parse(face_file(out, name, c, "front")).getroot() for c in CONFIGS}
    meta = json.loads((out / f"{name}.configs.json").read_text())
    idx = json.loads((dist / "components.json").read_text())["components"]
    payload = {
        "components": idx,
        "faces": {k: spec_of(v) for k, v in faces.items()},
        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                  for r in (OPTIC, PLUG, CAP)},
        "cages": {name: meta["cages"]["front"]},
        "allCages": {name: meta["cages"]},
        "faceBays": {name: meta["bays"].get("front", [])},
        "bays": {name: [b for v in meta["bays"].values() for b in v]},
        "configs": {name: meta["configs"]},
    }
    stdin = json.dumps(payload)
    return {"faces": faces, "comps": comps, "stdin": stdin, "out": node(stdin)}


def scenario(world, name):
    got = world["out"][name]
    assert not (isinstance(got, dict) and "error" in got), got.get("error")
    return got


def parity(world, face, key, have):
    want = built_occupant(world["faces"][face], key)
    return mismatches([{"name": face, "built": {key: want}}],
                      [{"name": face, "seated": {key: have}}])


def ver(world, ref):
    return f"{ref}:{world['comps'][ref]['version']}"


# ---------------------------------------------------------------- the build

def test_the_build_seats_a_plug_in_a_card_cages_optic(world):
    """The premise: render.py takes the chained key and draws the plug
    inside the optic's own group, named in the optic's namespace."""
    root = world["faces"]["ring"]
    for (nt, b), path in BORE.items():
        occ = built_occupant(root, path)
        assert occ["ref"] == PLUG and occ["parent"] == f"{CAGE[nt]}-occupant"
        assert occ["attrs"]["id"] == f"{nt}--module--qsfp-2-occupant--{b}-occupant"
        assert occ["attrs"]["data-path"] == f"{path}-occupant"


# ---------------------------------------------------------------- the kit

@needs_node
def test_nested_slots_reads_the_bores_of_a_seated_optic(world):
    c = scenario(world, "census")
    assert c["bare"] == sorted(c["bare"]) and set(c["bare"]) == set(CAGE.values())
    assert set(c["optics"]) == set(CAGE.values()) | set(BORE.values())
    assert c["tx"] == {**c["tx"], "key": "nt-a/qsfp-2-occupant/tx", "kind": "connector",
                       "accepts": [CAP, PLUG], "default": None, "carrier": OPTIC,
                       "modulePath": "nt-a/module/qsfp-2-occupant",
                       "moduleId": "nt-a--module--qsfp-2-occupant"}
    assert set(c["offered"]) == set(c["optics"])


@needs_node
def test_a_plug_seated_by_the_explorer_is_the_builds(world):
    s = scenario(world, "plugs")
    assert all(r == {"applied": 1, "refused": [], "failed": []} for r in s["res"].values()), s["res"]
    assert s["again"] == {"applied": 1, "refused": [], "failed": []}
    assert s["seated"][BORE[("nt-a", "tx")]]["count"] == 1, "a second plug stacked"
    for key, have in s["seated"].items():
        bad = parity(world, "ring", key, have)
        assert not bad, "\n".join(bad[:8])


@needs_node
def test_a_click_on_the_plug_or_the_bore_names_the_bore(world):
    s = scenario(world, "click")
    assert s["plug"] == BORE[("nt-a", "tx")]
    assert s["bore"] == BORE[("nt-a", "tx")]
    assert s["optic"] == CAGE["nt-a"]
    assert s["options"] == [
        {"value": "", "label": "— empty —", "selected": False},
        {"value": CAP, "label": CAP, "selected": False},
        {"value": PLUG, "label": PLUG, "selected": True}]


@needs_node
def test_seat_face_plugs_the_builds_optics_as_the_build_does(world):
    """The pass 3D and the faces not on screen take, given plugs for the
    optics the build seated: every plug is the build's, and so is every optic
    holding them, child for child - the plug seated before the optic's
    connection-point markers, where instance_group puts it."""
    s = scenario(world, "seatFacePlugs")
    assert s["res"] == {"applied": 4, "refused": [], "failed": [], "dropped": []}
    for key, have in s["seated"].items():
        bad = parity(world, "ring", key, have)
        assert not bad, "\n".join(bad[:8])


@needs_node
def test_seat_face_seats_the_optic_and_then_its_plugs(world):
    """The whole map on a face that holds no optic: the optic first, the face
    read again, then its plugs - each plug the build's."""
    s = scenario(world, "seatFace")
    assert s["res"] == {"applied": 6, "refused": [], "failed": [], "dropped": []}
    for key in BORE.values():
        bad = parity(world, "ring", key, s["seated"][key])
        assert not bad, "\n".join(bad[:8])


@needs_node
def test_an_optic_the_kit_seats_in_a_tilted_cage_is_the_builds(world):
    """The FANT-H's qsfp-2 stands on a 36-degree facet. The card's cage
    entry publishes it (`tilt`), and the kit draws the optic as
    _seat_nested_occupants does: scale(1,cos) before the turn, its `at`
    solved on the foreshortened mates, and data-tilt-on/-tilt/-facing -
    child for child the build's, as its plugs already were."""
    s = scenario(world, "seatFace")
    for nt in NTS:
        bad = parity(world, "ring", CAGE[nt], s["seated"][CAGE[nt]])
        assert not bad, "\n".join(bad[:8])


@needs_node
def test_a_plug_for_a_replacement_optic_lands_in_the_replacement(world):
    s = scenario(world, "replaceUnderPlugs")
    # the twin is OPTIC under another name, so it carries OPTIC's version
    # string, read from its contract rather than pinned to a release
    name, major = OPTIC.split("@")
    ver = yaml.safe_load((LIB / "components" / name / f"v{major}" / "contract.yaml")
                         .read_text())["version"]
    assert s == {"applied": 2, "optic": [f"generic/qsfp-lc-twin@1:{ver}"], "tx": 1, "rx": 0, "ntb": 1}, s


@needs_node
def test_accept_swaps_resolves_a_plug_through_what_the_cage_holds(world):
    a = scenario(world, "accept")
    tx, rx, nta = "nt-a/module/qsfp-2-occupant/tx", "nt-a/module/qsfp-2-occupant/rx", CAGE["nt-a"]
    assert a["both"] == {"accepted": {nta: OPTIC, tx: PLUG}, "ignored": [], "cages": [nta, tx]}
    assert a["reversed"] == a["both"]
    assert a["noOptic"] == {"accepted": {}, "ignored": [tx], "cages": []}
    assert a["onBuilt"] == {"accepted": {tx: PLUG}, "ignored": [rx], "cages": [tx]}
    assert a["emptied"] == {"accepted": {nta: None}, "ignored": [tx], "cages": [nta]}


@needs_node
def test_the_delta_measures_a_plug_against_the_optic_it_is_in(world):
    d = scenario(world, "delta")
    tx, rx = BORE[("nt-a", "tx")], BORE[("nt-a", "rx")]
    # the configuration's chained keys meet the drawing's paths
    assert {k: v for k, v in d["built"].items() if "qsfp-2" in k} == {
        **{CAGE[nt]: OPTIC for nt in NTS}, **{p: PLUG for p in BORE.values()}}
    assert d["untouched"] == {}
    assert d["plugOut"] == {rx: None}
    # the optic taken out took its plugs, and they are no swap of their own
    assert d["opticOut"] == {CAGE["nt-a"]: None}
    assert tx not in d["prunedKeys"] and rx not in d["prunedKeys"]
    assert BORE[("nt-b", "tx")] in d["prunedKeys"]
    # the build's optic put back is a fresh seat: its plugs are gone
    assert d["putBack"] == {tx: None, rx: None}
    assert d["onDuplex"] == {CAGE["nt-a"]: OPTIC, tx: PLUG}
    assert d["twin"] == {CAGE["nt-a"]: "generic/qsfp-lc-twin@1", tx: PLUG, rx: PLUG}
    assert d["codec"] == {CAGE["nt-a"]: OPTIC, tx: PLUG}
    assert d["under"] == [True, False, False, True]
    assert d["views"] == ["front"]


# THE FIXES, MUTATED. Each edit is applied to a copy of kit/swap.js and must
# turn its property back to the defect with every scenario it reads still
# running (test_nested_slots_js's rule).
MUTATIONS = [
    ("no slot on a seat", "if (n.getAttribute('data-path') !== `${f}-occupant`) return true;",
     "return true;", ["census"], lambda o: len(o["census"]["optics"]) == 6),
    ("one pass for every tier",
     "const frontier = todo.filter(c => !todo.some(o => o !== c && underCarrier(c.id, o.id)));",
     "const frontier = todo;", ["replaceUnderPlugs"],
     lambda o: o["replaceUnderPlugs"]["tx"] == 1),
    ("the resolver reads no occupant", "if (h !== undefined) return h;", "",
     ["accept"], lambda o: o["accept"]["both"]["ignored"] == []),
    ("a slot does not carry", "return k.startsWith(c) && /^(-occupant)+(\\/|$)/.test(k.slice(c.length));",
     "return false;",
     ["delta"], lambda o: o["delta"]["putBack"] == {"nt-a/module/qsfp-2-occupant/tx": None,
                                                    "nt-a/module/qsfp-2-occupant/rx": None}),
    ("the delta is not shallowest first",
     "const occEntries = Object.entries(cfgOccupants || {}).sort(([a], [b]) => chain(a) - chain(b));",
     "const occEntries = Object.entries(cfgOccupants || {}).sort(([a], [b]) => chain(b) - chain(a));",
     ["delta"], lambda o: len(o["delta"]["twin"]) == 3),
]


@needs_node
@pytest.mark.parametrize("label,old,new,scen,holds", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_a_mutated_fix_fails(world, tmp_path, label, old, new, scen, holds):
    src = (SPEC.parent / "kit/swap.js").read_text()
    assert src.count(old) == 1, f"{label}: the anchor {old!r} is not in swap.js exactly once"
    assert holds(world["out"]), f"{label}: the property does not hold on the real kit"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    got = node(world["stdin"], swap=mutant)
    crashed = {n: got[n]["error"][:200] for n in scen if isinstance(got[n], dict) and "error" in got[n]}
    assert not crashed, f"{label}: the mutant crashed a scenario rather than flipping it: {crashed}"
    assert not holds(got), f"{label}: the mutated kit still passes"
