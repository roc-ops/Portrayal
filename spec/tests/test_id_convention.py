"""L62: an id names the function, not the connector.

Written after one device was modelled twice and the two models agreed on the
chassis to the millimetre and diverged on NAMES - `clk-10mhz-out` against
`sma-10mhz-out`. The tests that matter are the pair a rule written after the
fact usually skips: does it fire on the ACTUAL divergence, and does it stay
quiet on everything sitting right beside it that is already correct.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint as L

LIB = [str(ROOT / "library")]


def run(placements):
    with L.collecting() as _found:
        doc = {"views": {"front": {"components": {"placements": list(placements)}}}}
        L.lint_device_id_convention("t", doc, LIB)
    return [w for w in _found.warnings if "L62" in w]


def p(pid, ref, **kw):
    return dict(id=pid, ref=ref, at=[0, 0], **kw)


# --- 1. the id that repeats its own connector -------------------------------

def test_the_divergence_this_rule_exists_for():
    """One agent wrote this and the other wrote clk-10mhz-out. Nothing told
    either which to pick."""
    hits = run([p("sma-10mhz-out", "common/sma-jack@1")])
    assert len(hits) == 1, hits
    assert "'sma'" in hits[0]
    assert "common/sma-jack@1 already states" in hits[0]
    # and it hands back a name the corpus already voted for, rather than
    # leaving the next agent to invent one.
    #
    # WHICH name is deliberately not asserted. It is whatever the library most
    # commonly calls this, and the library is data - remodelling one device
    # legitimately changes the count. An earlier version pinned the exact string
    # and failed the day the device that supplied it was rebuilt, which is a
    # test measuring the corpus rather than the rule.
    import re as _re
    m = _re.search(r"use '([^']+)'", hits[0])
    assert m, hits[0]
    assert m.group(1) != "sma-10mhz-out", "it must suggest something else"


def test_the_other_agents_name_is_silent():
    """THE HALF THAT MATTERS MOST. A rule that nags at the right answer as well
    as the wrong one teaches nothing except to switch it off."""
    assert run([p("clk-10mhz-out", "common/sma-jack@1")]) == []
    assert run([p("clk-1pps-in", "std/smb@1")]) == []


def test_a_traffic_port_is_silent():
    assert run([p("port-1", "std/qsfp-dd@1")]) == []
    assert run([p("port-48", "std/sfp-ganged@1")]) == []


def test_a_singleton_function_name_is_silent():
    """`console` over an RJ45, and `reset` over a button. The connector words
    are right there in the refs and neither id borrows one."""
    assert run([p("console", "std/rj45-ganged@2", attrs={"media": "rj45-serial"})]) == []
    assert run([p("reset", "common/reset-button@1")]) == []
    assert run([p("tod", "std/rj45@2")]) == []


def test_a_function_word_that_looks_like_a_connector_is_silent():
    """`usb` IS the service a USB-A receptacle provides, and the corpus uses it
    bare as an id on device after device. The vocabulary lets the corpus veto a
    word for exactly this case, so `usb-1` beside `usb-2` is left alone."""
    assert run([p("usb", "std/usb-a@1"), p("usb-1", "std/usb-a@1"),
                p("usb-2", "std/usb-a@1")]) == []


def test_a_bare_standard_is_left_alone():
    """`micro-usb` with nothing after it has no function half to keep. Renaming
    it is a decision about what the port is FOR; this rule only removes a word
    that is stated twice."""
    assert run([p("usb-a", "std/usb-a@1")]) == []


def test_a_connector_word_the_ref_does_not_state_is_silent():
    """The duplication has to be real. `sma-...` over a component that is not an
    SMA is a different mistake and not this rule's."""
    assert run([p("sma-10mhz-out", "std/smb@1")]) == []


def test_a_port_named_for_its_media_gets_port_n_back():
    hits = run([p("sfp-plus-3", "std/sfp-ganged@1")])
    assert len(hits) == 1, hits
    assert "'port-3'" in hits[0]


def test_the_stated_role_is_offered_as_the_function():
    """A placement that already carries `role: console` has written the function
    down; the message hands it back rather than making one up."""
    hits = run([p("micro-usb", "std/micro-usb@1",
                  attrs={"media": "micro-usb-b", "role": "console"})])
    assert len(hits) == 1, hits
    assert "'console'" in hits[0] and "role this placement states" in hits[0]


def test_a_function_word_that_is_not_a_connector_stays_out_of_the_vocabulary():
    """`common/esd-jack` states `media: esd` and `std/c14-inlet` states
    `media: ac`. Neither is a connector - one says what the jack is for, the
    other what comes down the cord - and the class filter is what knows it."""
    assert run([p("esd-jack", "common/esd-jack@1")]) == []
    assert run([p("ac-inlet-panel", "casa/c40g-ac-inlet-panel@1")]) == []


# --- 1b. the three ways the suggestion itself was wrong ----------------------

def test_a_suggestion_the_device_already_uses_is_not_offered():
    """Sixteen findings proposed a name the device was already using - `sfp-0`
    -> `port-0` on a switch whose port-0 is a QSFP. Following one merges two
    placements into a single id, which the schema forbids, so a rule that
    prints it is telling an agent to break the file. The duplication is still
    reported; the REPLACEMENT is what it declines to invent."""
    hits = run([p("port-0", "std/qsfp-dd@1"), p("sfp-0", "std/sfp-ganged@1")])
    assert len(hits) == 1, hits
    assert "IS ALREADY THIS DEVICE'S port-0" in hits[0]
    assert "use 'port-0'" not in hits[0], "it must not propose the collision"


def test_a_leftover_is_not_offered_as_a_name():
    """`sfp-leds` leaves `leds` once the connector comes off, and nothing in the
    library votes on that tail. The rule used to hand back the bare remainder,
    proposing a lamp pair be renamed `leds` - which names no function and
    duplicates the group it sits in."""
    hits = run([p("sfp-leds", "common/sfp-led-pair@1")])
    assert len(hits) == 1, hits
    assert "no settled name" in hits[0]
    assert "use 'leds'" not in hits[0]


def test_a_qualifier_does_not_split_the_vote():
    """THE ONE THAT WOULD HAVE SPLIT THE CORPUS PERMANENTLY.

    The library calls a one-pulse-per-second jack `clk-1pps` eighteen times. It
    also had two `timing-1pps-in` on a single device added last week - and
    because the vote was taken on the EXACT tail, `1pps-in` was a question only
    that device had ever answered, so it won unopposed and the rule told every
    Juniper modeller to write `timing-1pps-in`. The newest file always winning
    its own spelling is an echo, not a vote.

    A directional `1pps-in` is a qualified `1pps`, so the lead is credited with
    both.
    """
    hits = run([p("smb-1pps-in", "std/smb@1")])
    assert len(hits) == 1, hits
    assert "'clk-1pps-in'" in hits[0], hits[0]
    assert "timing" not in hits[0], hits[0]


# --- 2. the port lamp spelled some other way --------------------------------

def test_the_three_minority_spellings_fire():
    for pid, want in (("led-p1", "led-port-1"),
                      ("leds-port-0", "led-port-0"),
                      ("leds-p12", "led-port-12"),
                      ("led-p3-a", "led-port-3-a"),
                      ("leds-p48-p49", "led-port-48-port-49")):
        hits = run([p(pid, "common/led-dot@1")])
        assert len(hits) == 1, (pid, hits)
        assert repr(want) in hits[0], (pid, hits[0])


def test_the_plurality_spelling_is_silent():
    assert run([p("led-port-1", "common/led-dot@1")]) == []
    assert run([p("led-port-1-2", "common/led-dot@1")]) == []


def test_a_lamp_that_is_not_a_port_lamp_is_silent():
    """led-fan, led-sys, led-psN. The rule is about ONE naming choice and a rule
    that spreads past it becomes a style opinion."""
    for pid in ("led-fan", "led-sys", "led-ps1", "led-id", "led-sync"):
        assert run([p(pid, "common/led-dot@1")]) == [], pid
