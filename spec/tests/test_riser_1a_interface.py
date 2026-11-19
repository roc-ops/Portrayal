"""Riser 1A seats its full-height cards by form: `interface: pcie-fh` on its two connector slots.

The Dell riser 1A used to name every card it takes. Its slots 1 and 3 now state `interface: pcie-fh`, and the modules
that fit them state `mates: pcie-fh`, so a card is taken by what it is and not by being on a list. What each slot
takes is unchanged: the same parts, the filler by name, the two-slot bracket in slot 1 only.
"""
import pathlib

import pytest

from portrayal import render
from portrayal.manifest import load_yaml, mates_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RISER = LIB / "components/dell/riser-1a-14g/v2/contract.yaml"

FILLER = "dell/pcie-filler-fh-14g@2"
# What the riser named in its two connector slots before it stated an interface, and now finds by `mates`.
MATING = [
    "common/pcie-card-fh@2", "ufispace/n3100-4c@1",
    "nvidia/mcx4111a-fh@1", "nvidia/mcx4121a-fh@1", "nvidia/mcx4131a-fh@1", "nvidia/mcx512a-fh@1",
    "nvidia/mcx512f-fh@1", "nvidia/mcx515a-fh@1", "nvidia/mcx516a-fh@1", "nvidia/mcx621102-fh@1",
    "nvidia/mcx621202-fh@1", "nvidia/mcx623102a-fh@1", "nvidia/mcx623105-fh@1", "nvidia/mcx623106-fh@1",
    "nvidia/mcx713104-fh@1", "nvidia/mcx713106-fh@1", "nvidia/mcx713114-fh@1", "nvidia/mcx715105-fh@1",
    "nvidia/mcx75310-fh@1", "nvidia/mcx75510-fh@1", "nvidia/mcx755106-fh@1",
]
BRACKET = "std/pcie-bracket-fh@2"
TWO_SLOT = "std/pcie-bracket-fh-2slot@1"
GPUS = ["nvidia/a100-pcie-80gb@1", "nvidia/a100-pcie-40gb@1", "nvidia/l4@1"]
# Parts that state no `mates` stay in `accepts`: a bare bracket cannot (L11), the GPUs are not in this part.
LISTED_1 = [FILLER, BRACKET, TWO_SLOT, *GPUS]
LISTED_3 = [FILLER, BRACKET]
SLOT_1 = [*LISTED_1, *MATING]       # compared sorted; the order is not asked
SLOT_3 = [*LISTED_3, *MATING]


def _bays():
    return load_yaml(RISER)["bays"]


@pytest.fixture(scope="module")
def lib():
    return render.Library([str(LIB)])


@pytest.mark.parametrize("ref", MATING)
def test_the_part_mates_the_full_height_key(ref):
    ns_name, major = ref.split("@")
    contract = load_yaml(LIB / "components" / ns_name / f"v{major}" / "contract.yaml")
    assert mates_of(contract) == ["pcie-fh"], ref


def test_the_connector_slots_state_the_interface_and_the_blanked_one_does_not():
    bays = _bays()
    assert bays["slot-1"].get("interface") == "pcie-fh"
    assert bays["slot-3"].get("interface") == "pcie-fh"
    assert "interface" not in bays["slot-2"], "slot 2 has no connector behind it and stays a closed list"
    assert bays["slot-2"]["accepts"] == [FILLER]


def test_the_authored_lists_no_longer_name_the_cards_that_mate():
    for slot, kept in (("slot-1", LISTED_1), ("slot-3", LISTED_3)):
        listed = _bays()[slot]["accepts"]
        assert sorted(listed) == sorted(kept), slot
        assert _bays()[slot]["default"] == FILLER


def test_each_slot_takes_what_it_took(lib):
    bays = _bays()
    assert sorted(lib.offers(bays["slot-1"])) == sorted(SLOT_1)
    assert sorted(lib.offers(bays["slot-3"])) == sorted(SLOT_3)
    assert lib.offers(bays["slot-2"]) == [FILLER]


def test_the_two_slot_bracket_is_offered_where_a_span_allows_it(lib):
    bays = _bays()
    assert TWO_SLOT in lib.offers(bays["slot-1"])
    assert TWO_SLOT not in lib.offers(bays["slot-3"])
    assert TWO_SLOT not in lib.offers(bays["slot-2"])


def test_no_part_of_the_other_height_is_offered(lib):
    bays = _bays()
    for slot in ("slot-1", "slot-3"):
        for ref in lib.offers(bays[slot]):
            ns_name, major = ref.split("@")
            keys = mates_of(load_yaml(LIB / "components" / ns_name / f"v{major}" / "contract.yaml"))
            assert "pcie-lp" not in keys, (slot, ref)
