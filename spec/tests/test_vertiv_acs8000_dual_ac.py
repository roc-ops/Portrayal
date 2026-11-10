"""The Vertiv Avocent ACS8000 advanced console servers with dual AC power: the 16 and 48 port units.

Sources: the Avocent ACS8000 Advanced Console Server data sheet (AV-12339, 08/22) for the part numbers, the
dimensions and the power figures, the Installer/User Guide (Figure 1.1 and Table 1.1 show the dual power supply, and
section 2.2.1 the dual-supply note) and the maker's product photograph of the dual-AC front. No drawing is held, so
every position is an estimate and the tests hold the counts, the ids, the parts and the declarations, not a
coordinate; the one distance they hold is the pitch of the two inlet modules, read off the photograph.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/vertiv"
EXPORTS = LIB / "exports"

IN = 25.4

# device -> (model, serial ports)
MODELS = {
    "acs8016dac-400": ("ACS8016DAC-400", 16),
    "acs8048dac-400": ("ACS8048DAC-400", 48),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in d["views"][view]["components"].get("placements", [])}


@pytest.mark.parametrize("name", MODELS)
def test_the_device_is_the_part_number_the_data_sheet_orders(name):
    d = load(name)
    model, _ = MODELS[name]
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
def test_the_front_carries_two_inlets_each_with_its_own_power_switch(name):
    front = placements(load(name), "front")
    assert front["inlet-1"]["ref"] == front["inlet-2"]["ref"] == "std/c14-inlet@1"
    assert front["power-switch-1"]["ref"] == front["power-switch-2"]["ref"] == "vertiv/acs8000-rocker@1"
    assert front["power-switch-1"]["for"] == "inlet-1"
    assert front["power-switch-2"]["for"] == "inlet-2"
    assert [front[f"inlet-{n}"]["rel-pos"] for n in (1, 2)] == [1, 2]
    assert [front[f"power-switch-{n}"]["rel-pos"] for n in (1, 2)] == [1, 2]
    assert "inlet-3" not in front


@pytest.mark.parametrize("name", MODELS)
def test_the_second_inlet_module_stands_one_module_pitch_from_the_first(name):
    front = placements(load(name), "front")
    for part in ("inlet", "power-switch"):
        a, b = front[f"{part}-1"]["at"], front[f"{part}-2"]["at"]
        assert b[0] - a[0] == pytest.approx(24.1, abs=0.5), part
        assert b[1] == a[1], part
    assert front["inlet-2"]["rotate"] == front["inlet-1"]["rotate"]


@pytest.mark.parametrize("name", MODELS)
def test_the_inlets_and_switches_are_groups_of_two(name):
    d = load(name)
    members = {}
    for p in placements(d, "front").values():
        members.setdefault(p.get("group"), []).append(p["id"])
    assert len(members["inlets"]) == 2
    assert len(members["power-switches"]) == 2
    assert "two" in d["groups"]["inlets"]["description"]


@pytest.mark.parametrize("name", MODELS)
def test_the_front_keeps_the_sensor_jacks_six_usb_ports_and_the_sd_slot(name):
    front = placements(load(name), "front")
    assert front["digital-in"]["ref"] == front["sensor"]["ref"] == "std/rj45@2"
    assert sorted(i for i in front if i.startswith("usb-") and i != "usb-mark") == [f"usb-{n}" for n in range(1, 7)]
    assert front["card-slot"]["ref"] == "vertiv/sd-card-slot@1"


@pytest.mark.parametrize("name", MODELS)
def test_the_legend_beside_the_inlets_reads_two_entries(name):
    silk = load(name)["views"]["front"]["silkscreen"]
    texts = [s["text"] for s in silk if "text" in s]
    assert any(t.startswith("2X") for t in texts)
    assert not any(t.startswith("1X") for t in texts)


@pytest.mark.parametrize("name", MODELS)
def test_the_rear_carries_one_numbered_serial_port_for_each_port_the_model_has(name):
    d = load(name)
    _, ports = MODELS[name]
    rear = placements(d, "rear")
    serial = {i: p for i, p in rear.items() if p.get("group") == "serial"}
    assert sorted(p["rel-pos"] for p in serial.values()) == list(range(1, ports + 1))
    assert {"console", "lan-1", "lan-2", "fibre-1", "fibre-2", "led-status", "led-psu-1", "led-psu-2"} <= set(rear)
    assert d["groups"]["serial"]["attrs"]["media"] == "rj45-serial"


@pytest.mark.parametrize("name", MODELS)
def test_both_power_lamps_stand_for_a_supply_the_unit_has(name):
    rear = placements(load(name), "rear")
    states = {n: [s if isinstance(s, str) else s["name"] for s in rear[f"led-psu-{n}"]["states"]] for n in (1, 2)}
    assert states[1] == ["off", "power-supply-1-on"]
    assert states[2] == ["off", "power-supply-2-on"]


@pytest.mark.parametrize("name", MODELS)
def test_the_power_figures_are_the_data_sheets_and_say_there_are_two_entries(name):
    attrs = load(name)["attrs"]["power"]
    assert attrs["power-max-w"] == 28
    assert "two C14 inlets" in attrs["power-input"]
    assert "redundant" in attrs["psu-redundancy"]


@pytest.mark.parametrize("name", MODELS)
def test_the_faces_are_declared_estimated_and_say_the_method(name):
    prov = load(name)["provenance"]
    for key in ("method", "front-layout", "rear-layout", "port-numbering"):
        assert prov[key]["confidence"] == "estimated", key
    assert "photograph" in prov["method"]["note"]
    assert "dual-AC" in prov["method"]["note"]


@pytest.mark.parametrize("name", MODELS)
def test_which_inlet_is_supply_one_is_a_gap_because_no_document_says(name):
    gaps = {g["what"]: g for g in load(name)["gaps"]}
    assert gaps["supply-numbering"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("name", MODELS)
def test_each_device_type_is_exported_for_both_targets(name):
    model = MODELS[name][0]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Vertiv" / f"{model}.yaml"
        assert path.is_file(), path
        assert f"model: {model}" in path.read_text()
