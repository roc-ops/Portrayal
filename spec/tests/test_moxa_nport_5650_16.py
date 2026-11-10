"""The Moxa NPort 5650-16 and 5650-16-T serial device servers are in the library: six faces and their parts.

The two share one body and one rear: an AC inlet with a rocker switch, one LAN jack and sixteen RJ45 serial ports in two groups of
eight. They differ on the front. The standard-temperature unit has an LCD and four push buttons, which the wide-temperature unit
does not. Each figure the documents do not give is declared an estimate in the contract or the provenance that carries it.

These read the library and the registry and render nothing; they read no library/dist, except the device-type exports.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
VENDORS = ROOT / "spec" / "schemas" / "vendors.yaml"

MODELS = {"nport-5650-16": "NPort 5650-16", "nport-5650-16-t": "NPort 5650-16-T"}
NEW_PARTS = ["moxa/nport-5600-lcm", "moxa/nport-5600-keys", "moxa/nport-5600-power-rocker"]


def device(slug):
    return yaml.safe_load((LIB / "devices" / "moxa" / slug / "device.yaml").read_text())


def contract(name):
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


def placements(dev, view):
    return {p["id"]: p for p in dev["views"][view]["components"].get("placements", [])}


def test_moxa_is_a_registered_maker_with_its_source():
    entry = yaml.safe_load(VENDORS.read_text())["vendors"]["moxa"]
    assert entry["display"] == "Moxa" and entry["role"] == "hardware" and entry["source"]


@pytest.mark.parametrize("slug,model", MODELS.items())
def test_the_body_is_the_one_the_data_sheet_dimensions(slug, model):
    d = device(slug)
    assert d["manufacturer"] == "Moxa" and d["model"] == model
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (440, 45.5, 198.25)
    for face, size in {"front": (440, 45.5), "rear": (440, 45.5), "top": (440, 198.25),
                       "bottom": (440, 198.25), "left": (198.25, 45.5), "right": (198.25, 45.5)}.items():
        assert (d["views"][face]["size"]["w"], d["views"][face]["size"]["h"]) == size, face


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_has_sixteen_numbered_serial_ports_and_one_lan_jack(slug):
    d = device(slug)
    rear = placements(d, "rear")
    ports = [p for p in rear.values() if p.get("group") == "serial"]
    assert len(ports) == 16
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 17))
    assert d["groups"]["serial"]["role"] == "traffic"
    assert d["groups"]["serial"]["attrs"]["media"] == "rj45-serial"
    assert {p["attrs"]["role"] for p in ports} == {"console-server"}
    assert rear["lan"]["group"] == "lan" and d["groups"]["lan"]["role"] == "management"


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_carries_an_ac_inlet_with_its_switch_and_a_ground_screw(slug):
    rear = placements(device(slug), "rear")
    assert rear["inlet"]["ref"] == "std/c14-inlet@1"
    assert rear["power-switch"]["ref"] == "moxa/nport-5600-power-rocker@1" and rear["power-switch"]["for"] == "inlet"
    assert "ground" in rear


def test_only_the_standard_temperature_front_has_the_lcd_and_keys():
    std, wide = placements(device("nport-5650-16"), "front"), placements(device("nport-5650-16-t"), "front")
    assert std["lcm"]["ref"] == "moxa/nport-5600-lcm@1" and std["keys"]["ref"] == "moxa/nport-5600-keys@1"
    assert "lcm" not in wide and "keys" not in wide


@pytest.mark.parametrize("slug", MODELS)
def test_each_front_has_two_lamps_per_serial_port_and_the_system_lamps(slug):
    front = placements(device(slug), "front")
    assert {i for i in front if i.startswith("led-tx-")} == {f"led-tx-{n}" for n in range(1, 17)}
    assert {i for i in front if i.startswith("led-rx-")} == {f"led-rx-{n}" for n in range(1, 17)}
    for lamp in ("led-ready", "led-lan", "led-pwr", "reset"):
        assert lamp in front
    assert front["led-tx-3"]["for"] == "chassis" and front["led-rx-16"]["for"] == "chassis"


@pytest.mark.parametrize("name", NEW_PARTS)
def test_each_new_part_declares_how_sure_its_size_is_and_where_it_was_read(name):
    c = contract(name)
    assert c["size-confidence"], name
    assert "size" in c["provenance"], name


@pytest.mark.parametrize("slug,model", MODELS.items())
@pytest.mark.parametrize("export", ["netbox", "nautobot"])
def test_each_device_type_is_exported_under_the_model_name(slug, model, export):
    path = LIB / "exports" / export / "device-types" / "Moxa" / f"{model}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["model"] == model
    assert [p["name"] for p in doc["console-server-ports"]] == [f"port-{n}" for n in range(1, 17)]
    assert {p["type"] for p in doc["console-server-ports"]} == {"rj-45"}
    assert [i["name"] for i in doc["interfaces"]] == ["lan"]
