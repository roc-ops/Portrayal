"""The Cisco Catalyst 9300 pilot: the C9300-48P and C9300-48T.

Source: Cisco Catalyst 9300 Series Switches Hardware Installation Guide (first published
2017-06-20, last modified 2026-05-15). Table 42 gives each model's envelope, Table 18 its default
power supply, Table 35 the supplies the series takes, Table 5 the network module blank, Table 43
the weight and Table 48 the fan module. The tests hold each device to the guide's figures, not to
what the drawing happens to say.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/cisco"
COMPONENTS = LIB / "components/cisco"
EXPORTS = LIB / "exports"

IN = 25.4

# model -> (default supply of Table 18, weight of Table 43 in kg, DCIM part number)
MODELS = {
    "c9300-48p": {"model": "C9300-48P", "psu": "pwr-c1-715wac-p", "weight": 7.59},
    "c9300-48t": {"model": "C9300-48T", "psu": "pwr-c1-350wac-p", "weight": 7.45},
}

# Table 35, the supplies the C9300 series takes, and the 350 W Platinum supply of Table 18
SUPPLIES = {
    "pwr-c1-350wac": 350,
    "pwr-c1-350wac-p": 350,
    "pwr-c1-715wac": 715,
    "pwr-c1-715wac-p": 715,
    "pwr-c1-1100wac": 1100,
    "pwr-c1-1100wac-p": 1100,
    "pwr-c1-1900wac-p": 1900,
    "pwr-c1-1900whv-t": 1900,
    "pwr-c1-715wdc": 715,
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def placements(d, view):
    comps = d["views"][view]["components"]
    return {p["id"]: p for p in comps.get("placements", [])}


def bays(d, view):
    return {b["id"]: b for b in d["views"][view]["components"].get("bays", [])}


@pytest.fixture(params=sorted(MODELS))
def dev(request):
    return request.param, load(request.param), MODELS[request.param]


# ---------------------------------------------------------------- the envelope


def test_envelope_is_table_42(dev):
    """1.73 x 17.5 x 19.2 in for both models. The height is the rack unit, 44.45 mm, as every 1RU
    switch here carries it; the printed 1.73 in (43.9 mm) is nominal and within a millimetre."""
    _, d, _ = dev
    ch = d["chassis"]
    assert ch["width"] == pytest.approx(17.5 * IN, abs=0.1)
    assert ch["depth"] == pytest.approx(19.2 * IN, abs=0.5)
    assert ch["height"] == pytest.approx(1.73 * IN, abs=1.0)
    assert ch["ru"] == 1
    assert ch["airflow"] == "front-to-back"


def test_weight_is_table_43(dev):
    _, d, m = dev
    assert d["chassis"]["weight-kg"] == m["weight"]


def test_every_face_is_sized_from_the_chassis(dev):
    _, d, _ = dev
    ch = d["chassis"]
    for v in ("front", "rear"):
        assert d["views"][v]["size"] == {"w": ch["width"], "h": ch["height"]}
    for v in ("top", "bottom"):
        assert d["views"][v]["size"] == {"w": ch["width"], "h": ch["depth"]}


def test_the_ears_name_the_shipped_position(dev):
    _, d, _ = dev
    pos = d["chassis"]["ears"]["positions"]
    assert [p["name"] for p in pos if p.get("default")] == ["flush"]
    assert not [p for p in pos if "at" in p], "the guide prints no setback"
    assert "kits" not in d["chassis"], "no depth range is printed, so no kit is written"


# ----------------------------------------------------------------------- ports


def test_front_has_48_numbered_rj45_ports(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    ports = {k: v for k, v in pl.items() if re.fullmatch(r"port-\d+", k)}
    assert sorted(int(k.split("-")[1]) for k in ports) == list(range(1, 49))
    assert {p["ref"] for p in ports.values()} == {"std/rj45-ganged@2"}
    assert {p["group"] for p in ports.values()} == {"rj45"}
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "1g"}


def test_ports_run_down_each_column_in_four_blocks_of_six(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    for n in range(1, 49, 2):
        top, bottom = pl[f"port-{n}"]["at"], pl[f"port-{n + 1}"]["at"]
        assert top[0] == bottom[0] and top[1] < bottom[1], f"port {n} is over port {n + 1}"
    xs = sorted({pl[f"port-{n}"]["at"][0] for n in range(1, 49, 2)})
    assert len(xs) == 24
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert [i for i, s in enumerate(steps) if s > 15] == [5, 11, 17], "gutters after columns 6, 12, 18"


def test_every_port_has_a_lamp(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    lamps = {k for k in pl if k.startswith("led-port-")}
    assert lamps == {f"led-port-{n}" for n in range(1, 49)}
    assert all(pl[f"led-port-{n}"]["for"] == f"port-{n}" for n in range(1, 49))


def test_front_console_is_a_mini_usb_b_and_there_is_a_usb_a(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    assert pl["console-usb"]["ref"] == "std/mini-usb@1"
    assert pl["usb-a"]["ref"] == "std/usb-a@1"
    assert d["groups"]["usb-console"]["attrs"] == {"media": "mini-usb-b"}


def test_mini_usb_is_the_registered_size():
    c = yaml.safe_load((LIB / "components/std/mini-usb/v1/contract.yaml").read_text())
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]["mini-usb-b"]
    assert c["conforms"] == "mini-usb-b"
    assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == (std["w"], std["h"], std["depth"])


def test_rear_console_management_stack_and_power_stack_connectors(dev):
    _, d, _ = dev
    pl = placements(d, "rear")
    assert pl["console"]["attrs"]["role"] == "console"
    assert pl["mgmt"]["attrs"]["role"] == "mgmt"
    assert pl["console"]["at"][0] < pl["mgmt"]["at"][0]
    assert {k for k in pl if k.startswith("stack-")} == {"stack-1", "stack-2"}
    assert {k for k in pl if k.startswith("spwr-")} == {"spwr-1", "spwr-2"}
    assert pl["usb-ssd"]["attrs"]["usb"] == "3.0"
    assert {pl["stack-1"]["ref"], pl["stack-2"]["ref"]} == {"cisco/stackwise-480-port@1"}
    assert {pl["spwr-1"]["ref"], pl["spwr-2"]["ref"]} == {"cisco/stackpower-port@1"}


def test_each_stackwise_carrier_holds_three_connectors(dev):
    # the NetBox rear elevation draws three stacked connectors in each carrier; the guide's two
    # ports are the two carriers, so the port count stays two
    _, d, _ = dev
    c = contract("stackwise-480-port")
    openings = sorted((e["at"][1], e["size"]) for e in c["elements"].values())
    assert len(openings) == 3
    assert all(size == [14.9, 5.2] for _, size in openings)
    assert openings[-1][0] + 5.2 <= c["size"]["h"] + 1e-6
    pl = placements(d, "rear")
    for k in ("stack-1", "stack-2"):
        top, h = pl[k]["at"][1], c["size"]["h"]
        carrier = next(x for x in d["views"]["rear"]["panel"]["decor"] if x["id"].startswith("stackwise-carrier"))
        assert carrier["at"][1] <= top and top + h <= carrier["at"][1] + carrier["size"][1]


def test_the_poe_lamp_is_on_the_poe_switch_only():
    assert "led-poe" in placements(load("c9300-48p"), "front")
    assert "led-poe" not in placements(load("c9300-48t"), "front")


# ------------------------------------------------- supplies, fans and the bays


def test_three_fan_modules_seat_fan_t2(dev):
    _, d, _ = dev
    fb = bays(d, "rear")
    fans = {k: v for k, v in fb.items() if k.startswith("fan-")}
    assert sorted(fans) == ["fan-1", "fan-2", "fan-3"]
    assert all(b["accepts"] == ["cisco/fan-t2@1"] and b["default"] == "cisco/fan-t2@1"
               for b in fans.values())
    fan = contract("fan-t2")
    assert (fan["size"]["w"], fan["size"]["h"]) == (43.9, 41.1)
    assert fan["attrs"]["airflow-cfm"] == 20


def test_both_supply_bays_accept_every_supply_the_guide_lists(dev):
    _, d, _ = dev
    fb = bays(d, "rear")
    want = {f"cisco/{n}@1" for n in SUPPLIES} | {"cisco/c9300-psu-blank@1"}
    for bid in ("psu-1", "psu-2"):
        assert set(fb[bid]["accepts"]) == want


def test_default_supply_is_table_18_and_the_second_slot_has_the_cover(dev):
    _, d, m = dev
    fb = bays(d, "rear")
    assert fb["psu-1"]["default"] == f"cisco/{m['psu']}@1"
    assert fb["psu-2"]["default"] == "cisco/c9300-psu-blank@1"


@pytest.mark.parametrize("name,watts", sorted(SUPPLIES.items()))
def test_each_supply_states_its_output_and_airflow(name, watts):
    c = contract(name)
    assert c["name"] == name and c["class"] == "psu" and c["kind"] == "module"
    assert c["attrs"]["power-output-w"] == watts
    assert c["attrs"]["model"] == name.upper()
    assert c["attrs"]["airflow"] == "front-to-back" == contract("fan-t2")["attrs"]["airflow"]
    assert (c["size"]["w"], c["size"]["h"]) == (82.55, 40.1)
    assert c["body"]["depth"] == (348.2 if "1100" in name or "1900" in name else 309.9)
    assert (COMPONENTS / name / "v1/skins/default.svg").exists()


def test_the_dc_supply_feeds_a_dc_configuration(dev):
    _, d, _ = dev
    cfg = d["configurations"]["psu-715wdc"]
    assert cfg["power"] == "dc" and cfg["bays"] == {"psu-1": "cisco/pwr-c1-715wdc@1"}
    assert d["chassis"]["power"] == "ac"


def test_the_configurations_say_what_they_are(dev):
    name, d, m = dev
    cfgs = d["configurations"]
    orderable = {k: v for k, v in cfgs.items() if v["kind"] == "orderable"}
    assert list(orderable) == [name]
    assert orderable[name]["part-numbers"] == {m["model"]: {}}
    # the drawn default is the orderable build as shipped: the default supply and the cover, and
    # no base, because a base would empty the network module bay the guide says must hold a blank
    assert orderable[name]["default"] is True and "bays" not in orderable[name]
    assert not [k for k, v in cfgs.items() if v["kind"] == "base"]
    # every supply of Table 35 has a configuration that seats it, as an illustration
    seated = {c["bays"].get("psu-1") for c in cfgs.values() if "bays" in c}
    seated.add(f"cisco/{m['psu']}@1")
    assert {f"cisco/{n}@1" for n in SUPPLIES} <= seated
    assert {c["kind"] for k, c in cfgs.items() if k != name} == {"example"}
    assert "empty-supply-bay" in cfgs


def test_licence_suffix_is_not_a_part_number(dev):
    _, d, m = dev
    pn = d["configurations"][m["model"].lower()]["part-numbers"]
    assert not [k for k in pn if k.endswith(("-A", "-E"))]


# ------------------------------------------------------- the network module bay


def test_network_module_bay_is_blank_and_accepts_only_what_is_modelled(dev):
    _, d, _ = dev
    bay = bays(d, "front")["nm-bay"]
    assert bay["default"] == "cisco/c9300-nm-blank@1"
    modelled = {p.name for p in COMPONENTS.glob("c9300-nm-*")}
    assert {a.split("/")[1].split("@")[0] for a in bay["accepts"]} == modelled == {"c9300-nm-blank"}


def test_blank_covers_say_the_guide_names_no_part_number_for_the_psu_cover():
    cover = contract("c9300-psu-blank")
    assert cover["class"] == "blank"
    assert "NO PART NUMBER" in cover["provenance"]["model"].upper()


# ------------------------------------------------------- the DCIM device types


def device_types(vendor_dir):
    out = {}
    for f in (EXPORTS / vendor_dir / "device-types/Cisco").glob("C9300-48*.yaml"):
        t = yaml.safe_load(f.read_text())
        out[t["model"]] = t
    return out


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_dcim_exports_one_type_per_orderable_configuration(target):
    types = device_types(target)
    assert sorted(types) == ["C9300-48P", "C9300-48T"]
    for t in types.values():
        assert t["u_height"] == 1 == round(1.73 * IN / 44.45)
        assert t["manufacturer"] == "Cisco"


def test_the_exported_types_carry_no_illustration():
    names = [f.name for f in (EXPORTS / "netbox/device-types/Cisco").glob("C9300*")]
    assert sorted(names) == ["C9300-48P.yaml", "C9300-48T.yaml"]


def test_no_other_catalyst_9300_model_is_claimed():
    names = {p.name for p in DEVICES.glob("c9300*")}
    assert names == {"c9300-48p", "c9300-48t"}
