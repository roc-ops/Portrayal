"""The marker resolves where the geometry actually is, checked by hand.

generic/sfp-lc declares optical-tx at [3.60, 5.70] and, separately, composes
std/lc-bore@3 at [1.25, 1.75] rotated 180 with the bore declaring mate at
[2.35, 2.35] in a 4.7 x 6.3 body. Rotating about the bore's centre [2.35, 3.15]
gives [2.35, 3.95]; translating gives [3.60, 5.70]. The two numbers were written
independently and must agree, so this is a check on the RESOLUTION and not a
restatement of one contract.

It also pins the thing presented_interface gets wrong: that function forwards
`at + cm.at` and ignores `rotate`, which would put the point at [3.60, 4.10].
Nothing shipped composes a rotated aperture, so it is not a live defect - but
if a wrapper ever does, this arithmetic is the record of what correct means.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"
SVG = "{http://www.w3.org/2000/svg}"
FIXTURE = "generic--sfp-lc--v1--default.svg"


def _markers(root):
    return [el for el in root.iter(f"{SVG}g") if el.get("data-cp")]


def test_the_bores_mate_point_lands_on_the_declared_optical_axis():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}

    tx = [m for m in _markers(root) if m.get("data-cp") == "optical-tx"]
    assert len(tx) == 1, "sfp-lc declares exactly one optical-tx"
    declared = [float(v) for v in tx[0].get("data-cp-at").split()]
    assert declared == [3.6, 5.7]

    # the bore's own mate marker, inside the `tx` part group
    bore_mates = [m for m in _markers(root) if m.get("data-cp") == "mate"
                  and (parent.get(m) is not None
                       and (parent[m].get("id") or "").endswith("--tx"))]
    assert len(bore_mates) == 1, (
        "expected one mate marker inside the tx bore's group; got "
        f"{len(bore_mates)}")

    # resolve it: the marker is in the BORE's frame, the bore group carries the
    # rotate+translate transform, so the composed transform is what maps it.
    # The bore is 4.7 x 6.3 and the point is [2.35, 2.35]; rotate 180 about
    # [2.35, 3.15] -> [2.35, 3.95]; translate by [1.25, 1.75] -> [3.60, 5.70].
    at = [float(v) for v in bore_mates[0].get("data-cp-at").split()]
    assert at == [2.35, 2.35], "the marker must be in the bore's OWN frame"
    rotated = [2 * 2.35 - at[0], 2 * 3.15 - at[1]]
    resolved = [round(1.25 + rotated[0], 4), round(1.75 + rotated[1], 4)]
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
