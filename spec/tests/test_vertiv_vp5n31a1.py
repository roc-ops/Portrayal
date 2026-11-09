"""The Vertiv PowerIT VP5N31A1, a 1U switched rack PDU with twelve combination outlets.

What is true of the library once the device is in it: the combination outlet's
connector key is registered and a C14 or a C20 plug mates it, the device exists under
its maker, its twelve outlets are on the rear in two groups of six on one pitch,
numbered as the unit prints them, each fed by the input and run through one of two
breakers on the front, the monitoring module sits in a bay on the front with its
jacks, the box is the size the maker's table gives, and the outlet and the input
cord export as `other` power types with a label.
"""
import pathlib

import yaml

from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "vertiv" / "vp5n31a1" / "device.yaml"
COMPONENTS = ROOT / "library" / "components"
SCHEMAS = ROOT / "spec" / "schemas"

COMBO = "vertiv/combo-outlet"
CORD = "vertiv/rpdu-cord-l6-30p"
BREAKER = "vertiv/rpdu-breaker"
CARD = "vertiv/imd-5m"
KEY = "vertiv-combo"


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
    return [p for p in _placements(dev, "rear") if _base(p["ref"]) == COMBO]


def test_the_combination_outlet_key_is_registered_and_mated():
    connectors = _load(SCHEMAS / "connectors.yaml")["interfaces"]
    assert KEY in connectors
    assert _contract(COMBO)["interface"] == KEY
    for plug in ("c14-plug", "c20-plug"):
        mates = _contract(f"generic/{plug}")["mates"]
        assert KEY in (mates if isinstance(mates, list) else [mates])


def test_the_device_is_a_one_u_box_of_the_tables_size():
    dev = _device()
    assert dev["manufacturer"] == "Vertiv" and dev["model"] == "VP5N31A1"
    chassis = dev["chassis"]
    assert abs(chassis["height"] - 1.72 * 25.4) < 0.1
    assert abs(chassis["width"] - 17 * 25.4) < 0.1
    assert abs(chassis["depth"] - 12 * 25.4) < 0.1
    assert chassis["ru"] == 1
    assert set(dev["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


def test_twelve_combination_outlets_are_on_the_rear_numbered_as_printed():
    outlets = _outlets(_device())
    ids = sorted(int(p["id"].rsplit("-", 1)[1]) for p in outlets)
    assert ids == list(range(1, 13))
    assert not any(_base(p["ref"]) == COMBO for p in _placements(_device(), "front"))


def test_each_group_of_six_is_on_one_pitch():
    by_id = {int(p["id"].rsplit("-", 1)[1]): p["at"][0] for p in _outlets(_device())}
    for first in (1, 7):
        steps = [round(by_id[n + 1] - by_id[n], 2) for n in range(first, first + 5)]
        assert len(set(steps)) == 1, steps
    assert round(by_id[2] - by_id[1], 2) == round(by_id[8] - by_id[7], 2)


def test_every_outlet_is_fed_by_the_input_and_runs_through_a_breaker():
    dev = _device()
    breakers = [p for p in _placements(dev, "front") if _base(p["ref"]) == BREAKER]
    assert len(breakers) == 2
    names = {b["id"] for b in breakers}
    inputs = [p for p in _placements(dev, "rear") if _base(p["ref"]) == CORD]
    assert len(inputs) == 1
    for outlet in _outlets(dev):
        assert outlet["fed-by"] == inputs[0]["id"], outlet["id"]
        assert outlet["through"] in names, outlet["id"]
        assert outlet["states"] == ["on", "off"], outlet["id"]


def test_each_breaker_feeds_six_outlets():
    per = {}
    for outlet in _outlets(_device()):
        per[outlet["through"]] = per.get(outlet["through"], 0) + 1
    assert sorted(per.values()) == [6, 6]


def test_every_outlet_has_a_lamp_on_the_front():
    dev = _device()
    lamps = [p for p in _placements(dev, "front") if p.get("group") == "outlet-leds"]
    assert len(lamps) == len(_outlets(dev)) == 12


def test_the_monitoring_module_sits_in_a_bay_with_its_jacks():
    dev = _device()
    bays = dev["views"]["front"]["components"]["bays"]
    assert [b["default"] for b in bays] == [CARD + "@1"]
    parts = _contract(CARD)["parts"]
    refs = [_base(p["ref"]) for p in parts]
    assert refs.count("common/rj45-eth") == 2
    assert "common/rj11-jack" in refs and "std/usb-a" in refs and "std/rj45" in refs


def test_the_input_cord_is_fixed_and_the_ears_are_not_drawn():
    dev = _device()
    assert dev["attrs"]["power"]["input-cord"] == "fixed"
    assert dev["attrs"]["power"]["input-plug"] == "other"
    for view in dev["views"].values():
        for p in (view.get("components") or {}).get("placements") or []:
            assert _base(p["ref"]) != "common/rack-ear"


def test_the_outlet_and_the_cord_export_as_other_with_a_label():
    assert dx.PART_OUTLET[COMBO] == "other"
    assert dx.OUTLET_LABEL[COMBO] == "Vertiv combination C13/C19"
    assert dx.PART_POWER[CORD] == "other"
    assert dx.POWER_LABEL[CORD] == "NEMA L6-30P"
