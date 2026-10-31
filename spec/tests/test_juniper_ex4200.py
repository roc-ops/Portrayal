"""The Juniper EX4200 fixed access switches: EX4200-24T, -24P, -24PX, -24F, -48T, -48P and -48PX (#39).

One device per front panel and per PoE class, each with its power and spare-chassis builds as
`kind: orderable` configurations. The expected figures below are the hardware guide's (EX4200
Switch Hardware Guide, published 2022-01-16): Table 1 for the models, Table 3 for the envelope,
Table 9 and the power supply text for which supply each model takes, Table 37 for the packing
list, and the datasheet (1000215-026-EN, Feb 2019) for the ordering codes. Each test reads the
YAML a contributor edits, or the generated export a DCIM user imports; none reads a table the
exporter holds, because a table that says so proves nothing about the file.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INCH = 25.4

# the supplies the guide names, by component name: part number, output watts, feed
PSUS = {
    "ex4200-pwr-320-ac": ("EX-PWR-320-AC", 320, "ac"),
    "ex4200-pwr-600-ac": ("EX-PWR-600-AC", 600, "ac"),
    "ex4200-pwr-930-ac": ("EX-PWR-930-AC", 930, "ac"),
    "ex4200-pwr2-930-ac": ("EX-PWR2-930-AC", 930, "ac"),
    "ex4200-pwr3-930-ac": ("EX-PWR3-930-AC", 930, "ac"),
    "ex4200-pwr-190-dc": ("EX-PWR-190-DC", 190, "dc"),
}
COVERS = ["ex4200-psu-cover", "ex4200-uplink-cover"]
FAN = "ex4200-fan-tray"

# device: model, jacks, PoE ports, jack kind, the supply it ships with, depth in inches
# (Table 3: 17 in with the 320 W AC or 190 W DC supply, 19.25 in with a 600 W or 930 W AC supply),
# configurations -> part numbers (datasheet ordering information, and Table 1 for the -S builds)
DEVICES = {
    "ex4200-24t": ("EX4200-24T", 24, 8, "common/rj45-ganged-eth@1", "ex4200-pwr-320-ac", 17.0,
                   {"ac": ["EX4200-24T", "EX4200-24T-TAA"], "dc": ["EX4200-24T-DC"]}),
    "ex4200-24p": ("EX4200-24P", 24, 24, "common/rj45-ganged-eth@1", "ex4200-pwr-600-ac", 19.25,
                   {"ac": ["EX4200-24P", "EX4200-24P-TAA"]}),
    "ex4200-24px": ("EX4200-24PX", 24, 24, "common/rj45-ganged-eth@1", "ex4200-pwr3-930-ac", 19.25,
                    {"ac": ["EX4200-24PX"]}),
    "ex4200-24f": ("EX4200-24F", 24, 0, "std/sfp-ganged@1", "ex4200-pwr-320-ac", 17.0,
                   {"ac": ["EX4200-24F", "EX4200-24F-TAA"], "dc": ["EX4200-24F-DC"],
                    "s": ["EX4200-24F-S"]}),
    "ex4200-48t": ("EX4200-48T", 48, 8, "common/rj45-ganged-eth@1", "ex4200-pwr-320-ac", 17.0,
                   {"ac": ["EX4200-48T", "EX4200-48T-TAA"], "dc": ["EX4200-48T-DC"],
                    "s": ["EX4200-48T-S"]}),
    "ex4200-48p": ("EX4200-48P", 48, 48, "common/rj45-ganged-eth@1", "ex4200-pwr-930-ac", 19.25,
                   {"ac": ["EX4200-48P", "EX4200-48P-TAA"]}),
    "ex4200-48px": ("EX4200-48PX", 48, 48, "common/rj45-ganged-eth@1", "ex4200-pwr3-930-ac", 19.25,
                    {"ac": ["EX4200-48PX"]}),
}
# the supplies each model's bays take: the minimum for the model and above, and the DC supply of the
# -DC builds; the PX models work only with the EX-PWR2-930-AC and EX-PWR3-930-AC (the guide)
ACCEPTS = {
    "t": {"ex4200-pwr-320-ac", "ex4200-pwr-600-ac", "ex4200-pwr-930-ac", "ex4200-pwr2-930-ac",
          "ex4200-pwr3-930-ac", "ex4200-pwr-190-dc"},
    "24p": {"ex4200-pwr-600-ac", "ex4200-pwr-930-ac", "ex4200-pwr2-930-ac", "ex4200-pwr3-930-ac"},
    "48p": {"ex4200-pwr-930-ac", "ex4200-pwr2-930-ac", "ex4200-pwr3-930-ac"},
    "px": {"ex4200-pwr2-930-ac", "ex4200-pwr3-930-ac"},
}
CLASS = {"ex4200-24t": "t", "ex4200-24f": "t", "ex4200-48t": "t", "ex4200-24p": "24p",
         "ex4200-48p": "48p", "ex4200-24px": "px", "ex4200-48px": "px"}


def load(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load(
        (LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def printed(d, cfg):
    """The front legends as one configuration prints them: [(for, text, fill)].

    The "8PoE" line and the numerals 0 to 7 of the -24T and -48T are small parts placed with
    `only-in`, so a -DC build can leave the PoE colouring off. Their text is read from the skin.
    """
    out = [(s.get("for"), s["text"], s["fill"]) for s in d["views"]["front"]["silkscreen"]]
    for p in placements(d, "front"):
        name = name_of(p["ref"])
        if name not in ("ex4200-poe-plate", "ex4200-port-numerals"):
            continue
        if p.get("only-in") and cfg not in p["only-in"]:
            continue
        skin = p.get("skin", "default")
        svg = ET.parse(LIB / "components/juniper" / name / "v1/skins" / f"{skin}.svg").getroot()
        group = svg.find(".//{*}g[@id='silkscreen']")
        for t in group.findall("{*}text"):
            tag = None if name == "ex4200-poe-plate" else f"port-{t.text}"
            out.append((tag, t.text, group.get("fill")))
    return out


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def name_of(ref):
    return ref.split("/")[1].split("@")[0]


def seated(d, cfg):
    """Bay id -> the component name seated in that configuration, '' for an open bay."""
    out = {}
    for view in ("front", "rear"):
        for bid, b in bays(d, view).items():
            out[bid] = name_of(b["default"]) if b.get("default") else ""
    for bid, ref in ((d["configurations"][cfg].get("bays")) or {}).items():
        out[bid] = name_of(ref) if ref else ""
    return out


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("dev", DEVICES)
def test_the_envelope_is_table_3(dev):
    """Table 3: 1.75 in high, 17.25 in wide (the 19 in figure is over the brackets), 17 in deep
    with the 320 W AC or 190 W DC supply and 19.25 in with a 600 W or 930 W supply, one rack unit."""
    c = load(dev)["chassis"]
    assert c["ru"] == 1
    assert c["height"] == pytest.approx(1.75 * INCH, abs=0.1)
    assert c["width"] == pytest.approx(17.25 * INCH, abs=0.2)
    assert c["depth"] == pytest.approx(DEVICES[dev][5] * INCH, abs=0.2)


@pytest.mark.parametrize("dev", DEVICES)
def test_every_face_is_sized_from_the_envelope(dev):
    d = load(dev)
    c = d["chassis"]
    for v in ("front", "rear"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["height"]}
    for v in ("top", "bottom"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["depth"]}
    for v in ("left", "right"):
        assert d["views"][v]["size"] == {"w": c["depth"], "h": c["height"]}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_maker_and_the_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == DEVICES[dev][0]
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4200"}
    assert d["maturity"] == "modelled"
    assert d["chassis"]["airflow"] == "side"  # side to rear: the one airflow the guide gives


# ------------------------------------------------------------------ the faces


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_has_the_ports_the_guide_counts_numbered_as_printed(dev):
    _, n, poe, kind, *_ = DEVICES[dev]
    d = load(dev)
    ports = [p for p in placements(d, "front") if p["ref"] == kind]
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(n))
    for p in ports:
        k = int(p["id"].split("-")[1])
        assert p["rel-pos"] == k
    if kind.startswith("std/sfp"):
        assert {p["group"] for p in ports} == {"sfp"}
        assert d["groups"]["sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    else:
        assert {p["group"] for p in ports} == {"rj45"}
        for p in ports:
            k = int(p["id"].split("-")[1])
            # numbering runs down each column: the even number is the upper jack, turned 180
            assert p.get("rotate", 0) == (180 if k % 2 == 0 else 0)
        assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "1g"}
    # the printed numbers: one numeral per port, spelled as the metal spells it
    numerals = {f: t for f, t, _ in printed(d, "ac") if (f or "").startswith("port-")}
    assert numerals == {f"port-{k}": str(k) for k in range(n)}
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert {f"port-{k}" for k in range(n)} <= cut


@pytest.mark.parametrize("dev", DEVICES)
def test_the_ports_stand_in_blocks_of_six_columns_on_the_registry_pitch(dev):
    _, n, _, kind, *_ = DEVICES[dev]
    d = load(dev)
    if kind.startswith("std/sfp"):
        top = {int(p["id"].split("-")[1]): p["at"] for p in placements(d, "front")
               if p["ref"] == kind}
        pitch, columns = 14.25, n
    else:
        top = {int(p["id"].split("-")[1]): p["at"] for p in placements(d, "front")
               if p["ref"] == kind and p.get("rotate") == 180}
        pitch, columns = 13.97, n // 2
    xs = [top[k][0] for k in sorted(top)]
    assert len(xs) == columns
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    # the pitch within a block of six columns; wider between blocks
    assert steps.count(pitch) == columns - columns // 6
    assert all(s > pitch for s in steps if s != pitch)
    # blocks start 88.0 mm apart on both jack kinds
    starts = [xs[i] for i in range(0, columns, 6)]
    assert all(b - a == pytest.approx(88.0, abs=0.2) for a, b in zip(starts, starts[1:]))


@pytest.mark.parametrize("dev", DEVICES)
def test_poe_ports_print_their_numerals_in_orange(dev):
    """The datasheet photographs print the numerals of the PoE ports in orange and the rest white."""
    _, n, poe, *_ = DEVICES[dev]
    d = load(dev)
    for cfg in set(d["configurations"]) - {"dc"}:
        fills = {int(f.split("-")[1]): c for f, _, c in printed(d, cfg)
                 if (f or "").startswith("port-")}
        orange = {k for k, c in fills.items() if c == "#f2a33a"}
        assert orange == set(range(poe))
        assert len({fills[k] for k in range(poe, n)}) <= 1


@pytest.mark.parametrize("dev", [k for k, v in DEVICES.items() if "dc" in v[6] and v[2]])
def test_the_dc_builds_print_no_poe_legend_and_plain_numerals(dev):
    """Guide Table 1 and the text under it: a switch with a DC supply provides no PoE."""
    d = load(dev)
    assert d["configurations"]["dc"]["part-numbers"]
    legends = printed(d, "dc")
    assert not [t for _, t, _ in legends if "PoE" in t]
    assert "#f2a33a" not in {c for _, _, c in legends}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_carries_the_lcd_buttons_lamps_and_the_empty_uplink_slot(dev):
    d = load(dev)
    ids = {p["id"]: p["ref"] for p in placements(d, "front")}
    assert ids["btn-menu"] == ids["btn-enter"] == "juniper/ex4200-lcd-button@1"
    for lamp in ("led-alm", "led-sys", "led-mst"):
        assert ids[lamp] == "common/led-dot@1"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"]}
    assert {"EX4200", "ALM", "SYS", "MST"} <= legends
    # the front has no console port: the EX4200's console is on the rear
    assert "console" not in ids
    # the slot takes only the cover here; the four uplink modules are left for their own slice
    slot = bays(d, "front")["uplink"]
    assert slot["accepts"] == ["juniper/ex4200-uplink-cover@1"]
    assert slot["default"] == "juniper/ex4200-uplink-cover@1"
    assert set(bays(d, "front")) == {"uplink"}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_rear_has_the_vcp_usb_management_console_esd_and_three_bays(dev):
    d = load(dev)
    rear = {p["id"]: p for p in placements(d, "rear")}
    for k in range(2):
        assert rear[f"vcp-{k}"]["ref"] == "juniper/ex4200-vcp-port@1"
        assert rear[f"vcp-{k}"]["rel-pos"] == k
    assert rear["mgmt"]["ref"] == "common/rj45-eth@1"
    assert rear["console"]["ref"] == "std/rj45@2"
    assert rear["usb"]["ref"] == "std/usb-a@1"
    assert rear["esd-rear-jack"]["ref"] == "common/esd-jack@1"
    assert rear["led-temp"]["ref"] == "common/led-dot@1"
    assert set(bays(d, "rear")) == {"fan-0", "psu-0", "psu-1"}
    assert d["groups"]["fans"]["attrs"]["redundancy"] == "n+0"
    legends = {s["text"] for s in d["views"]["rear"]["silkscreen"]}
    assert {"VCP-0", "VCP-1"} <= legends


# ------------------------------------------------- the field-replaceable units


@pytest.mark.parametrize("comp", sorted(PSUS))
def test_a_power_supply_states_its_part_number_and_output(comp):
    pn, watts, feed = PSUS[comp]
    c = contract(comp)
    assert c["class"] == "psu" and c["kind"] == "module"
    assert list(c["part-numbers"]) == [pn]
    assert c["attrs"]["part-number"] == pn
    assert c["attrs"]["power-output-w"] == watts
    if feed == "dc":
        # Table 13: 36 through 72 VDC, 7 A maximum
        assert c["attrs"]["inlet"] == "dc-terminal"
        assert "36-72" in c["attrs"]["input-voltage"]
    else:
        assert any(p["ref"] == "std/c14-inlet@1" for p in c["parts"])
        assert "100-240" in c["attrs"]["input-voltage"]


@pytest.mark.parametrize("comp", ["ex4200-pwr-600-ac", "ex4200-pwr-930-ac", "ex4200-pwr2-930-ac",
                                  "ex4200-pwr3-930-ac"])
def test_the_large_supplies_stand_out_of_the_chassis_by_2_25_in(comp):
    assert contract(comp)["attrs"]["depth-beyond-chassis-mm"] == pytest.approx(2.25 * INCH, abs=0.1)
    assert contract(comp)["attrs"]["weight-kg"] == 1.4  # Table 3: 3.1 lb


@pytest.mark.parametrize("comp", ["ex4200-pwr-320-ac", "ex4200-pwr-190-dc"])
def test_the_small_supplies_are_flush_with_the_chassis(comp):
    assert contract(comp)["attrs"]["depth-beyond-chassis-mm"] == 0
    assert contract(comp)["attrs"]["weight-kg"] == 1.1  # Table 3: 2.5 lb


def test_the_fan_tray_has_three_fans_and_cools_side_to_rear():
    c = contract(FAN)
    assert c["class"] == "fan"
    assert c["attrs"]["fans"] == 3 and c["attrs"]["airflow"] == "side-to-rear"


@pytest.mark.parametrize("dev", DEVICES)
def test_the_bays_accept_what_the_guide_lists(dev):
    d = load(dev)
    want = {f"juniper/{c}@1" for c in ACCEPTS[CLASS[dev]]} | {"juniper/ex4200-psu-cover@1"}
    for bid in ("psu-0", "psu-1"):
        assert set(bays(d, "rear")[bid]["accepts"]) == want
    assert bays(d, "rear")["fan-0"]["accepts"] == [f"juniper/{FAN}@1"]


@pytest.mark.parametrize("dev", DEVICES)
def test_the_default_build_ships_what_the_guide_says(dev):
    """Tables 1 and 37: one supply, a cover panel over the other slot, the fan tray, a cover panel
    over the uplink slot."""
    psu = DEVICES[dev][4]
    s = seated(load(dev), "ac")
    assert s == {"uplink": "ex4200-uplink-cover", "psu-0": psu, "psu-1": "ex4200-psu-cover",
                 "fan-0": FAN}


# ------------------------------------------------------------- configurations


@pytest.mark.parametrize("dev", DEVICES)
def test_each_configuration_lists_its_part_numbers(dev):
    d = load(dev)
    want = DEVICES[dev][6]
    assert set(d["configurations"]) == set(want)
    for cfg, pns in want.items():
        got = d["configurations"][cfg]
        assert got["kind"] == "orderable"
        assert list(got["part-numbers"]) == pns
    defaults = [c for c, v in d["configurations"].items() if v.get("default")]
    assert defaults == ["ac"]


@pytest.mark.parametrize("dev", DEVICES)
def test_the_dc_build_seats_the_190_w_supply_and_gives_no_poe(dev):
    d = load(dev)
    if "dc" not in d["configurations"]:
        # only the 8-PoE, fibre and 48-port copper models have a DC build in Table 1
        assert CLASS[dev] != "t"
        return
    assert d["configurations"]["dc"]["power"] == "dc"
    assert d["chassis"]["power"] == "ac"
    s = seated(d, "dc")
    assert s["psu-0"] == "ex4200-pwr-190-dc" and s["psu-1"] == "ex4200-psu-cover"
    assert s["fan-0"] == FAN
    assert PSUS["ex4200-pwr-190-dc"][2] == "dc"


def test_only_the_models_table_1_lists_have_dc_and_spare_chassis_builds():
    """Table 1: -DC for the -24T, -24F and -48T; -S for the -24F and -48T alone."""
    dcs = {k for k in DEVICES if "dc" in load(k)["configurations"]}
    spares = {k for k in DEVICES if "s" in load(k)["configurations"]}
    assert dcs == {"ex4200-24t", "ex4200-24f", "ex4200-48t"}
    assert spares == {"ex4200-24f", "ex4200-48t"}


@pytest.mark.parametrize("dev", ["ex4200-24f", "ex4200-48t"])
def test_the_spare_chassis_shows_its_supply_and_fan_bays_open(dev):
    s = seated(load(dev), "s")
    assert s["psu-0"] == s["psu-1"] == s["fan-0"] == ""
    assert s["uplink"] == "ex4200-uplink-cover"


@pytest.mark.parametrize("dev", DEVICES)
def test_a_poe_model_ships_a_supply_whose_budget_covers_its_ports(dev):
    """Table 9: 130 W for the 8-PoE models on 320 W, 410 W for the 24P on 600 W, 740 W on 930 W."""
    d = load(dev)
    ship = PSUS[DEVICES[dev][4]][1]
    budget = {8: (320, 130), 24: (600, 410), 48: (930, 740)}
    poe = DEVICES[dev][2]
    if dev.endswith("px"):
        assert ship == 930 and d["attrs"]["power"]["poe-budget-w"] == 740
    elif poe:
        want_psu, want_budget = budget[poe]
        assert ship == want_psu and d["attrs"]["power"]["poe-budget-w"] == want_budget
    else:
        assert "poe-budget-w" not in d["attrs"].get("power", {})


# ------------------------------------------------------------------- the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", DEVICES)
def test_the_dcim_types_export_one_per_orderable_configuration(target, dev):
    d = load(dev)
    folder = LIB / "exports" / target / "device-types" / "Juniper"
    for cfg in d["configurations"].values():
        assert cfg["kind"] == "orderable"
        pn = sorted(cfg["part-numbers"])[0]  # the exporter names a type after the first code
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == pn
        assert doc["u_height"] == 1.0  # Table 3: 1.75 in, one rack unit


@pytest.mark.parametrize("dev", DEVICES)
def test_the_exported_type_lists_the_front_ports_and_the_rear_management_ports(dev):
    _, n, *_ = DEVICES[dev]
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Juniper" / f"{DEVICES[dev][0]}.yaml").read_text())
    names = {i["name"] for i in doc["interfaces"]}
    assert {f"port-{k}" for k in range(n)} <= names
    # the 68-pin Virtual Chassis ports present ex4200-vcp and no DCIM has a port type for
    # them (NOT_A_DCIM_PORT), so a DCIM type does not list them
    assert "mgmt" in names and not {"vcp-0", "vcp-1"} & names
    assert not {f"port-{k}" for k in range(n, 48)} & names
    consoles = {c["name"] for c in doc.get("console-ports") or []}
    assert consoles  # the rear RJ-45 console


# ------------------------------------------------------------- the components


def test_the_new_components_are_family_prefixed():
    """Every juniper/ part these devices place or seat is the EX4200's own: no shared component."""
    refs = set()
    for dev in DEVICES:
        d = load(dev)
        for view in ("front", "rear"):
            for p in placements(d, view):
                refs.add(p["ref"])
            for b in bays(d, view).values():
                refs.update(b["accepts"])
    mine = {r for r in refs if r.startswith("juniper/")}
    assert mine and all(r.startswith("juniper/ex4200-") for r in mine)


@pytest.mark.parametrize("comp", sorted(PSUS) + [FAN] + COVERS +
                         ["ex4200-lcd-button", "ex4200-vcp-port"])
def test_each_component_states_where_its_size_came_from(comp):
    c = contract(comp)
    assert c["size-confidence"]
    assert all(isinstance(v, str) for v in c["provenance"].values())


# ------------------------------------------------------------- the logo is not drawn


@pytest.mark.parametrize("dev", DEVICES)
def test_no_face_draws_the_vendor_logo_and_the_front_reserves_its_place(dev):
    """A vendor logo is never drawn; the front holds a logo-zone over where the mark sits (the
    top strip's left end in the datasheet photographs, 6.4 to 22.2 mm across and 1.0 to 5.1 down),
    and the plain EX4200 legend stays."""
    d = load(dev)
    for name, view in d["views"].items():
        drawn = list(view.get("silkscreen") or []) + list((view.get("panel") or {}).get("decor") or [])
        words = {str(i.get("text", "")).upper() for i in drawn}
        assert not words & {"JUNIPER", "NETWORKS"}, name
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1
    z = zones[0]
    assert 5.5 <= z["at"][0] <= 7.5 and 0.5 <= z["at"][1] <= 2.0
    assert 14.0 <= z["size"]["w"] <= 18.0 and 3.5 <= z["size"]["h"] <= 5.0
    assert "not drawn" in z["label"]
    assert "EX4200" in {s.get("text") for s in d["views"]["front"]["silkscreen"]}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_model_plate_prints_the_poe_count_or_the_sfp_count(dev):
    """The photographs print 8PoE, 24PoE, 48PoE or 24SFP after EX4200 on the plate."""
    _, n, poe, kind, *_ = DEVICES[dev]
    want = "24SFP" if kind.startswith("std/sfp") else f"{max(poe, 8) if poe <= 8 else n}PoE"
    legends = {t for _, t, _ in printed(load(dev), "ac")}
    assert want in legends
