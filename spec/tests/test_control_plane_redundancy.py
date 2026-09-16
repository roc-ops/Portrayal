"""L67: the cards that run and switch the box say whether the second one works.

The sibling power rule settled the same question for supplies. This one is the
higher-stakes half of it: two RSPs are either two working processors or one plus
a spare, and the CARD cannot tell you which - the ASR 9000's RSP is active/standby
for control and active/active for fabric on the same chassis. Only the chassis
knows, so the group says it.

The abbreviations are what makes this rule delicate. `re`, `rp`, `fc` are two and
three letters long, and a substring match for them drags in "furniture" and worse.
The matching is therefore on whole words of the group name and term, and the tests
below pin that.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint

LIB = ROOT / "library"


def run(doc):
    out = []
    real = lint.warn
    lint.warn = lambda p, r, m: out.append((r, m))
    try:
        lint.lint_device_control_plane_redundancy("t.yaml", doc)
    finally:
        lint.warn = real
    return out


def dev(bays, group=None, name="res"):
    group = {"term": "Slot", "role": "service", **(group or {})}
    return {
        "kind": "device",
        "groups": {name: group},
        "views": {"front": {"components": {
            "bays": [{"id": f"b{i}", "group": name} for i in range(bays)]}}},
    }


# ---- the rule ---------------------------------------------------------------

def test_two_routing_engine_bays_with_no_statement_are_flagged():
    hits = run(dev(2))
    assert [r for r, _ in hits] == ["L67"]
    assert "working one or a spare" in hits[0][1]


def test_a_stated_group_is_silent():
    assert not run(dev(2, {"attrs": {"redundancy": "1+1"}}))


def test_one_bay_needs_no_statement():
    """A single processor is not standing in for anything."""
    assert not run(dev(1))


def test_an_empty_string_is_not_a_statement():
    assert [r for r, _ in run(dev(2, {"attrs": {"redundancy": "  "}}))] == ["L67"]


def test_a_fabric_group_counts_too():
    hits = run(dev(7, {"term": "FC"}, name="fabric"))
    assert [r for r, _ in hits] == ["L67"]
    assert "fabric bays" in hits[0][1]


def test_the_message_names_which_kind_of_group_it_is():
    assert "control-plane bays" in run(dev(2, {"term": "RP"}, name="rp"))[0][1]


def test_every_vendors_spelling_is_caught():
    """Cisco says RSP and RP, Juniper says RE, RCB, SCB, SFB, SIB. The rule has
    to catch all of them or the convention only lands on one vendor's chassis."""
    for name, term in [("rp", "RP"), ("rsp", "RSP"), ("res", "Slot"),
                       ("scbs", "Slot"), ("sfbs", "Slot"), ("sibs", "Slot"),
                       ("fabric", "Slot"), ("supervisors", "Sup"),
                       ("smm", "Module")]:
        assert [r for r, _ in run(dev(2, {"term": term}, name=name))] == ["L67"], name


def test_a_word_that_merely_contains_an_abbreviation_is_not_a_match():
    """THE CONTAMINATION THIS RULE WAS BUILT TO AVOID. `re` is a substring of
    "furniture" and `sup` of "supply"; a substring match would flag both. Only
    whole words count."""
    for name in ("furniture", "covers", "power-supplies", "filters", "drives"):
        assert not run(dev(6, {"term": "Item"}, name=name)), name


def test_a_power_group_is_not_a_control_plane_group():
    """L66's territory, and the two rules must not both fire on one group."""
    assert not run(dev(4, {"term": "PSU"}, name="psus"))


def test_a_traffic_group_is_not_checked():
    """Line-card slots outnumber everything else in the library, and a chassis
    does not have a redundancy form for its line cards."""
    assert not run(dev(20, {"term": "Slot", "role": "traffic"}, name="fpcs"))


def test_bays_are_counted_across_views():
    d = dev(1)
    d["views"]["rear"] = {"components": {"bays": [{"id": "r0", "group": "res"}]}}
    assert [r for r, _ in run(d)] == ["L67"]


# ---- what the library actually says -----------------------------------------

def test_every_multi_bay_control_plane_or_fabric_group_in_the_library_is_stated():
    """The rollout. No deliberate holdouts: every such group in the library has a
    per-model guide behind it. If this list grows, the new device either needs its
    figure or needs to be named here with the reason it cannot have one - an
    unstated group is an honest gap, a guessed one is a lie wearing a citation."""
    unstated = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("kind") != "device":
            continue
        if run(d):
            unstated.append(f"{f.parent.parent.name}/{f.parent.name}")
    assert unstated == [], unstated


def test_a_stated_form_is_one_the_vendors_actually_use():
    """`N+M` with `n` allowed on either side: 4+2, 5+3 and 6+1 are all real vendor
    notation, and so are n+1 and n+n where the guide declines to spell the n."""
    import re
    bad = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        for name, g in (yaml.safe_load(f.read_text()).get("groups") or {}).items():
            r = ((g or {}).get("attrs") or {}).get("redundancy")
            if r and not re.fullmatch(r"(\d+|n)\+(\d+|n)", str(r)):
                bad.append(f"{f.parent.name}:{name}={r}")
    assert not bad, bad


def test_a_stated_group_carries_the_sentence_it_was_read_from():
    """The form collapses detail the note keeps - active/active versus standby,
    and, on the ASR 9910 and the MX960, why the form does not match the bay
    count."""
    thin = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        for name, g in (yaml.safe_load(f.read_text()).get("groups") or {}).items():
            a = ((g or {}).get("attrs") or {})
            if a.get("redundancy") and len(str(a.get("redundancy-note") or "")) < 10:
                thin.append(f"{f.parent.name}:{name}")
    assert not thin, thin


def test_the_notes_on_control_plane_and_fabric_groups_name_their_document():
    """Not "the datasheet". A note that cannot be checked against a named guide
    and section is a claim, not a citation."""
    vague = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("kind") != "device":
            continue
        for name, g in (d.get("groups") or {}).items():
            g = g or {}
            words = lint._group_words(name, str(g.get("term") or ""))
            if not (words & lint.CONTROL_PLANE_WORDS or words & lint.FABRIC_WORDS):
                continue
            note = str((g.get("attrs") or {}).get("redundancy-note") or "")
            if not note:
                continue
            if "guide" not in note.lower():
                vague.append(f"{f.parent.name}:{name}")
    assert not vague, vague
