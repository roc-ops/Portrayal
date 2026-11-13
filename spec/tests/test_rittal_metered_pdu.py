"""The seven Rittal DK 7979 metered PDUs and the controller they share.

What is true of the library: each device is the strip its dimensioned drawing gives. It takes the outlets its
maker's table counts, on the parts the library holds. It carries the controller of the PDU metered, with three RJ45
jacks, one RJ12 jack, one USB-A port and the two small headers. Its input is the fixed 16 A CEE cord and it has no
breaker. Every lamp states what it shows. Reads the device and component sources only; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

C13, C19 = "std/c13-outlet@1", "std/c19-outlet@1"
CORD_3P, CORD_1P = "rittal/pdu-cord-cee-16a@1", "rittal/pdu-cord-cee-16a-1p@1"

# sku -> (length mm, C13, C19, cord, the span between the two rear buttons)
DEVICES = {
    "210": (845, 12, 1, CORD_1P, 622.3),
    "230": (845, 0, 9, CORD_3P, 622.3),
    "235": (1094, 18, 3, CORD_3P, 933.45),
    "236": (1494, 24, 6, CORD_3P, 1244.6),
    "238": (1696, 18, 12, CORD_3P, 1555.75),
    "240": (1895, 36, 6, CORD_3P, 1600.2),
    "242": (1696, 42, 0, CORD_3P, 1555.75),
}
SKUS = sorted(DEVICES)


def _device(sku):
    return yaml.safe_load((LIB / "devices" / "rittal" / f"dk-7979-{sku}" / "device.yaml").read_text())


def _placements(sku, view="front"):
    return _device(sku)["views"][view]["components"]["placements"]


def _by_id(sku):
    return {p["id"]: p for p in _placements(sku)}


@pytest.mark.parametrize("sku", SKUS)
def test_the_device_is_new_and_the_strip_the_drawing_gives(sku):
    device = _device(sku)
    length = DEVICES[sku][0]
    assert device["name"] == f"dk-7979-{sku}" and device["model"] == f"DK 7979.{sku}"
    assert device["version"] == "0.1.0" and device["maturity"] == "modelled"
    chassis = device["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (44, length, 72.1)
    assert chassis["mount"] == "rack-side"
    assert device["views"]["front"]["size"] == {"w": 44, "h": length}


@pytest.mark.parametrize("sku", SKUS)
def test_every_face_is_stated(sku):
    views = _device(sku)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert views[face].get("empty"), f"{face} states neither parts nor why it is empty"


@pytest.mark.parametrize("sku", SKUS)
def test_the_outlets_are_the_ones_the_maker_counts(sku):
    _, c13, c19, _, _ = DEVICES[sku]
    outlets = [p for p in _placements(sku) if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == Counter({k: v for k, v in {C13: c13, C19: c19}.items() if v})
    assert all(p["fed-by"] == "input" for p in outlets)
    ys = [p["at"][1] for p in outlets]
    assert ys == sorted(ys, reverse=True), "outlets count from the foot, the highest y"


@pytest.mark.parametrize("sku", SKUS)
def test_the_input_is_the_fixed_16_a_cord_and_there_is_no_breaker(sku):
    cord = DEVICES[sku][3]
    placements = _placements(sku)
    assert [p["ref"] for p in placements if p["id"] == "input"] == [cord]
    power = _device(sku)["attrs"]["power"]
    assert power["input-cord"] == "fixed" and power["input-current-a"] == 16
    assert not [p for p in placements if "breaker" in p["ref"] or "breaker" in p["id"]]


@pytest.mark.parametrize("sku", SKUS)
def test_the_controller_carries_three_rj45_one_rj12_one_usb_and_two_headers(sku):
    by_id = _by_id(sku)
    refs = Counter(p["ref"] for p in by_id.values())
    assert refs["common/rj45-eth@1"] == 2 and refs["std/rj45@2"] == 1
    assert refs["common/rj11-jack@1"] == 1
    assert refs["common/usb-a@2"] == 1
    assert refs["rittal/pdu-controller@1"] == 1
    assert refs["rittal/pdu-digital-input@1"] == 1 and refs["rittal/pdu-alarm-relay@1"] == 1
    assert {"eth1", "eth2", "can", "rs232", "usb", "digital-input", "alarm-relay"} <= set(by_id)


@pytest.mark.parametrize("sku", SKUS)
def test_every_lamp_states_what_it_shows(sku):
    lamps = [p for p in _placements(sku) if p["ref"].startswith("common/led-")]
    assert {p["id"] for p in lamps} == {"lamp-power", "lamp-status", "lamp-can-green", "lamp-can-red"}
    for lamp in lamps:
        assert "states" in lamp, f"{lamp['id']} states nothing"
    by_id = _by_id(sku)
    assert by_id["can"]["attrs"]["media"] == "rj45-telemetry", "the CAN jack must not export as Ethernet"
    for jack in ("eth1", "eth2"):
        assert set(by_id[jack]["states"]) == {"led-a", "led-b"}


@pytest.mark.parametrize("sku", SKUS)
def test_the_two_buttons_are_the_dimensioned_span_apart(sku):
    buttons = [p for p in _placements(sku, "rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - DEVICES[sku][4]) < 0.5


@pytest.mark.parametrize("sku", SKUS)
def test_the_front_is_tiled_end_to_end_by_the_cells(sku):
    length = DEVICES[sku][0]
    cell_kinds = {"end-cap", "spacer", "phase-plate", "controller-cell"}
    decor = [d for d in _device(sku)["views"]["front"]["panel"]["decor"] if d["kind"] in cell_kinds]
    edge = 0.0
    for cell in sorted(decor, key=lambda d: d["at"][1]):
        assert abs(cell["at"][1] - edge) < 0.15, f"{cell['id']} leaves a gap or overlaps"
        edge = cell["at"][1] + cell["size"][1]
    assert abs(edge - length) < 0.15


def test_the_controller_part_carries_no_port():
    contract = yaml.safe_load((LIB / "components" / "rittal" / "pdu-controller" / "v1" / "contract.yaml").read_text())
    assert contract["version"] == "1.0.0" and "parts" not in contract
    assert {"esc", "up", "enter", "down", "display", "reset"} <= set(contract["elements"])


def test_the_two_headers_share_the_registered_key_and_their_plugs_mate_it():
    registry = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())
    entry = next(v for k, v in _flatten(registry).items() if k == "pdu-io-header")
    assert "claims none" in entry["note"] and "unmated" not in entry
    for name in ("pdu-digital-input", "pdu-alarm-relay"):
        path = LIB / "components" / "rittal" / name / "v1" / "contract.yaml"
        assert yaml.safe_load(path.read_text())["interface"] == "pdu-io-header"
        plug = LIB / "components" / "rittal" / f"{name}-plug" / "v1" / "contract.yaml"
        assert yaml.safe_load(plug.read_text())["mates"] == "pdu-io-header"


def _flatten(node, out=None):
    out = {} if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict) and "note" in v:
                out[k] = v
            _flatten(v, out)
    return out
