"""The fifty-five rear-faced fibre modules project exactly as they did before
the trunk existed.

`optical.trunk` (roc-ops/Portrayal#246) rewired the projection's three decision
points - which modules export, which end of a leg is the rear, how a rear port
is named - and for a module with a rear face every one of them must answer as
before. A rear face is the trunk by construction; `is_trunk` reads the face
prefix first, so the FS cassettes and panels and the Fibrain holders should
not notice. This is what checks that they did not.

PINNED BY DIGEST, NOT BY FILE. The fixture holds, per model, a digest of the
fibre map and of the front and rear port lists in each target - what a DCIM
imports - and not the comments, which carry contract version stamps that move
on every honest bump. It was recorded from the exports the trunk change was
built on. A digest that moves is either a projection change somebody meant, in
which case re-record the fixture in the same commit and say why, or a
regression, which is what this exists to catch. The population is pinned too:
a rear-faced model appearing or vanishing changes the key set.

Reads the committed exports, so it needs no build.
"""
import hashlib
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "library" / "exports"
FIXTURE = ROOT / "spec" / "tests" / "fixtures" / "rear_faced_fibre_projection.json"


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def current():
    out = {}
    for fm in sorted((EXPORTS / "fibre-maps").rglob("*.yaml")):
        man = fm.parent.name
        if man == "Smartoptics":
            continue                     # single-faced, with a stated trunk
        row = {"fibre-map": digest(yaml.safe_load(fm.read_text()))}
        for target in ("netbox", "nautobot"):
            d = yaml.safe_load((EXPORTS / target / "module-types" / man / fm.name).read_text())
            row[target] = digest({k: d.get(k) for k in ("front-ports", "rear-ports")})
        out[f"{man}/{fm.stem}"] = row
    return out


def test_the_rear_faced_fibre_modules_export_exactly_as_before_the_trunk():
    if not (EXPORTS / "fibre-maps").exists():
        pytest.skip("library/exports has no fibre maps")
    want = json.loads(FIXTURE.read_text())
    got = current()
    assert len(want) == 55, "the fixture is the fifty-five rear-faced modules"
    assert sorted(got) == sorted(want), sorted(set(got) ^ set(want))
    moved = sorted(m for m in want if got[m] != want[m])
    assert not moved, f"rear-faced projections changed: {moved}"
