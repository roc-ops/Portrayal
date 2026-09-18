"""L69: a cooling group with more than one bay says how many fans it can lose.

The third of the family, after L66 for power and L67 for the cards that run and
switch the box. What made it worth its own pass is that the data was already in
the library and unreachable: the comparison layer resolved `fan-redundancy` on
0 of 84 devices while 23 carried the figure as `attrs.fan-redundancy` and 14
more had it in their own description. Prose is not a field.

The rollout also produced the clearest example yet of the trap this project
keeps walking into, so it is pinned below: four Edgecore chassis whose staged
datasheets hold TWO fan figures each, where exactly one fills the bay count.
Taking the one that fits would be arithmetic wearing a citation.
"""
import pathlib
import sys

import yaml

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint

LIB = ROOT / "library"


def run(doc):
    out = []
    real = lint.warn
    lint.warn = lambda p, r, m: out.append((r, m))
    try:
        lint.lint_device_fan_redundancy("t.yaml", doc)
    finally:
        lint.warn = real
    return out


def dev(bays, group=None, name="fans"):
    group = {"term": "Fan", "role": "service", **(group or {})}
    return {"kind": "device", "groups": {name: group},
            "views": {"rear": {"components": {
                "bays": [{"id": f"ft{i}", "group": name} for i in range(bays)]}}}}


# ---- the rule ---------------------------------------------------------------

def test_a_multi_bay_cooling_group_with_no_figure_is_flagged():
    assert [r for r, _ in run(dev(4))] == ["L69"]


def test_a_stated_group_is_silent():
    assert not run(dev(4, {"attrs": {"redundancy": "3+1"}}))


def test_one_fan_bay_needs_no_figure():
    assert not run(dev(1))


def test_a_fanless_group_is_not_a_fan_group():
    """Whole words. Several access switches in this library are fanless, and
    the substring is right there in the word."""
    assert not run(dev(4, {"term": "Port", "role": "traffic"}, name="fanless-ports"))


def test_the_vendors_own_spellings_all_count():
    for name, term in (("fans", "Fan"), ("cooling", "Fan Tray"),
                       ("fan-trays", "Fan Tray"), ("blowers", "Blower")):
        assert [r for r, _ in run(dev(2, {"term": term}, name=name))] == ["L69"], name


def test_a_psu_group_is_not_a_fan_group():
    """The contamination the whole family exists to prevent, in the other
    direction: L66 owns this group and L69 must not also claim it."""
    assert not run(dev(2, {"term": "PSU"}, name="psus"))


def test_the_rule_does_not_police_the_arithmetic():
    """A form is the vendor's claim; a bay count is ours. The ASR 9910 states
    6+1 for a five-bay cage because Cisco counts planes across the RSP pair -
    a rule demanding the sum would call that an error."""
    assert not run(dev(5, {"attrs": {"redundancy": "6+1"}}))


# ---- what the library says --------------------------------------------------

def devices():
    """Over the once-parsed library - see libdata."""
    return libdata.devices()


def test_every_stated_fan_figure_fills_its_bays():
    """Not policed by the rule, but true of all 40 stated here, and worth
    knowing if it ever stops being true - a figure that no longer fills the
    tray is either a modelling error or a genuinely interesting chassis."""
    odd = []
    for slug, d in devices():
        bays = {}
        for v in (d.get("views") or {}).values():
            for b in ((v.get("components") or {}).get("bays") or []):
                if b.get("group"):
                    bays[b["group"]] = bays.get(b["group"], 0) + 1
        for name, g in (d.get("groups") or {}).items():
            form = (((g or {}).get("attrs") or {}).get("redundancy") or "")
            if not form or not (lint._group_words(name, str((g or {}).get("term") or "")) & lint.FAN_WORDS):
                continue
            parts = form.split("+")
            if all(p.isdigit() for p in parts) and sum(int(p) for p in parts) != bays.get(name, 0):
                odd.append(f"{slug}:{name} {form} in {bays.get(name)} bays")
    assert not odd, odd


def test_the_unstated_ones_are_the_ones_we_could_not_source():
    """The holdouts are deliberate and named. Four Edgecore chassis carry TWO
    conflicting fan figures in the staged corpus; the rest have no fan
    statement at all in any document we hold.

    THE ASR 9903 MADE IT TWENTY-ONE AND THE ASR 9902 TWENTY-TWO, and they are a
    third kind of holdout worth telling apart from the other two. Cisco is not
    silent about either and does not contradict itself: each data sheet says the
    chassis has its fans "in redundant configuration" and lists "Fan redundancy"
    in Table 2, and the fixed-port Hardware Installation Guide gives replacement
    steps. What none of them gives is the FORM. Four trays redundant is 3+1 or
    2+2, three trays is 2+1, and the difference is the whole question - so each
    group carries the sentence and no `redundancy`, which is the ruling the
    CSR310 got for "Hot swappable redundant fan modules" applied to a vendor who
    said more and still not enough.

    THE TWO ARRIVED TOGETHER AND THE SECOND ONE IS THE TEST OF THE FIRST. Three
    trays has only one sensible reading, 2+1, and it was still not written down,
    because a ratio nobody published is not a ratio this library states."""
    unstated = sorted(slug for slug, d in devices() if run(d))
    assert "edgecore/cor580" in unstated and "edgecore/dcs510" in unstated
    assert "cisco/asr-9903" in unstated and "cisco/asr-9902" in unstated
    assert len(unstated) == 22, unstated


def test_the_comparison_layer_can_now_reach_them():
    """The point of the exercise. It resolved on nothing before this. Forty
    when the rule landed; the R740xd made it forty-one the day its fans became
    bays with a group that quotes the technical guide's N+1, the AGR110
    forty-two, its fan group quoting the datasheet's 5+1, its AGR130 sibling
    forty-three, and the ASR 9006 forty-four the day FT0 and FT1 stopped being
    cutouts - its group states 1+1 and quotes the three sentences of the
    Overview and Reference Guide that have to be read together to get there.

    THE CSR310 DID NOT MAKE IT FORTY-FIVE, and that is the rule working rather
    than failing. Its fan tray IS a bay with a redundant group, but the
    datasheet's whole sentence is "Hot swappable redundant fan modules" - no
    form, no count - so the group carries a note and no `redundancy`, and the
    comparison layer correctly cannot reach it. An unstated group is an honest
    gap; the number this test holds counts devices whose vendor said something,
    not devices that have fans.

    THE TWO PARAGRAPHS ABOVE ARRIVED FROM DIFFERENT BRANCHES ON THE SAME DAY and
    are the two halves of one point: the ASR 9006 counts because its guide gives
    a form, the CSR310 does not because its datasheet gives a phrase. The number
    is meant to go up, one sourced statement at a time. A drop is the thing to
    look at.

    FORTY-FIVE IS THE CSR440, and it is the first in this family whose digit form
    and bay count agree without argument: the datasheet says 5+1 and the rear
    face has six fan modules, so test_every_stated_fan_figure_fills_its_bays
    checks 5+1 against six bays and is satisfied. Its CSR430 sibling had to drop
    its own 4+1 because that figure counts FANS INSIDE ONE TRAY - true at the
    wrong level - and the CSR310 above never had a form to check. Six removable
    modules is the arrangement the comparison layer was built for.

    FORTY-SIX IS THE DCS201, whose datasheet says "4+1 redundant fan modules" against five
    rear bays - and whose quick start counts them the same way, "5 x fan trays", so the two
    documents agree with each other and with the metal. Its three sibling chassis carry SIX
    fans on a 48.6 pitch and are already counted here; this one is five on a 58.8 pitch,
    which is why its fan is its own part rather than the family's.

    FORTY-SEVEN IS THE DCS202, the DCS201's copper sibling, which states the same "4+1
    redundant fan modules" over the same five bays - and seats the same fan, because its
    guide prints the DCS201's supply tables character for character and its own rear
    photograph puts the handles on a 59.06 pitch against the DCS201's 58.82. Two devices,
    one rear, one figure, counted twice because two vendors' documents state it twice.

    FORTY-EIGHT IS THE DCS240, and it is the first in this family to state 5+1 against SIX
    bays - "5+1 redundant hot-swappable fan modules" in the datasheet, "6 x fan trays" in the
    quick start's rear callout, and six measured bays on a 48.50 pitch. The CSR440's 5+1 was
    the first digit form to match its bay count at all; this one matches at a different count,
    on a different shell, with a fan of its own.
    """
    from portrayal import comparable as C
    n = sum(1 for _, d in devices() if C.resolve(d).get("fan-redundancy"))
    assert n == 48, n
