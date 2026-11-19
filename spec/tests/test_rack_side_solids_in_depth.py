"""A rack-side or zero-U part's solids lie inside the part.

rack.json carries, for a sheet part, the boxes a cable may not pass through
(rack_solids.py). Each box is placed in the part's own frame: z runs back from
the front face, so a part `d` deep has every solid between 0 and `d`. A solid
at a negative z stands in front of the part, and one past `d` behind it: a part
whose components are placed on its face without a well to stand in gets that,
and a rack drawn with it puts the part's solids a part-depth away from its
envelope.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
# rack.json boxes are rounded to three decimals
TOL = 0.01


def _rack_side_or_zero_u(entry):
    return entry.get("mount") == "rack-side" or entry.get("ru") == 0


@pytest.mark.heavy
def test_a_rack_side_or_zero_u_parts_solids_lie_within_its_depth():
    rack = DIST / "rack.json"
    assert rack.is_file(), "no library/dist/rack.json: run ./build.sh first (the suite reads the build)"
    devices = json.loads(rack.read_text())["devices"]
    parts = {n: e for n, e in devices.items() if _rack_side_or_zero_u(e)}
    assert parts, "no rack-side or zero-U part in rack.json"
    with_solids = {n: e for n, e in parts.items() if e.get("solids")}
    assert len(with_solids) > 10, "few rack-side parts carry solids: the check would be vacuous"
    outside = {}
    for name, entry in sorted(with_solids.items()):
        depth = entry["d"]
        for solid in entry["solids"]:
            box = solid["box"]
            if box["z"] < -TOL or box["z"] + box["d"] > depth + TOL:
                outside.setdefault(name, []).append(
                    f"{solid['part']} z {box['z']}..{round(box['z'] + box['d'], 3)}")
    assert not outside, "\n".join(
        f"{name} (depth {parts[name]['d']}): " + "; ".join(spans[:3]) + (f" and {len(spans) - 3} more" if len(spans) > 3 else "")
        for name, spans in outside.items())
