"""The wires of a plug, read by the kit.

A terminal plug leaves by one wire per pole, `wire-1` to `wire-N`, each on its
own stub. kit/relief.js `cablePoints(svg, 'wire')` (and `wirePoints`) reads
those points the way it reads a `cable` point: position, direction, the
feature it sits on and the seat chain, one point per wire. What a wire is in
the cable model is not decided by it.

- js/wire-points.mjs runs the reader over hand-built trees (no build needed);
- js/wire-points-built.mjs reads the compiled preview of every plug whose
  contract names wire points and this file compares it with the contract, so
  it needs a build.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
JS = Path(__file__).resolve().parent / "js"
LIB = ROOT / "library"
PREVIEWS = LIB / "dist" / "components"
WIRE = re.compile(r"wire-(\d+)")
NODE = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def plugs_with_wires():
    found = {}
    for path in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        doc = yaml.safe_load(path.read_text())
        points = doc.get("connection-points") or {}
        if any(WIRE.fullmatch(n) for n in points):
            ns, name, major = path.parts[-4], path.parts[-3], path.parts[-2]
            found[f"{ns}/{name}@{major[1:]}"] = (doc, f"{ns}--{name}--{major}--default.svg")
    return found


PLUGS = plugs_with_wires()
EACH = pytest.mark.parametrize("ref", sorted(PLUGS))


@NODE
def test_the_reader_over_hand_built_trees():
    p = subprocess.run(["node", "--test", str(JS / "wire-points.mjs")], capture_output=True,
                       text=True, cwd=str(JS), timeout=300)
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-2000:]
    assert "# fail 0" in p.stdout, p.stdout[-2000:]
    assert "# pass 0" not in p.stdout, p.stdout[-2000:]


def test_the_library_has_plugs_with_wires_to_read():
    assert len(PLUGS) >= 3, sorted(PLUGS)


@EACH
def test_the_wires_of_a_plug_are_numbered_from_1_without_a_gap(ref):
    points = PLUGS[ref][0]["connection-points"]
    numbers = sorted(int(WIRE.fullmatch(n).group(1)) for n in points if WIRE.fullmatch(n))
    assert numbers == list(range(1, len(numbers) + 1)), sorted(points)
    assert all(re.fullmatch(r"wire-[1-9]\d*", n) for n in points if n.startswith("wire-")), sorted(points)


@EACH
def test_the_wires_of_a_plug_are_at_places_of_their_own(ref):
    points = PLUGS[ref][0]["connection-points"]
    at = [tuple(p["at"]) for n, p in points.items() if WIRE.fullmatch(n)]
    assert len(set(at)) == len(at), at


def expected_z(doc, point):
    """Where the kit puts the point's depth: the node's absolute `out`, or a
    cyl's lift plus its length; the part's own face when it names no node."""
    on = point.get("on")
    if on is None:
        return 0
    feature = next(f for f in doc["relief"]["features"] if f["node"] == on)
    if "out" in feature:
        return feature["out"]
    return feature.get("lift", 0) + feature["cyl"]


@pytest.fixture(scope="module")
def read():
    files = {ref: PREVIEWS / preview for ref, (_doc, preview) in PLUGS.items()}
    missing = [f.name for f in files.values() if not f.exists()]
    assert not missing, f"library/dist/components/{missing[0]} is missing - run build.sh"
    p = subprocess.run(["node", str(JS / "wire-points-built.mjs"), *map(str, files.values())],
                       capture_output=True, text=True, cwd=str(JS), timeout=300)
    assert p.returncode == 0, p.stderr[-2000:]
    got = json.loads(p.stdout.strip().splitlines()[-1])
    return {ref: got[str(f)] for ref, f in files.items()}


@EACH
def test_the_compiled_plug_gives_one_point_per_wire(read, ref):
    doc = PLUGS[ref][0]
    points = doc["connection-points"]
    names = sorted((n for n in points if WIRE.fullmatch(n)), key=lambda n: int(n[5:]))
    got = read[ref]
    assert got["warned"] == []
    assert [p["name"] for p in got["wires"]] == names
    assert [p["wire"] for p in got["wires"]] == list(range(1, len(names) + 1))
    for p in got["wires"]:
        want = points[p["name"]]
        assert p["at"] == pytest.approx(want["at"])
        assert p["dir"] == want.get("direction")
        assert p["z"] == pytest.approx(expected_z(doc, want)), p["name"]


@EACH
def test_the_wires_are_not_read_as_cable_ends(read, ref):
    points = PLUGS[ref][0]["connection-points"]
    assert [p["name"] for p in read[ref]["cables"]] == (["cable"] if "cable" in points else [])
