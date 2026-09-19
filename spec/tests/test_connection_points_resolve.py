"""The marker resolves where the geometry actually is, checked by hand.

generic/sfp-lc declares optical-tx at [3.60, 5.70] and, separately, composes
std/lc-bore@3 at [1.25, 1.75] rotated 180 with the bore declaring mate at
[2.35, 2.35] in a 4.7 x 6.3 body. The rotation centre [2.35, 3.15] and the
translation [1.25, 1.75] are NOT hardcoded here - they are READ from the
`transform` attribute render.py actually wrote on the bore's group, so a
fault in how render.py composes `translate(centre) rotate(deg)
translate(-w/2,-h/2)` - a wrong centre, a dropped rotate, a sign flip, a
wrong translate - fails this test instead of hiding behind a static
arithmetic identity. Applying that transform to the marker's own-frame point
gives [3.60, 5.70], which is exactly the value the parent contract
independently wrote down for its optical axis. The two numbers were written
independently and must agree, so this is a check on the RESOLUTION and not a
restatement of one contract.

It also pins the thing presented_interface gets wrong: that function forwards
`at + cm.at` and ignores `rotate`, which would put the point at [3.60, 4.10].
Nothing shipped composes a rotated aperture, so it is not a live defect - but
if a wrapper ever does, this arithmetic is the record of what correct means.
"""
import math
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"
SVG = "{http://www.w3.org/2000/svg}"
FIXTURE = "generic--sfp-lc--v1--default.svg"

# translate(tx, ty) rotate(deg cx cy) - the exact shape render.py emits for a
# composed part's placement transform.
TRANSFORM_RE = re.compile(
    r"translate\(\s*([-\d.]+)[,\s]+([-\d.]+)\s*\)\s*"
    r"rotate\(\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)\s*\)"
)


def _markers(root):
    return [el for el in root.iter(f"{SVG}g") if el.get("data-cp")]


def _parse_translate_rotate(transform):
    """Parse a `translate(tx,ty) rotate(deg cx cy)` attribute into numbers.

    Asserts the parse succeeded - a silently-unmatched regex whose caller
    then treats a None as an identity transform would reintroduce exactly
    the defect this test exists to catch.
    """
    m = TRANSFORM_RE.match(transform.strip())
    assert m is not None, f"could not parse transform: {transform!r}"
    tx, ty, deg, cx, cy = (float(v) for v in m.groups())
    return tx, ty, deg, cx, cy


def _apply_translate_rotate(tx, ty, deg, cx, cy, point):
    """Map a point through `translate(tx,ty) rotate(deg cx cy)`.

    SVG semantics: the rightmost transform applies first in the element's
    own frame, so the point is rotated about (cx, cy) first, then the
    result is translated by (tx, ty).
    """
    px, py = point
    rad = math.radians(deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    dx, dy = px - cx, py - cy
    rx = dx * cos_a - dy * sin_a + cx
    ry = dx * sin_a + dy * cos_a + cy
    return [round(rx + tx, 4), round(ry + ty, 4)]


def test_the_bores_mate_point_lands_on_the_declared_optical_axis():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    tx = [m for m in _markers(root) if m.get("data-cp") == "optical-tx"]
    assert len(tx) == 1, "sfp-lc declares exactly one optical-tx"
    declared = [float(v) for v in tx[0].get("data-cp-at").split()]
    assert declared == [3.6, 5.7]

    # the bore's own mate marker, inside the `tx` part group - selected by
    # its PARENT group's id, not by the `mate` name alone, because three
    # markers in this drawing share that name.
    bore_mates = [m for m in _markers(root) if m.get("data-cp") == "mate"
                  and (parent.get(m) is not None
                       and (parent[m].get("id") or "").endswith("--tx"))]
    assert len(bore_mates) == 1, (
        "expected one mate marker inside the tx bore's group; got "
        f"{len(bore_mates)}")

    # the marker must stay in the BORE's own frame, not pre-offset by the
    # placement - this is Task 1's actual regression target.
    at = [float(v) for v in bore_mates[0].get("data-cp-at").split()]
    assert at == [2.35, 2.35], "the marker must be in the bore's OWN frame"

    # resolve it through the transform render.py ACTUALLY WROTE on the
    # bore's group - not through hardcoded numbers - so a genuine fault in
    # transform generation fails this test.
    tx_group = next((el for k, el in by_id.items() if (k or "").endswith("--tx")),
                     None)
    assert tx_group is not None, "no tx bore group in the drawing"
    transform = tx_group.get("transform")
    assert transform, "tx bore group carries no transform"
    tform_tx, tform_ty, deg, cx, cy = _parse_translate_rotate(transform)
    assert deg == 180, (
        "this test's arithmetic assumes the 180 degree rotation sfp-lc uses "
        f"for its tx bore; got {deg}")

    resolved = _apply_translate_rotate(tform_tx, tform_ty, deg, cx, cy, at)
    assert resolved == declared, (
        f"the bore's mate resolves to {resolved} but the part declares its "
        f"optical axis at {declared}. Two independently written numbers for the "
        "same physical spot have stopped agreeing.")


def test_the_bore_group_carries_the_lift_that_displaces_it():
    """10.0 of lift is why a plug seated here is not buried in the body."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    tx = next((el for k, el in by_id.items() if k.endswith("--tx")), None)
    assert tx is not None, "no tx bore group in the drawing"
    assert float(tx.get("data-z-lift") or 0) == 10.0
