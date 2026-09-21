"""The kit reads `configs[].occupants` ONE way, whatever shape it is written in.

spec/schemas/device.schema.json lets an `occupants:` value be a ref string or
a mapping `{ref, id, attrs, skin}`, and render.py's expansion lets a key name
an OCCUPANT - `{port-4: plug, port-4-occupant: boot}` seats a boot on the plug.
The explorer read the map raw: a mapping value reached the inspector as an
object (a seated optic shown as empty; swapping back to it a permanent swap),
and a chained key reached the swap test as a cage the build left empty - so an
untouched page wrote `swap=port-4-occupant~...` on load. No shipped device
uses either shape (test_cage_accepts pins that), so no gate saw it.

`builtOccupants` (kit/swap.js) is the one reading - shell.js builds its state
from it and index.html's swap test (`swapOverrides`, beside it) compares with
it. Both are pure and run here under node.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/built-occupants.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_mapping_value_is_read_as_its_ref(out):
    assert out["built"]["port-4"] == "generic/sfp-lc@1"


def test_a_chained_key_is_not_a_cage(out):
    assert out["built"] == {"port-4": "generic/sfp-lc@1", "port-5": "generic/rj45-plug@1"}, (
        "a chained tier (port-5-occupant, or a custom id like uplink-optic) or a key "
        "naming no cage must not reach the kit's cage state")
    assert out["collision"] == {"port-4": "a"}, (
        "a key another entry seats as its occupant is a tier even if a cage shares its id")
    assert out["noOccupants"] == [{}, {}, {}]


def test_an_untouched_page_writes_no_swap(out):
    assert out["untouched"] == {}
    assert out["untouchedSwap"] == ""
    assert "swap=" not in out["untouchedSearch"], out["untouchedSearch"]


def test_swapping_back_to_a_mapping_form_optic_is_no_swap(out):
    assert out["away"] == {"port-4": "generic/sfp-lc-simplex@2"}
    assert out["back"] == {}, "the configured optic, chosen again, is not a swap"
    assert out["emptied"] == {"port-4": None}
    assert out["filled"] == {"port-6": "generic/sfp-lc@1"}


def test_a_bays_built_answer_is_its_configuration_entry_else_its_default(out):
    assert out["bays"] == [{}, {"slot-0": "x/other@1"}, {"slot-1": None}]


def test_a_configuration_seated_nested_bay_is_what_the_build_put_there(out):
    # the manifest keys it slot-1/ppm-1, the drawing slot-1/module/ppm-1; read
    # raw, the swap test missed the entry, fell back to the bay's default and
    # wrote a swap= (and a 3D override) on an untouched ila-node page
    assert out["nestedBuilt"] == {"slot-1/module/ppm-1": "x/ppm-1510@1"}
    assert out["nestedUntouched"] == {}
    assert out["nestedUntouchedSwap"] == ""
    assert out["nestedAsBuilt"] == {}, "the module the configuration seats is no swap"
    assert out["nestedSwapped"] == {"slot-1/module/ppm-1": "x/cover@1"}
    assert out["noBays"] == [{}, {}, {}]
