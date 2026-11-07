"""The Dell PowerEdge R740xd lists its three rail kits and the cable management arm.

The Dell rail sizing and rack compatibility matrix (Version 4.7, December 2023) prints one row
for the R740 and R740xd with three rails, B6, B4 and B13, and a range per hole type for each.
The R740/R740xd Technical Guide (July 2019) prints older figures for the same rails, and the
matrix is the newer. Each kit states the matrix's figures and its provenance names the guide's.
"""
import pathlib

import pytest
import yaml

from portrayal import ears

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices/dell/r740xd"
KITS = {
    "dell/b6-sliding-rail-kit@1": {
        "motion": "sliding", "install": "drop-in", "racks": ["4-post"],
        "depth": {"square": [631, 868], "round": [617, 861], "threaded": [631, 883]},
        "rail-depth": 714, "cma": 845,
    },
    "dell/b13-sliding-rail-kit@1": {
        "motion": "sliding", "install": "both", "racks": ["4-post"],
        "depth": {"square": [559, 931], "round": [559, 931], "threaded": [559, 931]},
        "rail-depth": 714, "cma": 845,
    },
    "dell/b4-static-rail-kit@1": {
        "motion": "fixed", "install": "stab-in", "racks": ["4-post", "2-post", "2-post-centre"],
        "depth": {"square": [608, 879], "round": [594, 872], "threaded": [610, 898]},
        "rail-depth": 622, "cma": None,
    },
}


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def _device():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


@pytest.mark.parametrize("ref", sorted(KITS))
def test_the_kit_states_the_matrix_ranges_per_hole_type(ref):
    want, kit = KITS[ref], _contract(ref)
    assert kit["kind"] == "kit"
    assert kit["motion"] == want["motion"] and kit["install"] == want["install"]
    (config,) = kit["configurations"]
    assert config["racks"] == want["racks"]
    assert config["depth"] == want["depth"]
    assert config["rail-depth"] == want["rail-depth"]


@pytest.mark.parametrize("ref", sorted(KITS))
def test_the_kit_says_which_figures_of_the_older_guide_it_replaced(ref):
    text = " ".join(str(v) for v in _contract(ref)["provenance"].values())
    assert "Version 4.7" in text and "July 2019" in text


@pytest.mark.parametrize("ref", sorted(KITS))
def test_the_cable_management_arm_is_an_accessory_only_of_the_sliding_kits(ref):
    accessories = _contract(ref).get("accessories") or []
    cma = [a for a in accessories if a["kind"] == "cma"]
    if KITS[ref]["cma"] is None:
        assert not cma
    else:
        (arm,) = cma
        assert arm["rail-depth"] == KITS[ref]["cma"]
        assert _contract(arm["ref"])["kind"] == "component"
    assert not [a for a in accessories if a["kind"] == "srb"]


def test_the_strain_relief_bar_is_a_stated_gap_on_each_sliding_kit():
    for ref in ("dell/b6-sliding-rail-kit@1", "dell/b13-sliding-rail-kit@1"):
        gaps = [g for g in _contract(ref)["gaps"] if g["what"] == "strain-relief-bar"]
        assert gaps and gaps[0]["reason"] == "vendor-silent"


@pytest.mark.parametrize("ref", sorted(KITS))
def test_every_part_of_a_kit_is_a_component_with_an_estimated_size(ref):
    kit = _contract(ref)
    assert kit["parts"]
    for part in kit["parts"]:
        contract = _contract(part["ref"])
        assert contract["kind"] == "component"
        assert set(contract["size-confidence"].values()) == {"estimated"}
    assert [g for g in kit["gaps"] if g["what"] == "part-dimensions"]


def test_the_device_lists_each_kit_once():
    refs = [k["ref"] for k in _device()["chassis"]["kits"]]
    assert sorted(refs) == sorted(KITS)


def test_the_device_places_no_ear_of_its_own_and_states_no_ear_position():
    # The drawn 482.6 mm face already holds the ears and the ports they carry, and no
    # source page gives a setback, so the device says nothing about where its ears bolt.
    assert "ears" not in _device()["chassis"]
    for name in ("layout.yaml", "device.yaml"):
        path = DEVICE / name
        if path.exists():
            assert "common/rack-ear" not in path.read_text()


def test_a_viewer_that_asks_for_ears_gets_no_second_pair_over_the_ports():
    assert ears.plan(_device()) is None
