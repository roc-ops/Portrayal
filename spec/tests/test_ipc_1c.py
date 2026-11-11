"""The ReadyLinks IPC-1C, a one-port coax client for the room end of a coax run.

A GL coax switch carries data and PoE over existing coax to clients in the
rooms. The IPC-1C is the smallest of them: one F-connector ReadyLink port, one
multi-gig Ethernet port, a USB-C power input, a system lamp and a reset button.
This module holds what is true of the library once it is modelled: the device
validates and exports as a box that takes no rack unit, a coax run lands on its F
port the way it lands on the GL-12xC's, a cable lands on its Ethernet port, and
the faces draw what the data sheet's figure and the maker's model show: the two
ends carry the ports, the two long sides the seam between cover and base, and the
underside the four rubber feet.
"""
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

NAME = "ipc-1c"
DIR = LIB / "devices/readylinks" / NAME


def _device():
    return yaml.safe_load((DIR / "device.yaml").read_text())


def _decor(face):
    return _device()["views"][face].get("panel", {}).get("decor", [])


def test_the_device_is_in_the_library_and_validates_against_the_schema():
    errors = list(Draft202012Validator(SCHEMA).iter_errors(_device()))
    assert not errors, [e.message for e in errors[:3]]


def test_it_is_a_box_that_takes_no_rack_unit():
    chassis = _device()["chassis"]
    assert chassis["mount"] != "rack"
    assert not any(key in chassis for key in ("ru", "full-depth", "overhang", "ears", "kits"))


def test_its_body_is_the_makers_model_and_the_data_sheets_overall_size_is_kept():
    dev = _device()
    chassis = dev["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (37.0, 29.1, 71.7)
    assert dev["attrs"]["physical"]["overall-dimensions"].startswith("30 x 37 x 85 mm")


def test_it_has_an_f_port_and_an_ethernet_port_and_nothing_else_that_carries_traffic():
    ports = [p for view in _device()["views"].values()
             for p in view.get("components", {}).get("placements", [])
             if p["ref"] in ("std/f-type@1", "common/rj45-eth@1")]
    assert sorted(p["ref"] for p in ports) == ["common/rj45-eth@1", "std/f-type@1"]


def test_the_coax_port_is_the_same_f_connector_the_gl_12xc_card_places():
    card = yaml.safe_load(
        (LIB / "components/readylinks/gl-x-lc-12xc/v1/contract.yaml").read_text())
    card_ref = next(p["ref"] for p in card["parts"] if p["id"] == "rl1")
    coax = next(p for view in _device()["views"].values()
                for p in view.get("components", {}).get("placements", [])
                if p["ref"] == card_ref)
    assert coax["ref"] == "std/f-type@1"
    assert coax["attrs"]["impedance"] == 75


def test_the_ethernet_port_is_stated_as_multi_gig():
    groups = _device()["groups"]
    assert any(g.get("attrs", {}).get("media") == "rj45" and g["attrs"].get("speed") == "2.5g"
               for g in groups.values())


def test_power_comes_in_over_usb_c_and_the_draw_is_the_data_sheets_3_w():
    dev = _device()
    usb = [p for view in dev["views"].values()
           for p in view.get("components", {}).get("placements", [])
           if p["ref"] == "std/usb-c@1"]
    assert len(usb) == 1
    assert dev["attrs"]["power"]["power-max-w"] == 3


def test_it_states_no_poe_standard_because_the_data_sheet_prints_none():
    power = _device()["attrs"]["power"]
    assert not any(key.startswith("poe-pd") for key in power)


def test_the_coax_end_and_the_ethernet_end_are_both_drawn():
    views = _device()["views"]
    for face in ("front", "rear"):
        assert views[face].get("components", {}).get("placements"), face


@pytest.mark.parametrize("face", ("left", "right"))
def test_each_long_side_draws_the_seam_between_cover_and_base(face):
    seams = [d for d in _decor(face) if d.get("kind") == "cover-base-seam"]
    assert len(seams) == 1, face
    seam = seams[0]
    # the cover is the top 14.0 mm of the 29.1 mm body and the base lip rises to 12.7
    assert 12.7 <= seam["at"][1] + seam["size"][1] / 2 <= 14.0
    assert seam["at"][0] == 0 and seam["size"][0] == 71.7


def test_the_underside_draws_four_rubber_feet_inside_the_footprint():
    feet = [d for d in _decor("bottom") if d.get("kind") == "rubber-foot"]
    assert len(feet) == 4
    for foot in feet:
        x, y = foot["at"]
        w, h = foot["size"]
        assert x >= 0 and y >= 0 and x + w <= 37.0 and y + h <= 71.7
    assert len({tuple(f["at"]) for f in feet}) == 4


def test_every_face_that_draws_nothing_says_why():
    views = _device()["views"]
    for name, view in views.items():
        drawn = (view.get("components", {}).get("placements")
                 or [d for d in view.get("panel", {}).get("decor", [])
                     if d.get("kind") in ("cover-base-seam", "rubber-foot")])
        assert drawn or view.get("empty"), f"{name} draws nothing and does not say why"


@pytest.mark.parametrize("vendor", ("netbox", "nautobot"))
def test_it_exports_with_no_rack_unit_and_is_not_full_depth(vendor):
    path = LIB / "exports" / vendor / "device-types/ReadyLinks/IPC-1C.yaml"
    exported = yaml.safe_load(path.read_text())
    assert exported["u_height"] == 0
    assert exported["is_full_depth"] is False
    assert exported["manufacturer"] == "ReadyLinks"
