"""A bay inside a seated module is resolved from the drawing, not the manifest.

Which nested bays exist depends on what is currently populated - a `dcp-2` has
two traffic slots, and whether it also has two PPM bays depends on whether slot
1 holds a `dcp-f-a22` or a `dcp-404` - so they cannot be in the device manifest
and never could be. `swap.js`'s `nestedBays` reads them off the compiled face,
using the carrier's `data-ref` and the `bays` that `components_index.py` now
publishes.

39 components across the library declare bays and 84 nested bays in total, and
before this none of them could be populated: `kit/shell.js` keyed a bay by exact
id against the DEVICE's list, so `slot-1/module/ppm-1` was in neither lookup and
the occupant picker was never drawn.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/nested-bays.mjs"
DIST = ROOT / "library" / "dist"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_bay_inside_a_seated_module_resolves_from_the_drawing():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["ids"] == ["slot-1/module/ppm-1", "slot-1/module/ppm-2"], (
        "a nested bay is named by its full path, so two carriers of the same "
        f"model do not share an answer: {out['ids']}")
    assert out["accepts"] == [2, 2], (
        "a bay that names nothing offers nothing - the picker would be empty")
    assert out["defaults"] == ["smartoptics/ppm-dummy@1"] * 2

    # a device bay's shape, so one code path serves both
    assert out["keys"] == ["accepts", "at", "default", "id", "size"], out["keys"]
    assert out["at"] == [147.3, 2.5]
    assert out["size"] == {"w": 55.4, "h": 19.5}, (
        "the contract writes `size: [w, h]` and a device bay carries "
        f"`{{w, h}}`; the index has to normalise it: {out['size']}")

    # RE-DERIVED AFTER THE CARRIER CHANGES, which is what makes viewer3d's two
    # passes correct. It overrides the device's bays first and the nested ones
    # second, and 73 device bays in the library accept more than one bay-bearing
    # carrier - the r740xd's four risers, every mx2008 FPC - whose nested bays
    # differ in geometry. A descriptor taken before the swap would seat the
    # module at the OLD carrier's `at`, or miss a bay the new one introduces.
    assert out["afterIds"] == ["slot-1/module/ppm-1"], (
        "the replaced carrier declares one bay where the old one declared two, "
        f"and the resolver still reports the old pair: {out['afterIds']}")
    assert out["afterAt"] == [10, 20], (
        f"resolved against the carrier that is no longer seated: {out['afterAt']}")
    assert out["afterAccepts"] == ["x/y@1"]


def test_components_json_publishes_what_a_nested_bay_accepts():
    """Without this the resolver above has nothing to resolve against.

    `components_index.py` emitted `parts`, `elements`, `body`, `files`, `skins`
    and the rest and never `bays`, so a consumer holding the index could see
    that a carrier had been drawn with openings and had no way to learn what
    goes in one.
    """
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("components.json not built")
    comps = json.loads(f.read_text())["components"]
    withbays = [c for c in comps if c.get("bays")]
    assert withbays, (
        "no component publishes a bay. 39 declare them on disk; if this is "
        "empty the index has stopped carrying them and every nested bay in the "
        "library is unpopulatable again."
    )
    a22 = next((c for c in comps if c["name"] == "dcp-f-a22"), None)
    if a22 is None:
        pytest.skip("dcp-f-a22 not built")
    ppm = a22["bays"]["ppm-1"]
    assert ppm["size"] == {"w": 55.4, "h": 19.5}, (
        f"published unnormalised: {ppm['size']}")
    assert "smartoptics/ppm-ad1-1510@1" in ppm["accepts"]
    assert ppm["default"] == "smartoptics/ppm-dummy@1"
