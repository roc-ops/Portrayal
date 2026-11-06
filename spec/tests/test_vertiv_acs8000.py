"""The Vertiv Avocent ACS8000 advanced console servers: the 8, 16, 32 and 48 port single-AC units.

Sources: the Avocent ACS8000 Advanced Console Server data sheet (AV-12339, 08/22) for the part numbers, the
dimensions and the power figures, the Quick Installation Guide and the Installer/User Guide for the callouts, the
lamps and the multi-protocol ports, the Rack Mounting Guide for the brackets, and the maker's product photographs
for both faces. No drawing is held, so every position is an estimate and the tests hold the counts, the ids, the
ports' roles and the declarations, not a coordinate.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/vertiv"
EXPORTS = LIB / "exports"

IN = 25.4
PITCH = 14.07
GUTTER = 6.24

# device -> (model, serial ports, columns in each run of jacks)
MODELS = {
    "acs8008sac-400": ("ACS8008SAC-400", 8, [4]),
    "acs8016sac-400": ("ACS8016SAC-400", 16, [4, 4]),
    "acs8032sac-400": ("ACS8032SAC-400", 32, [4, 4, 8]),
    "acs8048sac-400": ("ACS8048SAC-400", 48, [4, 4, 8, 8]),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in d["views"][view]["components"].get("placements", [])}


def contract(path):
    return yaml.safe_load((LIB / "components" / path / "contract.yaml").read_text())


@pytest.mark.parametrize("name", MODELS)
def test_the_device_is_the_part_number_the_data_sheet_orders(name):
    d = load(name)
    model, ports, _ = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "Vertiv"
    assert d["model"] == model
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", MODELS)
def test_the_body_is_the_data_sheets_17_25_by_9_5_by_1_75_inches(name):
    chassis = load(name)["chassis"]
    assert chassis["width"] == pytest.approx(17.25 * IN, abs=0.01)
    assert chassis["depth"] == pytest.approx(9.5 * IN, abs=0.01)
    assert chassis["height"] == pytest.approx(1.75 * IN, abs=0.01)
    assert chassis["ru"] == 1


@pytest.mark.parametrize("name", MODELS)
def test_the_rear_carries_one_numbered_serial_port_for_each_port_the_model_has(name):
    d = load(name)
    _, ports, _ = MODELS[name]
    serial = {i: p for i, p in placements(d, "rear").items() if p.get("group") == "serial"}
    assert sorted(p["rel-pos"] for p in serial.values()) == list(range(1, ports + 1))
    assert set(serial) == {f"serial-{n}" for n in range(1, ports + 1)}
    assert d["groups"]["serial"]["attrs"]["media"] == "rj45-serial"
    assert not [p for p in placements(d, "front").values() if p.get("group") == "serial"]


@pytest.mark.parametrize("name", MODELS)
def test_only_the_first_two_serial_ports_take_rs_422_and_rs_485(name):
    d = load(name)
    serial = placements(d, "rear")
    for n in range(1, MODELS[name][1] + 1):
        protocols = serial[f"serial-{n}"]["attrs"]["serial-protocols"]
        assert ("RS-485" in protocols) == (n <= 2), (n, protocols)
        assert "RS-232" in protocols


@pytest.mark.parametrize("name", MODELS)
def test_the_serial_jacks_stand_in_runs_with_a_gutter_between_them(name):
    d = load(name)
    _, ports, runs = MODELS[name]
    serial = placements(d, "rear")
    # the upper jack of each column is the odd port; read the columns off the odd ports
    xs = [serial[f"serial-{n}"]["at"][0] for n in range(1, ports + 1, 2)]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len(xs) == sum(runs)
    assert all(s in (PITCH, round(PITCH + GUTTER, 2)) for s in steps), steps
    assert steps.count(round(PITCH + GUTTER, 2)) == len(runs) - 1
    breaks = [i + 1 for i, s in enumerate(steps) if s != PITCH]
    expected, acc = [], 0
    for r in runs[:-1]:
        acc += r
        expected.append(acc)
    assert breaks == expected


@pytest.mark.parametrize("name", MODELS)
def test_the_rear_carries_the_console_the_lan_jacks_the_fibre_cages_and_two_usb_ports(name):
    rear = placements(load(name), "rear")
    console = rear["console"]
    assert console["attrs"]["role"] == "console" and console["attrs"]["media"] == "rj45-serial"
    assert rear["lan-1"]["ref"] == rear["lan-2"]["ref"] == "common/rj45-eth@1"
    assert rear["fibre-1"]["ref"] == rear["fibre-2"]["ref"] == "std/sfp@1"
    assert {rear["usb-rear-1"]["ref"], rear["usb-rear-2"]["ref"]} == {"std/usb-a@1"}
    assert {"led-status", "led-psu-1", "led-psu-2"} <= set(rear)


@pytest.mark.parametrize("name", MODELS)
def test_the_front_carries_the_inlet_the_sensor_jacks_six_usb_ports_and_the_sd_slot(name):
    front = placements(load(name), "front")
    assert front["inlet-1"]["ref"] == "std/c14-inlet@1"
    assert "inlet-2" not in front
    assert front["power-switch-1"]["for"] == "inlet-1"
    assert front["digital-in"]["ref"] == front["sensor"]["ref"] == "std/rj45@2"
    assert sorted(i for i in front if i.startswith("usb-") and i != "usb-mark") == [f"usb-{n}" for n in range(1, 7)]
    assert front["card-slot"]["ref"] == "vertiv/sd-card-slot@1"


@pytest.mark.parametrize("name", MODELS)
def test_the_faces_are_declared_estimated_and_say_the_method(name):
    prov = load(name)["provenance"]
    for key in ("method", "front-layout", "rear-layout", "port-numbering"):
        assert prov[key]["confidence"] == "estimated", key
    assert "photograph" in prov["method"]["note"]


def test_the_sd_card_slot_is_a_part_with_a_key_and_a_mate():
    slot = contract("vertiv/sd-card-slot/v1")
    card = contract("common/sd-card/v1")
    keys = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    assert slot["interface"] == "sd-card"
    assert card["mates"] == "sd-card"
    assert "sd-card" in keys
    assert slot["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert card["size-confidence"] == {"w": "estimated", "h": "estimated"}


def test_the_rocker_declares_its_size_as_estimated():
    rocker = contract("vertiv/acs8000-rocker/v1")
    assert rocker["class"] == "button"
    assert rocker["size-confidence"] == {"w": "estimated", "h": "estimated"}


def test_the_maker_is_registered():
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert vendors["vertiv"]["role"] == "hardware"


@pytest.mark.parametrize("name", MODELS)
def test_each_device_type_is_exported_for_both_targets(name):
    model = MODELS[name][0]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Vertiv" / f"{model}.yaml"
        assert path.is_file(), path
        assert f"model: {model}" in path.read_text()
