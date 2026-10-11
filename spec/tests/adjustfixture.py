"""The adjustments fixture, for the tests of adjustable positions.

`spec/tests/fixtures/adjustments/lib` is a library root of its own: one device,
`fixture/slider`, and the four parts it places (its README says what each is).
The tests of each build step read it through here, so they share one device
and one way of linting and rendering it.
"""
import copy
import json
import pathlib
import sys

import yaml

import warmrender
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/adjustments/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/slider/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
ROOTS = [FIXTURE_LIB, LIB]
AID = "panel-setback"
CODES = tuple(f"L{n}" for n in range(173, 184))


def device():
    """The fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def placement(doc, view, pid):
    return next(p for p in doc["views"][view]["components"]["placements"] if p["id"] == pid)


def decor(doc, view, did):
    return next(d for d in doc["views"][view]["panel"]["decor"] if d.get("id") == did)


def findings(doc, path=DEVICE):
    """Every finding of the adjustment rules (L173 to L183) on `doc`, as
    `{code: [message]}`. The schema is asked first, as lint asks it: a
    document it refuses is reported under L1."""
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    from jsonschema import Draft202012Validator
    out = {}
    for e in Draft202012Validator(schema).iter_errors(doc):
        out.setdefault("L1", []).append(f"{'/'.join(str(p) for p in e.path)}: {e.message}")
    if out:
        return out
    with lint.collecting() as got:
        lint.lint_device_adjustments(path, doc, ROOTS)
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def render(tmp, edit=None):
    """Build the fixture (after `edit(doc)`, if given) into `tmp/o`.
    Returns (out dir, completed process)."""
    doc = device()
    if edit:
        edit(doc)
    dev = tmp / "slider" / "device.yaml"
    dev.parent.mkdir(parents=True, exist_ok=True)
    dev.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    return out, r
