"""The Juniper EX3300 family: four devices for the end-of-life fixed access switches.

Each device is one front panel. The EX3300 hardware guide (published 2020-12-15) gives one chassis
for the whole family in Table 5, the six models in Table 3, the airflow of each in Table 13 and the
power each consumes in Table 14. Its power supply and its fan tray are built in (Table 4), so no
model has a power supply bay or a fan bay, and no module is seated except a transceiver.

The devices: the 48-port EX3300-48T (with its back-to-front EX3300-48T-BF build), the PoE+ EX3300-48P,
the 24-port EX3300-24T (with its DC-powered EX3300-24T-DC build) and the PoE+ EX3300-24P.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/juniper"
EXPORTS = LIB / "exports/netbox"

# model -> (RJ-45 ports, PoE+, weight kg from Table 5)
MODELS = {
    "ex3300-24t": (24, False, 4.6),
    "ex3300-24p": (24, True, 5.3),
    "ex3300-48t": (48, False, 4.9),
    "ex3300-48p": (48, True, 5.8),
}

# Table 3: the variants that share a front panel are configurations of one device, keyed by
# configuration id and giving the part number.
CONFIGS = {
    "ex3300-24t": {"ac": "EX3300-24T", "dc": "EX3300-24T-DC"},
    "ex3300-24p": {"ac": "EX3300-24P"},
    "ex3300-48t": {"ac": "EX3300-48T", "bf": "EX3300-48T-BF"},
    "ex3300-48p": {"ac": "EX3300-48P"},
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, face):
    comps = (d["views"][face].get("components") or {})
    return comps.get("placements") or []


def bays(d, face):
    return (d["views"][face].get("components") or {}).get("bays") or []


@pytest.mark.parametrize("name", MODELS)
def test_envelope_is_table_5(name):
    # Table 5: 1.75 in. (4.45 cm) high, 17.5 in. (44.5 cm) wide, or 19 in. (48.2 cm) with the
    # mounting brackets attached, and 12 in. (30.5 cm) deep.
    d = load(name)
    ch = d["chassis"]
    assert ch["width"] == 444.5
    assert ch["height"] == 44.5
    assert ch["depth"] == 305.0
    assert ch["ru"] == 1
    assert ch["weight-kg"] == MODELS[name][2]
    for face, size in (("front", (444.5, 44.5)), ("rear", (444.5, 44.5)),
                       ("left", (305.0, 44.5)), ("top", (444.5, 305.0))):
        assert (d["views"][face]["size"]["w"], d["views"][face]["size"]["h"]) == size


@pytest.mark.parametrize("name", MODELS)
def test_naming(name):
    d = load(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX3300"}


@pytest.mark.parametrize("name", MODELS)
def test_front_jacks_are_numbered_from_zero_with_the_even_ports_on_top(name):
    count = MODELS[name][0]
    jacks = {p["id"]: p for p in placements(load(name), "front") if p["id"].startswith("port-")}
    assert sorted(jacks, key=lambda i: int(i.split("-")[1])) == [f"port-{n}" for n in range(count)]
    assert {p["ref"] for p in jacks.values()} == {"common/rj45-ganged-eth@1"}
    for n in range(count):
        j = jacks[f"port-{n}"]
        assert j["rel-pos"] == n
        # the upper jack of a column is turned 180 so that its keyway and lamps face up
        assert j.get("rotate", 0) == (180 if n % 2 == 0 else 0)
        if n % 2 == 0:
            assert jacks[f"port-{n + 1}"]["at"][1] > j["at"][1]
            assert jacks[f"port-{n + 1}"]["at"][0] == j["at"][0]


@pytest.mark.parametrize("name", MODELS)
def test_the_24_port_models_carry_their_jacks_at_the_right_of_the_panel(name):
    # Figure 2: the 24 jacks are the right two blocks of the 48-port face, and the left half is vented
    # metal. The 48-port jacks start at the left edge.
    jacks = [p for p in placements(load(name), "front") if p["id"].startswith("port-")]
    first = min(p["at"][0] for p in jacks)
    assert first == (189.42 if MODELS[name][0] == 24 else 10.1)
    last = max(p["at"][0] for p in jacks)
    # the last jack of the last block, whichever model: four blocks of six columns on a step of 89.66 mm
    assert round(last, 1) == 349.9


@pytest.mark.parametrize("name", MODELS)
def test_front_uplinks_are_four_sfp_cages_numbered_0_to_3(name):
    cages = [p for p in placements(load(name), "front") if p["id"].startswith("uplink-")]
    assert [p["id"] for p in cages] == [f"uplink-{n}" for n in range(4)]
    assert {p["ref"] for p in cages} == {"std/sfp-ganged@1"}
    xs = [p["at"][0] for p in cages]
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [14.25] * 3
    # each uplink has a Link/Activity lamp and a Status lamp (Figure 9)
    lamps = [p["id"] for p in placements(load(name), "front") if p["id"].startswith("led-uplink-")]
    assert len(lamps) == 8


@pytest.mark.parametrize("name", MODELS)
def test_front_has_the_lcd_and_the_status_block_the_guide_names(name):
    d = load(name)
    ids = {p["id"] for p in placements(d, "front")}
    # Figure 6: ALM, SYS, MST. Figure 5: the LCD panel with a Menu and an Enter button.
    assert {"led-sys", "led-alm", "led-mst", "btn-menu", "btn-enter"} <= ids
    assert any(x.get("id") == "lcd" for x in d["views"]["front"]["panel"]["decor"])
    texts = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"SYS", "ALM", "MST"} <= texts
    # the 48-port figure prints PoE+ beside the model, and the 24-port figure does not
    assert ("EX3300 PoE+" in texts) is MODELS[name][1]
    assert ("EX3300" in texts) is not MODELS[name][1]


@pytest.mark.parametrize("name", MODELS)
def test_no_face_draws_the_vendor_wordmark(name):
    # The logo is a trademark, so the layout reserves a `logo-zone` and prints nothing in it.
    d = load(name)
    texts = {s["text"].upper() for v in d["views"].values() for s in (v.get("silkscreen") or [])
             if "text" in s}
    assert not texts & {"JUNIPER", "NETWORKS", "JUNIPER NETWORKS"}
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])


@pytest.mark.parametrize("name", MODELS)
def test_rear_ports_and_fixed_parts(name):
    d = load(name)
    byid = {p["id"]: p["ref"] for p in placements(d, "rear")}
    # the rear panel topic: management port, USB port, console port, protective earthing terminal,
    # RPS port, ESD point, the fan, the AC power cord inlet or the DC power terminal block
    assert byid["mgmt"] == "common/rj45-eth@1"
    assert byid["con"] == "std/rj45@2"
    assert byid["usb"] == "std/usb-a@1"
    assert byid["rps"] == "juniper/ex3300-rps-port@1"
    assert byid["ground-pair"] == "juniper/ex3400-ground-pair@1"
    assert byid["esd-rear"] == "common/esd-jack@1"
    assert byid["fan-grille"] == "juniper/ex3300-rear-grille@1"
    assert byid["ac-inlet"] == "std/c14-inlet@1"
    legends = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON"} <= legends


@pytest.mark.parametrize("name", MODELS)
def test_the_power_supply_and_the_fan_are_built_in_so_there_is_no_bay(name):
    # Table 4: "Built-in power supply" and "Built-in fan tray"; Table 32: "Switch with built-in power
    # supply". A built-in unit is part of the chassis and not a bay.
    d = load(name)
    for face in d["views"]:
        assert not bays(d, face), (name, face)
    for cfg in d["configurations"].values():
        assert not cfg.get("bays")


@pytest.mark.parametrize("name", MODELS)
def test_configuration_part_numbers(name):
    d = load(name)
    cfgs = d["configurations"]
    assert {k: list(c["part-numbers"]) for k, c in cfgs.items()} == \
        {k: [pn] for k, pn in CONFIGS[name].items()}
    assert all(c["kind"] == "orderable" for c in cfgs.values())
    assert cfgs["ac"]["default"] is True
    assert not any(c.get("default") for k, c in cfgs.items() if k != "ac")
    assert list(cfgs["ac"]["part-numbers"]) == [d["model"]]


@pytest.mark.parametrize("name", MODELS)
def test_airflow_follows_table_13(name):
    # Table 13: every model is front-to-back except the EX3300-48T-BF
    d = load(name)
    assert d["chassis"]["airflow"] == "front-to-back"
    for cfg_id, cfg in d["configurations"].items():
        want = "back-to-front" if cfg_id == "bf" else "front-to-back"
        assert cfg.get("airflow", d["chassis"]["airflow"]) == want


def test_the_dc_build_swaps_the_inlet_for_the_terminal_block():
    d = load("ex3300-24t")
    by = {p["id"]: p for p in placements(d, "rear")}
    assert by["ac-inlet"]["only-in"] == ["ac"]
    assert by["dc-terminal"]["ref"] == "juniper/ex3300-dc-terminal@1"
    assert by["dc-terminal"]["only-in"] == ["dc"]
    assert d["configurations"]["dc"]["power"] == "dc"
    # no other model has a DC build (Table 3)
    for name in ("ex3300-24p", "ex3300-48t", "ex3300-48p"):
        assert "dc-terminal" not in {p["id"] for p in placements(load(name), "rear")}


@pytest.mark.parametrize("name", MODELS)
def test_poe_models_say_so_and_the_others_do_not(name):
    d = load(name)
    group = d["groups"]["rj45"]["attrs"]
    assert ("poe" in group) is MODELS[name][1]
    if MODELS[name][1]:
        assert group["poe"] == "802.3at"
        assert d["attrs"]["power"]["poe-budget-w"].startswith("740 W" if MODELS[name][0] == 48 else "405 W")
    else:
        assert "poe-budget-w" not in d["attrs"]["power"]


@pytest.mark.parametrize("name", MODELS)
def test_dcim_export_has_one_device_type_per_orderable_configuration(name):
    d = load(name)
    exported = sorted(p.stem for p in (EXPORTS / "device-types/Juniper").glob(f"{d['model']}*.yaml"))
    assert exported == sorted(CONFIGS[name].values())
    for pn in exported:
        doc = yaml.safe_load((EXPORTS / f"device-types/Juniper/{pn}.yaml").read_text())
        assert doc["u_height"] == 1.0
        assert doc["manufacturer"] == "Juniper"
        assert doc["airflow"] == ("rear-to-front" if pn.endswith("-BF") else "front-to-rear")


@pytest.mark.parametrize("name", MODELS)
def test_a_figure_read_off_a_picture_says_how(name):
    # The guide's drawings are the only reference, so the provenance names the figure and its scale.
    prov = load(name)["provenance"]
    assert "Figure" in prov["scale"]["note"] and "pt/mm" in prov["scale"]["note"]
    assert prov["rear-modules"]["confidence"] == "datasheet"
    assert "built in" in prov["rear-modules"]["note"]
