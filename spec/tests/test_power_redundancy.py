"""L66: a power group with more than one bay says whether the bays add up.

`power-output-w` on a supply is a fact about ONE module. Two of them in a
chassis is then ambiguous in exactly the way that matters: 2 x 1600 W is either
a 3200 W box or a 1600 W box that survives losing a supply, and no module can
tell you which - only the chassis knows. A reader who sums the bays is wrong
half the time, and it is the half where the box draws twice what was
provisioned for it.

So the module states what it passes and the GROUP states whether they add.

The survey that seeded this convention had to be run twice. The first pass
matched any `N+M` in the device file and picked up fan redundancy - "5+1" on a
two-bay chassis - which is why the rule below keys on the group being a POWER
group and not merely a service one.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))
import lint  # noqa: E402

LIB = ROOT / "library"


def run(doc):
    out = []
    real = lint.warn
    lint.warn = lambda p, r, m: out.append((r, m))
    try:
        lint.lint_device_power_redundancy("t.yaml", doc)
    finally:
        lint.warn = real
    return out


def dev(bays, group=None, name="psus"):
    group = {"term": "PSU", "role": "service", **(group or {})}
    return {
        "kind": "device",
        "groups": {name: group},
        "views": {"front": {"components": {
            "bays": [{"id": f"p{i}", "group": name} for i in range(bays)]}}},
    }


# ---- the rule ---------------------------------------------------------------

def test_two_power_bays_with_no_statement_are_flagged():
    hits = run(dev(2))
    assert [r for r, _ in hits] == ["L66"]
    assert "does not say whether they add up" in hits[0][1]


def test_a_stated_group_is_silent():
    assert not run(dev(2, {"attrs": {"redundancy": "1+1"}}))


def test_one_bay_needs_no_statement():
    """There is nothing to add and nothing to stand in for."""
    assert not run(dev(1))


def test_an_empty_string_is_not_a_statement():
    assert [r for r, _ in run(dev(2, {"attrs": {"redundancy": "   "}}))] == ["L66"]


def test_a_fan_group_is_not_a_power_group():
    """THE CONTAMINATION THIS RULE WAS BORN FROM. Fans are `service` too, and
    the first survey read a fan tray's "5+1" as a power figure."""
    assert not run(dev(6, {"term": "Fan"}, name="fans"))


def test_a_traffic_group_with_many_bays_is_not_a_power_group():
    assert not run(dev(48, {"term": "Port", "role": "traffic"}, name="ports"))


def test_a_group_named_power_counts_even_when_the_term_is_pem():
    """Casa calls the group PEM and names it `power`; Cisco names it
    `power-modules`. The rule has to catch both spellings."""
    assert [r for r, _ in run(dev(2, {"term": "PEM"}, name="power"))] == ["L66"]
    assert [r for r, _ in run(dev(2, {"term": "PSU"}, name="power-modules"))] == ["L66"]


def test_bays_are_counted_across_views():
    """The C40G carries four AC supplies on the front and two PEMs at the rear
    in one group. Counting a single view would have missed the group entirely
    on a chassis where each face has one bay."""
    d = dev(1)
    d["views"]["rear"] = {"components": {"bays": [{"id": "r0", "group": "psus"}]}}
    assert [r for r, _ in run(d)] == ["L66"]


# ---- what the library actually says -----------------------------------------

def test_every_multi_bay_power_group_in_the_library_is_stated():
    """The rollout, complete.

    The ASR 9001 was the last holdout and stayed unstated for a while on
    purpose: the 2+2 and 3+1 tables in its install guide describe four-module
    chassis, and borrowing one for a two-bay box would have been a guess wearing
    a citation. The answer was in a different document - the ASR-9001 FAQ says
    "Two AC or two DC power modules for redundancy" outright."""
    unstated = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("kind") != "device":
            continue
        if run(d):
            unstated.append(f"{f.parent.parent.name}/{f.parent.name}")
    assert unstated == [], unstated


def test_a_stated_form_is_one_the_vendors_actually_use():
    """Two things at once, and both were learned the hard way.

    SCOPED TO POWER GROUPS, and it was not always. It swept every group in the
    device and passed only for as long as power was the sole thing stating a
    form. The day L67 landed and the control-plane and fabric groups started
    stating theirs, it failed on 2+1, 6+1 and 7+1 - real vendor notation
    belonging to a rule that is not this one. A rollout test looks only at its
    own rollout.

    A PATTERN, NOT A FIXED LIST. The power vocabulary is itself wider than the
    four common forms: the ASR 9910 reference guide gives 4+2 for its AC power
    trays and 5+3 for its DC ones. Neither is in the library yet only because
    that chassis models no power trays at all - the day it does, a fixed list
    would reject a figure the vendor prints. The form is whatever the vendor
    writes, N+M with n allowed on either side, and not a menu we happened to
    have seen.
    """
    import re
    forms = set()
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        for name, g in (yaml.safe_load(f.read_text()).get("groups") or {}).items():
            g = g or {}
            term = str(g.get("term") or "").lower()
            if not any(w in name.lower() or w in term for w in ("psu", "power", "pem")):
                continue
            r = (g.get("attrs") or {}).get("redundancy")
            if r:
                forms.add(r)
    bad = [f for f in forms if not re.fullmatch(r"(\d+|n)\+(\d+|n)", f)]
    assert not bad, bad


def test_a_stated_group_carries_the_sentence_it_was_read_from():
    """The form collapses detail the note keeps - active-active versus standby,
    and on a chassis sold in two power variants, which variant it belongs to."""
    thin = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        for name, g in (yaml.safe_load(f.read_text()).get("groups") or {}).items():
            a = ((g or {}).get("attrs") or {})
            if a.get("redundancy") and len(str(a.get("redundancy-note") or "")) < 10:
                thin.append(f"{f.parent.name}:{name}")
    assert not thin, thin
