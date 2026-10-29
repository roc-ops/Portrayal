"""The ASR 9000 4th-generation -SE line cards, and the chassis bays that now take them.

`cisco/a9k-16x100ge-se@1` (A9K-16X100GE-SE) and `cisco/a99-32x100ge-se@1` (A99-32X100GE-SE) were components no
chassis accepted. No held Cisco document names either part number beside a chassis, so the seating is an
INFERENCE: each card is accepted by exactly the line-card bays that accept its -TR sibling, whose own data sheet
row says which chassis take it (c78-741100 p4 for the 16-port; c78-741101 p4 for the 32-port). This module writes
the inference as a test, so a later reading of the -SE's own row shows up as a deliberate change here.

The slot counts are the Overview and Reference Guide's "Chassis Slots" (PDF pp29-31): ASR 9010 eight, 9006 four,
9904 two, 9906 four, 9910 eight, 9922 twenty, 9912 ten line-card slots, which take only line cards.
"""
import re
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICES = LIBRARY / "devices/cisco"
COMPONENTS = LIBRARY / "components/cisco"

SE16, TR16 = "cisco/a9k-16x100ge-se@1", "cisco/a9k-16x100ge-tr@1"
SE32, TR32 = "cisco/a99-32x100ge-se@1", "cisco/a99-32x100ge-tr@1"
FAN_V3 = "cisco/asr-9922-fan-v3@1"

# chassis -> (line-card bays that take the 16-port, line-card bays that take the 32-port, all bays, version)
CHASSIS = {
    "9006": (4, 0, 11, "3.3.0"),
    "9010": (8, 0, 18, "1.2.0"),
    "9904": (2, 2, 8, "3.3.0"),
    "9906": (4, 4, 6, "1.3.0"),
    "9910": (8, 8, 10, "1.3.0"),
    "9912": (10, 10, 31, "2.3.0"),   # 2.2.0 here, then 2.3.0 with the A99-SFC2 (fabric boards change)
    "9922": (20, 20, 49, "2.3.0"),
}
CARDS = {"a9k-16x100ge-se": (SE16, TR16, "1.1.0"), "a99-32x100ge-se": (SE32, TR32, "1.2.0")}


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def device(chassis):
    return yaml.safe_load((DEVICES / f"asr-{chassis}/device.yaml").read_text())


def bays(chassis):
    return device(chassis)["views"]["front"]["components"]["bays"]


def bays_accepting(chassis, ref):
    return [b for b in bays(chassis) if ref in b["accepts"]]


def class_of(ref):
    name, major = ref.split("/")[1].split("@")
    return yaml.safe_load((COMPONENTS / name / f"v{major}/contract.yaml").read_text())["class"]


def line_card_bays(chassis):
    """The bays that take a line card: any bay that accepts a component whose class is line-card."""
    return [b for b in bays(chassis) if any(class_of(r) == "line-card" for r in b["accepts"])]


@pytest.fixture(params=sorted(CHASSIS))
def chassis(request):
    return request.param


# ---- which chassis accept each card, exactly

def test_the_16_port_is_in_the_56_line_card_bays_of_the_seven_modular_chassis():
    counts = {c: len(bays_accepting(c, SE16)) for c in CHASSIS}
    assert counts == {"9006": 4, "9010": 8, "9904": 2, "9906": 4, "9910": 8, "9912": 10, "9922": 20}
    assert sum(counts.values()) == 56


def test_the_32_port_is_in_the_44_bays_of_the_five_9900_generation_chassis_and_not_the_9006_or_9010():
    counts = {c: len(bays_accepting(c, SE32)) for c in CHASSIS}
    assert counts == {"9006": 0, "9010": 0, "9904": 2, "9906": 4, "9910": 8, "9912": 10, "9922": 20}
    assert sum(counts.values()) == 44


def test_no_bay_that_is_not_a_line_card_bay_accepts_either_card(chassis):
    lc = {b["id"] for b in line_card_bays(chassis)}
    for ref in (SE16, SE32):
        for b in bays_accepting(chassis, ref):
            assert b["id"] in lc, (chassis, b["id"])
    # the RSP, RP, fabric, fan and power bays name no line card at all
    for b in bays(chassis):
        if b["id"] not in lc:
            assert SE16 not in b["accepts"] and SE32 not in b["accepts"]


# ---- the inference, written as a test: the -SE is where the -TR is, and the reverse

def test_every_bay_that_accepts_the_tr_sibling_accepts_the_se_and_the_reverse(chassis):
    for se, tr in ((SE16, TR16), (SE32, TR32)):
        assert [b["id"] for b in bays_accepting(chassis, se)] == [b["id"] for b in bays_accepting(chassis, tr)]


def test_the_9006_and_9010_do_not_name_the_32_port_because_its_tr_row_does_not():
    for c in ("9006", "9010"):
        assert not bays_accepting(c, TR32) and not bays_accepting(c, SE32)


# ---- nothing else about the bays moved

def test_the_card_envelope_is_the_one_every_bay_that_takes_it_is_sized_for(chassis):
    for ref in (SE16, SE32):
        for b in bays_accepting(chassis, ref):
            # the 9006 and 9904 lay their cards flat and rotate the bay, which swaps w and h
            assert sorted(b["size"].values()) == [41.4, 395.7]
            assert b["default"] == "cisco/a9k-slot-cover@1"
    for name in CARDS:
        assert contract(name)["size"]["w"] == 41.4 and contract(name)["size"]["h"] == 395.7


def test_each_chassis_keeps_its_bay_count(chassis):
    assert len(bays(chassis)) == CHASSIS[chassis][2]


def test_the_9922_fan_bays_still_accept_only_the_v3_fan_tray():
    fans = [b for b in bays("9922") if b.get("group") == "fan-trays"]
    assert len(fans) == 4
    assert all(b["accepts"] == [FAN_V3] for b in fans)


def test_each_se_list_keeps_the_order_the_lists_already_had(chassis):
    for b in line_card_bays(chassis):
        refs = b["accepts"]
        if SE16 in refs:
            assert refs.index(SE16) == refs.index(TR16) - 1


# ---- the contracts

@pytest.mark.parametrize("name", sorted(CARDS))
def test_the_contract_is_no_longer_unplaced_and_says_the_seating_is_inferred(name):
    c = contract(name)
    assert "unplaced" not in c
    note = c["provenance"]["chassis-compatibility"]
    assert note.startswith("estimated")
    assert "INFERRED" in note and "overrides" in note
    sheet = "c78-741100" if name.startswith("a9k") else "c78-741101"
    assert sheet in note


@pytest.mark.parametrize("name", sorted(CARDS))
def test_the_contract_versions_are_the_minors_the_lock_asked_for(name):
    assert contract(name)["version"] == CARDS[name][2]


CLAIM = re.compile(r"\bCisco (?:states|stated|says|said|names|named|confirms|lists)\b", re.I)


def test_no_note_says_cisco_names_the_se():
    notes = [contract(n)["provenance"]["chassis-compatibility"] for n in CARDS]
    for c in CHASSIS:
        notes.append(device(c)["provenance"]["se-line-card-seating"]["note"])
    for note in notes:
        assert not CLAIM.search(note)
        assert "INFERRED" in note


def test_each_chassis_note_is_estimated_and_names_the_sibling_sheet_and_the_guide_pages(chassis):
    entry = device(chassis)["provenance"]["se-line-card-seating"]
    assert entry["confidence"] == "estimated"
    assert "c78-741100" in entry["note"] and "pp29-31" in entry["note"]
    assert "c78-741101" in entry["note"]
    # the 9006 and 9010 say the 32-port is NOT accepted; the others name it among the two cards seated
    assert ("A99-32X100GE-SE is not accepted" in entry["note"]) == (CHASSIS[chassis][1] == 0)


def test_the_counts_the_notes_state_are_the_counts_the_bays_have():
    words = {"9006": "four", "9010": "eight", "9904": "two", "9906": "four", "9910": "eight", "9912": "ten",
             "9922": "twenty"}
    for c, w in words.items():
        assert f"the {w} line card slots" in device(c)["provenance"]["se-line-card-seating"]["note"], c
        assert len(line_card_bays(c)) == CHASSIS[c][0]
    assert "56 bays" in contract("a9k-16x100ge-se")["provenance"]["chassis-compatibility"]
    assert "44 bays" in contract("a99-32x100ge-se")["provenance"]["chassis-compatibility"]


# ---- power: the guide's Table 35 row "(-SE)" prints no part number, so it is not joined

@pytest.mark.parametrize("name", sorted(CARDS))
def test_power_stays_absent_and_the_tr_figure_is_not_copied(name):
    attrs = contract(name)["attrs"]
    assert attrs["power-absent"] == "not-published"
    assert not any(k.startswith("power-draw") for k in attrs)


# ---- the lock

def test_each_chassis_is_at_the_minor_the_lock_asked_for_and_the_lock_agrees(chassis):
    assert device(chassis)["version"] == CHASSIS[chassis][3]
    mine = [f for f in devicelock.check(LIBRARY) if f[0] == f"cisco/asr-{chassis}"]
    assert mine == []


def test_the_two_components_are_locked_too():
    mine = [f for f in devicelock.check(LIBRARY) if f[0] in {f"cisco/{n}" for n in CARDS}]
    assert mine == []
