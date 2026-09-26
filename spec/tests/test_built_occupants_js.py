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


def test_a_chained_key_at_the_builds_name_is_a_slot_and_nothing_else_is(out):
    """Since #611 the chained tier IS a slot: the boot on the plug in `port-5`
    is keyed `port-5-occupant`, which the kit publishes on the seated plug
    (swap.js chainedSlots), so the boot the build put there is that slot's
    built answer. A tier chained on a CUSTOM id (`uplink-optic`) still is not -
    no slot is drawn at a name the kit cannot derive - and neither is a key
    naming no cage."""
    assert out["built"] == {"port-4": "generic/sfp-lc@1", "port-5": "generic/rj45-plug@1",
                            "port-5-occupant": "generic/boot@1"}
    assert out["collision"] == {"port-4": "a", "port-4-occupant": "b"}, (
        "a tier at the default name is kept whether or not a cage shares its id")
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


def test_a_configuration_seated_card_optic_is_keyed_by_the_drawing(out):
    # front-6/xg0 in the manifest is front-6/module/xg0 on the face, and so is
    # the tier chained on it at the default name (#611); the one chained on a
    # custom id is not a slot
    assert out["cardBuilt"] == {"front-6/module/xg0": "generic/sfp-lc@1",
                                "front-6/module/xg0-occupant": "generic/boot@1",
                                "front-6/module/cg0": "generic/qsfp-lc@1",
                                "port-4": "generic/sfp-lc@1"}


def test_an_untouched_page_with_a_card_optic_writes_no_swap(out):
    assert out["cardUntouched"] == {}
    assert "swap=" not in out["cardUntouchedSearch"], out["cardUntouchedSearch"]


def test_a_card_optic_is_a_swap_only_when_it_differs_from_the_build(out):
    assert out["cardAway"] == {"front-6/module/xg0": "generic/sfp-lc-simplex@2"}
    # the configured optic, chosen again, is not a swap - but it is a FRESH
    # seat, and the boot the build chained on the old one went with it
    # (swap.js removeSeat, #611), so the state records that tier emptied
    assert out["cardBack"] == {"front-6/module/xg0-occupant": None}
    assert out["cardEmptied"] == {"front-6/module/xg0": None}
    assert out["cardFilled"] == {"front-6/module/xg1": "generic/sfp-lc@1"}
    # a boot left in the state on an optic it was not built on is asked for;
    # the shell's dropOnSlot prunes it, which is why cardAway is one key
    assert out["cardAwayUnpruned"] == {"front-6/module/xg0": "generic/sfp-lc-simplex@2",
                                       "front-6/module/xg0-occupant": "generic/boot@1"}


def test_an_optic_on_a_swapped_card_is_always_a_swap(out):
    assert out["cardOnSwappedCarrier"] == {"front-6": "casa/smm-b@1",
                                           "front-6/module/xg0": "generic/sfp-lc@1"}
