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
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))
import lint  # noqa: E402

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
    statement at all in any document we hold."""
    unstated = sorted(slug for slug, d in devices() if run(d))
    assert "edgecore/cor580" in unstated and "edgecore/dcs510" in unstated
    assert len(unstated) == 20, unstated


def test_the_comparison_layer_can_now_reach_them():
    """The point of the exercise. It resolved on nothing before this. Forty
    when the rule landed; the R740xd made it forty-one the day its fans became
    bays with a group that quotes the technical guide's N+1."""
    import comparable as C
    n = sum(1 for _, d in devices() if C.resolve(d).get("fan-redundancy"))
    assert n == 41, n
