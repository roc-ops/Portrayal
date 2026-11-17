"""The Server Technology PRO3X Smart 3C01, Switched 3F01 and Switched POPS 3G01, and their controller panel.

What is true of the library once they are in it: each device has the 36 outlets of the Basic 3A01 chassis.
Each has a bay for the controller between the banks.
The controller's seven jacks are modelled parts with interface keys.
Switched units declare on and off on every outlet. The Smart unit declares no outlet state.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "servertech"
CONTROLLER = ROOT / "library" / "components" / "servertech" / "pro3x-controller" / "v1" / "contract.yaml"

CASES = {
    "pro3x-smart-3c01": ("branch", False),
    "pro3x-switched-3f01": ("branch", True),
    "pro3x-switched-pops-3g01": ("outlet", True),
}
OUTLET_REFS = ("servertech/hdot-cx-outlet@1", "std/c13-outlet@1")


def _device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text(encoding="utf-8"))


def _outlets(dev):
    return [p for p in dev["views"]["front"]["components"]["placements"] if p["ref"] in OUTLET_REFS]


def test_each_device_has_thirty_six_outlets_numbered_from_the_far_end():
    for name in CASES:
        outlets = _outlets(_device(name))
        assert sorted(int(p["id"].rsplit("-", 1)[1]) for p in outlets) == list(range(1, 37)), name
        refs = [p["ref"] for p in outlets]
        assert (refs.count("std/c13-outlet@1"), refs.count("servertech/hdot-cx-outlet@1")) == (18, 18), name


def test_each_device_has_a_controller_bay_between_the_banks():
    for name in CASES:
        dev = _device(name)
        bay = dev["views"]["front"]["components"]["bays"][0]
        assert bay["accepts"] == ["servertech/pro3x-controller@1"], name
        assert dev["configurations"]["base"]["bays"] == {"controller": "servertech/pro3x-controller@1"}, name
        far = max(p["at"][1] for p in _outlets(dev) if int(p["id"].rsplit("-", 1)[1]) <= 18)
        near = min(p["at"][1] for p in _outlets(dev) if int(p["id"].rsplit("-", 1)[1]) > 18)
        assert far < bay["at"][1] and bay["at"][1] + bay["size"]["h"] < near, name


def test_capability_follows_the_family():
    for name, (scope, switching) in CASES.items():
        management = _device(name)["attrs"]["management"]
        assert management["metering-scope"] == scope, name
        assert management["outlet-switching"] is switching, name
        states = {tuple(p.get("states", ())) for p in _outlets(_device(name))}
        assert states == ({("on", "off")} if switching else {()}), name


def test_the_controller_jacks_are_modelled_parts():
    part = yaml.safe_load(CONTROLLER.read_text(encoding="utf-8"))
    refs = {p["id"]: p["ref"] for p in part["parts"]}
    assert refs == {
        "eth1": "common/rj45-eth@1",
        "eth2": "common/rj45-eth@1",
        "console": "std/rj45@2",
        "sensor": "std/rj45@2",
        "aux": "common/rj11-jack@1",
        "usb-a": "std/usb-a@1",
        "usb-b": "raritan/pxo-usb-b@1",
    }
