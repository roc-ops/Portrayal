"""The Smartoptics DCP-2 states its ears and its rack-mount kit.

The user manual (release 14.0 A, section 3.2) lists seven kit parts and a table of seven
rack-depth bands for a four-post rack. Six bands print two figures and are a `depth` range; the
first prints one, 600 mm, and is a `preset` with a gap for the missing range. A two-post rack
uses the mid-mount part alone, so it is an ear position that names the part and no depth band.
The ground terminal is on the front brackets, so those parts compose a stud.
"""
import pathlib

import pytest
import yaml

from portrayal import ears

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KIT_REF = "smartoptics/dcp-rack-kit@1"
DEVICE = LIB / "devices/smartoptics/dcp-2"
OWN_EAR_IDS = {"ear-left", "ear-right", "ear-left-r", "ear-right-r"}

# the manual's table, section 3.2.2.1: band id -> (depth, parts)
BANDS = {
    "rack-600": (None, ["front-600", "rear-42"]),
    "rack-600-700": ([600, 700], ["front-600", "rear-142"]),
    "rack-700-820": ([700, 820], ["front-700", "rear-142"]),
    "rack-800-900": ([800, 900], ["front-700", "extension-270", "rear-42"]),
    "rack-840-1000": ([840, 1000], ["front-700", "extension-270", "rear-142"]),
    "rack-1000-1100": ([1000, 1100], ["front-700", "extension-470", "rear-42"]),
    "rack-1100-1200": ([1100, 1200], ["front-700", "extension-470", "rear-142"]),
}
FRONT_PARTS = ("front-600", "front-700", "mid-mount")


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def _device():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def _parts():
    return {p["id"]: p for p in _contract(KIT_REF)["parts"]}


def test_the_kit_has_the_manuals_seven_parts_two_of_each():
    parts = _parts()
    assert sorted(parts) == sorted(
        ["front-600", "front-700", "extension-270", "extension-470", "rear-142", "rear-42", "mid-mount"])
    for p in parts.values():
        assert p["count"] == 2
        assert _contract(p["ref"])["kind"] == "component"


def test_the_kit_is_telescoping_and_has_one_configuration_for_each_band():
    kit = _contract(KIT_REF)
    assert kit["kind"] == "kit" and kit["motion"] == "telescoping"
    got = {c["id"]: c for c in kit["configurations"]}
    assert list(got) == list(BANDS)
    for cid, (depth, parts) in BANDS.items():
        c = got[cid]
        assert c["racks"] == ["4-post"] and c["parts"] == parts, cid
        if depth is None:
            assert c["preset"] == 600 and "depth" not in c
        else:
            assert c["depth"] == depth and "preset" not in c, cid


def test_the_one_figure_band_says_its_range_is_a_gap():
    kit = _contract(KIT_REF)
    gaps = [g for g in kit["gaps"] if g["what"] == "depth"]
    assert len(gaps) == 1 and gaps[0]["scope"] == ["rack-600"]


def test_the_mid_mount_part_is_in_no_four_post_band():
    kit = _contract(KIT_REF)
    for c in kit["configurations"]:
        assert "mid-mount" not in c["parts"]


@pytest.mark.parametrize("part", FRONT_PARTS)
def test_a_front_bracket_carries_the_ground_stud(part):
    contract = _contract(_parts()[part]["ref"])
    assert [(p["id"], p["ref"]) for p in contract["parts"]] == [("earth", "common/ground-stud@1")]
    assert "3.2.8" in contract["provenance"]["ground"] or "3.2.2.2" in contract["provenance"]["ground"]


@pytest.mark.parametrize("part", ["extension-270", "extension-470", "rear-142", "rear-42"])
def test_the_other_parts_carry_no_stud(part):
    assert not _contract(_parts()[part]["ref"]).get("parts")


def test_the_parts_the_manual_does_not_dimension_are_estimated_and_the_kit_says_so():
    kit = _contract(KIT_REF)
    for p in kit["parts"]:
        assert _contract(p["ref"])["size-confidence"] == {"w": "estimated", "h": "estimated"}
    gaps = [g for g in kit["gaps"] if g["what"] == "part-dimensions"]
    assert gaps and sorted(gaps[0]["scope"]) == sorted(_parts())


def test_the_device_lists_the_kit_as_in_the_box():
    assert {"ref": KIT_REF, "supply": "in-box"} in _device()["chassis"]["kits"]


def test_the_device_states_the_four_positions_and_the_mid_mount_part():
    ears_ = _device()["chassis"]["ears"]
    assert isinstance(ears_, dict)
    by_label = {p["label"]: p for p in ears_["positions"]}
    assert sorted(by_label) == ["chassis flush", "mid-mount", "recessed", "transponder flush"]
    for label in ("chassis flush", "transponder flush", "recessed"):
        assert by_label[label]["racks"] == ["4-post"] and "at" not in by_label[label]
    mid = by_label["mid-mount"]
    assert mid["racks"] == ["2-post"] and mid["part"] == {"kit": KIT_REF, "part": "mid-mount"}
    assert "at" not in mid


@pytest.mark.parametrize("name", ["device.yaml"])
def test_the_device_places_no_ear_of_its_own(name):
    text = (DEVICE / name).read_text()
    assert "common/rack-ear" not in text
    assert "optional: ears" not in text
    for own in OWN_EAR_IDS:
        assert f"id: {own}," not in text


def test_the_generic_ear_is_drawn_for_it():
    plan = ears.plan(_device())
    assert plan is not None and plan["h_body"] == 45.0


def test_the_device_says_the_setback_is_not_given():
    gaps = [g for g in _device()["gaps"] if g["what"] == "rack-ear-setback"]
    assert gaps and gaps[0]["reason"] == "vendor-silent"
    assert sorted(gaps[0]["scope"]) == ["front", "rear"]


def test_the_ground_terminal_gap_no_longer_says_the_ear_carries_none():
    text = yaml.safe_dump(_device()["gaps"])
    assert "carries no terminal" not in text
