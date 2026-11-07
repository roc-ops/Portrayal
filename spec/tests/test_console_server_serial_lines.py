"""The serial lines of the Opengear CM8000 and Vertiv ACS8000 console servers are console server ports.

Opengear's CM8000 Quick Start Guide gives the serial ports the default mode "Console Server"; Vertiv's
Installer/User Guide says the Console Access Server profile gives remote access to serial console ports. Each
device's own console jack (the CM8000's USB-C port, the ACS8000's RJ45 console) is a console port and stays one.
The DCIM exports list the serial lines as console server ports and not as interfaces.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# (maker folder, device, export folder, model, serial lines, the box's own console port)
DEVICES = [
    ("opengear", "cm8004", "Opengear", "CM8004", 4, {"name": "Console (USB-C)", "type": "usb-c"}),
    ("opengear", "cm8004-c", "Opengear", "CM8004-C", 4, {"name": "Console (USB-C)", "type": "usb-c"}),
    ("opengear", "cm8008", "Opengear", "CM8008", 8, {"name": "Console (USB-C)", "type": "usb-c"}),
    ("opengear", "cm8008-c", "Opengear", "CM8008-C", 8, {"name": "Console (USB-C)", "type": "usb-c"}),
    ("vertiv", "acs8008sac-400", "Vertiv", "ACS8008SAC-400", 8, {"name": "Console", "type": "rj-45"}),
    ("vertiv", "acs8016sac-400", "Vertiv", "ACS8016SAC-400", 16, {"name": "Console", "type": "rj-45"}),
    ("vertiv", "acs8032sac-400", "Vertiv", "ACS8032SAC-400", 32, {"name": "Console", "type": "rj-45"}),
    ("vertiv", "acs8048sac-400", "Vertiv", "ACS8048SAC-400", 48, {"name": "Console", "type": "rj-45"}),
]
IDS = [d[1] for d in DEVICES]


def device(maker, name):
    return yaml.safe_load((LIB / "devices" / maker / name / "device.yaml").read_text())


def serial_placements(dev):
    return [p for v in dev["views"].values() for p in (v.get("components") or {}).get("placements", [])
            if p.get("group") == "serial"]


def export(target, folder, model):
    return yaml.safe_load((LIB / "exports" / target / "device-types" / folder / f"{model}.yaml").read_text())


@pytest.mark.parametrize("maker,name,folder,model,lines,console", DEVICES, ids=IDS)
def test_the_serial_group_says_console_server_over_rj45_serial(maker, name, folder, model, lines, console):
    dev = device(maker, name)
    attrs = dev["groups"]["serial"]["attrs"]
    assert attrs["media"] == "rj45-serial" and attrs["role"] == "console-server"
    placed = serial_placements(dev)
    assert len(placed) == lines
    assert all((p.get("attrs") or {}).get("role", "console-server") == "console-server" for p in placed)


@pytest.mark.parametrize("maker,name,folder,model,lines,console", DEVICES, ids=IDS)
@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_each_serial_line_as_a_console_server_port(maker, name, folder, model, lines, console, target):
    doc = export(target, folder, model)
    ids = [p["id"] for p in serial_placements(device(maker, name))]
    assert [r["name"] for r in doc["console-server-ports"]] == ids
    assert {r["type"] for r in doc["console-server-ports"]} == {"rj-45"}
    assert not set(ids) & {i["name"] for i in doc.get("interfaces", [])}


@pytest.mark.parametrize("maker,name,folder,model,lines,console", DEVICES, ids=IDS)
def test_the_boxs_own_console_port_is_still_a_console_port(maker, name, folder, model, lines, console):
    doc = export("netbox", folder, model)
    assert doc["console-ports"] == [console]
