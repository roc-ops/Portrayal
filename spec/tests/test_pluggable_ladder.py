"""spec/schemas/pluggables.yaml can be wrong, and the corpus is what catches it.

The registry is hand-written data, not derived from anything - a person read
`lint.PLUGGABLE_CAGES`, the fifteen media values L40 already asks about, and
sorted them onto eight ladders by hand. The design doc that preceded this file
got three things wrong on the way here: it dropped `sfp-dd` and `cxp` off the
vocabulary entirely, and it invented `qsfp-dd800`, a rate no device declares
and `PLUGGABLE_CAGES` itself does not carry. None of those mistakes would show
up reading the YAML - a missing family and a family with one value too many
both look like a perfectly ordinary ladder until something holds the file
against the vocabulary it claims to cover.

So this is that something. `PLUGGABLE_CAGES` is imported rather than restated
- a copy of the fifteen values in this file would drift the moment lint's set
changed, and the test would then be checking the registry against a stale
memory of the vocabulary instead of the vocabulary itself. Every check below
is a way the registry could silently stop matching the corpus: a value with no
family, a value claimed by two families, a stray rate that is not in the
vocabulary at all (which is exactly the shape `qsfp-dd800` had), a ladder that
does not climb, an `also-accepts` pointing at nothing, a family with no
`source` to say what it rests on.
"""
import pathlib

import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]

from portrayal import lint


def _registry():
    doc = yaml.safe_load((SPEC / "schemas" / "pluggables.yaml").read_text())
    return doc["families"]


def test_every_pluggable_cage_value_has_exactly_one_family():
    """A value missing from every ladder, or claimed by two, both mean L40's
    question about that cage has nowhere single to land."""
    families = _registry()
    owner = {}
    for name, fam in families.items():
        for rate in fam["rates"]:
            owner.setdefault(rate, []).append(name)

    missing = sorted(v for v in lint.PLUGGABLE_CAGES if v not in owner)
    assert not missing, f"PLUGGABLE_CAGES values with no family: {missing}"

    duplicated = {v: names for v, names in owner.items() if len(names) > 1}
    assert not duplicated, f"values claimed by more than one family: {duplicated}"


def test_every_rate_is_in_the_vocabulary():
    """The other half of the same check: a rate outside PLUGGABLE_CAGES is how
    `qsfp-dd800` got into the design doc's draft - a value the registry invents
    rather than one the corpus actually asks about."""
    families = _registry()
    for name, fam in families.items():
        stray = sorted(r for r in fam["rates"] if r not in lint.PLUGGABLE_CAGES)
        assert not stray, f"family {name!r} names rates outside PLUGGABLE_CAGES: {stray}"


# PLUGGABLE_CAGES is a SET - lint asks no order of it, because L40 only needs
# to know a value is a cage, never which cage came first. Ordering is this
# registry's own fact, not lint's, so it cannot be imported: each family's
# generation number, by bit rate, per the SFF/QSFP-DD specs the `source`
# fields cite. Used only to check a ladder climbs - family membership is
# already held against PLUGGABLE_CAGES by the test above, so this table
# duplicating that assignment would not be the drift the docstring warns
# about; it would just be redundant with it.
_GENERATION = {
    "sfp": 1, "sfp-plus": 2, "sfp28": 3, "sfp56": 4,
    "sfp-dd": 1,
    "qsfp": 1, "qsfp28": 2, "qsfp56": 3, "qsfp112": 4,
    "qsfp-dd": 1,
    "osfp": 1, "xfp": 1, "cfp": 1, "cfp2": 1, "cfp4": 1, "cxp": 1,
}


def test_rates_climb_and_include_the_interface():
    """A ladder that doesn't ascend is not a ladder, and a family whose own
    `interface` is itself a rate has to appear on its own rungs - `sfp` is a
    rung of the `sfp` family, not a label floating outside it."""
    families = _registry()
    for name, fam in families.items():
        rates = fam["rates"]
        assert len(rates) == len(set(rates)), f"family {name!r} repeats a rate: {rates}"
        ranks = [_GENERATION[r] for r in rates]
        assert ranks == sorted(ranks), (
            f"family {name!r} does not climb: {rates}")

        interface = fam["interface"]
        if interface in lint.PLUGGABLE_CAGES:
            assert interface in rates, (
                f"family {name!r} names interface {interface!r}, which is a "
                "rate in PLUGGABLE_CAGES, but it is not among its own rates")


def test_also_accepts_names_a_real_family():
    """`also-accepts` is how a QSFP-DD cage says it takes a QSFP module - an
    entry naming a family that does not exist points the accept list Task 3
    builds at nothing."""
    families = _registry()
    for name, fam in families.items():
        for other in fam.get("also-accepts", []):
            assert other in families, (
                f"family {name!r} also-accepts {other!r}, which is not a "
                "family in this registry")


def test_every_family_carries_a_source():
    """A `source` that is empty or missing is indistinguishable from a family
    invented on the spot - the five families with no MSA held in `working/`
    have to say so, in words, rather than by leaving the field blank."""
    families = _registry()
    thin = {name: fam.get("source") for name, fam in families.items()
            if not (fam.get("source") or "").strip()}
    assert not thin, f"families with no source: {sorted(thin)}"


def test_the_registry_is_not_vacuous():
    """A registry that failed to parse, or parsed to nothing, would pass every
    check above by having nothing to check - the same silent-collapse shape
    `test_silent_drops.py`'s own vacuity test exists to catch, one file over."""
    families = _registry()
    assert len(families) >= 8, f"only {len(families)} family(ies) loaded"
    assert sum(len(fam["rates"]) for fam in families.values()) == len(lint.PLUGGABLE_CAGES)
