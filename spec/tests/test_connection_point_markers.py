"""Every declared connection point reaches the drawing, and none of them is a feature.

render.py read `mate` to place an occupant and dropped the rest, so a part's
optical-tx, power or cable point existed in the contract and nowhere a consumer
could see it. The cabling library in spec B needs the `cable` point; A's
transceivers get optical-tx/rx back for free.

A marker is deliberately INERT: no data-z-*, no data-ref, no data-path, no
data-class. relief.js decides what exists in 3D by querying the DOM for
attributes, and its own comment warns that every query is a chance to see data
it should not. A marker that carried data-z-out would become a raised box.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"
SVG = "{http://www.w3.org/2000/svg}"

# generic/sfp-lc declares three points and composes two bores that declare one
# each - the richest small fixture in the library.
FIXTURE = "generic--sfp-lc--v1--default.svg"


def markers(root):
    return [el for el in root.iter(f"{SVG}g") if el.get("data-cp")]


def test_a_parts_own_points_are_emitted():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    got = {m.get("data-cp") for m in markers(root)}
    assert {"mate", "optical-tx", "optical-rx"} <= got, (
        f"generic/sfp-lc declares mate, optical-tx and optical-rx; the drawing "
        f"carries {sorted(got)}")


def test_a_point_carries_its_position_and_direction():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}
    # THE PART'S OWN POINTS, not a composed bore's. There are three `mate`
    # markers in this drawing - sfp-lc's own and one inside each lc-bore - so
    # selecting by name alone reads whichever came last. A point belongs to the
    # part whose instance group is its DIRECT parent.
    own = {m.get("data-cp"): m for m in markers(root)
           if (parent.get(m) is not None
               and parent[m].get("data-ref", "").startswith("generic/sfp-lc@"))}
    assert set(own) == {"mate", "optical-tx", "optical-rx"}, (
        f"sfp-lc's own points are {sorted(own)}; a composed bore's mate has "
        "leaked into the selection")
    # the contract's own numbers, in the part's own frame
    assert own["mate"].get("data-cp-at") == "6.775 4.275"
    assert own["mate"].get("data-cp-dir") == "front"
    assert own["optical-tx"].get("data-cp-at") == "3.6 5.7"


def test_a_composed_parts_points_come_too():
    """The two std/lc-bore@3 cores inside sfp-lc each declare a `mate`."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    mates = [m for m in markers(root) if m.get("data-cp") == "mate"]
    assert len(mates) == 3, (
        "expected the part's own mate plus one from each composed bore, got "
        f"{len(mates)}")


def test_a_marker_is_inert():
    """It must be invisible to relief.js, shell.js and states.js alike."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    for m in markers(root):
        for bad in ("data-ref", "data-path", "data-class", "data-depth",
                    "data-body-depth", "data-behaviour"):
            assert m.get(bad) is None, (
                f"marker {m.get('data-cp')} carries {bad}; shell.js reads "
                "[data-ref] as occupancy and states.js indexes [data-path]")
        for k in m.attrib:
            assert not k.startswith("data-z-"), (
                f"marker {m.get('data-cp')} carries {k}; relief.js would build "
                "a box out of it")
        assert len(list(m)) == 0, "a marker draws nothing"


def test_every_built_component_with_points_has_markers():
    """Not just the fixture - the whole library, so a regression is loud."""
    if not DIST.exists():
        pytest.skip("components not built")
    seen = 0
    for f in sorted(DIST.glob("*--default.svg")):
        root = ET.parse(f).getroot()
        seen += len(markers(root))
    assert seen > 100, (
        f"only {seen} connection-point markers across the whole built library; "
        "94 components declare connection-points, so the loop is not running")
