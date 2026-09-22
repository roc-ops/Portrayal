"""A nested bay is compared against the build only while its carrier is the
build's (#484's cage rule, applied to bays).

Two 2D/3D disagreements, both in what kit/swap.js hands `swap=` and the 3D
override map:

- re-seating the BUILT carrier seats it fresh, so its nested bays hold the
  component's defaults - but the override list came out empty and 3D kept the
  module the configuration had put there (`pruneCarrier` + `freshBaysUnder`);
- under a SWAPPED carrier, choosing the module the configuration had put in the
  old carrier's nested bay was read as "no swap", so `swap=` recorded only the
  carrier and 3D showed the new carrier's default (`swapOverrides`).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/nested-bay-carrier.mjs"

PPM = "smartoptics/ppm-ad1-1510@1"
DUMMY = "smartoptics/ppm-dummy@1"
X404 = "smartoptics/dcp-404@1"
NESTED = "slot-1/module/ppm-1"


def run(mode):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), mode], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_an_untouched_page_writes_no_swap():
    assert run("reseat")["untouched"] == {}


def test_swapping_the_carrier_away_drops_the_nested_bay():
    assert run("reseat")["away"] == {"slot-1": X404}


def test_reseating_the_built_carrier_empties_the_builds_nested_module():
    out = run("reseat")
    assert out["back"] == {NESTED: DUMMY}, \
        "3D would keep the configuration's PPM while 2D shows the fresh default"
    assert out["backState"] == DUMMY, "the inspector should read the face's default"
    assert out["backTouched"]


def test_fresh_bays_under_covers_only_the_configurations_nested_bays():
    out = run("reseat")
    assert out["fresh"] == {NESTED: DUMMY}
    for k in ("freshElsewhere", "freshUnknown", "freshBadRef", "freshNoCfg"):
        assert out[k] == {}, k


def test_under_a_swapped_carrier_the_old_carriers_module_is_a_swap():
    out = run("swapped")
    assert out["chosen"] == {"slot-1": X404, NESTED: PPM}
    assert out["chosenNoIndex"] == {"slot-1": X404, NESTED: PPM}


def test_under_a_swapped_carrier_the_answer_is_its_fresh_default():
    out = run("swapped")
    assert out["fresh"] == {"slot-1": X404}
    assert out["emptied"] == {"slot-1": X404, NESTED: None}


def test_an_unnamed_nested_bay_is_built_at_its_default():
    out = run("swapped")
    assert out["unnamedEmptied"] == {"slot-1/module/ppm-2": None}
    assert out["unnamedDefault"] == {}


def test_a_nested_key_before_its_carrier_is_still_judged_under_it():
    assert run("order")["delta"] == {"slot-1": X404, NESTED: PPM}
