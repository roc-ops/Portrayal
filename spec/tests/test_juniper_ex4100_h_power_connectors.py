"""The EX4100-H pluggable connectors are places a wire lands, and the four supplies say where their wires do not.

The EX4100-H-12MP draws two five-position PSU connectors and a six-position dry contact alarm connector, and the
EX4100-H-24F and -24MP draw the same alarm connector. Each is a green pluggable screw-terminal block that ships
preassembled to the switch. This change makes each a connector that presents its registered key and gives each a part
that mates it:

  - juniper/ex4100-h-psu-connector@1 presents `terminal-381-5` and juniper/ex4100-h-psu-plug@1 mates it;
  - juniper/ex4100-h-alarm-connector@1 presents `terminal-350-6` and juniper/ex4100-h-alarm-plug@1 mates it;
  - each plug is a declared stand-in: no document held names a maker or a part number for either connector;
  - the printed marks of each connector are recorded in the contract's provenance, as roles, and no port is stated.

The four supplies of the EX4100-H-24F and -24MP draw no connector. The guide lands the wires on the power input terminals
on the front of the switch, so each supply says in its contract that no cable lands on it.

These read contracts and the registry. They read no library/dist and render nothing.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

CONNECTORS = {
    "juniper/ex4100-h-psu-connector@1": ("terminal-381-5", "juniper/ex4100-h-psu-plug@1"),
    "juniper/ex4100-h-alarm-connector@1": ("terminal-350-6", "juniper/ex4100-h-alarm-plug@1"),
}
SUPPLIES = [
    "juniper/ex4100-h-24f-dc-psu@1",
    "juniper/ex4100-h-24mp-dc-psu@1",
    "juniper/ex4100-h-jpsu-340w-ac@1",
    "juniper/ex4100-h-jpsu-90w-ac@1",
]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


def registry():
    return yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())


def test_each_connector_presents_its_registered_key_at_a_mate_point():
    keys = registry()["interfaces"]
    for ref, (key, _plug) in CONNECTORS.items():
        c = contract(ref)
        assert c["interface"] == key, ref
        assert key in keys, key
        assert "mate" in c["connection-points"], ref


def test_each_key_has_a_part_that_mates_it_and_says_it_is_a_stand_in():
    for ref, (key, plug) in CONNECTORS.items():
        p = contract(plug)
        assert p["class"] == "port", plug
        assert p["mates"] == key, plug
        assert "mate" in p["connection-points"], plug
        assert "STAND-IN" in str(p["provenance"]["part"]), plug
        assert "STAND-IN" in str(contract(ref)["provenance"]["part"]), ref


def test_the_connectors_record_the_printed_marks_as_roles_and_state_no_port():
    for ref in CONNECTORS:
        c = contract(ref)
        assert "roles" in c["provenance"], ref
        assert "dc" not in c and "ports" not in c, ref


def test_the_alarm_connector_says_it_carries_no_power():
    text = words(contract("juniper/ex4100-h-alarm-connector@1")["provenance"]["roles"]).lower()
    assert "no power" in text


def test_each_supply_says_no_cable_lands_on_it_and_where_the_wires_land():
    for ref in SUPPLIES:
        c = contract(ref)
        sentence = words(c["unmated"])
        assert len(sentence) >= 40, ref
        assert "front of the switch" in sentence, ref
        assert "parts" not in c, ref
