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


def components():
    idx = json.loads((DIST / "components.json").read_text())["components"]
    return {f"{c['ns']}/{c['name']}@{c['major'].lstrip('v')}": c for c in idx}


def skin_root(comp):
    f = DIST / "components" / f"{comp['ns']}--{comp['name']}--{comp['major']}--default.svg"
    root = next(e for e in ET.parse(f).iter() if e.get("id") == comp["name"])
    return dict(root.attrib)


def fitted_ports(tmp_path, name, refs):
    """Render `name` bare and fitted; return one parity case per seated port."""
    src = LIB / "devices/ufispace" / name
    run_render(src / "device.yaml", tmp_path / f"{name}-bare")
    bare = json.loads((tmp_path / f"{name}-bare" / f"{name}.configs.json").read_text())
    cages = {c["id"]: c for c in bare["cages"]["front"]}
    occupants = {c["id"]: ref for ref in refs for c in pick(bare["cages"]["front"], ref)}
    assert occupants, f"{name}: no cage accepts any of {refs}"

    dev = tmp_path / f"{name}-fit" / name / "device.yaml"
    shutil.copytree(src, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    run_render(dev, tmp_path / f"{name}-fit" / "out")
    face = ET.parse(tmp_path / f"{name}-fit" / "out" / f"{name}.dc.front.svg")
    built = {e.get("data-path"): dict(e.attrib) for e in face.iter()
             if (e.get("data-path") or "").endswith("-occupant")}

    comps = components()
    out = []
    for port, ref in occupants.items():
        comp = comps[ref]
        out.append({"port": port, "ref": ref, "cage": cages[port], "comp": comp,
                    "skinRoot": skin_root(comp), "device": name,
                    "built": built[f"{port}-occupant"]})
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
    return (fitted_ports(tmp, "s9510-28dc", [QSFP, SFP])
            + fitted_ports(tmp, "s9501-28smt", [SFP]))


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
def test_an_occupant_override_replaces_empties_and_leaves_alone():
    out = node("overrides")
    assert out["before"] == {"port-4": 1, "port-5": 1, "port-6": 1, "port-7": 1, "port-8": 1}
    assert out["applied"] == 4, "port-7 is not in the map and must not be touched"
    assert out["refused"] == ["port-8"], (
        "a lifted cage is refused, and the refusal is reported to the caller")
    assert out["after"]["port-8"] == [], (
        "a refused cage is left empty - never a half-lifted optic")
    assert out["seatLifted"] is None
    assert out["second"] == {"applied": 1, "refused": []}

    [p4] = out["after"]["port-4"]
    assert p4["ref"] == "generic/sfp-lc-simplex@1:1.0.0", "one occupant, the new one"
    assert p4["id"] == p4["path"] == "port-4-occupant"
    assert p4["besideHost"] == "port-4", "seated as the host's next sibling"
    assert p4["media"] == "sfp28" and p4["group"] == "sfp28", (
        "the cage's occupant-attrs win over the skin's own media")
    assert p4["children"] == [["port-4-occupant--body", None],
                              ["port-4-occupant--tx", "port-4-occupant/tx"]]
    assert p4["transform"].startswith("translate(")

    assert out["after"]["port-5"] == [], "null empties the cage"
    assert out["after"]["port-6"] == [], "an unknown ref leaves the cage empty"
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
