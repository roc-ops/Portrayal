"""The ASR 9906's five rear fabric bays, and the fabric card they take.

Cisco's Overview and Reference Guide says the ASR 9906 holds five fabric cards (Table 13's
configuration row), and the IOS XR data sheet's System requirements table pairs the ASR 9906 with the
A99-SFC3-T. The chassis' rear elevation prints FC0 to FC4 under a cage of five slots. Five bays on
the rear face take that card, and no other bay of the chassis does.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
CHASSIS = LIBRARY / "devices/cisco/asr-9906/device.yaml"
COMPONENTS = LIBRARY / "components/cisco"

CARD = "cisco/a99-sfc3-t@2"
RETIRED = "cisco/a99-sfc3-t@1"


def contract(ref):
    name, major = ref.split("/")[1].split("@")
    return yaml.safe_load((COMPONENTS / name / f"v{major}/contract.yaml").read_text())


def device():
    return yaml.safe_load(CHASSIS.read_text())


def rear_bays():
    return device()["views"]["rear"]["components"]["bays"]


def test_the_rear_face_has_five_fabric_bays_that_take_the_card():
    bays = rear_bays()
    assert [b["id"] for b in bays] == [f"fc-{i}" for i in range(5)]
    for b in bays:
        assert b["accepts"] == [CARD], b["id"]
        assert b["group"] == "fabric"


def test_the_card_fills_its_bay_and_the_bays_do_not_overlap():
    size = contract(CARD)["size"]
    bays = sorted(rear_bays(), key=lambda b: b["at"][0])
    for b in bays:
        assert b["size"] == size, b["id"]
    for left, right in zip(bays, bays[1:]):
        assert left["at"][0] + left["size"]["w"] <= right["at"][0] + 1e-6, (left["id"], right["id"])


def test_no_other_bay_of_the_chassis_names_the_card():
    d = device()
    for view in d["views"].values():
        for b in view.get("components", {}).get("bays", []):
            if not b["id"].startswith("fc-"):
                assert CARD not in b["accepts"] and RETIRED not in b["accepts"], b["id"]


def test_the_card_that_is_seated_is_not_declared_unplaced():
    assert "unplaced" not in contract(CARD)


def test_the_first_major_is_kept_and_points_at_the_one_that_replaced_it():
    old = contract(RETIRED)
    assert old["superseded-by"] == CARD
    assert "unplaced" in old


def test_the_chassis_says_where_the_bays_come_from():
    entry = device()["provenance"]["fabric-bays"]
    assert entry["confidence"] == "drawing"
    assert "ASR-9906 Rear" in entry["note"] and "FC0" in entry["note"]


@pytest.mark.heavy
def test_the_chassis_is_locked():
    mine = [f for f in devicelock.check(LIBRARY) if f[0] == "cisco/asr-9906"]
    assert mine == []
