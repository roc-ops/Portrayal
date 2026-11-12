"""The Vertiv Geist VP9562, a 1U basic rack PDU with ten NEMA 5-15R outlets.

What is true of the library once the device is in it: the device exists under its
maker and is a 1U box, its ten outlets are in one row on the rear on one pitch, each
a 5-15R fed by the input and run through the one breaker on the front, the fixed cord
is a 5-15P that exports as that power type, and the PDU neither meters nor switches.
"""
import pathlib

import yaml

from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "vertiv" / "vp9562" / "device.yaml"
COMPONENTS = ROOT / "library" / "components"

OUTLET = "std/nema-5-15r"
CORD = "vertiv/rpdu-cord-5-15p"
BREAKER = "vertiv/rpdu-thermal-breaker"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _device():
    return _load(DEVICE)


def _contract(ref):
    ns, name = ref.split("/")
    return _load(COMPONENTS / ns / name / "v1" / "contract.yaml")


def _placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def _base(ref):
    return ref.split("@")[0]


def _outlets(dev):
    return [p for p in _placements(dev, "rear") if _base(p["ref"]) == OUTLET]


def test_the_device_is_a_one_u_box_with_all_six_faces():
    dev = _device()
    assert dev["manufacturer"] == "Vertiv" and dev["model"] == "VP9562"
    chassis = dev["chassis"]
    assert chassis["ru"] == 1
    assert abs(chassis["height"] - 44.45) < 0.01
    assert abs(chassis["depth"] - 3.75 * 25.4) < 0.1
    assert set(dev["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
    assert list(dev["configurations"]["base"]["part-numbers"]) == ["VP9562"]


def test_ten_outlets_are_in_one_row_on_the_rear_on_one_pitch():
    outlets = _outlets(_device())
    by_id = {int(p["id"].rsplit("-", 1)[1]): p for p in outlets}
    assert sorted(by_id) == list(range(1, 11))
    assert len({p["at"][1] for p in outlets}) == 1
    steps = [round(by_id[n + 1]["at"][0] - by_id[n]["at"][0], 2) for n in range(1, 10)]
    assert len(set(steps)) == 1, steps
    assert not any(_base(p["ref"]) == OUTLET for p in _placements(_device(), "front"))


def test_every_outlet_is_fed_by_the_input_and_runs_through_the_one_breaker():
    dev = _device()
    breakers = [p for p in _placements(dev, "front") if _base(p["ref"]) == BREAKER]
    assert len(breakers) == 1
    inputs = [p for p in _placements(dev, "rear") if _base(p["ref"]) == CORD]
    assert len(inputs) == 1
    for outlet in _outlets(dev):
        assert outlet["fed-by"] == inputs[0]["id"], outlet["id"]
        assert outlet["through"] == breakers[0]["id"], outlet["id"]
        assert "states" not in outlet, outlet["id"]


def test_the_outlet_is_a_5_15r_and_the_cord_a_fixed_5_15p():
    assert _contract(OUTLET)["interface"] == "nema-5-15r"
    cord = _contract(CORD)
    assert cord["attrs"]["plug"] == "nema-5-15p"
    assert cord["class"] == "inlet"
    power = _device()["attrs"]["power"]
    assert power["input-cord"] == "fixed"
    assert power["input-plug"] == "nema-5-15p"
    assert power["input-voltage-v"] == 120 and power["input-current-a"] == 15


def test_the_breaker_is_a_fifteen_amp_thermal_breaker():
    contract = _contract(BREAKER)
    assert contract["class"] == "breaker"
    assert contract["elements"]["button"]["states"] == ["on", "off"]
    assert "15A Thermal Breaker" in contract["provenance"]["rating"]


def test_the_pdu_neither_meters_nor_switches():
    management = _device()["attrs"]["management"]
    assert management["outlet-switching"] is False
    assert management["metering-scope"] == "none"


def test_the_cord_exports_as_a_nema_5_15p_power_port():
    assert dx.PART_POWER[CORD] == "nema-5-15p"
