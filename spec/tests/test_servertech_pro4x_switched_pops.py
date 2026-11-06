"""The Server Technology PRO4X Switched POPS 4G16A, a 0U rack PDU with 36 outlets.

What is true of the library once the device is in it: the maker and its HDOT Cx
outlet are registered, the device exists under its maker, its 36 outlets are 12
HDOT C13 and 24 HDOT Cx numbered as the unit prints them, each outlet runs through one
of six branch breakers, the controller carries two network jacks, and the HDOT Cx outlet exports as an `other` power outlet labelled
`HDOT Cx`.
"""
import pathlib

import yaml

from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "servertech" / "pro4x-switched-pops-4g16a" / "device.yaml"
COMPONENTS = ROOT / "library" / "components" / "servertech"
SCHEMAS = ROOT / "spec" / "schemas"

HDOT_CX = "servertech/hdot-cx-outlet"
C13 = "std/c13-outlet"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _device():
    return _load(DEVICE)


def _placements(dev):
    out = []
    for view in dev.get("views", {}).values():
        out.extend((view.get("components") or {}).get("placements") or [])
    return out


def _outlets(dev):
    return [p for p in _placements(dev) if p["ref"].split("@")[0] in (HDOT_CX, C13)]


def test_the_maker_and_the_outlet_key_are_registered():
    vendors = _load(SCHEMAS / "vendors.yaml")
    assert vendors["vendors"]["servertech"]["display"] == "Server Technology"
    connectors = (SCHEMAS / "connectors.yaml").read_text(encoding="utf-8")
    assert "servertech-hdot-cx:" in connectors


def test_the_hdot_cx_outlet_mates_a_c14_and_a_c20_plug():
    contract = _load(COMPONENTS / "hdot-cx-outlet" / "v1" / "contract.yaml")
    assert contract["interface"] == "servertech-hdot-cx"
    for plug in ("c14-plug", "c20-plug"):
        mates = _load(ROOT / "library" / "components" / "generic" / plug / "v1" / "contract.yaml")["mates"]
        assert "servertech-hdot-cx" in (mates if isinstance(mates, list) else [mates])


def test_the_outlets_are_twelve_c13_and_twenty_four_cx():
    refs = [p["ref"].split("@")[0] for p in _outlets(_device())]
    assert (refs.count(C13), refs.count(HDOT_CX)) == (12, 24)


def test_the_outlets_are_numbered_one_to_thirty_six_as_printed():
    ids = sorted(int(p["id"].rsplit("-", 1)[1]) for p in _outlets(_device()))
    assert ids == list(range(1, 37))


def test_every_outlet_runs_through_one_of_six_breakers():
    dev = _device()
    breakers = [p for p in _placements(dev) if p["ref"].startswith("servertech/pro4x-breaker")]
    assert len(breakers) == 6
    names = {b["id"] for b in breakers}
    for outlet in _outlets(dev):
        assert outlet["through"] in names, outlet["id"]
        assert outlet["states"] == ["on", "off"], outlet["id"]


def test_each_breaker_feeds_six_outlets():
    dev = _device()
    per = {}
    for outlet in _outlets(dev):
        per[outlet["through"]] = per.get(outlet["through"], 0) + 1
    assert sorted(per.values()) == [6] * 6


def test_the_controller_carries_two_network_jacks():
    contract = _load(COMPONENTS / "pro4x-controller" / "v1" / "contract.yaml")
    eth = [p for p in contract["parts"] if p.get("group") == "ethernet"]
    assert len(eth) == 2
    assert {p["ref"] for p in eth} == {"common/rj45-eth@1"}


def test_the_overall_length_is_the_drawings():
    dev = _device()
    assert dev["attrs"]["physical"]["length-mm"] == 1778.2
    assert dev["chassis"]["height"] == 1778.2


def test_the_hdot_cx_outlet_exports_as_other_labelled_hdot_cx():
    assert dx.PART_OUTLET[HDOT_CX] == "other"
    assert dx.OUTLET_LABEL[HDOT_CX] == "HDOT Cx"
