"""The kit seats an optic in a cage ON A CARD exactly where, and exactly as, the
build does (#484).

render.py's `_seat_nested_occupants` (R2) draws a configured optic on a seated
card INSIDE the card's group, at `<bay>/module/<cage>-occupant`, placed by the
card-frame mate points - so it inherits the bay's translate and turn. The kit
reads the card's cages off the drawing (`nestedCages`, from the component's
own `cages` in components.json, R1) and seats through the same
`applyOccupantOverrides` and the same `occupantTransform` a device cage uses,
in the card's frame. Nothing about the bay transform is solved a second time,
and this holds the two halves to one answer from a REAL build.

THE LIBRARY SHIPS NO POPULATED CARD, so the fitted builds are copies in
tmp_path (test_nested_occupants.py's idiom). Three devices, so the matrix of
turns is complete: the C100G's SMM-300GM (cages at 90 in an upright bay), a
C40G card (cages at 90 in a bay at 90 - a half turn on the page), and the
MX304's LMIC16 (cages upright and at 180).

The kit is handed the BUILT face with EVERY optic taken out of it (the
build's own stay behind as the reference) and the same override map, so it
must find each cage off the card and seat its own in the same parent - an
optic the kit did not seat cannot be in the face to be compared. Every number and attribute it
writes is compared with what render.py wrote, and both optics' composed
device-frame maps are compared as well, so a kit optic in the right parent
at the wrong place cannot pass.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"
SCRIPT = SPEC / "tests/js/nested-cage-seat.mjs"

SFP, QSFP, QSFPDD = "generic/sfp-lc@1", "generic/qsfp-lc@1", "generic/qsfp-dd-lc@1"
XFP = "generic/xfp-lc@1"

# (vendor, device, configuration, bays merged in, occupants, card ref)
DEVICES = [
    ("casa", "c100g", "base", {"front-6": "casa/smm-300gm@1"},
     {"front-6/xg0": SFP, "front-6/cg0": QSFP}, "casa/smm-300gm@1"),
    ("casa", "c40g", "base", {"front-2": "casa/smm-8x10g@1"},
     {"front-2/xg0": SFP, "front-2/g0": SFP}, "casa/smm-8x10g@1"),
    ("juniper", "mx304", "dc", {},
     {"lmic0/port-0": QSFPDD, "lmic0/port-1": QSFP}, "juniper/mx304-lmic16@1"),
    # #261: a card TURNED INSIDE A CARD. The MX2000's adapter seats the MX240
    # card in a component bay at rotate 90, so the cage's turn comes from a
    # nested bay, not the device's - at depth 2 (the MPC's own cages) and at
    # depth 3 (a MIC in the turned MPC).
    ("juniper", "mx2010", "base",
     {"fpc0": "juniper/mx2000-lc-adapter@1", "fpc0/mpc": "juniper/mpc4e-3d-32xge-sfpp@2"},
     {"fpc0/mpc/port-0-0": SFP, "fpc0/mpc/port-0-1": SFP}, "juniper/mpc4e-3d-32xge-sfpp@2"),
    ("juniper", "mx2020", "base",
     {"fpc0": "juniper/mx2000-lc-adapter@1", "fpc0/mpc": "juniper/mpc2e-3d@3",
      "fpc0/mpc/mic0": "juniper/mic-3d-4xge-xfp@3"},
     {"fpc0/mpc/mic0/port-0-0": XFP, "fpc0/mpc/mic0/port-0-3": XFP}, "juniper/mic-3d-4xge-xfp@3"),
]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else None


def spec_of(el):
    """An element tree in the fake DOM's JSON form (tests/js/fake-dom.mjs)."""
    return {"t": local(el.tag), "a": dict(el.attrib),
            "c": [spec_of(k) for k in el if isinstance(k.tag, str)]}


def without_occupants(el):
    """`el` in fake-dom form with EVERY seated optic taken out - what the kit is
    handed. The build's optics stay in `built` as the reference; left in the
    face, a kit that counted a card cage as applied and seated nothing would
    leave the build's optic standing, identical to the answer, and pass."""
    return {"t": local(el.tag), "a": dict(el.attrib),
            "c": [without_occupants(k) for k in el
                  if isinstance(k.tag, str) and k.get("data-behaviour") != "occupies"]}


def count_occupants(spec):
    return (spec["a"].get("data-behaviour") == "occupies") + sum(
        count_occupants(k) for k in spec["c"])


def descendants(el):
    """As test_cage_seat_js.py: every element below `el`, an empty <style>
    dropped (a standalone skin carries one and a device face does not)."""
    return [{"t": local(e.tag), "a": dict(e.attrib)} for e in el.iter()
            if e is not el and isinstance(e.tag, str)
            and not (local(e.tag) == "style" and not (e.text or "").strip() and not len(e))]


def build_components(out):
    """components.json and the compiled skins, BUILT HERE rather than read
    from library/dist - a stale dist is a stale answer. Built once per session
    by onebuild, by the same command, and copied here."""
    onebuild.components_index_into(out)
    idx = json.loads((out / "components.json").read_text())["components"]
    return {f"{c['ns']}/{c['name']}@{c['major'].lstrip('v')}": c for c in idx}


def skin_file(dist, comp):
    return dist / "components" / f"{comp['ns']}--{comp['name']}--{comp['major']}--default.svg"


# --- transforms, parsed numerically (test_nested_occupants.py's reading) ----

def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _op(name, args):
    if name == "translate":
        tx, ty = (args + [0.0])[:2]
        return [[1, 0, tx], [0, 1, ty], [0, 0, 1]]
    if name == "scale":
        sx = args[0]
        sy = args[1] if len(args) > 1 else sx
        return [[sx, 0, 0], [0, sy, 0], [0, 0, 1]]
    if name == "rotate":
        c, s = math.cos(math.radians(args[0])), math.sin(math.radians(args[0]))
        r = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        if len(args) == 3:
            return _mul(_mul(_op("translate", args[1:]), r), _op("translate", [-args[1], -args[2]]))
        return r
    raise AssertionError(f"unexpected transform op {name}")


def matrix(tf):
    m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for name, body in re.findall(r"(\w+)\(([^)]*)\)", tf or ""):
        m = _mul(m, _op(name, [float(v) for v in re.split(r"[ ,]+", body.strip())]))
    return m


def numbers(tf):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", tf or "")]


def chain_matrix(tfs):
    m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for tf in tfs:
        m = _mul(m, matrix(tf))
    return m


def drawing_key(key):
    """`front-6/xg0` -> `front-6/module/xg0` (kit/swap.js configBayPath)."""
    return "/module/".join(key.split("/"))


def fitted(tmp, dist_comps, dist, vendor, name, config, bays, occupants, card_ref):
    src = LIB / "devices" / vendor / name
    dev = tmp / name / "src" / "device.yaml"
    shutil.copytree(src, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"][config]
    if bays:
        cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / name / "out"
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    face_path = out / f"{name}.{config}.front.svg"
    root = ET.parse(face_path).getroot()
    parents = {c: p for p in root.iter() for c in p}

    def ancestors_tf(el):
        chain, node = [], el
        while node is not None:
            chain.append(node.get("transform"))
            node = parents.get(node)
        return list(reversed(chain))

    built = {}
    for key, ref in occupants.items():
        cage = key.rsplit("/", 1)[1]
        [occ] = [e for e in root.iter() if e.get("data-path") == f"{drawing_key(key)}-occupant"]
        built[drawing_key(key)] = {
            "ref": ref, "cage": cage,
            "parent": parents[occ].get("data-path"),
            "transform": occ.get("transform"),
            "attrs": {k: v for k, v in occ.attrib.items() if k.startswith("data-") or k == "id"},
            "children": descendants(occ),
            "device": chain_matrix(ancestors_tf(occ)),
            "parentDevice": chain_matrix(ancestors_tf(parents[occ])),
        }
    refs = {ref.split(":")[0] for ref in occupants.values()} | {card_ref}
    comps = {r: dist_comps[r] for r in refs}
    skins = {r: json.dumps(spec_of(ET.parse(skin_file(dist, dist_comps[r])).getroot()))
             for r in occupants.values()}
    return {"device": name, "card": card_ref, "built": built,
            "payload": {"device": name, "face": without_occupants(root), "comps": comps,
                        "skins": skins,
                        "overrides": {drawing_key(k): r for k, r in occupants.items()}}}


def node(mode, stdin=None):
    p = subprocess.run(["node", str(SCRIPT), mode], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def parity(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("nested-cage-seat")
    dist = tmp / "dist"
    comps = build_components(dist)
    cases = [fitted(tmp, comps, dist, *d) for d in DEVICES]
    got = node("parity", json.dumps({"devices": [c["payload"] for c in cases]}))
    return cases, got


@needs_node
def test_the_matrix_is_the_one_claimed(parity):
    """An upright cage, a turned one, and a card in a turned bay - a library
    edit that un-turned them would otherwise pass on the easy case alone."""
    cases, _ = parity
    turns = set()
    for case in cases:
        card = case["payload"]["comps"][case["card"]]
        for key in case["built"]:
            cage = next(c for c in card["cages"] if c["id"] == key.rsplit("/", 1)[1])
            bay_turned = abs(case["built"][key]["parentDevice"][0][1]) > 0.5
            turns.add((cage.get("rotate") or 0, bay_turned))
    assert {(0, False), (90, False), (90, True), (180, False)} <= turns, turns


@needs_node
def test_the_kit_seats_an_optic_on_a_card_where_the_build_does(parity):
    cases, got = parity
    assert [g["device"] for g in got] == [c["device"] for c in cases]
    # the kit starts from a face with NO optic in it, so whatever it holds after
    # is what the kit seated - never the build's left standing
    for case, g in zip(cases, got):
        assert count_occupants(case["payload"]["face"]) == 0, case["device"]
        assert all(v == 0 for v in g["before"].values()), (case["device"], g["before"])
    worst, n = 0.0, 0
    for case, g in zip(cases, got):
        assert g["result"] == {"applied": len(case["built"]), "refused": [], "failed": []}, (
            case["device"], g["result"])
        card = case["payload"]["comps"][case["card"]]
        for key, want in case["built"].items():
            where = f"{case['device']} {key} ({want['ref']})"
            have = g["seated"][key]
            # found by nestedCages, off the drawing, from the component's cages
            entry = have["entry"]
            assert entry, f"{where}: nestedCages found no such cage in {g['cageIds']}"
            pub = next(c for c in card["cages"] if c["id"] == want["cage"])
            assert entry["mate"] == pub["mate"] and entry["rotate"] == pub.get("rotate"), where
            assert entry["modulePath"] == want["parent"] and entry["moduleIsElement"], where
            assert entry["carrier"] == case["card"], where
            # ONE optic, and it is the kit's: the face it was handed had none
            assert have["count"] == 1, f"{where}: {have['count']} optics in the cage"
            # THE SAME PARENT: the card's group, where render.py appends it
            assert have["parent"] == want["parent"] == key.rsplit("/", 1)[0], (
                where, have["parent"], want["parent"])
            # THE TRANSFORM, number by number and as a composed map
            kn, bn = numbers(have["transform"]), numbers(want["transform"])
            assert len(kn) == len(bn), (where, have["transform"], want["transform"])
            err = max([abs(a - b) for a, b in zip(kn, bn)] or [0.0])
            dev_k = _mul(want["parentDevice"], matrix(have["transform"]))
            err = max(err, *(abs(dev_k[i][j] - want["device"][i][j])
                             for i in range(2) for j in range(3)))
            assert err < 1e-6, f"{where}: kit {have['transform']} vs build {want['transform']}"
            worst = max(worst, err)
            # EQUAL, not a subset (test_cage_seat_js.py's rule)
            ka = {k: v for k, v in have["attrs"].items() if k.startswith("data-") or k == "id"}
            assert ka == want["attrs"], (
                f"{where}: kit-only {sorted(set(ka) - set(want['attrs']))}, "
                f"build-only {sorted(set(want['attrs']) - set(ka))}, differing "
                f"{sorted(k for k in set(ka) & set(want['attrs']) if ka[k] != want['attrs'][k])}")
            # and every descendant, with every attribute
            assert want["children"], f"{where}: the build's optic has no children - vacuous"
            assert have["children"] == want["children"], f"{where}: children differ"
            n += 1
    assert n == sum(len(c["built"]) for c in cases) == 10, n
    print(f"nested cage parity: {len(cases)} devices, {n} cages, max error {worst:.3g}")


@needs_node
def test_a_nested_override_seats_replaces_empties_refuses_and_fails():
    out = node("overrides")
    assert out["before"]["front-6/module/xg1"] == 1 and out["before"]["front-6/module/xg0"] == 0
    # THE RULE CHANGED (B3 Task 9): a lifted card cage and a card in a sunk bay
    # are seated, not refused - the kit now moves the optic's `out` as the
    # build does (test_lifted_seat_js.py holds it to real builds)
    assert out["result"] == {
        "applied": 6,
        "refused": [],
        "failed": ["front-6/module/xg3"]}, out["result"]
    [x0] = out["after"]["front-6/module/xg0"]
    assert x0["id"] == "front-6--module--xg0-occupant"
    assert x0["path"] == "front-6/module/xg0-occupant"
    assert x0["parent"] == "front-6/module", "seated INSIDE the card's group"
    assert x0["children"] == [["front-6--module--xg0-occupant--body", None],
                              ["front-6--module--xg0-occupant--tx",
                               "front-6/module/xg0-occupant/tx"]]
    assert x0["transform"].endswith("rotate(90 6.775 4.275)"), "turns with its cage"
    [x1] = out["after"]["front-6/module/xg1"]
    assert x1["ref"] == "generic/sfp-lc-simplex@2:2.0.0", "the built optic replaced, once"
    assert x1["parent"] == "front-6/module" and x1["last"], "appended, as render.py does"
    assert out["after"]["front-6/module/xg2"] == [], "null empties a card cage"
    # A FAILED LOAD CHANGES NOTHING: the cage keeps its built optic
    [x3] = out["after"]["front-6/module/xg3"]
    assert x3["ref"] == "generic/sfp-lc@1:1.0.0" and out["held"] == "generic/sfp-lc@1"
    assert out["after"]["front-6/module/xg4"] == [], "an absent key is untouched"
    # SEATED ON THE EFFECTIVE FACTS (R4): a lifted card cage and a card in a
    # sunk bay each hold one optic, inside the card, and the group carries the
    # cage's OWN lift - 44 on the shelf, none for a flat cage in a sunk bay,
    # whose -3 is the bay group's and is summed by relief.js
    for key in ("front-6/module/c1", "front-7/module/xg0"):
        [o] = out["after"][key]
        assert o["ref"] == "generic/sfp-lc@1:1.0.0" and o["parent"] == key.rsplit("/", 1)[0], o
    assert out["zLift"] == {"front-6/module/c1": ["44"], "front-7/module/xg0": [None]}
    assert out["lifts"]["front-6/module/c1"] == 44 and out["lifts"]["front-7/module/xg0"] == -3
    assert out["lifts"]["front-7/module/c2"] == 0
    assert out["reasons"]["front-7/module/c2"] is None, "a depth is no longer a refusal"
    assert all(out["reasons"][f"front-6/module/xg{i}"] is None for i in range(5))
    # a mirrored card still mirrors every cage on it, lifted ones included
    assert out["mirrored"] == ["mirror"] * 7
    # the device cage in the same call is untouched by the rule
    [p4] = out["deviceSeat"]
    assert p4["id"] == p4["path"] == "port-4-occupant"
    assert out["deviceNames"] == {"id": "port-4-occupant", "path": "port-4-occupant"}
    assert out["names"] == {"id": "front-6--module--xg0-occupant",
                            "path": "front-6/module/xg0-occupant"}
    assert out["second"] == {"applied": 1, "refused": [], "failed": []}
    assert out["again"] == ["generic/sfp-lc@1:1.0.0"], "a second swap replaces, never stacks"
    assert out["led"] == 1, "an LED data-for the cage is not its occupant"
    # A CAGE OF A CARD THAT LEFT IS NO CAGE: the entry is re-checked at apply
    assert out["staleRes"] == {"applied": 0, "refused": [], "failed": []}
    assert out["staleHeld"] == ["generic/sfp-lc@1:1.0.0"]
    # the entry: keyed by the drawing's path, the placement not the composed cage
    assert "front-6/module/xg0" in out["ids"]
    assert not any(i.endswith("/cage") for i in out["ids"])
    assert out["entry"] == {"cage": "xg0", "modulePath": "front-6/module",
                            "moduleId": "front-6--module", "carrier": "casa/card@1",
                            "moduleIsElement": True, "mate": [12.6, 75], "rotate": 90}
    assert out["unknownCard"] == 0


@needs_node
def test_overlapping_nested_swaps_end_as_one_and_the_later():
    out = node("race")
    assert out["held"] == ["generic/sfp-lc-simplex@2:2.0.0"]
    assert out["results"] == [{"applied": 0, "refused": [], "failed": []},
                              {"applied": 1, "refused": [], "failed": []}]
