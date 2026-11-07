"""The Perle IOLAN SCG34 R and SCG50 R console servers are in the library: six faces, the module bays and the fixed parts.

Both are the AC build of the R/U product page: 32 or 48 RJ45 RS-232 serial ports in G16 modules in the three rear bays, two
network pairs (RJ45 and SFP), two AC inlets with a rocker each, and a front with a display, a keypad, a power button, a
card slot, an RJ45 and a micro-USB admin port, two USB ports and a reset. Each bay states the module class it takes and a
module is drawn in each bay that holds one. Each figure the documents do not give is declared an estimate in the contract
or the provenance that carries it.

These read the library and the registry and render nothing; they read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
CONNECTORS = ROOT / "spec" / "schemas" / "connectors.yaml"
VENDORS = ROOT / "spec" / "schemas" / "vendors.yaml"

MODELS = {"iolan-scg50-r": 48, "iolan-scg34-r": 32}
NEW_PARTS = ["perle/scg-lcd", "perle/scg-keypad", "perle/scg-power-button", "perle/scg-sd-slot",
             "perle/scg-power-rocker"]


def contract(name):
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


def load(model):
    return yaml.safe_load((LIB / "devices" / "perle" / model / "device.yaml").read_text())


@pytest.fixture(params=sorted(MODELS))
def device(request):
    return load(request.param)


def placements(device, view):
    return {p["id"]: p for p in device["views"][view]["components"].get("placements", [])}


def test_the_chassis_is_the_one_u_body_the_drawing_dimensions(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (436, 44, 262, 1)
    for face, size in {"front": (436, 44), "rear": (436, 44), "top": (436, 262), "bottom": (436, 262),
                       "left": (262, 44), "right": (262, 44)}.items():
        assert (device["views"][face]["size"]["w"], device["views"][face]["size"]["h"]) == size, face


def test_the_rear_has_the_serial_ports_the_model_name_counts(device):
    jacks = [p for p in placements(device, "rear").values() if p["ref"] == "common/rj45-ganged-eth-plain@1"]
    assert len(jacks) == MODELS[device["name"]]
    assert {p["group"] for p in jacks} == {"serial"}


def test_an_empty_bay_states_the_module_class_and_a_filled_one_is_not_declared(device):
    bays = device["views"]["rear"]["components"].get("bays", [])
    modules = MODELS[device["name"]] // 16
    assert [b["id"] for b in bays] == [f"bay-{i}" for i in range(modules + 1, 4)]
    assert {b["interface"] for b in bays} <= {"scg-g16-module"}
    assert all(b["group"] == "module-bays" for b in bays)


def test_the_base_build_leaves_an_empty_bay_empty(device):
    base = next(c for c in device["configurations"].values() if c.get("kind") == "base")
    bays = device["views"]["rear"]["components"].get("bays", [])
    assert (base.get("bays") or {}) == {b["id"]: "" for b in bays}


def test_the_module_class_is_a_registered_key_that_cites_the_guide():
    registry = yaml.safe_load(CONNECTORS.read_text())["interfaces"]
    note = registry["scg-g16-module"]["note"]
    assert "5500427-10" in note and "consecutive order" in note


def test_the_maker_is_in_the_vendor_registry():
    assert "perle" in yaml.safe_load(VENDORS.read_text())["vendors"]


def test_the_rear_carries_two_combo_pairs_and_two_ac_inlets(device):
    rear = placements(device, "rear")
    assert [rear[i]["ref"] for i in ("net1-rj45", "net2-rj45")] == ["common/rj45-eth@1"] * 2
    assert [rear[i]["ref"] for i in ("net1-sfp", "net2-sfp")] == ["std/sfp@1"] * 2
    assert [rear[i]["ref"] for i in ("inlet-1", "inlet-2")] == ["std/c14-inlet@1"] * 2
    assert [rear[i]["for"] for i in ("switch-1", "switch-2")] == ["inlet-1", "inlet-2"]


def test_the_front_carries_what_the_guide_lists_and_no_cellular_parts(device):
    front = placements(device, "front")
    assert {"display", "keypad", "power-button", "card-slot", "console", "console-usb", "usb-a", "usb-b",
            "reset", "ready"} <= set(front)
    assert front["power-button"]["ref"] == "perle/scg-power-button@1"
    assert front["card-slot"]["ref"] == "perle/scg-sd-slot@1"
    assert front["display"]["ref"] == "perle/scg-lcd@1"
    assert front["keypad"]["ref"] == "perle/scg-keypad@1"
    assert front["console"]["attrs"]["role"] == "console"
    assert not {"sim", "modem", "wwan-1", "wlan-1"} & set(front)


def test_the_keypad_has_the_six_keys_the_drawing_shows():
    assert sorted(contract("perle/scg-keypad")["elements"]) == ["back", "down", "enter", "left", "right", "up"]


def test_each_model_lists_its_six_part_numbers_one_per_power_cord(device):
    parts = [p for cfg in device["configurations"].values() for p in cfg.get("part-numbers", {})]
    assert len(parts) == 6 and all(p.isdigit() and len(p) == 8 for p in parts)


@pytest.mark.parametrize("name", NEW_PARTS)
def test_each_new_part_says_which_of_its_figures_are_estimates(name):
    d = contract(name)
    assert d["size-confidence"]
    text = " ".join(str(v) for v in d["provenance"].values()).lower()
    assert "estimated" in text or "drawing" in text


def test_every_new_part_has_a_skin_for_each_name_in_its_contract():
    for name in NEW_PARTS:
        ns, part = name.split("/")
        for skin in contract(name)["skins"]:
            assert (LIB / "components" / ns / part / "v1" / "skins" / f"{skin}.svg").is_file(), (name, skin)


def test_the_device_says_what_its_figures_rest_on(device):
    notes = " ".join(v["note"] for v in device["provenance"].values()).lower()
    assert "photo" in notes and "drawing" in notes
    assert device["gaps"]


@pytest.mark.parametrize("export", ["netbox", "nautobot"])
@pytest.mark.parametrize("model,size", [("iolan-scg50-r", "SCG50"), ("iolan-scg34-r", "SCG34")])
def test_the_device_type_lists_the_serial_ports_and_the_empty_bay(export, model, size):
    docs = [yaml.safe_load(p.read_text()) for p in (LIB / "exports" / export / "device-types" / "Perle").glob("*.yaml")]
    doc = next(d for d in docs if f"IOLAN {size} R" in d["description"])
    ports = [i for i in doc["interfaces"] if i["name"].startswith("port-")]
    assert len(ports) == MODELS[model]
    assert len(doc.get("module-bays", [])) == 3 - MODELS[model] // 16
    assert {"Ethernet 1", "Ethernet 1 SFP", "Ethernet 2", "Ethernet 2 SFP"} <= {i["name"] for i in doc["interfaces"]}
