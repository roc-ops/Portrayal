"""The Server Technology PRO3X Basic 3A01, a 0U rack PDU with 36 outlets, two breakers and no controller.

What is true of the library once the device is in it: the device exists under its maker, its 36 outlets are
18 HDOT C13 and 18 HDOT Cx numbered 1 to 36 from the far end, the cord side breaker feeds outlets 19 to 36 and the far
one 1 to 18, each breaker states the two lines it sits across, the unit meters and switches nothing, and its fixed cord
exports as an `other` power port labelled as the IEC 60309 2P+E 6h plug.
"""
import pathlib

import yaml

from portrayal import dcim_export as dx
from portrayal import dcim_registers as dr

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "servertech" / "pro3x-basic-3a01" / "device.yaml"
COMPONENTS = ROOT / "library" / "components" / "servertech"

HDOT_CX = "servertech/hdot-cx-outlet"
C13 = "std/c13-outlet"
BREAKER = "servertech/pro3x-breaker-handle"
CORD = "servertech/pro3x-cord-60309-2pe"


def _device():
    return yaml.safe_load(DEVICE.read_text(encoding="utf-8"))


def _placements(dev):
    out = []
    for view in dev.get("views", {}).values():
        out.extend((view.get("components") or {}).get("placements") or [])
    return out


def _outlets(dev):
    return [p for p in _placements(dev) if p["ref"].split("@")[0] in (HDOT_CX, C13)]


def _breakers(dev):
    return [p for p in _placements(dev) if p["ref"].split("@")[0] == BREAKER]


def _number(placement):
    return int(placement["id"].rsplit("-", 1)[1])


def test_the_outlets_are_eighteen_c13_and_eighteen_cx():
    refs = [p["ref"].split("@")[0] for p in _outlets(_device())]
    assert (refs.count(C13), refs.count(HDOT_CX)) == (18, 18)


def test_the_outlets_are_numbered_one_to_thirty_six_from_the_far_end():
    assert sorted(_number(p) for p in _outlets(_device())) == list(range(1, 37))


def test_each_breaker_feeds_three_groups_of_six_outlets():
    dev = _device()
    names = {b["id"] for b in _breakers(dev)}
    assert names == {"breaker-1", "breaker-2"}
    for outlet in _outlets(dev):
        n = _number(outlet)
        assert outlet["through"] == ("breaker-2" if n > 18 else "breaker-1"), outlet["id"]


def test_each_breaker_states_the_two_lines_it_sits_across():
    for breaker in _breakers(_device()):
        assert len(breaker["lines"]) == 2, breaker["id"]
        assert breaker["lines"][0] != breaker["lines"][1], breaker["id"]


def test_the_unit_meters_and_switches_nothing():
    dev = _device()
    mgmt = dev["attrs"]["management"]
    assert mgmt["metering-scope"] == "none"
    assert mgmt["outlet-switching"] is False
    assert all("states" not in p for p in _outlets(dev))


def test_the_overall_length_is_the_drawings():
    dev = _device()
    assert dev["attrs"]["physical"]["length-mm"] == 1778.0
    assert dev["chassis"]["height"] == 1778.0


def test_the_input_is_a_single_phase_cord_that_exports_as_other():
    dev = _device()
    power = dev["attrs"]["power"]
    assert (power["input-phase"], power["input-cord"], power["input-voltage-v"]) == ("single", "fixed", 230)
    assert dx.PART_POWER[CORD] == "other"
    assert "2P+E 6h" in dr.POWER_LABEL[CORD]
    contract = yaml.safe_load((COMPONENTS / "pro3x-cord-60309-2pe" / "v1" / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["class"] == "inlet"
