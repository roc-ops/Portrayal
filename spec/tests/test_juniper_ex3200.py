"""The Juniper EX3200 fixed access switches: EX3200-24T, -48T, -24P and -48P (#39).

One device per model, each with its power build as a `kind: orderable` configuration. The expected
figures are the hardware guide's (EX3200 Switch Hardware Guide, published 2020-12-15): Table 3 for the
models, Table 5 for the envelope, Table 11 for the PoE budgets, and the datasheet (1000216-013-EN,
Nov 2011) for the supply part numbers. Each test reads the YAML a contributor edits, or the generated
export a DCIM user imports; none reads a table the exporter holds.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INCH = 25.4

# component -> (part number, output watts, feed); the EX4200 and EX3200 datasheets print the same codes
PSUS = {
    "ex4200-pwr-320-ac": ("EX-PWR-320-AC", 320, "ac"),
    "ex4200-pwr-600-ac": ("EX-PWR-600-AC", 600, "ac"),
    "ex4200-pwr-930-ac": ("EX-PWR-930-AC", 930, "ac"),
    "ex4200-pwr-190-dc": ("EX-PWR-190-DC", 190, "dc"),
}
FAN = "ex3200-fan-tray"
COVER = "ex3200-uplink-cover"

# device: model, jacks, PoE ports, the supply it ships with, depth in inches (Table 5: 17 in with the
# 320 W AC or 190 W DC supply, 19.25 in with a 600 W or 930 W AC supply), configurations -> part numbers
DEVICES = {
    "ex3200-24t": ("EX3200-24T", 24, 8, "ex4200-pwr-320-ac", 17.0,
                   {"ac": ["EX3200-24T"], "dc": ["EX3200-24T-DC"]}),
    "ex3200-48t": ("EX3200-48T", 48, 8, "ex4200-pwr-320-ac", 17.0,
                   {"ac": ["EX3200-48T"], "dc": ["EX3200-48T-DC"]}),
    "ex3200-24p": ("EX3200-24P", 24, 24, "ex4200-pwr-600-ac", 19.25, {"ac": ["EX3200-24P"]}),
    "ex3200-48p": ("EX3200-48P", 48, 48, "ex4200-pwr-930-ac", 19.25, {"ac": ["EX3200-48P"]}),
}
# the supplies each model's bay takes: the minimum of Table 3 and above, and the 190 W DC supply of
# the -DC builds
ACCEPTS = {
    "ex3200-24t": {"ex4200-pwr-320-ac", "ex4200-pwr-600-ac", "ex4200-pwr-930-ac", "ex4200-pwr-190-dc"},
    "ex3200-48t": {"ex4200-pwr-320-ac", "ex4200-pwr-600-ac", "ex4200-pwr-930-ac", "ex4200-pwr-190-dc"},
    "ex3200-24p": {"ex4200-pwr-600-ac", "ex4200-pwr-930-ac"},
    "ex3200-48p": {"ex4200-pwr-930-ac"},
}
BUDGET = {"ex3200-24t": 130, "ex3200-48t": 130, "ex3200-24p": 410, "ex3200-48p": 740}


def load(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "layout.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def name_of(ref):
    return ref.split("/")[1].split("@")[0]


def seated(d, cfg):
    """Bay id -> the component name seated in that configuration."""
    out = {}
    for view in ("front", "rear"):
        for bid, b in bays(d, view).items():
            out[bid] = name_of(b["default"]) if b.get("default") else ""
    for bid, ref in ((d["configurations"][cfg].get("bays")) or {}).items():
        out[bid] = name_of(ref) if ref else ""
    return out


@pytest.mark.parametrize("dev", DEVICES)
def test_each_device_has_a_layout_and_a_device_in_step(dev):
    folder = LIB / "devices/juniper" / dev
    assert (folder / "layout.yaml").is_file() and (folder / "device.yaml").is_file()
    assert (folder / "device.lock.json").is_file()


@pytest.mark.parametrize("dev", DEVICES)
def test_the_envelope_is_table_5(dev):
    """Table 5: 1.75 in high, 17.25 in wide, 17 in deep with the 320 W AC or 190 W DC supply and 19.25
    in with a 600 W or 930 W supply, one rack unit."""
    c = load(dev)["chassis"]
    assert c["ru"] == 1
    assert c["height"] == pytest.approx(1.75 * INCH, abs=0.1)
    assert c["width"] == pytest.approx(17.25 * INCH, abs=0.2)
    assert c["depth"] == pytest.approx(DEVICES[dev][4] * INCH, abs=0.2)


@pytest.mark.parametrize("dev", DEVICES)
def test_the_maker_and_the_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == DEVICES[dev][0]
    assert d["portfolio"] == {"line": "EX Series", "family": "EX3200"}
    assert d["maturity"] == "modelled"
    assert d["chassis"]["airflow"] == "side"  # side to rear: the one airflow the guide gives


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_has_the_ports_the_guide_counts_numbered_as_printed(dev):
    _, n, *_ = DEVICES[dev]
    d = load(dev)
    ports = [p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth@1"]
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(n))
    for p in ports:
        k = int(p["id"].split("-")[1])
        assert p["rel-pos"] == k
        # numbering runs down each column: the even number is the upper jack, turned 180
        assert p.get("rotate", 0) == (180 if k % 2 == 0 else 0)
    assert {p["group"] for p in ports} == {"rj45"}
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "1g"}
    numerals = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
                if (s.get("for") or "").startswith("port-")}
    assert numerals == {f"port-{k}": str(k) for k in range(n)}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_ports_stand_in_blocks_of_six_columns_on_the_registry_pitch(dev):
    n = DEVICES[dev][1]
    d = load(dev)
    top = {int(p["id"].split("-")[1]): p["at"][0] for p in placements(d, "front")
           if p["ref"] == "common/rj45-ganged-eth@1" and p.get("rotate") == 180}
    xs = [top[k] for k in sorted(top)]
    columns = n // 2
    assert len(xs) == columns
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(13.97) == columns - columns // 6
    starts = [xs[i] for i in range(0, columns, 6)]
    assert len(starts) == columns // 6
    assert all(b - a == pytest.approx(88.0, abs=0.2) for a, b in zip(starts, starts[1:]))


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_carries_the_lcd_buttons_lamps_and_the_covered_uplink_slot(dev):
    d = load(dev)
    ids = {p["id"]: p["ref"] for p in placements(d, "front")}
    assert ids["btn-menu"] == ids["btn-enter"] == "juniper/ex4200-lcd-button@1"
    for lamp in ("led-alm", "led-sys", "led-mst"):
        assert ids[lamp] == "common/led-dot@1"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"]}
    assert {"EX3200", "ALM", "SYS", "MST"} <= legends
    slot = bays(d, "front")["uplink"]
    assert slot["accepts"] == [f"juniper/{COVER}@1"] and slot["default"] == f"juniper/{COVER}@1"
    assert set(bays(d, "front")) == {"uplink"}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_poe_legend_follows_table_3(dev):
    """The model plate prints the PoE count; the -T models place it only in their AC build."""
    _, n, poe, *_ = DEVICES[dev]
    d = load(dev)
    texts = {s["text"] for s in d["views"]["front"]["silkscreen"]}
    legend = [p for p in placements(d, "front") if p["ref"] == "juniper/ex3200-poe-legend@1"]
    if poe == 8:
        assert len(legend) == 1 and legend[0]["only-in"] == ["ac"]
        assert not {"24PoE", "48PoE"} & texts
    else:
        assert not legend and f"{n}PoE" in texts
    assert d["attrs"]["power"]["poe-ports"] == poe


@pytest.mark.parametrize("dev", DEVICES)
def test_the_rear_has_the_guides_connectors_and_no_virtual_chassis_or_rps_port(dev):
    d = load(dev)
    rear = {p["id"]: p for p in placements(d, "rear")}
    assert rear["mgmt"]["ref"] == "common/rj45-eth@1"
    assert rear["console"]["ref"] == "std/rj45@2"
    assert rear["usb"]["ref"] == "std/usb-a@1"
    assert rear["esd-rear-jack"]["ref"] == "common/esd-jack@1"
    assert rear["led-temp"]["ref"] == "common/led-dot@1"
    assert rear["ground-pair"]["ref"] == "juniper/ex3400-ground-pair@1"
    assert not [r for r in rear if r.startswith(("vcp", "rps"))]
    assert set(bays(d, "rear")) == {"fan-0", "psu-0"}  # one supply, one fan tray (Table 3, Cooling System)
    assert d["groups"]["fans"]["attrs"]["redundancy"] == "n+0"


@pytest.mark.parametrize("comp", sorted(PSUS))
def test_a_reused_supply_carries_the_part_number_the_datasheet_prints(comp):
    pn, watts, feed = PSUS[comp]
    c = contract(comp)
    assert c["class"] == "psu"
    assert list(c["part-numbers"]) == [pn]
    assert c["attrs"]["power-output-w"] == watts


def test_the_fan_tray_has_one_fan_and_cools_side_to_rear():
    c = contract(FAN)
    assert c["class"] == "fan"
    assert c["attrs"]["fans"] == 1 and c["attrs"]["airflow"] == "side-to-rear"
    assert c["attrs"]["airflow-cfm"] == 23.5


@pytest.mark.parametrize("dev", DEVICES)
def test_the_bay_accepts_what_the_guide_lists_and_ships_the_minimum(dev):
    d = load(dev)
    assert set(bays(d, "rear")["psu-0"]["accepts"]) == {f"juniper/{c}@1" for c in ACCEPTS[dev]}
    assert bays(d, "rear")["fan-0"]["accepts"] == [f"juniper/{FAN}@1"]
    assert seated(d, "ac") == {"uplink": COVER, "psu-0": DEVICES[dev][3], "fan-0": FAN}


@pytest.mark.parametrize("dev", DEVICES)
def test_each_configuration_lists_its_part_numbers(dev):
    d = load(dev)
    want = DEVICES[dev][5]
    assert set(d["configurations"]) == set(want)
    for cfg, pns in want.items():
        got = d["configurations"][cfg]
        assert got["kind"] == "orderable" and list(got["part-numbers"]) == pns
    assert [c for c, v in d["configurations"].items() if v.get("default")] == ["ac"]


@pytest.mark.parametrize("dev", [k for k, v in DEVICES.items() if "dc" in v[5]])
def test_the_dc_build_seats_the_190_w_supply_and_states_no_poe(dev):
    """Table 3: the -DC builds have no PoE-enabled ports and a 190 W supply."""
    d = load(dev)
    cfg = d["configurations"]["dc"]
    assert cfg["power"] == "dc"
    assert seated(d, "dc")["psu-0"] == "ex4200-pwr-190-dc"
    assert "no PoE" in cfg["description"]
    legend = [p for p in placements(d, "front") if p["ref"] == "juniper/ex3200-poe-legend@1"]
    assert legend and legend[0]["only-in"] == ["ac"]


def test_only_the_models_table_3_lists_have_a_dc_build():
    assert {k for k in DEVICES if "dc" in load(k)["configurations"]} == {"ex3200-24t", "ex3200-48t"}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_poe_budget_is_table_11(dev):
    d = load(dev)
    assert d["attrs"]["power"]["poe-budget-w"] == BUDGET[dev]
    assert d["attrs"]["power"]["poe-ports"] == DEVICES[dev][2]


@pytest.mark.parametrize("dev", DEVICES)
def test_every_figure_the_guide_does_not_print_is_a_declared_gap(dev):
    """No photograph is held at full resolution and no figure dimensions the faces: the gaps say so."""
    d = layout(dev)
    gaps = {g["what"] for g in d["gaps"]}
    assert {"uplink-modules", "rear-blank-plate", "side-faces", "rack-ears", "lcd-component"} <= gaps
    for key in ("gate-1-front", "gate-1-rear", "front-ports", "rear", "colour"):
        assert d["provenance"][key]["confidence"] == "estimated"


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", DEVICES)
def test_the_dcim_types_export_one_per_orderable_configuration(target, dev):
    d = load(dev)
    folder = LIB / "exports" / target / "device-types" / "Juniper"
    for cfg in d["configurations"].values():
        pn = sorted(cfg["part-numbers"])[0]
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Juniper" and doc["model"] == pn
        assert doc["u_height"] == 1.0


@pytest.mark.parametrize("dev", DEVICES)
def test_the_exported_type_lists_the_front_ports_and_the_rear_management_ports(dev):
    n = DEVICES[dev][1]
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Juniper" / f"{DEVICES[dev][0]}.yaml").read_text())
    names = {i["name"] for i in doc["interfaces"]}
    assert {f"port-{k}" for k in range(n)} <= names and "mgmt" in names
    assert not {f"port-{k}" for k in range(n, 48)} & names
    assert {c["name"] for c in doc.get("console-ports") or []}


@pytest.mark.parametrize("dev", DEVICES)
def test_no_face_draws_the_vendor_logo_and_the_front_reserves_its_place(dev):
    d = load(dev)
    for name, view in d["views"].items():
        drawn = list(view.get("silkscreen") or []) + list((view.get("panel") or {}).get("decor") or [])
        assert not {str(i.get("text", "")).upper() for i in drawn} & {"JUNIPER", "NETWORKS"}, name
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
