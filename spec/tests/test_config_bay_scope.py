"""L8: a configuration seats nothing in a bay its own configuration removes.

`only-in` takes a bay out of the metal for every configuration it does not
name, and render.py skips the bay before it ever reads the configuration's
`bays:` map. So a configuration that seats a module in such a bay asserts an
occupant the drawing cannot show, and the drawing drops it without a word.

The CommScope CH3000 found it: slot-15 and slot-16 were `only-in: [base]`, a
second configuration seated a receiver in each, lint was clean, and the render
drew 12 receivers instead of 14. A nested key (`slot-1/ppm-1`, module-less) is
scoped by its head - a component's bays carry no `only-in` of their own.
"""
from pathlib import Path

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"
CARD = "smartoptics/ppm-ad1-1510@2"


def device(cfg_bays, only_in=("base",)):
    bay = {"id": "slot-15", "at": [0, 0], "size": {"w": 10, "h": 10},
           "accepts": [CARD]}
    if only_in is not None:
        bay["only-in"] = list(only_in)
    free = {"id": "slot-1", "at": [20, 0], "size": {"w": 10, "h": 10},
            "accepts": [CARD]}
    return {
        "views": {"front": {"components": {"bays": [bay, free]}}},
        "configurations": {"base": {"bays": {}}, "x14": {"bays": cfg_bays}},
    }


def run(data):
    with lint.collecting() as got:
        lint.lint_device_configuration_bays("dev.yaml", data, [LIB])
    return [e for e in got.errors if "[L8]" in e]


def test_seating_a_bay_scoped_out_of_the_configuration_is_an_error():
    errs = run(device({"slot-15": CARD}))
    assert len(errs) == 1, errs
    assert "x14" in errs[0] and "slot-15" in errs[0] and "only-in" in errs[0]


def test_a_nested_key_is_scoped_by_its_head():
    errs = run(device({"slot-15/ppm-1": CARD}))
    assert any("slot-15/ppm-1" in e and "only-in" in e for e in errs), errs


def test_a_bay_the_configuration_is_scoped_into_is_fine():
    data = device({"slot-15": CARD})
    data["configurations"]["base"]["bays"] = {"slot-15": CARD}
    data["views"]["front"]["components"]["bays"][0]["only-in"] = ["base", "x14"]
    assert run(data) == []


def test_an_unscoped_bay_is_fine():
    assert run(device({"slot-15": CARD}, only_in=None)) == []


def test_emptying_a_scoped_out_bay_is_fine():
    """`""` seats nothing, and a bay that is not there is empty too - the key
    is redundant, but the drawing shows exactly what it says."""
    assert run(device({"slot-15": ""})) == []


def test_the_same_id_unscoped_in_another_view_is_enough():
    """The rule is that the key reaches a bay in SOME view that exists in the
    configuration: a rear bay of the same id with no scope still draws it."""
    data = device({"slot-15": CARD})
    data["views"]["rear"] = {"components": {"bays": [
        {"id": "slot-15", "at": [0, 0], "size": {"w": 10, "h": 10}, "accepts": [CARD]}]}}
    assert run(data) == []
