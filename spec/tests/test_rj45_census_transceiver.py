"""L76's RJ45 census does not ask a pluggable transceiver's jack for lamps.

A copper SFP carries no link LEDs of its own - the Finisar, FS, Cambium and
Optcore drawings show none - and the host port's lamps report the link. The
exemption is keyed on `class: transceiver`; the second test proves it is the
class that exempts, and not something else about the contract."""
import copy
import pathlib

import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/sfp-rj45/v1/contract.yaml"
D = yaml.safe_load(P.read_text())


def l76(data):
    with lint.collecting() as got:
        lint.lint_component_rj45_lamps(P, data, [str(LIB)])
    return [e for e in got.errors + got.warnings if "[L76]" in e]


def test_a_transceivers_bare_jack_is_not_counted():
    assert D["class"] == "transceiver"
    assert l76(D) == []


def test_the_same_contract_as_a_line_card_is_counted():
    card = copy.deepcopy(D)
    card["class"] = "line-card"
    assert l76(card), "the exemption must be the class, not an accident of the contract"
