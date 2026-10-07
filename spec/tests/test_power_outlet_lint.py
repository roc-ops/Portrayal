"""L132-L135: a power outlet names its feed, and the position it runs through
resolves (#806, docs/power-outlets-design.md).

An output circuit on a distribution panel exports as a power outlet whose
`power_port` is the input its `fed-by` names, and whose description names the
breaker position its `through` names. Both cross a face - the output on the
rear, the breaker on the front - so both resolve over the whole device.
"""
import pytest

from portrayal import lint

OUT = "amphenol-ns/output-terminal@1"
FEED = "amphenol-ns/input-feed-studs@1"


def panel(maturity="modelled", **outputs):
    """A two-face panel: one breaker bay on the front, one feed and the given
    outputs (id -> extra keys) on the rear."""
    rear = [{"id": "input-a", "ref": FEED, "at": [0, 0]},
            {"id": "alarm", "ref": "amphenol-ns/alarm-card-307608@1", "at": [50, 0]}]
    for i, (oid, keys) in enumerate(sorted(outputs.items())):
        rear.append({"id": oid, "ref": OUT, "at": [100 + 15 * i, 0], **keys})
    return {"maturity": maturity, "views": {
        "front": {"components": {"bays": [
            {"id": "breaker-a1", "at": [0, 0], "size": {"w": 10, "h": 10},
             "accepts": ["amphenol-ns/breaker-1ru@1"]},
            {"id": "breaker-a2", "at": [20, 0], "size": {"w": 10, "h": 10},
             "accepts": ["amphenol-ns/breaker-1ru@1"]}]}},
        "rear": {"components": {"placements": rear}}}}


def findings(doc, code):
    with lint.collecting() as found:
        lint.lint_device_power_outlets("device.yaml", doc)
    return ([m for m in found.errors if f"[{code}]" in m],
            [m for m in found.warnings if f"[{code}]" in m])


def test_a_fed_outlet_through_a_bay_is_clean():
    doc = panel(**{"output-a1": {"fed-by": "input-a", "through": "breaker-a1"},
                   "output-a2": {"fed-by": "input-a", "through": "breaker-a2"}})
    for code in ("L132", "L133", "L134", "L135"):
        assert findings(doc, code) == ([], []), code


def test_L132_fed_by_names_nothing():
    errs, _ = findings(panel(**{"output-a1": {"fed-by": "input-z"}}), "L132")
    assert len(errs) == 1 and "no placement" in errs[0]


def test_L132_fed_by_names_a_part_with_no_power_port():
    errs, _ = findings(panel(**{"output-a1": {"fed-by": "alarm"}}), "L132")
    assert len(errs) == 1 and "exports no power port" in errs[0]


def test_L132_fed_by_on_a_part_that_is_not_an_outlet():
    doc = panel()
    doc["views"]["rear"]["components"]["placements"][1]["fed-by"] = "input-a"
    errs, _ = findings(doc, "L132")
    assert len(errs) == 1 and "exports no power outlet" in errs[0]


def test_L133_through_names_no_bay():
    for via in ("breaker-a9", "input-a"):     # nothing, and a placement that is not a bay
        errs, _ = findings(panel(**{"output-a1": {"fed-by": "input-a", "through": via}}),
                           "L133")
        assert len(errs) == 1, via


@pytest.mark.parametrize("maturity, loud", [("draft", False), ("modelled", False),
                                            ("verified", True)])
def test_L134_an_outlet_states_a_feed(maturity, loud):
    errs, warns = findings(panel(maturity, **{"output-a1": {}}), "L134")
    assert (len(errs), len(warns)) == ((1, 0) if loud else (0, 1))


def test_L135_one_position_one_circuit():
    doc = panel(**{"output-a1": {"fed-by": "input-a", "through": "breaker-a1"},
                   "output-a2": {"fed-by": "input-a", "through": "breaker-a1"}})
    errs, warns = findings(doc, "L135")
    assert not errs and len(warns) == 1
    assert "output-a1" in warns[0] and "output-a2" in warns[0]
