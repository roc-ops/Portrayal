"""The explorer offers an optic on a cage that sits on a seated card, drops it
when the card goes, and hands it to the 3D scene (#484).

Three rules, all in kit/swap.js so shell.js and viewer3d.js call one copy
and node can run them:

- `cageAt` - which cage a path names: a device cage or a card's cage (read off
  the drawing through `nestedCages`), and a click inside the optic in a cage,
  or on the cage's own parts, names that cage; an LED `data-for` a cage does not.
- `pruneCarrier` (R5) - replacing or emptying a card drops every entry keyed
  under its path from the explorer's state, so an optic cannot outlive the card
  it sat in, in the state, in `swap=` or in the 3D override map; re-seating the
  BUILT card seats it fresh, so the optics the build put in it read as emptied.
- `applyFaceOverrides` - the per-face pass viewer3d runs: bays first, then the
  cages of the face as it now stands, device and card alike.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/nested-cage-explorer.mjs"


def run(mode):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), mode], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_cage_at_names_device_and_card_cages():
    out = run("cage-at")
    assert out["device"] == "port-4"
    assert out["card"] == "front-6/module/xg0"
    assert out["accepts"] == ["generic/sfp-lc@1"], "the select offers the card cage's accepts"
    assert out["faceCages"] == ["port-4", "front-6/module/xg0", "front-6/module/xg1"]
    assert out["faceCagesNoFace"] == ["port-4"]


def test_a_click_inside_an_optic_names_its_cage():
    out = run("cage-at")
    assert out["deviceOptic"] == "port-4"
    assert out["deviceOpticPart"] == "port-4"
    assert out["cardOptic"] == "front-6/module/xg1"
    assert out["cardOpticPart"] == "front-6/module/xg1"


def test_a_click_on_a_cages_own_part_names_the_cage():
    out = run("cage-at")
    assert out["deviceOpening"] == "port-4"
    assert out["cardOpening"] == "front-6/module/xg0"


def test_what_is_no_cage_names_none():
    out = run("cage-at")
    for k in ("deviceLed", "cardLed", "cardPlate", "cardItself", "bay", "nothing",
              "nul", "noFace"):
        assert out[k] is None, k


def test_replacing_or_emptying_a_card_drops_everything_under_it():
    out = run("prune")
    d = out["dropped"]
    assert d["cfgBays"] == {"front-6": "casa/card@1", "front-7": "casa/card@1"}
    assert d["cfgOccupants"] == {"port-4": "generic/sfp-lc@1",
                                 "front-7/module/xg0": "generic/sfp-lc@1",
                                 "front-60/module/xg0": "generic/sfp-lc@1"}
    assert d["touched"] == ["front-6", "front-7/module/xg0", "port-4"]
    assert d["refused"] == {}
    assert d["failed"] == {"port-4": "generic/sfp-lc@1"}
    assert out["inputKept"], "pruneCarrier changed the state it was handed"
    assert out["garbage"] == {"cfgBays": {}, "cfgOccupants": {}, "touched": [],
                              "refused": {}, "failed": {}}


def test_the_built_card_seated_again_holds_none_of_the_builds_optics():
    r = run("prune")["rebuilt"]
    assert r["cfgOccupants"] == {"port-4": "generic/sfp-lc@1",
                                 "front-7/module/xg0": "generic/sfp-lc@1",
                                 "front-60/module/xg0": "generic/sfp-lc@1",
                                 "front-6/module/xg0": None, "front-6/module/xg1": None}
    assert r["touched"] == ["front-6", "front-6/module/xg0", "front-6/module/xg1",
                            "front-7/module/xg0", "port-4"]


def test_the_pruned_state_is_what_swap_and_3d_are_given():
    out = run("prune")
    # the card taken out: the swap is the card, and nothing under it
    assert out["emptiedDelta"] == {"front-6": None}
    assert out["emptiedSwap"] == "front-6~"
    # the built card put back: it is fresh, so the build's optics are emptied -
    # which is what 2D shows, and what 3D (handed no card swap) must be told
    assert out["backDelta"] == {"front-6/module/xg0": None, "front-6/module/xg1": None}
    assert out["backSwap"] == "front-6%2Fmodule%2Fxg0~,front-6%2Fmodule%2Fxg1~"


def test_the_3d_pass_seats_a_card_cage():
    out = run("face")
    c = out["cageOnly"]
    assert c["xg0"] == ["front-6/module"], "the optic is seated inside the card"
    assert c["xg1"] == 0, "the build's optic, emptied"
    assert c["port4"] == 1
    assert c["result"]["refused"] == [] and c["result"]["failed"] == []
    assert c["result"]["applied"] == 3
    assert c["result"]["dropped"] == []


def test_the_3d_pass_reads_cages_off_the_card_it_just_seated():
    s = run("face")["carrierSwapped"]
    # with its version, as render.py writes a seated module's ref (B3 Task 10c)
    assert s["modules"] == 1 and s["freshCard"] == "casa/card@1:1.2.0"
    assert s["xg0"] == [True], "the optic is in the NEW card"
    assert s["xg1"] == 0, "the build's optic went with the card it sat in"
    assert s["applied"] == 2


def test_the_3d_pass_seats_nothing_on_an_emptied_card():
    e = run("face")["carrierEmptied"]
    assert e == {"applied": 1, "xg0": 0}


def test_a_card_replaced_while_its_optic_loads_takes_the_swap_with_it():
    out = run("race")
    assert out["replaced"]
    assert out["liveAfter"] is False, \
        "the optic swap's claim outlived its card: the shell would write its ref under the new card"
    assert out["otherLive"] is True, "front-60 is not under front-6"
    assert out["oldOptics"] == 0, "the stale optic was appended to the card that left"
    assert out["staleOnFace"] == 0
    assert out["res"] == {"applied": 0, "refused": [], "failed": []}
    assert out["again"]["applied"] == 1 and out["landed"] == [True], \
        "a new swap on the new card must still land"
