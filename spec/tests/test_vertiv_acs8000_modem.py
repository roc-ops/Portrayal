"""The Vertiv Avocent ACS8000 dual-AC units with a built-in modem: the 8, 16, 32 and 48 port units.

Sources: the Avocent ACS8000 Advanced Console Server data sheet (AV-12339, 08/22). It gives the part numbers, the
dimensions and the power figures. The Installer/User Guide gives Figure 1.1 and Table 1.1: callout 3, the modem port.
The Quick Installation Guide shows the phone line that reaches the modem jack.

No photograph of a modem unit is held, so the modem jack is read off the guide's figure. The tests hold the counts,
the ids, the parts, the order along the face, the declarations and loose bounds on the jack. They hold no exact
coordinate.
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
MODEM = {
    "acs8008mdac-400": ("ACS8008MDAC-400", 8),
    "acs8016mdac-400": ("ACS8016MDAC-400", 16),
    "acs8032mdac-400": ("ACS8032MDAC-400", 32),
    "acs8048mdac-400": ("ACS8048MDAC-400", 48),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in d["views"][view]["components"].get("placements", [])}


@pytest.mark.parametrize("name", MODEM)
def test_the_device_is_the_part_number_the_data_sheet_orders(name):
    d = load(name)
    model, _ = MODEM[name]
    assert d["name"] == name
    assert d["manufacturer"] == "Vertiv"
    assert d["model"] == model
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", MODEM)
def test_the_unit_says_it_has_a_built_in_modem(name):
    d = load(name)
    assert "modem" in d["description"]
    assert "analog modem" in d["configurations"]["base"]["description"]
    assert "V.92" in d["attrs"]["features"]["modem"]


@pytest.mark.parametrize("name", MODEM)
def test_the_body_is_the_data_sheets_17_25_by_9_5_by_1_75_inches(name):
    chassis = load(name)["chassis"]
    assert chassis["width"] == pytest.approx(17.25 * IN, abs=0.01)
    assert chassis["depth"] == pytest.approx(9.5 * IN, abs=0.01)
    assert chassis["height"] == pytest.approx(1.75 * IN, abs=0.01)
    assert chassis["ru"] == 1


@pytest.mark.parametrize("name", MODEM)
def test_the_front_carries_one_rj45_modem_jack_right_of_the_sd_slot(name):
    d = load(name)
    front = placements(d, "front")
    modem = front["modem"]
    assert modem["ref"] == "std/rj45@2"
    assert modem["group"] == "modem"
    assert modem["attrs"]["function"] == "modem"
    assert d["groups"]["modem"]["role"] == "management"
    assert modem["at"][0] > front["card-slot"]["at"][0] + 30.0
    assert modem["at"][0] + 16.0 < d["chassis"]["width"]
    assert modem["at"][1] == front["digital-in"]["at"][1]
    assert sum(1 for p in front.values() if p.get("group") == "modem") == 1


@pytest.mark.parametrize("name", MODEM)
def test_the_front_has_no_antenna_jack_and_no_cellular_word(name):
    d = load(name)
    front = placements(d, "front")
    assert "aux" not in front and "cell" not in front
    assert "antennas" not in d["groups"]
    texts = [s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s]
    assert "CELLULAR" not in texts
    assert "Avocent ACS8000" in texts


@pytest.mark.parametrize("name", MODEM)
def test_the_front_keeps_the_dual_ac_face(name):
    d = load(name)
    front = placements(d, "front")
    assert front["inlet-1"]["ref"] == front["inlet-2"]["ref"] == "std/c14-inlet@1"
    assert front["power-switch-1"]["ref"] == front["power-switch-2"]["ref"] == "vertiv/acs8000-rocker@1"
    assert "inlet-3" not in front
    assert front["digital-in"]["ref"] == front["sensor"]["ref"] == "std/rj45@2"
    assert sorted(i for i in front if i.startswith("usb-") and i != "usb-mark") == [f"usb-{n}" for n in range(1, 7)]
    assert front["card-slot"]["ref"] == "vertiv/sd-card-slot@1"
    texts = [s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s]
    assert any(t.startswith("2X") for t in texts)


@pytest.mark.parametrize("name", MODEM)
def test_the_rear_carries_one_numbered_serial_port_for_each_port_the_model_has(name):
    d = load(name)
    _, ports = MODEM[name]
    rear = placements(d, "rear")
    serial = {i: p for i, p in rear.items() if p.get("group") == "serial"}
    assert sorted(p["rel-pos"] for p in serial.values()) == list(range(1, ports + 1))
    assert {"console", "lan-1", "lan-2", "fibre-1", "fibre-2", "led-status", "led-psu-1", "led-psu-2"} <= set(rear)
    assert d["groups"]["serial"]["attrs"]["media"] == "rj45-serial"


@pytest.mark.parametrize("name", MODEM)
def test_the_power_figures_are_the_data_sheets_and_say_there_are_two_entries(name):
    attrs = load(name)["attrs"]["power"]
    assert attrs["power-max-w"] == 28
    assert "two C14 inlets" in attrs["power-input"]
    assert "redundant" in attrs["psu-redundancy"]


@pytest.mark.parametrize("name", MODEM)
def test_the_faces_are_declared_estimated_and_say_the_method(name):
    prov = load(name)["provenance"]
    for key in ("method", "front-layout", "rear-layout", "port-numbering"):
        assert prov[key]["confidence"] == "estimated", key
    assert "photograph" in prov["method"]["note"]


@pytest.mark.parametrize("name", MODEM)
def test_the_modem_jack_is_read_off_the_guide_figure_and_says_so(name):
    d = load(name)
    assert "figure 1.1" in d["provenance"]["method"]["note"].lower()
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"modem-photograph", "supply-numbering"} <= set(gaps)
    assert gaps["modem-photograph"]["scope"] == ["front"]
    assert gaps["supply-numbering"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("name", MODEM)
def test_the_lamps_note_gives_the_sampled_colours_and_says_they_are_drawn_dark(name):
    note = load(name)["provenance"]["lamps"]["note"]
    assert "#206700" in note and "#858585" in note
    assert "drawn dark" in note


@pytest.mark.parametrize("name", MODEM)
def test_each_device_type_is_exported_for_both_targets(name):
    model = MODEM[name][0]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Vertiv" / f"{model}.yaml"
        assert path.is_file(), path
        assert f"model: {model}" in path.read_text()


@pytest.mark.parametrize("name", MODEM)
def test_the_export_lists_the_modem_jack(name):
    model = MODEM[name][0]
    text = (EXPORTS / "netbox" / "device-types" / "Vertiv" / f"{model}.yaml").read_text()
    assert "modem" in text.lower()
