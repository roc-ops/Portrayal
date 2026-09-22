"""An optic seated on a card is a FRU of its own in 3D (#484).

kit/relief.js sent every fills/occupies instance deeper than two path
segments to the card's sub-bodies, which are built only from `body.boxes` -
and a generic optic declares none - so an optic chosen on
`front-6/module/xg0` had no body and could not be pulled on its own. The
decision is `bodyRole`; a device-level optic, a bay module and a module in a
module's bay keep the answer they always had.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/body-role.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_device_level_parts_are_unchanged(out):
    assert out["deviceOptic"] == {"fru": "port-4-occupant"}
    assert out["deviceChained"] == {"fru": "port-5-occupant-occupant"}
    assert out["bayModule"] == {"fru": "front-6"}
    assert out["legacyClass"] == {"fru": "psu-1"}


def test_an_optic_on_a_card_is_its_own_fru(out):
    assert out["cardOptic"] == {"fru": "front-6/module/xg0-occupant", "nested": True}
    assert out["cardChained"] == {"fru": "front-6/module/xg0-occupant-occupant",
                                  "nested": True}
    assert out["deepCardOptic"] == {"fru": "slot-1/module/ppm-1/module/p0-occupant",
                                    "nested": True}


def test_a_modules_own_parts_and_nested_modules_ride_with_the_carrier(out):
    assert out["cardPart"] == {"sub": "front-6"}
    assert out["nestedBayModule"] == {"sub": "slot-1"}


def test_no_path_no_role(out):
    assert out["empty"] is None and out["nul"] is None
