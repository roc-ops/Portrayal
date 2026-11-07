"""The NVIDIA A100 40GB and L4 seat in riser 1A of the Dell R740xd, and the three
cards its documents do not support stay unplaced (#877).

The R740xd installation and service manual (table 27) lists double-width GPUs in
riser 1A's slot 1 and "Nvidia A16, A30, A40, A100, A800" among them; the spec
sheet caps a double-width GPU at 300 W. The A100 40GB is 250 W. The L4 is a
single-width, full-height-bracket, 72 W card, inside the manual's single-width
GPU class (spec sheet: six 150 W single-width GPUs), and fits slot 1 only: the
manual's GPU slot priority is slots 1, 8 and 4, never riser 1A's slot 3.
"""
from pathlib import Path

import pytest

from portrayal import lint
from portrayal.manifest import load_yaml, slot_width, span_covers

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RISER = LIB / "components/dell/riser-1a-14g/v2/contract.yaml"
A100_40 = "nvidia/a100-pcie-40gb@1"
L4 = "nvidia/l4@1"
LEFT_OUT = ["nvidia/h100-pcie@1", "nvidia/h100-nvl@1", "nvidia/l40s@1"]


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return load_yaml(LIB / f"components/{ns}/{name}/v{major}/contract.yaml")


def _bays():
    return load_yaml(RISER)["bays"]


def _span_findings(riser, parts):
    got = []
    saved = lint.err, lint.resolve_component, lint.load_yaml
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    lint.resolve_component = lambda ref, roots: ref if ref in parts else None
    lint.load_yaml = lambda ref: parts[ref]
    try:
        lint.lint_component_span(Path("x/contract.yaml"), riser, [str(LIB)])
    finally:
        lint.err, lint.resolve_component, lint.load_yaml = saved
    return got


# --- the A100 40GB: two slots wide, seated where a bay spans -----------------------

def test_the_a100_40gb_is_two_slots_wide_and_no_longer_unplaced():
    card = _contract(A100_40)
    assert slot_width(card) == 2
    assert "unplaced" not in card


def test_the_a100_40gb_seats_in_riser_1a_slot_1_which_spans_slot_2():
    bay = _bays()["slot-1"]
    assert A100_40 in bay["accepts"]
    assert span_covers(bay, slot_width(_contract(A100_40))) == ["slot-2"]


@pytest.mark.parametrize("narrow", ["slot-2", "slot-3"])
def test_the_a100_40gb_is_refused_a_slot_too_narrow_for_it(narrow):
    assert A100_40 not in _bays()[narrow]["accepts"]


def test_l185_is_quiet_on_riser_1a_and_refuses_the_a100_40gb_in_slot_3():
    parts = {A100_40: _contract(A100_40)}
    assert _span_findings(load_yaml(RISER), parts) == []
    import copy
    riser = copy.deepcopy(load_yaml(RISER))
    slot3 = riser["bays"]["slot-3"]
    slot3["accepts"] = [*slot3["accepts"], A100_40]
    assert [m for _, m in _span_findings(riser, parts)] == [
        f"bays/slot-3: accepts {A100_40}, which is 2 slots wide, and names 0 bay(s) in "
        "`span` for it to cover"]


def test_the_a100_40gb_draws_within_the_dell_300w_ceiling():
    assert _contract(A100_40)["attrs"]["power-draw-max-w"] <= 300


# --- the L4: one slot, seated in the full-height full-length slot ------------------

def test_the_l4_is_one_slot_wide_full_height_and_no_longer_unplaced():
    card = _contract(L4)
    assert slot_width(card) == 1
    assert card["attrs"]["pcie-height"] == "full"
    assert "unplaced" not in card


def test_the_l4_seats_in_riser_1a_slot_1_and_needs_no_span():
    bays = _bays()
    assert L4 in bays["slot-1"]["accepts"]
    assert span_covers(bays["slot-1"], slot_width(_contract(L4))) == []


@pytest.mark.parametrize("refused", ["slot-2", "slot-3"])
def test_the_l4_is_refused_the_opening_with_no_connector_and_the_slot_outside_the_gpu_priority(refused):
    assert L4 not in _bays()[refused]["accepts"]


def test_no_low_profile_riser_takes_the_l4():
    """The L4 is modelled on its full-height bracket; the low-profile one is not
    drawn, so no low-profile slot may list it."""
    lp = [p for p in (LIB / "components").glob("*/*/v*/contract.yaml")
          if "-lp-" in p.parent.parent.name or p.parent.parent.name.endswith("-lp")]
    for path in lp:
        for bay in (load_yaml(path).get("bays") or {}).values():
            assert L4 not in (bay.get("accepts") or []), path


# --- the cards the R740xd's documents do not support stay out ----------------------

@pytest.mark.parametrize("ref", LEFT_OUT)
def test_a_card_over_the_300w_ceiling_is_seated_nowhere_and_says_why(ref):
    card = _contract(ref)
    assert card["attrs"]["power-draw-max-w"] > 300
    assert "300 W" in card["unplaced"]
    for path in (LIB / "components").glob("*/*/v*/contract.yaml"):
        for bay in (load_yaml(path).get("bays") or {}).values():
            assert ref not in (bay.get("accepts") or []), path
