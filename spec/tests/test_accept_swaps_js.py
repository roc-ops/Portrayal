"""A reloaded swap is taken into the explorer's state only if the 2D face
would seat it.

What the explorer's state holds is written back into `swap=` and sent to the
3D scene, and viewer3d's applyOverrides does not check accepts. An entry that
names no bay or cage, or a ref the bay or cage does not accept, taken into state
anyway is seated in 3D while 2D refuses it - the divergence swap.js exists to
prevent - and it lives in the URL forever. Nested keys were the hole: they were
taken on the strength of sitting under some device bay's `/module/`. They are
now resolved through the carrier's component, after the carrier's own entry is
decided.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/accept-swaps.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_device_level_entries(out):
    assert out["device"] == {"accepted": {"slot-1": "so/a22@1", "port-4": "generic/qsfp-lc@1",
                                          "port-9": None, "slot-2": None}, "ignored": []}
    r = out["deviceRefused"]
    assert r["accepted"] == {}
    assert sorted(r["ignored"]) == ["nope", "port-4", "port-9", "slot-1"]


def test_a_nested_key_resolves_through_its_carrier(out):
    assert out["nestedUnderSwap"]["accepted"] == {"slot-1": "so/a22@1",
                                                  "slot-1/module/ppm-1": "so/ppm-y@1"}
    assert out["nestedUnderBuilt"] == {"accepted": {"slot-2/module/ppm-2": "so/ppm-x@1"},
                                       "ignored": []}


def test_a_nested_key_naming_nothing_is_ignored(out):
    assert out["nestedNoCarrier"] == {"accepted": {}, "ignored": ["slot-1/module/ppm-1"]}
    assert out["nestedCarrierEmptied"] == {"accepted": {"slot-2": None},
                                           "ignored": ["slot-2/module/ppm-1"]}
    r = out["nestedRefused"]
    assert r["accepted"] == {}
    assert sorted(r["ignored"]) == ["slot-2/module/bogus", "slot-2/module/ppm-1"]


def test_emptying_an_existing_nested_bay_is_allowed(out):
    assert out["nestedEmptied"] == {"accepted": {"slot-2/module/ppm-1": None}, "ignored": []}


def test_a_refused_carrier_leaves_the_built_one_in_charge(out):
    assert out["carrierRefused"] == {"accepted": {"slot-2/module/ppm-1": "so/ppm-y@1"},
                                     "ignored": ["slot-2"]}


def test_three_levels(out):
    assert out["deep"]["accepted"] == {"slot-2/module/ppm-2": "so/deep@1",
                                       "slot-2/module/ppm-2/module/sub-1": "so/leaf@1"}
    # ppm-2 declares no default, so nothing is seated there and sub-1 does not exist
    assert out["deepNoMiddle"] == {"accepted": {},
                                   "ignored": ["slot-2/module/ppm-2/module/sub-1"]}


def test_garbage_never_throws(out):
    assert out["garbage"][0] == {"accepted": {}, "ignored": []}
    assert out["garbage"][1] == {"accepted": {}, "ignored": []}
    assert out["garbage"][2] == {"accepted": {}, "ignored": ["slot-1"]}
    for r in out["garbage"][3:]:
        assert r["accepted"] == {} and len(r["ignored"]) == 1


def test_a_nested_default_is_seated_but_built_empty_is_not(out):
    assert out["nestedDefault"]["accepted"] == {}            # ppm-x declares no bays yet
    assert out["viaDefault"]["accepted"] == {"slot-2/module/ppm-1/module/x": "so/leaf@1"}
    assert out["viaBuiltEmpty"] == {"accepted": {}, "ignored": ["slot-2/module/ppm-1/module/x"]}
