"""What a bore is off the panel, the plug seated in it is too.

The bay case is already held by test_bay_occupant_lift.py. This is the MATE-TO
case, which had no z at all: only `parts:` composition carried `lift`, so an
occupant positioned by mate points sat at the panel plane no matter how far
forward the thing it seats into stands.

Asserted on the UNIT rather than on a shipped drawing, because no device in the
library seats an optic any more - spec A made them all bare on purpose - so
there is no compiled fixture to read. The invariant is about the function.
"""
from portrayal.manifest import presented_interface


def _res(table):
    return lambda ref: table.get(ref)


def test_a_host_that_presents_its_own_point_lifts_nothing():
    host = {"interface": "sfp", "connection-points": {"mate": {"at": [8.0, 5.0]}}}
    iface, at, lift = presented_interface(host, _res({}))
    assert (iface, at) == ("sfp", [8.0, 5.0])
    assert lift == 0.0, "a host mating on its own face displaces nothing"


def test_a_forwarded_point_carries_the_composed_parts_lift():
    """The whole point: the aperture is the thing that stands forward."""
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx",
                       "at": [1.25, 1.75], "lift": 10.0}]}
    iface, at, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert iface == "lc"
    assert at == [3.6, 4.1]
    assert lift == 10.0, (
        "the bore stands 10.0 off the module face; a plug seated in it that "
        "ignores that is buried in the transceiver body")


def test_a_composed_part_with_no_lift_forwards_zero():
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx", "at": [1.25, 1.75]}]}
    _, _, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert lift == 0.0


# ---------------------------------------------------------------------------
# AND THE SAME INVARIANT AT RENDER LEVEL, because the unit tests above prove
# only that `presented_interface` REPORTS the lift. They say nothing about
# whether draw_placement carries it into the drawing, and for the whole of this
# branch's first draft it did not: the occupant's `lift` was fed to `z_inset`
# alone, which writes no attribute, so the occupant's group carried no
# `data-z-lift`, relief.js's `liftOf` returned 0 for it, and a plug seated in a
# 10 mm-proud bore drew buried in the transceiver body. The comment claimed the
# attribute was written; nothing checked.
#
# CARRYING IT IS A TRIO, not one assignment - `z_inset -= lift`,
# `z_group_lift += lift`, and `data-z-lift` on the group - because relief.js
# reads `data-z-out` as ABSOLUTE and SUMS `data-z-lift` up the ancestor chain.
# The first alone moves nothing; the third without the second counts the lift
# twice, which is the dcp-f-a22 white-spikes defect
# (test_composed_lift_not_doubled.py). So both halves are asserted here: the
# effective lift is the aperture's, and the relief inside the occupant still
# has the extent it has anywhere else.
#
# THE HOST IS `generic/sfp-lc-simplex@1`, and the choice is not arbitrary.
# `std/sfp-ganged@1` presents its own `mate` point and so forwards a lift of
# ZERO - seating on it would pass whatever this code did. `generic/sfp-lc@1`
# composes two lifted bores, and `presented_interface` declines to pick one of
# two, so it forwards zero as well. The simplex part composes exactly ONE
# `std/lc-bore@3` at `lift: 10.0`, which makes it the only host in the library
# that presents a non-zero lift - checked below rather than assumed.
#
# The PLUG is planted in a scratch library (spec B2 owns the real ones, and
# this branch adds no parts), seated on a scratch device, and rendered by
# subprocess - the idiom test_occupants.py uses.
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
HOST = "generic/sfp-lc-simplex@1"
SVG = "{http://www.w3.org/2000/svg}"

# the plug's own relief, which is what proves the lift is counted ONCE. `tip`
# declares a lift of its own, so a lift folded into both the group and the
# child - the double-count - shows up as a `tip` standing 10 mm further out
# than it does on a bare plug.
PLUG_TIP_LIFT = 3.0
PLUG_TIP_OUT = 4.0


def _plant_plug(root):
    """An LC plug in a scratch library. Not a part - a test fixture."""
    d = root / "components" / "acme" / "lc-plug" / "v1"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "component", "name": "lc-plug", "version": "1.0.0",
        "class": "port", "interface": "lc", "size": {"w": 4.0, "h": 4.0, "d": 20.0},
        "elements": {"body": {"at": [0, 0], "size": [4.0, 4.0]},
                     "tip": {"at": [1.0, 1.0], "size": [2.0, 2.0]}},
        "relief": {"features": [{"node": "body", "out": 2.0},
                                {"node": "tip", "lift": PLUG_TIP_LIFT,
                                 "out": PLUG_TIP_OUT}]},
        "connection-points": {"mate": {"at": [2.0, 2.0], "direction": "front"},
                              "cable": {"at": [2.0, 2.0], "direction": "rear"}},
        "skins": ["default"],
    }))
    (d / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="4mm" height="4mm" '
        'viewBox="0 0 4 4">'
        '<rect id="body" x="0" y="0" width="4" height="4" fill="#2b6cb0"/>'
        '<rect id="tip" x="1" y="1" width="2" height="2" fill="#e8ecef"/>'
        "</svg>")
    return root


def _device(path, seated):
    """One host at a known position, with or without a plug seated in it."""
    placements = [{"id": "port-1", "ref": HOST, "at": [10, 10]}]
    if seated:
        placements.append({"id": "plug-1", "ref": "acme/lc-plug@1",
                           "mate-to": "port-1"})
    path.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": "seat", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "T", "model": "T",
        "chassis": {"width": 60, "height": 30, "depth": 60},
        "views": {"front": {"size": {"w": 60, "h": 30},
                            "components": {"placements": placements}}},
    }))
    return path


def _render(dev, scratch_lib, out):
    r = subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--library", str(scratch_lib), "--out", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return ET.parse(out / "seat.front.svg").getroot()


def _lift_of(el, parent):
    """relief.js's liftOf: the sum up the ancestor chain, this node included."""
    total = 0.0
    while el is not None:
        total += float(el.get("data-z-lift") or 0)
        el = parent.get(el)
    return total


def _aperture_lift():
    from portrayal.manifest import presented_interface
    contract = yaml.safe_load(
        (LIB / "components/generic/sfp-lc-simplex/v1/contract.yaml").read_text())

    def res(ref):
        ns, rest = ref.split("/", 1)
        name, major = rest.split("@")
        p = LIB / f"components/{ns}/{name}/v{major}/contract.yaml"
        return yaml.safe_load(p.read_text()) if p.exists() else None

    _, _, lift = presented_interface(contract, res)
    return lift


def test_a_mate_to_occupant_carries_the_hosts_aperture_lift(tmp_path):
    lift = _aperture_lift()
    assert lift == 10.0, (
        f"{HOST} was chosen because it presents a lifted aperture; it now "
        f"presents {lift}, so this test proves nothing. Find another host "
        "with a non-zero presented lift before relaxing this.")

    lib = _plant_plug(tmp_path / "lib")
    root = _render(_device(tmp_path / "device.yaml", seated=True), lib,
                   tmp_path / "out")
    parent = {c: p for p in root.iter() for c in p}
    plug = next((el for el in root.iter() if el.get("data-path") == "plug-1"), None)
    assert plug is not None, "the plug was not seated in the drawing at all"

    got = _lift_of(plug, parent)
    assert got == lift, (
        f"the seated plug's effective lift is {got}, not the {lift} its host's "
        f"aperture stands off the face. At 0 it is buried in the transceiver "
        f"body; at {2 * lift} the lift has been counted twice and every solid "
        "on the plug builds inside out.")
    assert got != 2 * lift, "the aperture lift has been double-counted"


def test_seating_the_plug_does_not_resize_its_relief(tmp_path):
    """The other half of the trio. Lifting a part moves it; it must not
    stretch it - so `out` minus the summed lift is the same seated as bare."""
    lib = _plant_plug(tmp_path / "lib")
    root = _render(_device(tmp_path / "device.yaml", seated=True), lib,
                   tmp_path / "out")
    parent = {c: p for p in root.iter() for c in p}
    tip = next((el for el in root.iter() if (el.get("id") or "") == "plug-1--tip"),
               None)
    assert tip is not None, "the plug's tip did not reach the drawing"
    extent = float(tip.get("data-z-out")) - _lift_of(tip, parent)
    assert extent == pytest.approx(PLUG_TIP_OUT - PLUG_TIP_LIFT), (
        f"the tip's extent is {extent} seated and "
        f"{PLUG_TIP_OUT - PLUG_TIP_LIFT} on a bare plug. A lift folded into "
        "the group AND into the child's own lift is counted twice (see "
        "_inset_feature's group_lift, and the dcp-f-a22 white spikes).")
