"""The Perle IOLAN SCG R-LA and R-LE console servers are in the library: the R build with the cellular front.

Each of the six devices is the R chassis of its size (SCG18, SCG34, SCG50). It adds the 4G LTE parts the L product page
lists. They are a Micro-SIM slot and two SMA antenna jacks, WWAN 1 and WWAN 2, on the front. The -LA and -LE devices differ in
the radio's bands and so in their part numbers. The SIM slot is a part with its own registered connector key.

These read the library and the registry and render nothing; they read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
CONNECTORS = ROOT / "spec" / "schemas" / "connectors.yaml"

PART_NUMBERS = {
    "iolan-scg18-r-la": {"04032754", "04032758"},
    "iolan-scg18-r-le": {"04032791", "04032792", "04032798"},
    "iolan-scg34-r-la": {"04032874", "04032878"},
    "iolan-scg34-r-le": {"04032911", "04032912", "04032918"},
    "iolan-scg50-r-la": {"04032994", "04032998"},
    "iolan-scg50-r-le": {"04033031", "04033032", "04033038"},
}
SERIAL = {"18": 16, "34": 32, "50": 48}
NEW_PARTS = ["perle/scg-sim-slot", "generic/sim-card-3ff"]


def serial_count(name):
    return SERIAL[name.split("-")[1][3:]]


def contract(name):
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


def load(model):
    return yaml.safe_load((LIB / "devices" / "perle" / model / "device.yaml").read_text())


@pytest.fixture(params=sorted(PART_NUMBERS))
def device(request):
    return load(request.param)


def placements(device, view):
    return {p["id"]: p for p in device["views"][view]["components"].get("placements", [])}


def test_the_chassis_is_the_r_chassis_of_its_size(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (436, 44, 262, 1)
    sizes = {f: (v["size"]["w"], v["size"]["h"]) for f, v in device["views"].items()}
    assert sizes == {"front": (480.2, 44), "rear": (436, 44), "top": (436, 262), "bottom": (436, 262),
                     "left": (262, 44), "right": (262, 44)}


def test_the_rear_has_the_serial_ports_the_model_name_counts(device):
    jacks = [p for p in placements(device, "rear").values() if p["ref"] == "common/rj45-ganged-eth-plain@1"]
    assert len(jacks) == serial_count(device["name"])


def test_the_front_has_a_micro_sim_slot_and_the_two_wwan_jacks(device):
    front = placements(device, "front")
    assert front["sim"]["ref"] == "perle/scg-sim-slot@1"
    assert [front[i]["ref"] for i in ("wwan-1", "wwan-2")] == ["common/sma-jack@1"] * 2
    assert front["wwan-1"]["at"][0] > front["wwan-2"]["at"][0]
    assert not {"wlan-1", "wlan-2", "modem"} & set(front)


def test_the_sim_slot_sits_between_the_admin_ports_and_the_usb_ports(device):
    front = placements(device, "front")
    assert front["console"]["at"][0] < front["sim"]["at"][0] < front["usb-a"]["at"][0]


def test_each_device_lists_the_part_numbers_of_its_product_page_row(device):
    parts = {p for cfg in device["configurations"].values() for p in cfg.get("part-numbers", {})}
    assert parts == PART_NUMBERS[device["name"]]


def test_the_device_says_which_radio_it_carries(device):
    text = " ".join(str(v) for v in device["description"].split()).lower()
    band = "america" if device["name"].endswith("-la") else "europe"
    assert band in text and "lte" in text


def test_the_module_bays_are_the_r_devices(device):
    bays = device["views"]["rear"]["components"].get("bays", [])
    assert [b["id"] for b in bays] == [f"bay-{i}" for i in range(serial_count(device["name"]) // 16 + 1, 4)]
    assert {b["interface"] for b in bays} <= {"scg-g16-module"}


def test_the_sim_key_is_registered_and_cites_the_guide():
    registry = yaml.safe_load(CONNECTORS.read_text())["interfaces"]
    note = registry["sim-card-3ff"]["note"]
    assert "5500427-10" in note and "3FF" in note


def test_the_sim_slot_presents_the_key_and_the_card_mates_it():
    assert contract("perle/scg-sim-slot")["interface"] == "sim-card-3ff"
    assert contract("generic/sim-card-3ff")["mates"] == "sim-card-3ff"


@pytest.mark.parametrize("name", NEW_PARTS)
def test_each_new_part_says_which_of_its_figures_are_estimates(name):
    d = contract(name)
    assert d["size-confidence"]
    text = " ".join(str(v) for v in d["provenance"].values()).lower()
    assert "estimated" in text or "drawing" in text


@pytest.mark.parametrize("name", NEW_PARTS)
def test_every_new_part_has_a_skin_for_each_name_in_its_contract(name):
    ns, part = name.split("/")
    for skin in contract(name)["skins"]:
        assert (LIB / "components" / ns / part / "v1" / "skins" / f"{skin}.svg").is_file(), (name, skin)


def test_the_device_says_what_its_front_cellular_figures_rest_on(device):
    notes = device["provenance"]["front-layout"]["note"].lower()
    assert "photo" in notes and "wwan" in notes and "estimated" in notes
