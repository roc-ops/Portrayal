"""The kit's half of a turned occupant (#829), run under node.

The share link carries a turn in a parameter of its own, `turn=<key>~<deg>`,
never as a third `~` piece in `swap=`: decodeSwaps drops an entry with two
`~`, so an old kit reading a new link (or a new link pasted into an old page)
would have lost the lug with its turn. The decoder never throws; the gate
(acceptTurns) takes a turn only for a slot that exists and publishes `turns`
holding that angle; an untouched page writes no `turn=`; a seat takes the
reader's turn, else the build's published default; the transform is the
build's (solve_seat's summed rotate) with the mate on the stud at every turn;
a turn names its view for the 3D pass; and a held face is re-seated by a turn
even though it already holds the same ref.

The same seat against REAL builds - default, explicit and turn-only - is held
by test_ground_stud_lugs.py's kit section.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/occupant-turn.mjs"
LUG = "generic/ring-lug@1"


@pytest.fixture(scope="module")
def out():
    assert shutil.which("node"), "node is needed to run the kit"
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_turn_map_round_trips_through_its_own_parameter(out):
    assert out["roundTrip"] == {"a~b,c": 270, "ground-stud-1": 180,
                                "ground-studs-rear/stud-tr": 90, "zero": 0}
    assert out["encodedTwice"]
    # sorted, escaped as swap= is, `~` and `,` inside a key included
    assert out["encoded"] == ("a%7Eb%2Cc~270,ground-stud-1~180,"
                              "ground-studs-rear%2Fstud-tr~90,zero~0")
    assert out["encodedNothing"] == ["", "", "", ""]
    assert out["search"] == "?turn=ground-stud-1~180&device=mx150&swap=a~b"


def test_a_bad_turn_string_never_throws_and_drops_only_itself(out):
    assert "threw" not in out["junk"]
    # every malformed entry is dropped; `constructor` is an ordinary key, and
    # the one well-formed pair among empties survives
    kept = [j for j in out["junk"] if j]
    assert kept == [{"constructor": 90}, {"a": 90, "b": 180}]


def test_a_turn_is_never_a_third_piece_of_a_swap(out):
    """Why `turn=` is its own parameter: the swap decoder drops an entry with
    two `~`, so a turn carried there would cost the lug its seat."""
    assert out["swapUntouched"] == {"ground-stud-1": LUG}
    assert out["turnInSwap"] == {}


def test_the_gate_takes_a_turn_only_where_the_slot_allows_it(out):
    acc = out["accept"]
    assert acc["accepted"] == {"ground-stud-1": 90, "ground-studs-rear/stud-tr": 270}
    assert sorted(acc["ignored"]) == sorted([
        "pole",                         # a terminal screw: no `turns` published
        "port-1",                       # a cage
        "nowhere", "ground-stud-2",     # no such slot
        "ground-studs-rear/stud-xx",    # no such part on the terminal
        "ground-stud-1-occupant",       # a lug presents nothing to turn
    ])
    assert out["acceptAngle"] == {"accepted": {}, "ignored": ["ground-stud-1"]}


def test_an_untouched_page_writes_no_turn(out):
    assert out["builtCtx"] == {"ground-stud-1": 90, "ground-studs-rear/stud-bl": 270}
    assert out["untouched"] == ""
    assert out["touched"] == {"ground-stud-1": 180, "ground-stud-0": 0}
    assert out["noCfg"] == [{}, {}, {}]


def test_a_seat_takes_the_readers_turn_else_the_published_default(out):
    assert out["seatTurn"] == {"chosen": 270, "def": 180, "disallowed": 180, "none": 0,
                               "pole": 0, "nested": 90}


def test_the_transform_is_the_builds_and_the_mate_stays_on_the_stud(out):
    t = out["transform"]
    # 0 is the seat's own answer: no rotate is written, exactly as before #829
    assert t["t0"] == t["t0explicit"] == "translate(31.25,3.75)"
    assert t["t90"] == "translate(20.3,-7.2) rotate(90 2.75 13.7)"
    assert t["t180"] == "translate(31.25,-18.15) rotate(180 2.75 13.7)"
    # a host turned 90 and a lug turned 270 on it is drawn upright, no rotate
    assert t["host90t270"] == t["t0"]
    assert t["host90t0"] == t["t90"]
    assert t["rot"] == [None, 90, 0, 0, 270]
    for pair in out["mates"]:
        for x, y in pair:
            assert (x, y) == pytest.approx((34, 6.5), abs=1e-9)


def test_a_turning_seat_records_its_turn_and_a_fixed_one_does_not(out):
    assert out["attrs"] == {"stud": "90", "studNone": "0", "pole": None}


def test_a_turn_names_its_view_for_the_3d_pass(out):
    assert out["views"] == {"turnOnly": ["rear"], "swapOnly": ["front"],
                            "both": ["front", "rear"], "none": []}


def test_a_turn_re_seats_a_held_face_that_holds_the_same_ref(out):
    """The face queue skips an entry a face already holds; the shell stamps a
    slot's turn on what it holds, so a turn is a change and a repeat is not."""
    assert out["queue"] == {"again": 0, "afterTurn": 1, "sameTurn": 0, "seen": 2}
