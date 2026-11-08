"""The Vertiv Avocent ACS800 serial console: the ACS804MEAC-400, the one model its data sheet orders.

The model is read from the data sheet's size and ports, the installer guide's callouts, the mounting guide
and the maker's front and rear photographs, with the rear of the eight-port unit pictured on the data sheet.
The rear of the four-port unit is not photographed, so its jacks take the positions the eight-port picture
gives the first four, and the device says so. The Digital Out header is a part of its own (the library holds
no four-position header on a pitch a document states), and a plug mates it.
"""
import pathlib

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
DEVICE = LIB / "devices/vertiv/acs804meac-400/device.yaml"
KEY = "screw-terminal-4-relay"
HEADER = "vertiv/acs800-digital-out@1"
PLUG = "vertiv/acs800-digital-out-plug@1"
IN_TO_MM = 25.4


def _load(p):
    return yaml.safe_load(pathlib.Path(p).read_text())


def _contract(ref):
    name, major = ref.split("@")
    return _load(LIB / "components" / name / f"v{major}" / "contract.yaml")


def _device():
    return _load(DEVICE)


def _placements(view):
    return _device()["views"][view]["components"]["placements"]


def _by_group(view, group):
    return [p for p in _placements(view) if p.get("group") == group]


def test_the_device_is_the_one_model_the_data_sheet_orders():
    d = _device()
    assert d["manufacturer"] == "Vertiv"
    assert d["model"] == "ACS804MEAC-400"
    assert d["configurations"]["base"]["part-numbers"] == {"ACS804MEAC-400": {}}


def test_the_chassis_is_the_data_sheets_size_and_has_no_rack_units():
    c = _device()["chassis"]
    assert c["width"] == pytest.approx(8.374 * IN_TO_MM, abs=0.05)
    assert c["depth"] == pytest.approx(7.156 * IN_TO_MM, abs=0.05)
    assert c["height"] == pytest.approx(1.161 * IN_TO_MM, abs=0.05)
    assert c["mount"] == "desktop"
    assert "ru" not in c


def test_all_six_faces_are_drawn_or_say_why_not():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for name in ("top", "bottom", "left", "right"):
        assert views[name].get("empty"), name


def test_the_front_carries_the_ports_the_photograph_shows():
    ids = {p["id"] for p in _placements("front")}
    assert {"modem", "digital-in", "digital-out", "sensor"} <= ids
    assert len(_by_group("front", "usb")) == 4
    assert {"led-status", "led-power"} <= ids


def test_the_rear_carries_the_power_jack_console_lan_and_four_serial_ports():
    ids = {p["id"] for p in _placements("rear")}
    assert {"power-in", "console", "lan-1", "lan-2"} <= ids
    serial = _by_group("rear", "serial")
    assert sorted(p["rel-pos"] for p in serial) == [1, 2, 3, 4]
    refs = {p["id"]: p["ref"] for p in _placements("rear")}
    assert refs["power-in"] == "common/dc-barrel@1"


def test_the_power_jack_states_the_twelve_volts_the_data_sheet_gives():
    jack = next(p for p in _placements("rear") if p["id"] == "power-in")
    assert jack["attrs"]["input-voltage"] == 12


def test_the_digital_out_header_presents_a_registered_key_and_a_plug_mates_it():
    keys = _load(SPEC / "schemas/connectors.yaml")
    assert KEY in keys["interfaces"]
    assert _contract(HEADER)["interface"] == KEY
    assert _contract(PLUG)["mates"] == KEY
    digital_out = next(p for p in _placements("front") if p["id"] == "digital-out")
    assert digital_out["ref"] == HEADER


def test_the_new_parts_declare_what_no_document_gives():
    for ref in (HEADER, PLUG):
        c = _contract(ref)
        assert c["size-confidence"], ref
        text = " ".join(str(v) for v in c["provenance"].values())
        assert "STAND-IN" in text or "ESTIMATE" in text.upper(), ref


def test_the_two_weights_the_guide_and_the_data_sheet_give_are_a_gap_and_no_weight_is_stated():
    d = _device()
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["weight"]["reason"] == "sources-disagree"
    assert "weight" not in d["attrs"].get("physical", {})
