"""The UfiSpace 771 mm adjustable mounting rail is a sliding kit that seventeen devices list.

Each device's own hardware installation guide prints the same rail in its accessory list:
771 x 44 x 22 mm, for a rack depth of 22 to 33 inches. The guide gives the depth in inches
only, so the kit states it converted at 25.4 mm to the inch, and it says the rail is pulled
out "fully extended" without a figure, so the kit's travel is `full`. No guide dimensions a
member of the rail, so the kit is one part and says so in a gap. The devices list the kit as
shipped in the box and state no ears.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KIT_REF = "ufispace/adjustable-rail-771-kit@1"
RAIL_REF = "ufispace/adjustable-rail-771@1"
DEVICES = [
    "s9710-76d", "s9700-23d", "s9700-53dx", "s9705-48d", "s9720-56ed", "s9725-64e",
    "s9600-28dx", "s9600-30dx", "s9600-32x", "s9600-56dx", "s9600-64x",
    "s9610-36d", "s9610-46dx", "s9610-48dx", "s9611-36d",
    "s9321-64e", "s9321-64eo",
]


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def _device(slug):
    return yaml.safe_load((LIB / "devices/ufispace" / slug / "device.yaml").read_text())


def test_the_kit_is_a_sliding_kit_with_full_travel():
    kit = _contract(KIT_REF)
    assert kit["kind"] == "kit"
    assert kit["motion"] == "sliding" and kit["travel"] == "full"


def test_the_one_configuration_is_four_post_with_the_guides_range_in_millimetres():
    kit = _contract(KIT_REF)
    (config,) = kit["configurations"]
    assert config["id"] == "four-post" and config["racks"] == ["4-post"]
    assert config["depth"] == [558.8, 838.2]
    assert "preset" not in config
    assert round(22 * 25.4, 1) == config["depth"][0]
    assert round(33 * 25.4, 1) == config["depth"][1]


def test_the_kit_is_two_sets_of_one_rail_part():
    kit = _contract(KIT_REF)
    (part,) = kit["parts"]
    assert part["ref"] == RAIL_REF and part["count"] == 2
    assert kit["configurations"][0]["parts"] == [part["id"]]


def test_the_rail_part_carries_the_size_the_guide_prints():
    rail = _contract(RAIL_REF)
    assert rail["kind"] == "component" and rail["class"] == "mount"
    assert rail["size"] == {"w": 22.0, "h": 44.0, "d": 771.0}
    assert set(rail["size-confidence"].values()) == {"datasheet"}


def test_the_kit_says_no_member_is_dimensioned():
    kit = _contract(KIT_REF)
    gaps = [g for g in kit["gaps"] if g["what"] == "part-dimensions"]
    assert gaps and kit["parts"][0]["id"] in gaps[0]["scope"]
    assert all(g["what"] != "depth" for g in kit["gaps"])


def test_the_kits_provenance_names_the_conversion_the_members_and_the_travel_sentence():
    text = " ".join(str(v) for v in _contract(KIT_REF)["provenance"].values())
    assert "25.4 mm to the inch" in text and "558.8" in text and "838.2" in text
    assert "inner rail" in text and "middle rail" in text and "outer rail" in text
    assert "fully extended" in text


@pytest.mark.parametrize("slug", DEVICES)
def test_the_device_lists_the_kit_as_in_the_box(slug):
    chassis = _device(slug)["chassis"]
    assert {"ref": KIT_REF, "supply": "in-box"} in chassis["kits"]
    assert "depth" not in chassis["kits"][0]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_device_states_no_ears_and_places_none(slug):
    text = (LIB / "devices/ufispace" / slug / "device.yaml").read_text()
    assert "ears" not in _device(slug)["chassis"]
    assert "common/rack-ear" not in text
    assert "optional: ears" not in text
