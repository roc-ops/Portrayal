"""The Vertiv Geist VP8841, a unit-level monitored vertical rack PDU with an L6-30P cord.

What is true of the library once the device is in it. It is a 1778 mm strip, 51 mm wide and deep.
Thirty-six C13 and six C19 outlets sit on its front, in two circuits that each run through one breaker.
A monitoring module with two Ethernet jacks and a four-digit display sits between the circuits.
The fixed cord exports as a power port of type other.
"""
import pathlib
import xml.etree.ElementTree as ET

import yaml

from portrayal import dcim_export as dx
from portrayal import dcim_registers as dr

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "vertiv" / "vp8841" / "device.yaml"
COMPONENTS = ROOT / "library" / "components"

C13 = "std/c13-outlet"
C19 = "std/c19-outlet"
CORD = "vertiv/rpdu-cord-l6-30p-round"
BREAKER = "vertiv/rpdu-magnetic-breaker-2p"
MODULE = "vertiv/geist-imd"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contract(ref):
    ns, name = ref.split("/")
    return _load(COMPONENTS / ns / name / "v1" / "contract.yaml")


def _base(ref):
    return ref.split("@")[0]


def _placements():
    return _load(DEVICE)["views"]["front"]["components"]["placements"]


def _of(ref):
    return [p for p in _placements() if _base(p["ref"]) == ref]


def test_the_device_is_a_1778_mm_strip_with_all_six_faces():
    dev = _load(DEVICE)
    assert dev["manufacturer"] == "Vertiv" and dev["model"] == "VP8841"
    chassis = dev["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (50.8, 1778.0, 50.8)
    assert set(dev["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
    assert list(dev["configurations"]["base"]["part-numbers"]) == ["VP8841"]


def test_the_front_carries_the_outlets_the_data_sheet_counts():
    assert len(_of(C13)) == 36
    assert len(_of(C19)) == 6
    for p in _of(C13) + _of(C19):
        assert 0 <= p["at"][0] and p["at"][0] + 36 <= 50.8, p["id"]
        assert 0 <= p["at"][1] and p["at"][1] + 28 <= 1778.0, p["id"]


def test_each_breaker_feeds_eighteen_c13_and_three_c19():
    breakers = _of(BREAKER)
    assert len(breakers) == 2
    outlets = _of(C13) + _of(C19)
    for b in breakers:
        fed = [p for p in outlets if p["through"] == b["id"]]
        assert sum(_base(p["ref"]) == C13 for p in fed) == 18, b["id"]
        assert sum(_base(p["ref"]) == C19 for p in fed) == 3, b["id"]


def test_every_outlet_is_fed_by_the_fixed_cord_and_carries_no_switch_state():
    cords = _of(CORD)
    assert len(cords) == 1
    for p in _of(C13) + _of(C19):
        assert p["fed-by"] == cords[0]["id"], p["id"]
        assert "states" not in p, p["id"]


def test_the_cord_is_an_l6_30p_that_exports_as_other():
    contract = _contract(CORD)
    assert contract["class"] == "inlet"
    assert contract["attrs"]["plug"] == "nema-l6-30p"
    assert dx.PART_POWER[CORD] == "other"
    assert "L6-30P" in dr.POWER_LABEL[CORD]
    assert _load(DEVICE)["attrs"]["power"]["input-plug"] == "other"


def test_the_exports_carry_the_cord_as_a_labelled_power_port_of_type_other():
    for tool in ("netbox", "nautobot"):
        path = ROOT / "library" / "exports" / tool / "device-types" / "Vertiv" / "VP8841.yaml"
        ports = _load(path)["power-ports"]
        assert [(p["name"], p["type"], p["label"]) for p in ports] == [("input", "other", "NEMA L6-30P")], tool


def test_the_pdu_meters_its_branches_and_switches_no_outlet():
    management = _load(DEVICE)["attrs"]["management"]
    assert management["metering-scope"] == "branch"
    assert management["outlet-switching"] is False


def test_the_breaker_part_switches_and_each_export_outlet_names_its_breaker():
    """The contract carries no rating, so the rating is the device's text. The states and the exported links are behaviour."""
    contract = _contract(BREAKER)
    assert contract["class"] == "breaker"
    assert contract["elements"]["button"]["class"] == "breaker"
    assert contract["elements"]["button"]["states"] == ["on", "off"]
    dev = _load(DEVICE)
    assert "20 A double-pole" in dev["attrs"]["power"]["breakers"]
    for tool in ("netbox", "nautobot"):
        path = ROOT / "library" / "exports" / tool / "device-types" / "Vertiv" / "VP8841.yaml"
        outlets = _load(path)["power-outlets"]
        said = [o.get("description", "") for o in outlets]
        assert len(outlets) == 42, tool
        assert said.count("Through breaker-1") == 21, tool
        assert said.count("Through breaker-2") == 21, tool


def _skin_rects():
    skin = COMPONENTS / "vertiv" / "geist-imd" / "v1" / "skins" / "default.svg"
    root = ET.fromstring(skin.read_text(encoding="utf-8"))
    return [e for e in root.iter() if e.tag.endswith("rect")]


def _luma(colour):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_the_module_draws_a_black_square_at_each_end():
    squares = [r for r in _skin_rects() if r.get("fill") == "#050505"]
    assert len(squares) == 2
    height = _contract(MODULE)["size"]["h"]
    (a, b) = sorted(squares, key=lambda r: float(r.get("y")))
    assert (a.get("x"), a.get("width"), a.get("height")) == (b.get("x"), b.get("width"), b.get("height"))
    top = float(a.get("y")) + float(a.get("height")) / 2
    bottom = float(b.get("y")) + float(b.get("height")) / 2
    assert abs(top - (height - bottom)) < 0.3
    assert top < 10 and bottom > height - 10


def test_the_module_plate_is_no_lighter_than_the_body():
    plate = [r for r in _skin_rects() if r.get("id") == "plate"][0]
    body = _load(DEVICE)["chassis"]["color"]
    assert _luma(plate.get("fill")) <= _luma(body)


def test_the_module_has_two_ethernet_jacks_a_four_digit_display_and_three_buttons():
    contract = _contract(MODULE)
    assert contract["kind"] == "module"
    jacks = [p for p in contract["parts"] if _base(p["ref"]) == "common/rj45-eth"]
    assert len(jacks) == 2
    assert sorted(_base(p["ref"]) for p in contract["parts"] if p["group"] == "peripheral") == [
        "common/rj11-jack", "std/rj45", "std/usb-a"]
    window = contract["elements"]["display"]
    assert window["class"] == "display" and window["characters"] == 4
    digits = [k for k in contract["elements"] if k.startswith("digit-")]
    assert len(digits) == 4
    buttons = [k for k, v in contract["elements"].items() if v.get("class") == "button"]
    assert len(buttons) == 3


def test_the_device_places_the_module_in_a_bay():
    dev = _load(DEVICE)
    bays = dev["views"]["front"]["components"]["bays"]
    assert [b["default"] for b in bays] == [MODULE + "@1"]
    assert dev["configurations"]["base"]["bays"]["module"] == MODULE + "@1"
