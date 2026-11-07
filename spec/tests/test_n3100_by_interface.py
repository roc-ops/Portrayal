"""The first card that seats by its form: the UfiSpace N3100-4C in slot 1 of Dell riser 1A.

docs/cards-by-interface-design.md, "The first build slice", cut to one card in one
slot. The card states `mates: pcie-fh`; the riser's slot 1 states
`interface: pcie-fh` and keeps its list, so the union is what is exercised and
nothing that was seated can stop being seated. The mechanism itself is held by
test_cards_by_interface.py on a small library; this file holds what is true of
the real parts.
"""
import copy
import pathlib

import pytest

from portrayal import libwalk
from portrayal import render
from portrayal.manifest import load_yaml, mates_of, takes

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
CARD = "ufispace/n3100-4c@1"
CARD_FILE = LIB / "components/ufispace/n3100-4c/v1/contract.yaml"
RISER_FILE = LIB / "components/dell/riser-1a-14g/v2/contract.yaml"
BRACKET_OF = {"pcie-fh": "std/pcie-bracket-fh", "pcie-lp": "std/pcie-bracket-lp"}


def _card():
    return load_yaml(CARD_FILE)


def _slot_1():
    return load_yaml(RISER_FILE)["bays"]["slot-1"]


def _composed(doc):
    """Every ref a contract's `parts` places, nested or not."""
    out = []

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("ref"), str):
                out.append(x["ref"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc.get("parts"))
    return out


def test_the_card_mates_the_full_height_key():
    assert mates_of(_card()) == ["pcie-fh"]


def test_slot_1_of_riser_1a_states_the_full_height_interface():
    assert _slot_1().get("interface") == "pcie-fh"


def test_the_card_that_mates_a_pcie_key_composes_the_bracket_that_key_points_at():
    """Every part in the library that mates a PCIe key composes (or is) the
    bracket the key's registry entry points at, so the two statements of one
    fact agree."""
    found = []
    for cf in libwalk.iter_components([LIB]):
        doc = load_yaml(cf) or {}
        for key in set(mates_of(doc)) & set(BRACKET_OF):
            wanted = BRACKET_OF[key]
            made = f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}@{cf.parent.name[1:]}"
            refs = _composed(doc) + [made]
            if not any(r.startswith(wanted + "@") or r.startswith(wanted + "-2slot@")
                       for r in refs):
                found.append(f"{made} mates {key}")
    assert found == [], found


def test_the_card_is_taken_by_its_mates_without_being_named():
    """Take the card out of slot 1's list: the interface alone seats it."""
    bay = copy.deepcopy(_slot_1())
    bay["accepts"] = [r for r in bay["accepts"] if r != CARD]
    assert CARD not in bay["accepts"]
    assert takes(bay, CARD, _card())


def test_a_card_of_the_other_height_is_refused():
    bay = copy.deepcopy(_slot_1())
    bay["accepts"] = [r for r in bay["accepts"] if r != CARD]
    low = copy.deepcopy(_card())
    low["mates"] = "pcie-lp"
    assert not takes(bay, CARD, low)


def test_a_part_that_mates_nothing_is_not_taken_through_the_interface():
    bay = copy.deepcopy(_slot_1())
    bay["accepts"] = [r for r in bay["accepts"] if r != CARD]
    bare = copy.deepcopy(_card())
    bare.pop("mates", None)
    assert not takes(bay, CARD, bare)


@pytest.mark.heavy
def test_what_slot_1_offers_is_the_list_it_states():
    """The published list of the migrated riser does not move: the one card that
    mates the key is already in the list, so the union adds nothing."""
    bay = _slot_1()
    assert render.Library([str(LIB)]).offers(bay) == list(bay["accepts"])
