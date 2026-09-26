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


def test_the_rj45_chain_boot_is_its_own_fru_three_deep(out):
    """generic/sfp-rj45@1 -> generic/rj45-plug@1 -> common/rj45-boot@1, the
    copper SFP chain (docs/pluggables-heads-design.md section 6 item 3):
    the same `occupant-occupant` reading cardChained already holds, one link
    further - the boot must still be picked out as its own removable part,
    not absorbed into the plug it wraps."""
    assert out["cardRj45Boot"] == {"fru": "front-6/module/xg0-occupant-occupant-occupant",
                                   "nested": True}


def test_an_occupant_two_segments_down_is_its_own_fru(out):
    """B3 Task 10c: `xc01/1-occupant` was keyed `xc01` - both bore caps of
    an adapter, and the adapter's own art, came out as one part."""
    assert out["boreCap"] == {"fru": "xc01/1-occupant", "nested": True}
    assert out["loneBackCap"] == {"fru": "fhd-2mtp12-lc-rear/mtp1-occupant", "nested": True}


def test_on_a_back_an_occupant_rides_with_the_module(out):
    assert out["backCap"] is None
    assert out["backBayModule"] == {"fru": "front-6"}


def test_a_modules_own_parts_and_nested_modules_ride_with_the_carrier(out):
    assert out["cardPart"] == {"sub": "front-6"}
    assert out["nestedBayModule"] == {"sub": "slot-1"}


def test_no_path_no_role(out):
    assert out["empty"] is None and out["nul"] is None


def test_a_seated_optic_without_a_body_block_gets_one_box_its_own_depth(out):
    b = out["body"]
    assert b["sfp"] == {"w": 8.55, "h": 13.55, "depth": 47.5}
    assert b["qsfp"] == {"w": 18.35, "h": 8.5, "depth": 52.4}
    assert b["qsfpdd"] == {"w": 18.35, "h": 8.5, "depth": 58.26}


def test_nothing_that_is_not_a_body_less_optic_gets_one(out):
    b = out["body"]
    for k in ("declared", "module", "legacy", "noDepth", "zeroSize", "nothing"):
        assert b[k] is None, k


def test_a_marker_rides_with_the_deepest_fru_on_its_path(out):
    f = out["fruFor"]
    assert f["cardOptic"] == f["cardOpticPart"] == "front-6/module/xg0-occupant"
    assert f["cardCage"] == f["card"] == f["bay"] == "front-6"
    assert f["prefixNotSegment"] is None, "front-60 is not under front-6"
    assert f["deviceOptic"] == "port-4-occupant"
    assert f["module"] == "psu-1"
    assert f["none"] is None and f["empty"] is None
