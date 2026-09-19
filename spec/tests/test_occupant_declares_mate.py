"""L11: an occupant declares its own mate point.

A HOST may present a mate point it does not own - `manifest.presented_interface`
forwards one up from an aperture a vendor cage composes, which is roc-ops/Portrayal#54. AN
OCCUPANT MAY NOT. `render.py` says so where it seats one: "The occupant's is its
own: a module is the thing that mates, not a wrapper around one", and it raises
on a `mate-to` placement whose occupant has no `mate` connection-point.

So a `behaviour: occupies` contract without one is a part that cannot be seated,
and nothing said so until the first device tried. The README's own vendor-wrapper
example was that part for the length of a branch: it composed `generic/sfp-lc@1`
and trusted composition to hand the mate point up, which composition does not do.
Lint refuses it now, at the contract.
"""
import pathlib

from portrayal import lint

P = pathlib.Path("library/components/cisco/sfp-10g-lr/v1/contract.yaml")


def run(doc):
    with lint.collecting() as got:
        lint.lint_component_mating(P, doc, [])
        return [e for e in got.errors if "[L11]" in e]


def occupant(**over):
    doc = {"kind": "module", "name": "sfp-10g-lr", "class": "transceiver",
           "behaviour": "occupies"}
    doc.update(over)
    return doc


def test_an_occupant_without_a_mate_point_is_an_error():
    errs = run(occupant())
    assert len(errs) == 1, errs
    assert "an occupant mates with ITS OWN point" in errs[0]


def test_an_occupant_with_one_is_fine():
    assert run(occupant(**{"connection-points":
                           {"mate": {"at": [6.775, 4.275], "direction": "front"}}})) == []


def test_a_host_port_without_one_is_not_asked():
    """A cage is a HOST: it may forward the mate point of an aperture it composes,
    and L11's older half already asks the question for anything declaring an
    `interface:` or `mates:`."""
    assert run({"kind": "component", "name": "sfp-cage", "class": "port",
                "behaviour": "hosts"}) == []


def test_the_rule_is_registered_as_a_component_rule():
    assert lint.RULES["L11"][0] == "component"
