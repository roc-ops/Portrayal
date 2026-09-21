"""The kit seats an optic exactly where, and exactly as, the build does.

`kit/swap.js` gained `seatOccupant` so a runtime swap can put an optic into a
cage in 2D and 3D alike. It repeats ONE formula from render.py - `seat_at`, as
`occupantAt` - and assembles the occupant's attributes from three published
sources: the skin root's `data-*`, the cage's `occupant-attrs` (render.py's
`group_side_attrs`), and identity (`data-ref`, `data-for`, `id`/`data-path`).
A LIFTED cage is refused rather than half-seated - the build also shifts every
child's absolute `out`, and no lifted cage exists to hold that to. A formula checked against itself
proves nothing, so both halves are held to a REAL build: a fitted copy is
rendered, and what render.py wrote on every occupant is the expected answer.

THE LIBRARY SHIPS NO FITTED DEVICE (docs/pluggables-design.md decision 2), so
the fitted builds are copies in tmp_path - test_occupants' idiom. Two devices,
because the S9510-28DC has a turned QSFP28 cage but no turned SFP one; the
S9501-28SMT has twelve, and groups that carry a `description`.

The cages are PICKED from the bare build's `cages[]`, not hard-coded: an
upright and a turned cage of each form factor wherever the device has them.
"""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
DIST = LIB / "dist"
RENDER = SPEC / "tools/portrayal/render.py"
SCRIPT = SPEC / "tests/js/cage-seat.mjs"

QSFP, SFP = "generic/qsfp-lc@1", "generic/sfp-lc@1"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def run_render(dev, out):
    r = subprocess.run([sys.executable, str(RENDER), str(dev),
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]


def pick(cages, ref):
    """The first upright and the first turned cage that accept `ref`."""
    ok = [c for c in cages if ref in c["accepts"]]
    upright = next((c for c in ok if not c.get("rotate")), None)
    turned = next((c for c in ok if c.get("rotate")), None)
    return [c for c in (upright, turned) if c]


def build_components(out):
    """components.json and the compiled skins, BUILT HERE rather than read
    from library/dist - a stale dist is a stale answer, and nothing about this
    test would say so (the "gates measure the installed tree" hazard)."""
    r = subprocess.run([sys.executable, "-m", "portrayal.components_index",
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(SPEC / "tools")})
    assert r.returncode == 0, r.stderr[-600:]
    return out


def components(dist):
    idx = json.loads((dist / "components.json").read_text())["components"]
    return {f"{c['ns']}/{c['name']}@{c['major'].lstrip('v')}": c for c in idx}


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else None


def spec_of(el):
    """An element tree in the fake DOM's JSON form (tests/js/fake-dom.mjs)."""
    return {"t": local(el.tag), "a": dict(el.attrib),
            "c": [spec_of(k) for k in el if isinstance(k.tag, str)]}


def skin_file(dist, comp):
    return dist / "components" / f"{comp['ns']}--{comp['name']}--{comp['major']}--default.svg"


def skin_root(dist, comp):
    root = next(e for e in ET.parse(skin_file(dist, comp)).iter() if e.get("id") == comp["name"])
    return dict(root.attrib)


def descendants(el):
    """Every element below `el`, in document order, as (tag, attributes) -
    the build's side of the children comparison. An empty <style> is dropped:
    a standalone skin carries one and a device face does not, which seatModule
    has always done too, and it names nothing."""
    return [{"t": local(e.tag), "a": dict(e.attrib)} for e in el.iter()
            if e is not el and isinstance(e.tag, str)
            and not (local(e.tag) == "style" and not (e.text or "").strip() and not len(e))]


def fitted_ports(tmp_path, dist, name, refs, every=False):
    """Render `name` bare and fitted; return one parity case per seated port.
    `every` fills EVERY cage that accepts one of `refs` (the first it
    accepts), rather than one upright and one turned cage per ref."""
    src = LIB / "devices/ufispace" / name
    run_render(src / "device.yaml", tmp_path / f"{name}-bare")
    bare = json.loads((tmp_path / f"{name}-bare" / f"{name}.configs.json").read_text())
    cages = {c["id"]: c for c in bare["cages"]["front"]}
    if every:
        occupants = {c["id"]: next(r for r in refs if r in c["accepts"])
                     for c in bare["cages"]["front"] if any(r in c["accepts"] for r in refs)}
    else:
        occupants = {c["id"]: ref for ref in refs for c in pick(bare["cages"]["front"], ref)}
    assert occupants, f"{name}: no cage accepts any of {refs}"

    dev = tmp_path / f"{name}-fit" / name / "device.yaml"
    shutil.copytree(src, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    run_render(dev, tmp_path / f"{name}-fit" / "out")
    face = ET.parse(tmp_path / f"{name}-fit" / "out" / f"{name}.dc.front.svg")
    occ_els = {e.get("data-path"): e for e in face.iter()
               if (e.get("data-path") or "").endswith("-occupant")}
    built = {k: dict(e.attrib) for k, e in occ_els.items()}

    comps = components(dist)
    out = []
    for port, ref in occupants.items():
        comp = comps[ref]
        out.append({"port": port, "ref": ref, "cage": cages[port], "comp": comp,
                    "skinRoot": skin_root(dist, comp), "device": name,
                    "skin": json.dumps(spec_of(ET.parse(skin_file(dist, comp)).getroot())),
                    "built": built[f"{port}-occupant"],
                    "builtChildren": descendants(occ_els[f"{port}-occupant"])})
    return out


def parse_transform(tf):
    import re
    m = re.fullmatch(r"translate\(([^,]+),([^)]+)\)(?: rotate\(([^ ]+) ([^ ]+) ([^)]+)\))?", tf)
    assert m, tf
    rot = [float(v) for v in m.group(3, 4, 5)] if m.group(3) else None
    return {"tx": float(m.group(1)), "ty": float(m.group(2)), "rotate": rot}


def node(mode, stdin=None):
    p = subprocess.run(["node", str(SCRIPT), mode], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cage-seat")
    dist = build_components(tmp / "dist")
    return (fitted_ports(tmp, dist, "s9510-28dc", [QSFP, SFP])
            + fitted_ports(tmp, dist, "s9501-28smt", [SFP]))


@pytest.fixture(scope="module")
def every_case(tmp_path_factory):
    """Every cage of both devices filled - 52 occupants at this writing."""
    tmp = tmp_path_factory.mktemp("cage-seat-every")
    dist = build_components(tmp / "dist")
    return (fitted_ports(tmp, dist, "s9510-28dc", [QSFP, SFP], every=True)
            + fitted_ports(tmp, dist, "s9501-28smt", [SFP], every=True))


@needs_node
def test_the_kit_seats_every_optic_where_the_build_does(cases):
    # the matrix this is meant to cover must actually be in it - a device edit
    # that un-turned every cage would otherwise pass on upright seats alone
    kinds = {(c["ref"], bool(c["cage"].get("rotate"))) for c in cases}
    assert kinds == {(QSFP, False), (QSFP, True), (SFP, False), (SFP, True)}, kinds
    assert any("data-description" in c["cage"]["occupant-attrs"] for c in cases)

    got = node("parity", json.dumps({"ports": cases}))
    assert [g["port"] for g in got] == [c["port"] for c in cases]
    for case, g in zip(cases, got):
        where = f"{case['device']} {case['port']} ({case['ref']})"
        want = parse_transform(case["built"]["transform"])
        t = g["transform"]
        assert t, f"{where}: kit wrote {g['transformText']!r}"
        assert abs(t["tx"] - want["tx"]) < 1e-6 and abs(t["ty"] - want["ty"]) < 1e-6, (
            f"{where}: kit {g['transformText']} vs build {case['built']['transform']}")
        assert (t["rotate"] is None) == (want["rotate"] is None), where
        if want["rotate"]:
            assert all(abs(a - b) < 1e-6 for a, b in zip(t["rotate"], want["rotate"])), where

        # EQUAL, not a subset: an attribute the build writes that the kit cannot
        # supply is a missing published fact, and one the kit invents is a lie
        built = {k: v for k, v in case["built"].items() if k.startswith("data-") or k == "id"}
        assert g["attrs"] == built, (
            f"{where}: kit-only {sorted(set(g['attrs']) - set(built))}, "
            f"build-only {sorted(set(built) - set(g['attrs']))}, differing "
            f"{sorted(k for k in set(g['attrs']) & set(built) if g['attrs'][k] != built[k])}")


@needs_node
def test_a_kit_seated_optics_children_are_the_builds(every_case):
    """THE CHILDREN, NOT ONLY THE GROUP. seatOccupant renames the skin's own
    namespace into the occupant's (`sfp-lc--tx` -> `port-4-occupant--tx`,
    `url(#...)` rewritten with it), and the 3D scene reads every child's
    data-path and data-z-*. The final review measured all of them equal on
    every occupant of both devices; this holds it: every descendant, in
    document order, with EVERY attribute - id, data-path, data-z-*, url()
    references and the rest - against what render.py wrote."""
    cases = every_case
    turned = sum(bool(c["cage"].get("rotate")) for c in cases)
    assert turned and turned < len(cases), turned
    got = node("children", json.dumps({"ports": cases}))
    assert len(got) == len(cases) >= 50, len(got)
    for case, g in zip(cases, got):
        where = f"{case['device']} {case['port']} ({case['ref']})"
        want = case["builtChildren"]
        assert want, f"{where}: the build's occupant has no children - vacuous"
        assert any(k.startswith("data-z-") for d in want for k in d["a"]), (
            f"{where}: no data-z-* below the occupant - the 3D half is unchecked")
        assert len(g["children"]) == len(want), (
            f"{where}: kit {len(g['children'])} children, build {len(want)}")
        for i, (k, b) in enumerate(zip(g["children"], want)):
            assert k == b, f"{where}: child {i} differs: kit {k} vs build {b}"


@needs_node
def test_an_occupant_override_replaces_empties_and_leaves_alone():
    out = node("overrides")
    assert out["before"] == {f"port-{i}": 1 for i in range(4, 11)}
    assert out["applied"] == 5, (
        "port-7 is not in the map and must not be touched; port-6's skin never "
        "loaded, so nothing about it changed")
    assert out["refused"] == ["port-8", "port-9", "port-10"], (
        "a lifted, a mirrored and a group-states cage are each refused, and the "
        "refusal is reported to the caller")
    for port in ("port-8", "port-9", "port-10"):
        assert out["after"][port] == [], (
            f"{port}: a refused cage is left empty - never a half-seated optic")
    assert out["seatRefused"] == [None, None, None]
    assert out["reasons"] == [None, None, None, None, "lift", "mirror", "group-states"]
    assert out["emptyRefused"] == {"applied": 1, "refused": [], "failed": []}, (
        "emptying a refused cage is not a refusal")
    assert out["second"] == {"applied": 1, "refused": [], "failed": []}

    [p4] = out["after"]["port-4"]
    assert p4["ref"] == "generic/sfp-lc-simplex@2:2.0.0", "one occupant, the new one"
    assert p4["id"] == p4["path"] == "port-4-occupant"
    assert p4["besideHost"] == "port-4", "seated as the host's next sibling"
    assert p4["media"] == "sfp28" and p4["group"] == "sfp28", (
        "the cage's occupant-attrs win over the skin's own media")
    assert p4["children"] == [["port-4-occupant--body", None],
                              ["port-4-occupant--tx", "port-4-occupant/tx"]]
    assert p4["transform"].startswith("translate(")

    assert out["after"]["port-5"] == [], "null empties the cage"
    # A FAILED LOAD IS REPORTED AND CHANGES NOTHING: the cage keeps the optic
    # it held, so a caller's state can say what the drawing shows
    assert out["failed"] == ["port-6"], "a skin that did not load is reported"
    assert [o["ref"] for o in out["after"]["port-6"]] == ["generic/sfp-lc@1:1.0.0"], (
        "a failed load must not empty the cage")
    assert out["heldAfterFailure"] == "generic/sfp-lc@1"
    assert out["heldWhenEmpty"] is None
    assert [o["ref"] for o in out["after"]["port-7"]] == ["generic/sfp-lc@1:1.0.0"]
    assert out["led"] == 1, "an LED data-for the same port is not an occupant"
    assert out["again"] == ["generic/sfp-lc@1:1.0.0"], (
        "a second swap replaces the first swap's occupant rather than stacking")


@needs_node
def test_an_occupant_is_named_with_no_namespace_word():
    out = node("rename")
    assert out["bare"] == [
        [None, "port-4-occupant", None],
        ["port-4-occupant--tx", "port-4-occupant/tx", None],
        ["port-4-occupant--w0", None, None],
        [None, None, "url(#port-4-occupant--w0)"],
    ]
    assert out["dflt"] == [
        [None, "front-0/module", None],
        ["front-0--module--tx", "front-0/module/tx", None],
        ["front-0--module--w0", None, None],
        [None, None, "url(#front-0--module--w0)"],
    ]


@needs_node
def test_overlapping_swaps_on_one_target_end_as_one_and_the_later():
    """The final review's reproduction, held: two applies on one cage whose
    skin loads were both in flight left TWO optics on the face (['a', 'b']),
    and the bay path had the same shape. One mechanism - a claim per target
    (seatClaims) plus load-before-remove - covers bays and cages."""
    out = node("race")
    assert out["cageInOrder"] == ["generic/b@1:1.0.0"], (
        "two unclaimed overlapping cage swaps stacked two optics")
    assert out["cageOutOfOrder"] == ["generic/b@1:1.0.0"], (
        "the later request must win even when the earlier fetch resolves last")
    assert out["cageResults"][0] == {"applied": 0, "refused": [], "failed": []}, (
        "a stale claim is none of applied, refused or failed")
    assert out["cageEmptiedWhileLoading"] == [], (
        "emptying a cage while an earlier swap loads must not be undone by it")
    assert out["bayOutOfOrder"] == ["generic/b@1"], (
        "overlapping bay swaps must leave one module, the later one")
    assert out["claims"] == [False, True, True], (
        "a newer claim retires an older one on the same key and no other")
