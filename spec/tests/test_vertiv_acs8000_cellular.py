"""The Vertiv Avocent ACS8000 cellular console servers with dual AC power: the 8, 16, 32 and 48 port LN units.

Sources: the Avocent ACS8000 Advanced Console Server data sheet (AV-12339, 08/22) for the part numbers, the
dimensions, the power figures and the cellular type, the Installer/User Guide (Figure 1.1 and Table 1.1: the
cellular antennas, the SIM card slot, the dual power supply) and the maker's product photograph of the cellular
front. No drawing is held and the antennas stand in front of both antenna jacks in the photograph, so every
position is an estimate and the tests hold the counts, the ids, the parts, the order along the face, the
declarations and loose bounds on the two jacks (no exact coordinate).
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
    "acs8008-ln-dac-400": ("ACS8008-LN-DAC-400", 8),
    "acs8016-ln-dac-400": ("ACS8016-LN-DAC-400", 16),
    "acs8032-ln-dac-400": ("ACS8032-LN-DAC-400", 32),
    "acs8048-ln-dac-400": ("ACS8048-LN-DAC-400", 48),
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
    assert "AT&T" in d["description"]


@pytest.mark.parametrize("name", MODELS)
def test_the_body_is_the_data_sheets_17_25_by_9_5_by_1_75_inches(name):
    chassis = load(name)["chassis"]
    assert chassis["width"] == pytest.approx(17.25 * IN, abs=0.01)
    assert chassis["depth"] == pytest.approx(9.5 * IN, abs=0.01)
    assert chassis["height"] == pytest.approx(1.75 * IN, abs=0.01)
    assert chassis["ru"] == 1


@pytest.mark.parametrize("name", MODELS)
def test_the_front_carries_two_antenna_jacks_that_are_sma(name):
    d = load(name)
    front = placements(d, "front")
    for jack in ("aux", "cell"):
        assert front[jack]["ref"] == "std/sma@1", jack
        assert front[jack]["group"] == "antennas", jack
    assert [front[j]["rel-pos"] for j in ("aux", "cell")] == [1, 2]
    assert d["groups"]["antennas"]["attrs"]["media"] == "coax-sma"
    assert "antenna" not in {p["ref"].split("/")[-1].split("@")[0] for p in front.values()}


@pytest.mark.parametrize("name", MODELS)
def test_the_aux_jack_is_over_the_first_usb_column_and_the_cell_jack_over_the_sd_slot(name):
    front = placements(load(name), "front")
    usb, sd = front["usb-1"]["at"], front["card-slot"]["at"]
    assert abs(front["aux"]["at"][0] + 3.175 - (usb[0] + 6.0)) < 4.0
    assert front["aux"]["at"][1] < usb[1]
    assert front["cell"]["at"][0] > front["usb-6"]["at"][0]
    assert abs(front["cell"]["at"][0] + 3.175 - (sd[0] + 12.6)) < 6.0
    assert front["cell"]["at"][1] < sd[1]


@pytest.mark.parametrize("name", MODELS)
def test_the_front_keeps_the_dual_ac_face(name):
    front = placements(load(name), "front")
    assert front["inlet-1"]["ref"] == front["inlet-2"]["ref"] == "std/c14-inlet@1"
    assert front["power-switch-1"]["ref"] == front["power-switch-2"]["ref"] == "vertiv/acs8000-rocker@1"
    assert "inlet-3" not in front
    assert front["digital-in"]["ref"] == front["sensor"]["ref"] == "std/rj45@2"
    assert sorted(i for i in front if i.startswith("usb-") and i != "usb-mark") == [f"usb-{n}" for n in range(1, 7)]
    assert front["card-slot"]["ref"] == "vertiv/sd-card-slot@1"


@pytest.mark.parametrize("name", MODELS)
def test_the_front_prints_cellular_under_the_product_name_and_two_entries_in_the_legend(name):
    texts = [s["text"] for s in load(name)["views"]["front"]["silkscreen"] if "text" in s]
    assert "CELLULAR" in texts
    assert "AUX" in texts and "CELL" in texts
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
def test_the_power_figures_are_the_data_sheets_and_say_there_are_two_entries(name):
    attrs = load(name)["attrs"]["power"]
    assert attrs["power-max-w"] == 28
    assert "two C14 inlets" in attrs["power-input"]
    assert "redundant" in attrs["psu-redundancy"]


@pytest.mark.parametrize("name", MODELS)
def test_the_cellular_type_is_the_data_sheets_and_names_the_bands_of_the_ln_models(name):
    note = load(name)["attrs"]["features"]["cellular"]
    assert "4G/LTE Cat.4" in note
    assert "2FF" in note
    assert "B2, B4, B5, B12, B13" in note


@pytest.mark.parametrize("name", MODELS)
def test_the_faces_are_declared_estimated_and_say_the_method(name):
    prov = load(name)["provenance"]
    for key in ("method", "front-layout", "rear-layout", "port-numbering"):
        assert prov[key]["confidence"] == "estimated", key
    assert "photograph" in prov["method"]["note"]
    assert "antenna" in prov["front-layout"]["note"]


@pytest.mark.parametrize("name", MODELS)
def test_what_no_held_page_gives_is_a_named_gap(name):
    gaps = {g["what"]: g for g in load(name)["gaps"]}
    assert {"antennas", "sim-slot", "supply-numbering"} <= set(gaps)
    assert gaps["sim-slot"]["scope"] == ["top"]
    assert gaps["supply-numbering"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("name", MODELS)
def test_each_device_type_is_exported_for_both_targets(name):
    model = MODELS[name][0]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Vertiv" / f"{model}.yaml"
        assert path.is_file(), path
        assert f"model: {model}" in path.read_text()


@pytest.mark.parametrize("name", MODELS)
def test_only_the_jacks_horizontal_position_is_claimed_as_measured(name):
    prov = load(name)["provenance"]
    assert "not a measurement" in prov["method"]["note"]
    gap = {g["what"]: g for g in load(name)["gaps"]}["antennas"]["note"]
    assert "not a measurement" in gap


@pytest.mark.parametrize("name", MODELS)
def test_the_quick_installation_guide_step_is_cited_and_the_certification_names_its_edition(name):
    d = load(name)
    assert "Quick Installation Guide page 2, step 10" in d["provenance"]["sources"]["note"]
    assert "APAC edition" in d["attrs"]["compliance"]["certification"]
