"""A `cable` point may sit `'on':` a `cyl` feature, and lands at its far end.

A connection point `on:` a relief feature stands on that feature's REAR
(test_seat_depth.py; docs/pluggables-3d-design.md). That was defined only for
an `out` feature, whose rear is its `out` - absolute from the part's mounting
plane. A cable end whose cable leaves from a round stub (a boot's strain-relief
cylinder behind the head) has no `out`: its rear is `lift + cyl`, the far end
of the cylinder, in the feature's own frame. The lift is where it STARTS and is
summed up the ancestors exactly as relief.js's liftOf sums it; `cyl` is its
length from there.

The fixture: a part with a stub at lift 34.8, 30 long, and a `cable` point on
it. Its rear is 64.8. The existing `out` cases stay as they were
(test_seat_depth.py, test_cable_points_js.py).
"""
import xml.etree.ElementTree as ET

import pytest

from portrayal import lint
from portrayal import render as render_mod
from portrayal.manifest import presented_interface


def _part():
    return {
        "format": 1, "kind": "component", "name": "stubbed", "version": "1.0.0",
        "class": "connector", "size": {"w": 10, "h": 10}, "skins": ["default"],
        "interface": "cable-end",
        "interface-at": "cable",
        "connection-points": {
            "mate": {"at": [5, 5], "direction": "front"},
            "cable": {"at": [5, 5], "direction": "rear", "on": "stub"},
        },
        "relief": {"features": [
            {"node": "body", "out": 34.8},
            {"node": "stub", "lift": 34.8, "cyl": 30, "dia": 4},
        ]},
    }


def _lint(tmp_path, d):
    p = tmp_path / "contract.yaml"
    with lint.collecting() as got:
        lint.lint_component_seat_point(p, d)
        return [e for e in got.errors if "[L106]" in e]


def test_a_cable_point_on_a_cyl_lints_clean(tmp_path):
    assert _lint(tmp_path, _part()) == []


def test_a_feature_with_neither_out_nor_cyl_is_still_refused(tmp_path):
    d = _part()
    d["relief"]["features"][1] = {"node": "stub", "sink": 1.0}
    errs = _lint(tmp_path, d)
    assert len(errs) == 1 and "'stub'" in errs[0], errs


def test_a_point_on_a_cyl_presents_at_its_far_end():
    """manifest's seat depth, the other `on:` resolution: a part seated on the
    stub stands at lift + cyl."""
    _, at, lift = presented_interface(_part(), lambda ref: None)
    assert (at, lift) == ([5, 5], pytest.approx(64.8))


def _effective_lift(node, parents):
    total = 0.0
    while node is not None:
        if node.get("data-z-lift") is not None:
            total += float(node.get("data-z-lift"))
        node = parents.get(node)
    return total


def test_the_compiled_marker_resolves_to_the_stub_rear(tmp_path):
    """render.py names the stub on the marker; its rear is the stub's summed
    lift plus its data-z-cyl - relief.js's reading, done by hand here."""
    skins = tmp_path / "skins"
    skins.mkdir()
    (skins / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<rect id="body" width="10" height="10"/>'
        '<circle id="stub" cx="5" cy="5" r="2"/></svg>')
    lib = render_mod.Library([str(tmp_path)])
    lib.cache["local/stubbed@1"] = (_part(), skins)
    g, _ = render_mod.instance_group(lib, "local/stubbed@1", "t", [0, 0], None, None,
                                     None, None)
    root = ET.Element("root")
    root.append(g)
    parents = {c: p for p in root.iter() for c in p}
    marker = next(el for el in g.iter() if el.get("data-cp") == "cable")
    on = marker.get("data-cp-on")
    assert on == "t--stub", on
    feat = next(el for el in g.iter() if el.get("id") == on)
    assert feat.get("data-z-cyl") is not None and feat.get("data-z-out") is None
    rear = _effective_lift(feat, parents) + float(feat.get("data-z-cyl"))
    assert rear == pytest.approx(64.8)
