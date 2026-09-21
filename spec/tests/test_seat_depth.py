"""A connection point may name the relief feature it sits on (pluggables D, D3).

A boot seats on a plug's REAR, and the plug's rear is not its face: it is the
end of the plug body, which stands `out` millimetres proud of the face the plug
is drawn on. `presented_interface` returned 0.0 for every host that declares its
own `interface` + `mate`, which every plug does, so a boot seated on a plug was
drawn at the plug's face - inside the body it is supposed to wrap.

Two keys fix it, and both are opt-in:

- `interface-at: <point>` beside `interface` says WHICH connection point the
  presented interface is presented at. A plug mates INTO its receptacle at
  `mate` and presents `lc-plug` to a boot at `boot`; before this, the
  presented point was always `mate`, which is the wrong end of the plug.
- `on: <relief node>` on a connection point says the point sits on that relief
  feature, so a part seated there stands off by the feature's `out`. `out` is
  ABSOLUTE from the part's own face (memory: relief-out-is-absolute-lift-is-
  summed), so the rear face of a feature is at `out` whatever its `lift`.

A contract with neither key presents exactly what it did before, and a full
build of the library is byte-identical across this change (task-3-report.md).
"""
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint
from portrayal.manifest import presented_interface

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SRC = LIB / "devices/ufispace/s9510-28dc"
PLUG = LIB / "components/generic/lc-plug/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((SPEC / "schemas/component.schema.json").read_text())


def _res(table):
    return lambda ref: table.get(ref)


def _plug(**extra):
    """A synthetic LC plug: a body standing 12 proud, a boot point on it."""
    d = {
        "interface": "lc-plug",
        "mates": "lc",
        "connection-points": {
            "mate": {"at": [2.79, 7.61], "direction": "front"},
            "boot": {"at": [2.79, 7.61], "direction": "rear", "on": "body"},
        },
        "relief": {"features": [{"node": "body", "out": 12}]},
    }
    d.update(extra)
    return d


# ---------------------------------------------------------------- the unit

def test_interface_at_presents_the_named_point_lifted_by_its_feature():
    iface, at, lift = presented_interface(_plug(**{"interface-at": "boot"}), _res({}))
    assert (iface, at, lift) == ("lc-plug", [2.79, 7.61], 12.0)
    assert isinstance(lift, float)


def test_without_interface_at_the_mate_point_presents_and_lifts_nothing():
    """Exactly today's answer: the `mate` point, 0.0 - even though `boot` has
    an `on:`, because `boot` is not the point being presented."""
    iface, at, lift = presented_interface(_plug(), _res({}))
    assert (iface, at, lift) == ("lc-plug", [2.79, 7.61], 0.0)


def test_the_presented_point_is_the_named_one_not_mate():
    """A different position, so a test that passes on `mate` by coincidence
    of coordinates cannot pass here."""
    d = _plug(**{"interface-at": "boot"})
    d["connection-points"]["boot"]["at"] = [1.0, 2.0]
    _, at, _ = presented_interface(d, _res({}))
    assert at == [1.0, 2.0]


def test_a_point_on_a_lifted_feature_takes_its_out_not_out_plus_lift():
    """`out` is absolute; `lift` is where the feature STARTS, not where it ends."""
    d = _plug(**{"interface-at": "boot"})
    d["relief"]["features"][0]["lift"] = 3.0
    _, _, lift = presented_interface(d, _res({}))
    assert lift == 12.0


def test_the_mate_point_can_sit_on_a_feature_too():
    d = _plug()
    d["connection-points"]["mate"]["on"] = "body"
    _, _, lift = presented_interface(d, _res({}))
    assert lift == 12.0


def test_the_forwarded_path_is_unchanged():
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx",
                       "at": [1.25, 1.75], "lift": 10.0}]}
    assert presented_interface(host, _res({"std/lc-bore@3": bore})) == \
        ("lc", [3.6, 4.1], 10.0)


# ---------------------------------------------------------------- the schema

def _validate(d):
    base = {"format": 1, "kind": "component", "name": "x", "version": "1.0.0",
            "class": "port", "size": {"w": 5.58, "h": 10.43}}
    base.update(d)
    v = jsonschema.Draft202012Validator(COMPONENT_SCHEMA)
    return [e.message for e in v.iter_errors(base)]


def test_the_schema_accepts_both_keys():
    assert _validate(_plug(**{"interface-at": "boot"})) == []


def test_interface_at_is_allowed_only_beside_interface():
    d = _plug(**{"interface-at": "boot"})
    del d["interface"]
    errs = _validate(d)
    assert any("dependency" in e and "interface-at" in e for e in errs), errs


# ---------------------------------------------------------------- the lint

def _l105(tmp_path, d):
    p = tmp_path / "contract.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False))
    with lint.collecting() as got:
        lint.lint_component_seat_point(p, d)
        return ([e for e in got.errors if "[L106]" in e],
                [w for w in got.warnings if "[L106]" in w])


def test_a_well_formed_contract_is_clean(tmp_path):
    errs, warns = _l105(tmp_path, _plug(**{"interface-at": "boot"}))
    assert errs == [] and warns == []


def test_on_naming_a_missing_node_is_an_error(tmp_path):
    d = _plug(**{"interface-at": "boot"})
    d["connection-points"]["boot"]["on"] = "nope"
    errs, _ = _l105(tmp_path, d)
    assert len(errs) == 1 and "'nope'" in errs[0], errs


def test_on_naming_a_feature_with_no_out_is_an_error(tmp_path):
    """A feature that does not stand proud has no rear face to seat on."""
    d = _plug(**{"interface-at": "boot"})
    d["relief"]["features"] = [{"node": "body", "sink": 1.0}]
    errs, _ = _l105(tmp_path, d)
    assert len(errs) == 1 and "out" in errs[0], errs


def test_interface_at_naming_a_missing_point_is_an_error(tmp_path):
    d = _plug(**{"interface-at": "nope"})
    errs, _ = _l105(tmp_path, d)
    assert len(errs) == 1 and "'nope'" in errs[0], errs


def test_the_rule_is_catalogued():
    assert "L106" in lint.RULES


def test_no_library_contract_trips_the_rule():
    """The shipped library is clean under L106 - and the sweep measured
    something (skip-gates-and-vacuous-passes)."""
    seen, found = 0, []
    for f in sorted(LIB.glob("components/**/contract.yaml")):
        d = yaml.safe_load(f.read_text())
        seen += 1
        with lint.collecting() as got:
            lint.lint_component_seat_point(f, d)
            found += [e for e in got.errors if "[L106]" in e]
    assert seen > 100
    assert found == []


# ---------------------------------------------------------------- integration

def _effective_lift(root, target_id):
    """relief.js's `liftOf`: data-z-lift summed from a node up to the root."""
    parents = {c: p for p in root.iter() for c in p}
    node = next(el for el in root.iter() if el.get("id") == target_id)
    total = 0.0
    while node is not None:
        if node.get("data-z-lift") is not None:
            total += float(node.get("data-z-lift"))
        node = parents.get(node)
    return total


@pytest.mark.xfail(strict=True, reason=(
    "pluggables D Task 4 gives generic/lc-plug@1 its body `out` and points "
    "`interface-at: boot` / `boot.on: body` at it; until then the plug presents "
    "its mate point and lifts nothing"))
def test_a_boot_on_a_seated_plug_stands_on_the_plug_body(tmp_path):
    """Seat generic/sfp-lc-simplex@1 in an SFP cage, generic/lc-plug@1 in it and
    common/lc-boot@1 on the plug, through the chained `occupants:` keys.

    The hand arithmetic: s9510-28dc's port-4 cage is flush (cage lift 0), and
    the optic composes one std/lc-bore@3 at `lift: 10.0`, so the optic presents
    10.0 and the plug stands at 10.0. The boot stands at that PLUS the plug
    body's `out`, the absolute depth of the plug's rear face off its own face.
    The `out` is read from the contract because Task 4 sets it; the 10.0 is
    written here because nothing in this task may move it.
    """
    plug = yaml.safe_load(PLUG.read_text())
    cps = plug["connection-points"]
    at = plug.get("interface-at")
    assert at == "boot", "the plug does not present lc-plug at its boot point"
    on = cps[at]["on"]
    body_out = next(f["out"] for f in plug["relief"]["features"] if f["node"] == on)

    d = yaml.safe_load((SRC / "device.yaml").read_text())
    for cfg in d["configurations"].values():
        cfg["occupants"] = {
            "port-4": "generic/sfp-lc-simplex@1",
            "port-4-occupant": "generic/lc-plug@1",
            "port-4-occupant-occupant": "common/lc-boot@1",
        }
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    out.mkdir()
    r = subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--out", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    optic_presented = 10.0
    assert _effective_lift(root, "port-4-occupant") == 0.0
    assert _effective_lift(root, "port-4-occupant-occupant") == optic_presented
    boot = by_id["port-4-occupant-occupant-occupant"]
    assert float(boot.get("data-z-lift")) == optic_presented + float(body_out), (
        f"the boot's data-z-lift is {boot.get('data-z-lift')}; it should stand on "
        f"the plug's rear face at {optic_presented} + {body_out}")
