"""The cable point's arithmetic, checked against hand sums under bare node,
plus the DOM wrapper against a hand-built fake tree (see cable-points.mjs)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/cable-points.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_resolver_sums_the_ancestor_chain():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    # no `out` key at all - a cable point lands on the reference plane via
    # the lift sum alone
    assert out["bare"] == {"name": "cable", "at": [6.75, 4.25],
                           "dir": "rear", "lift": 0, "z": 0}
    assert out["lifted"]["z"] == 10.0
    # 10.0 of lift on the way up; stray `out` keys on the ancestors are not
    # summed and not read from the outermost entry
    assert out["stacked"]["z"] == 10.0
    assert "out" not in out["stacked"]
    assert out["noDir"]["dir"] is None
    assert out["junk"]["z"] == 0, "a junk lift must be 0, never NaN"

    # A JUNK LIFT IS 0 AND A JUNK POINT IS NULL, and the two must not be
    # levelled. A lift has a safe default - undisplaced - while [0, 0] is a
    # position on the part that a consumer cannot tell from a real answer.
    for case in ("noAt", "emptyAt", "junkAt", "shortAt"):
        assert out[case]["at"] is None, (
            f"{case} resolved to {out[case]['at']}; an unreadable point must "
            "be null, never the part's origin")
    assert out["noAt"]["z"] == 2, "an unreadable point still resolves its z"
    assert out["stringAt"]["at"] == [1.5, 2.5], "dataset values arrive as strings"

    # A POINT ON A FEATURE lands on that feature's far face, which is absolute:
    # the boot of the seated LC chain is 22.5 (lift) to 37.6 (data-z-out), and
    # its cable leaves at 37.6 - the lift is reported, never added to it.
    assert out["onRear"]["z"] == 37.6
    assert out["onRear"]["lift"] == 22.5
    assert out["junkRear"]["z"] == 22.5, "an unreadable rear keeps the part's face"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cable_points_resolves_the_fake_drawing():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    points = {pt["path"]: pt for pt in out["points"]}

    # every connector survives exactly once, at the path that won it
    assert set(points) == {
        "cage-a", "cage-b", "cage-c/plug/boot",
        "sfp-lc/tx", "sfp-lc/rx", "sfp-1", "sfp-10",
        "cage-g/plug/boot", "wrap/a", "wrap/b", "cage-j",
        "cage-plug-boot", "cage-l", "cycle-self",
        "/rear/x", "plug-o",
        "p-plug-boot", "q-plug", "r-part",
    }
    # the seated chain's boot wins and its cable leaves the boot's rear; a
    # bare plug's leaves the plug body's rear; a point on a node with no
    # data-z-out keeps its lift and is named on stderr
    assert (points["p-plug-boot"]["z"], points["p-plug-boot"]["lift"]) == (37.6, 22.5)
    assert (points["q-plug"]["z"], points["q-plug"]["lift"]) == (22.5, 10.0)
    assert points["r-part"]["z"] == 4.0
    assert any("r-part" in w and "data-z-out" in w for w in out["warnings"]), out["warnings"]
    assert "out" not in points["cage-a"]

    # THE OWNER ELEMENT COMES BACK. `at` is the marker's OWN-FRAME point, so a
    # consumer needs the element to finish the transform itself; a point
    # without one cannot be resolved into the chassis frame by anybody.
    assert all(pt["elIsMarker"] for pt in out["points"]), \
        "every point must carry the marker element it came from"

    # a marker whose point does not parse is still REPORTED - dropping the
    # connector would be its own silent failure - but with at: None
    assert points["cage-j"]["at"] is None

    # a single marker resolves to its own position, direction and lift-only z
    assert points["cage-a"]["at"] == [1, 2]
    assert points["cage-a"]["dir"] == "front"
    assert points["cage-a"]["z"] == 2.5

    # no data-cp-dir comes back null, not undefined/missing
    assert points["cage-b"]["dir"] is None
    assert points["cage-b"]["z"] == 0

    # two markers on one chain (plug + boot): the outermost - the boot's,
    # 5mm further out than the plug's - is the one that survives
    assert "cage-c/plug" not in points, \
        "the plug's marker must lose to the boot's when a boot is seated"
    assert points["cage-c/plug/boot"]["z"] == 5
    assert points["cage-c/plug/boot"]["at"] == [3, 3.2]
    assert points["cage-c/plug/boot"]["dir"] == "rear"

    # two markers under a SHARED LEADING SEGMENT that are NOT on one chain
    # (siblings, "sfp-lc/tx" and "sfp-lc/rx") must both survive - grouping by
    # leading segment alone would wrongly collapse an LC duplex to one point
    assert points["sfp-lc/tx"]["z"] == 3
    assert points["sfp-lc/rx"]["z"] == 4

    # "sfp-1" is not a chain-prefix of "sfp-10" - the trailing "/" boundary
    # must keep them apart
    assert set(points) >= {"sfp-1", "sfp-10"}

    # an exact z tie on one chain (plug vs boot): the plug's path is a
    # strict prefix of the boot's, so the plug is shadowed regardless of z -
    # no tie-break needed, the boot wins structurally
    assert "cage-g/plug" not in points, \
        "the plug must be shadowed by the boot even on an exact z tie"
    assert points["cage-g/plug/boot"]["z"] == 0

    # THE BRANCHING CASE: a wrapper with its own marker plus two marked
    # children that are siblings of each other (neither a prefix of the
    # other). The wrapper is shadowed by both children and must not survive;
    # the children must not shadow each other. A union-find clustering over
    # "shares a chain member" fuses all three through the wrapper and
    # wrongly keeps only one - this is the case that tells shadowing and
    # clustering apart.
    assert "wrap" not in points, "a marker shadowed by two children must still drop"
    assert points["wrap/a"]["at"] == [4, 5]
    assert points["wrap/b"]["at"] == [4, 6]

    # A CHAIN OF SEATS: three TOP-LEVEL, UNRELATED data-path values ("cage",
    # "cage-plug", "cage-plug-boot" - no one a prefix of another), tied
    # together only by `data-for` ("cage-plug" names "cage", "cage-plug-boot"
    # names "cage-plug"), exactly the shape a `mate-to` occupant produces.
    # Path-prefix alone cannot relate these at all - this is the case that
    # returns three points under that rule and must return one here.
    assert "cage" not in points, "the cage's own marker must lose to its seats"
    assert "cage-plug" not in points, "the plug's marker must lose to the boot"
    assert points["cage-plug-boot"]["at"] == [2, 2.2]

    # A `data-for` naming an owner that does not exist in this drawing (a
    # typo, or an unresolved cross-view target) must not throw and must not
    # spin forever - the chain walk just stops, and the marker still reports.
    assert points["cage-l"]["at"] == [9, 1]

    # A 2-CYCLE IN data-for (cycle-a names cycle-b, cycle-b names cycle-a).
    # The subprocess call above completing at all IS the cycle test - a
    # regression that broke the Set guard would hang node rather than fail
    # an assertion. Each element sees the other in the other's chain tail,
    # so each shadows the other; the sensible result is that BOTH drop
    # rather than one winning by array order on symmetric, contradictory data.
    assert "cycle-a" not in points, "a data-for 2-cycle must not let either side win"
    assert "cycle-b" not in points, "a data-for 2-cycle must not let either side win"

    # A SELF-REFERENCE (cycle-self names itself). The walk stops after one
    # step, so nothing shadows it and the marker survives. It is still a
    # 1-cycle, so it warns as well - see
    # test_a_data_for_cycle_is_said_out_loud; surviving and being
    # unremarkable are not the same thing.
    assert points["cycle-self"]["at"] == [6, 6.2]

    # A MULTI-TOKEN `data-for` WITH A CROSS-VIEW TOKEN IN FRONT. "plug-o" says
    # `data-for="/rear/x cage-o"`. The leading-slash token names another view
    # and must be SKIPPED, not looked up; the walk must go on to "cage-o" and
    # find the real host there. The fixture plants a marked owner under the
    # literal path "/rear/x" so the skip is observable: without the guard the
    # first token would win, "plug-o" would chain to the cross-view element
    # instead, and both assertions below would fail.
    assert "cage-o" not in points, (
        "plug-o's second data-for token names cage-o as its host, so the "
        "host's own marker must lose to the seat's - if it survived, the "
        "multi-token walk stopped at the first token")
    assert points["plug-o"]["at"] == [1, 1.5]
    assert points["/rear/x"]["at"] == [0, 7], (
        "the cross-view token must be skipped, not resolved - resolving it "
        "would make /rear/x plug-o's host and shadow it")

    # a drawing with no cable markers at all returns [], not a throw
    assert out["empty"] == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_data_for_cycle_is_said_out_loud():
    """A cycle drops BOTH connectors. An absence is not a diagnosis.

    `seen` has always stopped the walk, so nothing hung - but a 2-cycle makes
    each side shadow the other and both vanish from the returned list with
    nothing said, while an unreadable `data-cp-at` a few lines away has warned
    since it was written. Same class of malformed input, same treatment.
    """
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    warned = out["warnings"]

    cycle = [w for w in warned if "data-for cycle" in w]
    assert cycle, (
        f"the 2-cycle (cycle-a <-> cycle-b) dropped both connectors without a "
        f"word; warnings were {warned}")
    assert any("cycle-a" in w for w in cycle) and any("cycle-b" in w for w in cycle), (
        f"the warning must name the elements on the cycle; got {cycle}")

    # the pre-existing warning is still there, and the two are told apart
    assert any("unreadable data-cp-at" in w for w in warned), (
        f"cage-j's unparseable point stopped warning; got {warned}")
