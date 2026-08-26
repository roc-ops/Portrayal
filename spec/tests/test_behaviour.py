"""How a part MOVES, which is what a renderer needs and a catalogue class cannot say.

The 3D viewer decided what could be ejected from a hardcoded list of class names,
so every new removable type meant editing that list - and a transceiver, which is
removable, was not on it. `behaviour` replaces the list with a fact the component
states about itself.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

CONTRACTS = sorted(LIB.glob("components/*/*/*/contract.yaml"))
VALID = {"fills", "occupies", "mounts"}


def load(p):
    return yaml.safe_load(p.read_text()) or {}


def test_every_behaviour_is_one_of_three():
    for p in CONTRACTS:
        b = load(p).get("behaviour")
        assert b is None or b in VALID, (p, b)


def test_a_class_cannot_answer_this_which_is_why_the_field_exists():
    """Two classes are already mixed, and a class list cannot express either.

    `filter` holds five slide-out air filters and one snap-on cover; `inlet`
    holds three receptacles and one bolted panel. If these ever collapse to one
    behaviour each, either the library changed or somebody derived the field
    from the class again and lost the distinction.
    """
    for cls in ("filter", "inlet"):
        seen = {load(p).get("behaviour") for p in CONTRACTS if load(p).get("class") == cls}
        assert len(seen) > 1, f"{cls} came out uniform: {seen}"


def test_a_receptacle_does_not_move():
    """A cage, a lamp, a button and a printed mark do not come out, and saying
    nothing is how they say so. A `port` that gains a behaviour would be given a
    3D body and an eject control it has no business having."""
    for p in CONTRACTS:
        d = load(p)
        if d.get("class") in ("port", "led", "button", "silkscreen"):
            assert d.get("behaviour") is None, p


def test_the_transceiver_is_removable():
    """The gap this issue was filed for: removable, and not on the class list."""
    for name in ("common/sfp-lc-duplex", "common/qsfp-transceiver"):
        ns, n = name.split("/")
        p = next(iter(LIB.glob(f"components/{ns}/{n}/*/contract.yaml")))
        assert load(p).get("behaviour") == "occupies", p


def test_the_old_class_list_is_a_subset_of_fills():
    """Nothing that used to get a body may lose one. The five classes the viewer
    hardcoded must all still qualify, or the migration dropped a FRU."""
    for cls in ("psu", "fan", "tab", "power", "cooling"):
        for p in CONTRACTS:
            d = load(p)
            if d.get("class") == cls:
                assert d.get("behaviour") == "fills", (p, d.get("behaviour"))
