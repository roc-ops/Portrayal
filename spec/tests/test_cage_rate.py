"""The cage says what FITS; the card says what RUNS - and when the card is silent
the table answers for it.

An SFP housing takes a 1G optic and a 10G one. So `cage_type` reads the family
from the cage ref and the rate from a media attr on the card, and falls back to a
per-cage default in `PART_IFACE` when the card declares none. That fallback is a
default standing in for a fact, and **1215 placements across 114 cards reached
it** with nothing anywhere to say so.

It has been wrong at least seven times:

  - `dpce-r-40ge-sfp` exported forty 10G interfaces on a card whose model number
    and description both say 40x1GbE (found by #267)
  - `mic3-3d-2x40ge-qsfpp` exported two 100G ports on a 40GbE MIC
  - `A9K-40GE-B` did the identical thing in roc-ops/Portrayal#23, three years earlier, and was
    fixed the same way - by stating `sfp: 40`

The defect came back because nothing counted the fallback. L96 counts it now, and
`export_modules` prints the total; these tests hold the counter honest and pin
the ones that have been resolved so they cannot silently regress.
"""
import functools
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import dcim_export as dx    # noqa: E402
import lint                 # noqa: E402


@functools.lru_cache(maxsize=1)
def _modules():
    out = {}
    for cf in sorted(LIB.glob("components/*/*/*/contract.yaml")):
        d = yaml.safe_load(cf.read_text()) or {}
        if d.get("kind") == "module":
            out[f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"] = d
    return out


def _defaulting():
    """ref -> how many of its cages are typed by the table."""
    out = {}
    for ref, d in _modules().items():
        attrs = d.get("attrs") or {}
        n = sum(1 for p in (d.get("parts") or [])
                if isinstance(p, dict) and "ref" in p
                and dx.cage_family_needs_a_rate(p["ref"].split("@")[0], attrs))
        if n:
            out[ref] = n
    return out


# --- the rule asks the exporter's own question -------------------------------

def test_l96_is_registered_as_a_component_rule():
    assert lint.RULES["L96"][0] == "component"


def test_a_family_with_no_attrs_to_declare_is_not_a_gap():
    """XFP runs at one rate, so `FAMILY_ATTRS` gives it nothing to declare and an
    XFP cage answers for itself. Counting it would put 97 placements into a
    backlog that has no fix."""
    assert dx.FAMILY_ATTRS["xfp"] == ()
    assert not dx.cage_family_needs_a_rate("std/xfp", {})
    assert dx.cage_type("std/xfp", {}) == "10gbase-x-xfp"


def test_declaring_the_rate_answers_the_question():
    assert dx.cage_family_needs_a_rate("std/sfp-ganged", {})
    assert not dx.cage_family_needs_a_rate("std/sfp-ganged", {"sfp": 40})
    assert dx.cage_type("std/sfp-ganged", {"sfp": 40}) == "1000base-x-sfp"
    assert dx.cage_type("std/sfp-ganged", {}) == "10gbase-x-sfpp"


# --- what was wrong, pinned so it cannot come back ---------------------------

@pytest.mark.parametrize("ref,attr,count,expected", [
    # Each of these took a table default that its own description contradicts.
    ("juniper/dpce-r-40ge-sfp", "sfp", 40, "1000base-x-sfp"),     # "40x1GbE"
    ("juniper/dpce-r-40ge-sfp-v", "sfp", 40, "1000base-x-sfp"),
    ("juniper/dpce-q-20ge-sfp", "sfp", 20, "1000base-x-sfp"),     # "twenty SFP"
    ("juniper/mic-3d-20ge-sfp", "sfp", 20, "1000base-x-sfp"),     # "Gigabit Ethernet MIC"
    ("juniper/mic-macsec-20ge", "sfp", 20, "1000base-x-sfp"),     # "MACsec Gigabit Ethernet"
    ("juniper/dpce-20ge-2xge", "sfp", 20, "1000base-x-sfp"),      # "twenty SFP ... plus two XFP"
    ("cisco/a9k-mpa-1x40ge", "qsfp", 1, "40gbase-x-qsfpp"),       # "40 Gigabit ... QSFP+"
    ("cisco/a9k-mpa-2x40ge", "qsfp", 2, "40gbase-x-qsfpp"),
    ("juniper/mic3-3d-2x40ge-qsfpp", "qsfp", 2, "40gbase-x-qsfpp"),  # "40GbE ... QSFP+"
    ("juniper/jnp10003-lc2103", "qsfp", 6, "40gbase-x-qsfpp"),    # "six fixed QSFP+ ports"
])
def test_a_card_the_default_contradicted_now_states_its_rate(ref, attr, count, expected):
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get(attr) == count, f"{ref} lost its `{attr}: {count}`"
    cage = next(p["ref"].split("@")[0] for p in d["parts"]
                if isinstance(p, dict) and p["ref"].split("@")[0] in dx.CAGE_FAMILY)
    assert dx.cage_type(cage, attrs) == expected


def test_a_40g_card_does_not_export_100g_ports():
    """The end of the chain, read off the committed export rather than the
    contract - which is the reading that found the original defect."""
    p = LIB / "exports/netbox/module-types/Juniper/MIC3-3D-2X40GE-QSFPP.yaml"
    if not p.exists():
        pytest.skip("the MIC3-3D-2X40GE-QSFPP export is not in this library")
    types = {i["type"] for i in (yaml.safe_load(p.read_text()) or {}).get("interfaces") or []}
    assert types == {"40gbase-x-qsfpp"}, types


# --- the census, which is meant to shrink ------------------------------------

def test_the_backlog_is_counted_and_shrinking():
    """A CENSUS WARNING of the L92/L93 kind. Most of what it names is probably
    right - an SFP-ganged strip on a modern line card usually is SFP+ - and
    "probably right" is exactly what cannot be told from "wrong" without asking.

    An upper bound, not an equality: answering one is a good afternoon's work
    and must not fail the suite.
    """
    n = sum(_defaulting().values())
    assert n <= 865, f"{n} cage placements take the table default, up from 865"
    assert len(_modules()) >= 300, "the census did not find the module catalogue"


def test_the_census_and_the_rule_count_the_same_things():
    """The printed total and L96 have to be one question asked once. A second
    copy of "which cages need a rate" drifts from the table it is about - which
    is the mistake docs/failure-by-omission.md records twice already, so the
    rule imports the exporter rather than restating it."""
    import inspect
    src = inspect.getsource(lint.lint_component_cage_rate)
    assert "dcim_export.cage_family_needs_a_rate" in src
