"""The Edgecore COR550 states its ears and its rail kit.

The quick start guide prints one figure for the rail, the position marked 630 mm on
the rear slide plate, and no range, so the kit's one configuration states a
`preset` and no `depth`, and a gap says the range is unknown. The device lists the
kit as shipped in the box and states its ears, so the generic ear is drawn when a
viewer asks and the device places no ear of its own.
"""
import pathlib

import pytest
import yaml

from portrayal import ears

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KIT_REF = "edgecore/cor550-rack-kit@1"
DEVICE = LIB / "devices/edgecore/cor550"
OWN_EAR_IDS = {"ear-left", "ear-right", "rear-ear-left", "rear-ear-right"}


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def _device():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def test_the_kit_is_a_telescoping_kit_with_a_preset_and_no_depth():
    kit = _contract(KIT_REF)
    assert kit["kind"] == "kit" and kit["motion"] == "telescoping"
    (config,) = kit["configurations"]
    assert config["preset"] == 630
    assert "depth" not in config


def test_the_kit_says_its_depth_range_is_a_gap_for_that_configuration():
    kit = _contract(KIT_REF)
    config_id = kit["configurations"][0]["id"]
    gaps = [g for g in kit["gaps"] if g["what"] == "depth"]
    assert gaps and config_id in gaps[0]["scope"]


def test_the_kits_parts_resolve_to_components():
    kit = _contract(KIT_REF)
    assert kit["parts"]
    for part in kit["parts"]:
        assert _contract(part["ref"])["kind"] == "component"


def test_the_device_lists_the_kit_as_in_the_box_and_states_its_ears():
    chassis = _device()["chassis"]
    assert {"ref": KIT_REF, "supply": "in-box"} in chassis["kits"]
    assert isinstance(chassis["ears"], dict)


@pytest.mark.parametrize("name", ["layout.yaml", "device.yaml"])
def test_the_device_places_no_ear_of_its_own(name):
    text = (DEVICE / name).read_text()
    assert "common/rack-ear" not in text
    assert "optional: ears" not in text
    for own in OWN_EAR_IDS:
        assert f"id: {own}," not in text


def test_the_generic_ear_is_drawn_for_it():
    plan = ears.plan(_device())
    assert plan is not None
    assert plan["h_body"] == 87.0 and plan["y"] == 0.25


def test_the_kits_provenance_carries_the_guides_630_sentence():
    text = " ".join(str(v) for v in _contract(KIT_REF)["provenance"].values())
    assert "630mm" in text and "rear slide plate" in text
