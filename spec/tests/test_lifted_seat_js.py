"""The kit seats an occupant in a LIFTED slot exactly as the build does (B3
Task 9).

A slot whose aperture stands off the face by L - a cage on the A22's 44 mm
block, a bore 3.175 proud of its adapter, the FS duplex slot 1.2 proud -
makes the build do two things to what it seats: `data-z-lift` on the occupant
group, and every descendant's absolute `data-z-out` moved by
`_inset_feature(feat, back=-L, group_lift=L)`, because `out` is absolute and
`lift` is summed. The kit refused every such slot until it did both
(swap.js `refusalReason` returned 'lift'); it now ports that arithmetic.

HELD TO REAL BUILDS, and the kit is handed each face with EVERY occupant taken
out of it (the #484 vacuous-parity lesson): a kit that seated nothing, or
seated into the wrong parent, cannot find the build's occupant standing in
the face and pass on it. Three faces:

  dcp-2 ila-node, configured in a tmp copy: an SFP in each of the A22's two
      cages at lift 44 (one upright, one at 180), a duplex plug on the A22's
      `edfa` adapter (lift 47.175, its bores emptied), and every cap the
      build seats by DEFAULT - on the A22's `ocm` bores (a slot on a part
      lifted 44 inside the card) and the PPM's bores (a card in a bay the
      A22 raises 44);
  dcp-2 dcp-404-x1, configured: a QSFP in each of the DCP-404's five cages on
      its 44 mm faceplate - with the A22's two, the 7 card cages the old rule
      refused (docs/pluggables-caps-design.md, decision 8);
  dcp-r-34d-cs as it ships: 72 default dust caps in lc-duplex-adapter@5 bores
      placed on the device, lift 3.175, turned 180;
  fhd-1ufce populated: 24 default duplex caps on the cassettes' v-adapter
      slots, lift 1.2, turned 270.

Where a default already holds the slot, the kit seats into the EMPTIED slot
exactly as the build seated the default - the case every shipped cap is.
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

from portrayal.render import _inset_feature

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
RENDER = SPEC / "tools/portrayal/render.py"
SCRIPT = SPEC / "tests/js/lifted-seat.mjs"
SWAP = ROOT / "kit/swap.js"

SFP, QSFP, QSFPDD = "generic/sfp-lc@1", "generic/qsfp-lc@1", "generic/qsfp-dd-lc@1"
DUPLEX = "generic/lc-duplex-plug@2"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# (case name, vendor/device, configuration, occupants merged into it)
FACES = [
    ("dcp-2 ila-node", "smartoptics/dcp-2", "ila-node",
     {"slot-1/sfp-1": SFP, "slot-1/sfp-2": SFP,
      "slot-1/edfa": DUPLEX, "slot-1/edfa/tx": "", "slot-1/edfa/rx": ""}),
    ("dcp-2 dcp-404-x1", "smartoptics/dcp-2", "dcp-404-x1",
     {"slot-1/c1": QSFP, "slot-1/c2": QSFP, "slot-1/c3": QSFP, "slot-1/c4": QSFP,
      "slot-1/line": QSFPDD}),
    ("dcp-r-34d-cs default", "smartoptics/dcp-r-34d-cs", "default", None),
    ("fhd-1ufce populated", "fs/fhd-1ufce", "populated", None),
]


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else None


def spec_of(el):
    return {"t": local(el.tag), "a": dict(el.attrib),
            "c": [spec_of(k) for k in el if isinstance(k.tag, str)]}


def is_occupant(attrs):
    """What the build seated: `data-for` its slot, at `<slot>-occupant`. NOT
    `data-behaviour="occupies"` - a cap and an optic carry it, but a PLUG does
    not (generic/lc-duplex-plug@2 is data-class `port` with no behaviour), and
    an LED is `data-for` a port too but is no occupant."""
    return bool(attrs.get("data-for")) and (attrs.get("data-path") or "").endswith("-occupant")


def without_occupants(el):
    """`el` in fake-dom form with EVERY seated occupant taken out - what the kit
    is handed; the build's stay in the reference."""
    return {"t": local(el.tag), "a": dict(el.attrib),
            "c": [without_occupants(k) for k in el
                  if isinstance(k.tag, str) and not is_occupant(k.attrib)]}


def count_occupants(spec):
    return is_occupant(spec["a"]) + sum(count_occupants(k) for k in spec["c"])


def descendants(el):
    return [{"t": local(e.tag), "a": dict(e.attrib)} for e in el.iter()
            if e is not el and isinstance(e.tag, str)
            and not (local(e.tag) == "style" and not (e.text or "").strip() and not len(e))]


def build_components(out):
    r = subprocess.run([sys.executable, "-m", "portrayal.components_index",
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(SPEC / "tools")})
    assert r.returncode == 0, r.stderr[-600:]
    idx = json.loads((out / "components.json").read_text())["components"]
    return {f"{c['ns']}/{c['name']}@{c['major'].lstrip('v')}": c for c in idx}


def skin_file(dist, comp):
    return dist / "components" / f"{comp['ns']}--{comp['name']}--{comp['major']}--default.svg"


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


def chain_matrix(tfs):
    m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for tf in tfs:
        m = _mul(m, matrix(tf))
    return m


def numbers(tf):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", tf or "")]


def face_case(tmp, comps, dist, name, device, config, occupants):
    vendor, dev_name = device.split("/")
    src = LIB / "devices" / device
    work = tmp / re.sub(r"\W+", "-", name)
    dev = work / "src" / "device.yaml"
    shutil.copytree(src, dev.parent)
    if occupants:
        d = yaml.safe_load(dev.read_text())
        cfg = d["configurations"][config]
        cfg["occupants"] = {**(cfg.get("occupants") or {}), **occupants}
        dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = work / "out"
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / f"{dev_name}.{config}.front.svg").getroot()
    parents = {c: p for p in root.iter() for c in p}

    def chain(el):
        tfs, n = [], el
        while n is not None:
            tfs.append(n.get("transform"))
            n = parents.get(n)
        return chain_matrix(list(reversed(tfs)))

    def inside_occupant(el):
        n = parents.get(el)
        while n is not None:
            if is_occupant(n.attrib):
                return True
            n = parents.get(n)
        return False

    built, keys = {}, []
    for occ in root.iter():
        if not is_occupant(occ.attrib) or inside_occupant(occ):
            continue
        key = occ.get("data-for")
        assert key and "/" in key, f"{name}: a device-level occupant {key!r} - not this test's"
        carrier = key.rsplit("/", 1)[0]
        ref = occ.get("data-ref").split(":")[0]
        keys.append({"key": key, "ref": ref, "carrier": carrier})
        built[key] = {
            "ref": ref, "parent": parents[occ].get("data-path"),
            "transform": occ.get("transform"),
            "attrs": {k: v for k, v in occ.attrib.items() if k.startswith("data-") or k == "id"},
            "children": descendants(occ),
            "device": chain(occ), "parentDevice": chain(parents[occ]),
        }
    carriers = {next(e for e in root.iter() if e.get("data-path") == k["carrier"])
                .get("data-ref").split(":")[0] for k in keys}
    refs = {k["ref"] for k in keys}
    return {"name": name, "built": built,
            "payload": {"name": name, "face": without_occupants(root),
                        "comps": {r: comps[r] for r in refs | carriers},
                        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                                  for r in refs},
                        "keys": keys}}


def node(mode, stdin, swap=None):
    env = {**os.environ, **({"SWAP_MODULE": str(swap)} if swap else {})}
    p = subprocess.run(["node", str(SCRIPT), mode], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent), env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def same_attrs(kit, build):
    """EQUAL, not a subset. A `data-z-*` figure may differ by 1e-6; every other
    attribute is compared as the string it is."""
    bad = sorted(set(kit) ^ set(build))
    for k in set(kit) & set(build):
        if kit[k] == build[k]:
            continue
        a, b = _num(kit[k]), _num(build[k])
        if k.startswith("data-z-") and a is not None and b is not None and abs(a - b) < 1e-6:
            continue
        bad.append(k)
    return bad


# A KNOWN GAP, NOT A LIFT ONE, pinned so it cannot widen and must be closed
# on purpose. A plug's connection-point marker names the relief node it sits
# on, `data-cp-on="<instance>--a--body"` (render.py instance_group); the kit's
# `rename` rewrites ids, data-path and url(#...) but not this reference, so a
# kit-seated plug keeps `lc-duplex-plug--a--body`. Closing it is B3 Task 10c
# (3D cable anchors). The plug carries no data-behaviour="occupies"; the kit
# now finds it by `data-for` and its slot's accepts (swap.js isOccupantOf,
# Task 10a, test_nested_slots_js.py). The lift arithmetic on the plug is
# checked here like every other case.
CP_ON_GAP = "data-cp-on"


def mismatches(cases, got, gaps=None):
    """Every way a kit seat differs from the build's, as readable strings.
    A `data-cp-on` difference on a PLUG goes to `gaps` instead (CP_ON_GAP)."""
    out = []
    for case, g in zip(cases, got):
        assert g["name"] == case["name"]
        for key, want in case["built"].items():
            where = f"{case['name']} {key} ({want['ref']})"
            have = g["seated"][key]
            if have["count"] != 1:
                out.append(f"{where}: {have['count']} occupants (refused: {have['reason']})")
                continue
            if have["parent"] != want["parent"]:
                out.append(f"{where}: parent {have['parent']} vs {want['parent']}")
            kn, bn = numbers(have["transform"]), numbers(want["transform"])
            err = max([abs(a - b) for a, b in zip(kn, bn)] or [0.0]) if len(kn) == len(bn) else 1.0
            dev_k = _mul(want["parentDevice"], matrix(have["transform"]))
            err = max(err, *(abs(dev_k[i][j] - want["device"][i][j])
                             for i in range(2) for j in range(3)))
            if err >= 1e-6:
                out.append(f"{where}: transform {have['transform']} vs {want['transform']}")
            ka = {k: v for k, v in have["attrs"].items() if k.startswith("data-") or k == "id"}
            bad = same_attrs(ka, want["attrs"])
            if bad:
                out.append(f"{where}: group attrs {bad}: kit "
                           f"{ {k: ka.get(k) for k in bad} } build "
                           f"{ {k: want['attrs'].get(k) for k in bad} }")
            kc, bc = have["children"], want["children"]
            if len(kc) != len(bc):
                out.append(f"{where}: {len(kc)} descendants vs {len(bc)}")
                continue
            for i, (k, b) in enumerate(zip(kc, bc)):
                bad = same_attrs(k["a"], b["a"]) if k["t"] == b["t"] else ["<tag>"]
                if gaps is not None and "plug" in want["ref"] and CP_ON_GAP in bad:
                    bad.remove(CP_ON_GAP)
                    gaps.append((key, k["a"].get(CP_ON_GAP), b["a"].get(CP_ON_GAP)))
                if bad:
                    out.append(f"{where}: descendant {i} ({b['a'].get('id')}) {bad}: kit "
                               f"{ {x: k['a'].get(x) for x in bad} } build "
                               f"{ {x: b['a'].get(x) for x in bad} }")
    return out


@pytest.fixture(scope="module")
def parity(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lifted-seat")
    dist = tmp / "dist"
    comps = build_components(dist)
    cases = [face_case(tmp, comps, dist, *f) for f in FACES]
    stdin = json.dumps({"cases": [c["payload"] for c in cases]})
    return cases, stdin, node("parity", stdin)


@needs_node
def test_every_case_is_a_lifted_slot_the_kit_used_to_refuse(parity):
    """The census, pinned: the cases this file is about are all LIFTED, the
    matrix of lifts it claims is in it, and the kit's face held none of them."""
    cases, _, got = parity
    by = {c["name"]: c for c in cases}
    counts = {c["name"]: len(c["built"]) for c in cases}
    # 11 on the dcp-2: 2 SFPs + 1 duplex plug + 2 ocm bore caps + 6 PPM bore caps
    assert counts == {"dcp-2 ila-node": 11, "dcp-2 dcp-404-x1": 5,
                      "dcp-r-34d-cs default": 72, "fhd-1ufce populated": 24}, counts
    # the seven lifted CAGES (kind cage, not connector) of the library, all here
    cages = {k for c, g in zip(cases, got) for k, h in g["seated"].items()
             if h["entry"] and not k.rsplit("/", 1)[1] in ("tx", "rx")
             and (h["entry"]["lift"] == 44)}
    assert len(cages) == 7, sorted(cages)
    lifts, depths = set(), set()
    for case, g in zip(cases, got):
        assert count_occupants(case["payload"]["face"]) == 0, case["name"]
        assert all(v == 0 for v in g["before"].values()), (case["name"], g["before"])
        for key, have in g["seated"].items():
            e = have["entry"]
            assert e, f"{case['name']} {key}: no slot entry"
            # every one is off the face - the whole population the old rule refused
            assert e["lift"], f"{case['name']} {key}: lift 0 - not a lifted case"
            lifts.add((round(e["lift"], 4), e["rotate"] or 0))
            depths.add(round(e["seat-depth"], 4))
    assert {(44.0, 0), (44.0, 180), (47.175, 0), (3.175, 180), (1.2, 270)} <= lifts, lifts
    assert {0, 44.0} <= depths, "a slot under a lifted ancestor (the seat-depth term) is in the matrix"
    assert by["dcp-2 ila-node"]["built"]["slot-1/module/sfp-2"]["ref"] == SFP
    assert by["dcp-2 ila-node"]["built"]["slot-1/module/edfa"]["ref"] == DUPLEX


@needs_node
def test_nestedSlots_is_the_slot_entry_on_every_carrier(parity):
    """The parity seats through the kit's own nestedSlots (B3 Task 10a) - on
    a card, on an adapter placed on the device, on one composed on a card.
    Task 9's `slotEntries` helper, which stood in for it, is kept as the
    reference: on every carrier the kit's entry equals it, field for field."""
    _, _, got = parity
    checked = [h for g in got for h in g["helperVsKit"]]
    assert checked and all(h["n"] > 0 for h in checked), checked
    assert all(h["same"] for h in checked), checked


@needs_node
def test_the_kit_seats_a_lifted_slot_exactly_as_the_build(parity):
    cases, _, got = parity
    for case, g in zip(cases, got):
        assert g["result"] == {"applied": len(case["built"]), "refused": [], "failed": []}, (
            case["name"], g["result"])
    gaps = []
    bad = mismatches(cases, got, gaps)
    assert not bad, f"{len(bad)} differences, first: " + "\n".join(bad[:8])
    # the plug's four markers, and nothing else, differ by the rename gap
    assert gaps and all(k == "slot-1/module/edfa" for k, _, _ in gaps), gaps
    assert all(kit.startswith("lc-duplex-plug--")
               and build.startswith("slot-1--module--edfa-occupant--")
               and kit[len("lc-duplex-plug--"):] == build[len("slot-1--module--edfa-occupant--"):]
               for _, kit, build in gaps), gaps
    assert len(gaps) == 4, gaps
    # and the shift is really in what was compared: an `out` moved, and a lift
    # written on the group, in every case
    for case in cases:
        for key, want in case["built"].items():
            assert want["attrs"].get("data-z-lift"), (case["name"], key)
            assert any("data-z-out" in d["a"] for d in want["children"]), (case["name"], key)


@needs_node
def test_insetFeature_is_render_py_inset_feature():
    """THE PORT, BRANCH BY BRANCH, against the function it ports. A real seat
    only ever calls it with back = -L and group_lift = L, so `lift`, `cyl`,
    `bar` and `uhandle` come out unchanged there; this grid drives every
    branch - a lift folded by a nonzero `back + group_lift`, a length
    re-measured from a moved base, a lift that reaches 0 and is dropped, a
    feature left wholly behind the face - through both and compares."""
    feats = [{"out": 6.35}, {"out": 12.5, "lift": 6.6}, {"lift": 10.0, "bar": 1.05},
             {"lift": 3, "cyl": 5}, {"uhandle": 24, "lift": 2.5, "out": 3.0},
             {"out": 0.15}, {"lift": 0.5}, {"cyl": 1.2}, {"top": 2.2, "color": "#fff"}]
    moves = [(0.0, 0.0), (-3.175, 3.175), (-47.175, 47.175), (3.0, -3.0), (-44.0, 0.0),
             (2.0, 0.0), (0.4, 0.2), (-1.2, 1.2), (5.0, 1.0), (-0.3, 0.0)]
    grid = [[f, b, g] for f in feats for b, g in moves]
    got = node("inset", json.dumps(grid))
    dropped = 0
    for (f, b, g), k in zip(grid, got):
        want = _inset_feature(dict(f), b, g)
        dropped += want is None
        assert (k is None) == (want is None), (f, b, g, k, want)
        if want is not None:
            assert set(k) == set(want), (f, b, g, k, want)
            for key, v in want.items():
                assert (abs(k[key] - v) < 1e-9) if isinstance(v, (int, float)) else k[key] == v, (
                    f, b, g, key, k[key], v)
    assert dropped and dropped < len(grid), dropped


# THE SHIFT, MUTATED. Each edit is applied to a copy of kit/swap.js and must
# make the parity above fail - on every case for the first, and on the slots
# under a lifted ancestor for the other two, which are the only ones where the
# group's own lift and the shift differ.
MUTATIONS = [
    ("no shift", "liftOccupant(wrap, +cage.lift || 0);", "liftOccupant(wrap, 0);", "all"),
    ("group lift is the effective lift",
     "const own = (+cage.lift || 0) - (+cage['seat-depth'] || 0);",
     "const own = (+cage.lift || 0);", "depth"),
    ("shift by the group's own lift",
     "liftOccupant(wrap, +cage.lift || 0);",
     "liftOccupant(wrap, (+cage.lift || 0) - (+cage['seat-depth'] || 0));", "depth"),
]


@needs_node
@pytest.mark.parametrize("label,old,new,where", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_a_mutated_shift_fails_the_parity(parity, tmp_path, label, old, new, where):
    cases, stdin, _ = parity
    src = SWAP.read_text()
    assert src.count(old) == 1, f"{label}: the anchor {old!r} is not in swap.js exactly once"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    bad = mismatches(cases, node("parity", stdin, swap=mutant), [])
    total = sum(len(c["built"]) for c in cases)
    hit = {b.split(":")[0] for b in bad}
    deep = {f"{c['name']} {k} ({w['ref']})" for c in cases for k, w in c["built"].items()
            if k.startswith("slot-1/module/ocm/") or k.startswith("slot-1/module/ppm-")}
    assert len(deep) == 8, deep
    if where == "all":
        assert len(hit) == total, f"{label}: only {len(hit)} of {total} cases failed"
    else:
        assert hit == deep, f"{label}: failed {sorted(hit ^ deep)[:6]} unexpectedly"
