"""The Juniper EX4000 line, from the EX4000 Switch Hardware Guide (published 2026-01-20): ten fixed access switches.

One device per front panel, and the guide shows each of the ten models once: the PoE, multigigabit and non-PoE models do not share a
front, and the guide lists no DC, back-to-front, -S or -TAA variant, so each device carries one configuration, its own part number.
The supply and the fans are built into every EX4000 chassis ("The EX4000 switch models have inbuilt fixed fans and power supply
units"), so there is no bay, no module and no component in this slice.

What the guide fixes, and so what these tests hold:
  Table 26                 the envelope of each model - height, width, depth and weight
  Tables 7 to 25           the ports of each model, their number and their kind
  Figures 1 to 20          what is on each face, and the numbering printed on the metal
  Tables 6 to 24           the cooling of each model - no fan on the 8- and 12-port models, one to three fans on the others
  the datasheet, Table 1   the part number of each model
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

IN = 25.4
# Table 26 (inches as printed, the centimetre figure beside each), Tables 7 to 25 (ports), Tables 6 to 24 (fans)
MODELS = {
    "ex4000-8p": {"h_in": 1.75, "w_cm": 26.40, "d_cm": 24.5, "kg": 2.6, "fans": 0, "poe": "802.3at", "front_mgmt": True,
                  "jacks": 8, "jack_ref": "common/rj45-eth@1", "np": 2, "sfp": {"uplink": [2, 3]}, "mg": 0},
    "ex4000-12t": {"h_in": 1.75, "w_cm": 26.40, "d_cm": 24.5, "kg": 2.3, "fans": 0, "poe": None, "front_mgmt": True,
                   "jacks": 12, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-12p": {"h_in": 1.75, "w_cm": 26.40, "d_cm": 25.37, "kg": 3.2, "fans": 0, "poe": "802.3at", "front_mgmt": True,
                   "jacks": 12, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-12mp": {"h_in": 1.75, "w_cm": 26.40, "d_cm": 25.37, "kg": 3.2, "fans": 0, "poe": "802.3bt", "front_mgmt": True,
                    "jacks": 12, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 4},
    "ex4000-24p": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 25.8, "kg": 4.2, "fans": 2, "poe": "802.3at", "front_mgmt": False,
                   "jacks": 24, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-24t": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 21.40, "kg": 2.9, "fans": 1, "poe": None, "front_mgmt": False,
                   "jacks": 24, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-24mp": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 25.80, "kg": 4.1, "fans": 2, "poe": "802.3bt", "front_mgmt": False,
                    "jacks": 24, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 4},
    "ex4000-48p": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 30.40, "kg": 4.9, "fans": 3, "poe": "802.3at", "front_mgmt": False,
                   "jacks": 48, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-48t": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 25.8, "kg": 3.6, "fans": 1, "poe": None, "front_mgmt": False,
                   "jacks": 48, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 0},
    "ex4000-48mp": {"h_in": 1.71, "w_cm": 44.10, "d_cm": 30.40, "kg": 5.3, "fans": 3, "poe": "802.3bt", "front_mgmt": False,
                    "jacks": 48, "jack_ref": "common/rj45-ganged-eth@1", "np": 0, "sfp": {"vcp": [0, 1], "uplink": [2, 3]}, "mg": 8},
}
DEVICES = sorted(MODELS)
RACK = [n for n in DEVICES if MODELS[n]["w_cm"] > 40]
COMPACT = [n for n in DEVICES if MODELS[n]["w_cm"] < 40]


def part_number(name):
    return name.upper()


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def by_id(dev, view):
    return {p["id"]: p for p in placements(dev, view)}


def silk_texts(dev, view):
    return [s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")]


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_26(name):
    m = MODELS[name]
    ch = load_device(name)["chassis"]
    if name in COMPACT:
        # desktop mounting is the default for these four (hardware guide, printed page 85)
        assert ch["mount"] == "desktop" and "ru" not in ch
    else:
        assert ch["ru"] == 1
    # Table 26 prints 1.75 in (4.44 cm) for the 8- and 12-port models and 1.71 in (4.34 cm) for the others
    assert ch["height"] == pytest.approx({1.75: 44.4, 1.71: 43.4}[m["h_in"]], abs=0.05)
    assert ch["width"] == pytest.approx(m["w_cm"] * 10, abs=0.1)
    assert ch["depth"] == pytest.approx(m["d_cm"] * 10, abs=0.3)
    assert ch["weight-kg"] == pytest.approx(m["kg"], abs=0.01)


@pytest.mark.parametrize("name", DEVICES)
def test_the_faces_are_sized_from_the_envelope(name):
    d = load_device(name)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


@pytest.mark.parametrize("name", RACK)
def test_the_24_and_48_port_models_are_the_guides_17_36_inch_body(name):
    ch = load_device(name)["chassis"]
    assert ch["width"] == 441.0 and ch["height"] == 43.4
    # the two positions the mounting topics name: the front-mount brackets, and the 2 in. recessed ones
    pos = ch["ears"]["positions"]
    assert [(p["name"], p["at"], bool(p.get("default"))) for p in pos] == [("flush", 0, True), ("recessed", 50.8, False)]


@pytest.mark.parametrize("name", COMPACT)
def test_the_8_and_12_port_models_are_the_guides_10_39_inch_desk_unit(name):
    ch = load_device(name)["chassis"]
    assert ch["width"] == 264.0 and ch["height"] == 44.4
    # the guide gives no bracket position for the optional EX4000-2PST-RMK, so no ear is stated
    assert "ears" not in ch


# --- the front ports ---------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_guides_jacks_numbered_from_zero_as_printed(name):
    d = load_device(name)
    m = MODELS[name]
    pl = by_id(d, "front")
    ports = [pl[f"port-{i}"] for i in range(m["jacks"])]
    assert not [i for i in pl if i.startswith("port-") and int(i.split("-")[1]) >= m["jacks"]]
    for i, p in enumerate(ports):
        assert p["ref"] == m["jack_ref"]
        assert p["rel-pos"] == i
        assert p["group"] == ("mg" if i < m["mg"] else "rj45")
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
             if str(s.get("for", "")).startswith("port-") and s.get("text", "").isdigit()}
    assert texts == {f"port-{i}": str(i) for i in range(m["jacks"])}


@pytest.mark.parametrize("name", DEVICES)
def test_the_jacks_stand_in_two_rows_with_the_even_number_on_top(name):
    pl = by_id(load_device(name), "front")
    n = MODELS[name]["jacks"]
    for col in range(n // 2):
        upper, lower = pl[f"port-{2 * col}"], pl[f"port-{2 * col + 1}"]
        assert upper["at"][0] == lower["at"][0]
        assert upper["at"][1] < lower["at"][1]
        assert upper.get("rotate") == 180 and not lower.get("rotate")
    assert len({p["at"][1] for i, p in pl.items() if i.startswith("port-") and int(i[5:]) % 2 == 0}) == 1


@pytest.mark.parametrize("name", [n for n in DEVICES if n != "ex4000-8p"])
def test_the_ganged_jacks_keep_the_registry_pitch_within_a_shell(name):
    pl = by_id(load_device(name), "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    n = MODELS[name]["jacks"] // 2
    assert len(xs) == n
    assert steps.count(13.97) == n - (n // 6)
    shells = n // 6
    # 48 ports: a 3.98 mm gutter between shells; 24 ports: 10.1 mm; 12 ports: one shell
    gap = {4: 17.95, 2: 24.07, 1: None}[shells]
    assert all(s == 13.97 or s == gap for s in steps)


def test_the_8p_has_eight_poe_jacks_and_two_non_poe_jacks_that_abut():
    d = load_device("ex4000-8p")
    pl = by_id(d, "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    assert len(xs) == 4 and [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [15.8, 15.8, 15.8]
    np = [pl["np-0"], pl["np-1"]]
    assert {p["ref"] for p in np} == {"common/rj45-eth@1"} and {p["group"] for p in np} == {"np"}
    assert np[0]["at"][0] == np[1]["at"][0] and np[0]["at"][1] < np[1]["at"][1]
    # the guide: the two ports 0 and 1 do not support PoE
    assert "poe" not in d["groups"]["np"]["attrs"] and d["groups"]["rj45"]["attrs"]["poe"] == "802.3at"
    printed = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
               if str(s.get("for", "")).startswith("np-") and s.get("text", "").isdigit()}
    assert printed == {"np-0": "0", "np-1": "1"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_sfp_plus_ports_are_the_guides_and_numbered_as_printed(name):
    d = load_device(name)
    pl = by_id(d, "front")
    sfp = MODELS[name]["sfp"]
    cages = {}
    for group, nums in sfp.items():
        for n in nums:
            cages[f"{group}-{n}"] = group
    assert {i for i in pl if i.startswith(("vcp-", "uplink-")) and not i.startswith("led-")} == set(cages)
    for i, group in cages.items():
        p = pl[i]
        assert p["ref"] == ("std/sfp@1" if name == "ex4000-8p" else "std/sfp-ganged@1")
        assert p["group"] == group
        assert p["rel-pos"] == int(i.split("-")[1])
        assert d["groups"][group]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    # a Link Activity lamp and a Status lamp for each cage
    assert len([i for i in pl if i.startswith(("led-vcp-", "led-uplink-"))]) == 2 * len(cages)
    printed = sorted(s["text"] for s in d["views"]["front"]["silkscreen"]
                     if str(s.get("for", "")).startswith(("vcp-", "uplink-")) and s.get("text", "").isdigit())
    assert printed == sorted(str(int(i.split("-")[1])) for i in cages)


@pytest.mark.parametrize("name", [n for n in DEVICES if n not in ("ex4000-8p",) and n.split("-")[1][:2] in ("24", "48")])
def test_the_24_and_48_port_models_have_two_columns_of_stacked_sfp_plus_cages(name):
    pl = by_id(load_device(name), "front")
    cages = [pl[i] for i in ("vcp-0", "vcp-1", "uplink-2", "uplink-3")]
    assert pl["vcp-0"]["at"][0] == pl["vcp-1"]["at"][0] and pl["uplink-2"]["at"][0] == pl["uplink-3"]["at"][0]
    assert pl["vcp-0"]["at"][1] < pl["vcp-1"]["at"][1]
    assert pl["vcp-1"].get("rotate") == 180 and not pl["vcp-0"].get("rotate")
    assert len([i for i in pl if i.startswith("led-vcp-") or i.startswith("led-uplink-")]) == 8
    assert {c["ref"] for c in cages} == {"std/sfp-ganged@1"}


@pytest.mark.parametrize("name", [n for n in DEVICES if n.split("-")[1][:2] in ("12",)])
def test_the_12_port_models_have_four_abutting_sfp_plus_cages_in_one_row(name):
    pl = by_id(load_device(name), "front")
    xs = [pl[i]["at"][0] for i in ("vcp-0", "vcp-1", "uplink-2", "uplink-3")]
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [14.25, 14.25, 14.25]
    assert len({pl[i]["at"][1] for i in ("vcp-0", "vcp-1", "uplink-2", "uplink-3")}) == 1
    assert len([i for i in pl if i.startswith("led-vcp-") or i.startswith("led-uplink-")]) == 8


@pytest.mark.parametrize("name", DEVICES)
def test_poe_and_multigigabit_are_stated_on_the_jack_groups(name):
    m = MODELS[name]
    g = load_device(name)["groups"]
    assert g["rj45"]["attrs"]["media"] == "rj45" and g["rj45"]["attrs"]["speed"] == "1g"
    assert g["rj45"]["attrs"].get("poe") == m["poe"]
    if m["mg"]:
        assert g["mg"]["attrs"] == {"media": "rj45", "speed": "2.5g", "poe": "802.3bt"}
    else:
        assert "mg" not in g


@pytest.mark.parametrize("name", [n for n in DEVICES if MODELS[n]["mg"]])
def test_the_mg_models_bracket_their_multigigabit_ports_as_printed(name):
    d = load_device(name)
    n = MODELS[name]["mg"]
    mg = {i for i, p in by_id(d, "front").items() if p.get("group") == "mg"}
    assert mg == {f"port-{i}" for i in range(n)}
    assert "MG" in silk_texts(d, "front")
    outline = [s for s in d["views"]["front"]["silkscreen"] if s.get("id") == "mg-outline"]
    assert len(outline) == 1 and sorted(outline[0]["for"]) == sorted(mg)


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_status_lamps_usb_and_reset(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert {"led-sys", "led-mst", "led-cld"} <= set(pl)
    assert pl["usb"]["ref"] == "std/usb-a@1" and pl["usb"]["skin"] == "usb2"
    assert pl["reset-pinhole"]["ref"] == "juniper/ex4100-reset-pinhole@1"
    legends = set(silk_texts(d, "front"))
    assert {"SYS", "MST", "CLD", "EX4000"} <= legends
    model = [t for t in legends if t.startswith("PoE") or t.startswith("MG PoE")]
    assert bool(model) == bool(MODELS[name]["poe"])


@pytest.mark.parametrize("name", [n for n in DEVICES if MODELS[n]["front_mgmt"]])
def test_the_8_and_12_port_models_carry_the_management_and_console_ports_on_the_front(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1" and pl["con"]["ref"] == "std/rj45@2"
    assert pl["con"]["attrs"]["role"] == "console"
    assert {"MGMT", "CON"} <= set(silk_texts(d, "front"))
    assert not {"mgmt", "con"} & set(by_id(d, "rear"))


@pytest.mark.parametrize("name", [n for n in DEVICES if not MODELS[n]["front_mgmt"]])
def test_the_24_and_48_port_models_carry_the_management_and_console_ports_on_the_rear(name):
    d = load_device(name)
    pl = by_id(d, "rear")
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1" and pl["con"]["ref"] == "std/rj45@2"
    assert pl["con"]["attrs"]["role"] == "console"
    assert {"MGMT", "CON"} <= set(silk_texts(d, "rear"))
    assert not {"mgmt", "con"} & set(by_id(d, "front"))


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_ac_inlet_the_earthing_terminal_and_the_guides_fans(name):
    d = load_device(name)
    pl = by_id(d, "rear")
    assert pl["ac-inlet"]["ref"] == "std/c14-inlet@1" and pl["ac-inlet"]["group"] == "power-input"
    decor = {x.get("id"): x for x in d["views"]["rear"]["panel"]["decor"]}
    assert {"earth-plate", "earth-hole-1", "earth-hole-2"} <= set(decor)
    fans = [x for x in decor.values() if x.get("kind") == "fan-grille"]
    assert len(fans) == MODELS[name]["fans"]
    if MODELS[name]["fans"] == 0:
        assert d["chassis"].get("airflow") is None
    else:
        assert d["chassis"]["airflow"] == "front-to-back"
        assert d["attrs"]["thermal"]["cooling"].split()[0] in ("one", "two", "three")


@pytest.mark.parametrize("name", [n for n in DEVICES if n in ("ex4000-12p", "ex4000-12mp")])
def test_the_12p_and_12mp_rears_have_two_heat_sink_vents(name):
    d = load_device(name)
    vents = [x for x in d["views"]["rear"]["panel"]["decor"] if str(x.get("id", "")).startswith("heatsink-vent")]
    assert len(vents) == 2
    assert any(s.get("id") == "heat-triangle" for s in d["views"]["rear"]["silkscreen"])


# --- the built-in supply and fans are the chassis, not bays ------------------

@pytest.mark.parametrize("name", DEVICES)
def test_no_bay_and_no_supply_or_fan_component_is_modelled(name):
    d = load_device(name)
    for view in d["views"]:
        assert not bays(d, view), f"{name} {view}: the guide's supply and fans are built in"
        for p in placements(d, view):
            ref = p["ref"].split("/")[-1]
            assert not any(w in ref for w in ("psu", "fan", "jpsu")), (name, view, p["id"])
    note = " ".join(d["provenance"]["built-in-power-and-fans"]["note"].split())
    assert "part of the chassis and not a bay" in note.replace("not bays", "not a bay") and "no part number" in note


def test_this_slice_adds_no_component():
    """Every part is a registry, common or EX4100 one: the supply and the fans are built in, and no
    module bay exists on any EX4000 model."""
    assert not list(COMP.glob("ex4000-*"))


# --- the configurations and the DCIM export ----------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_model_has_one_configuration_carrying_its_part_number(name):
    d = load_device(name)
    assert list(d["configurations"]) == ["ac"]
    cfg = d["configurations"]["ac"]
    assert set(cfg["part-numbers"]) == {part_number(name)}
    assert cfg["kind"] == "base" and cfg["default"] is True
    assert d["chassis"]["power"] == "ac"


@pytest.mark.parametrize("name", DEVICES)
def test_the_dcim_device_type_exports_with_the_guides_u_height(name):
    part = part_number(name)
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        # 1.71 in is one rack unit; the four desktop models are no rack unit
        assert doc["u_height"] == (0.0 if name in COMPACT else 1.0)
        assert not doc.get("module-bays")


# --- the power and PoE figures ------------------------------------------------

POWER = {  # datasheet Table 2 (maximum system power without PoE), Table 35 (PoE budget)
    "ex4000-8p": (30, 120), "ex4000-12t": (34, None), "ex4000-12p": (34, 240), "ex4000-12mp": (40, 240),
    "ex4000-24p": (51, 370), "ex4000-24t": (43, None), "ex4000-24mp": (57, 480),
    "ex4000-48p": (71, 740), "ex4000-48t": (63, None), "ex4000-48mp": (92, 960),
}


@pytest.mark.parametrize("name", DEVICES)
def test_the_power_figures_are_the_datasheets_and_the_guides(name):
    p = load_device(name)["attrs"]["power"]
    mx, poe = POWER[name]
    assert p["power-max-w"] == mx
    assert p.get("poe-budget-w") == poe


# --- the logo, the sources ---------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_vendor_wordmark_is_a_reserved_zone_not_text(name):
    d = load_device(name)
    drawn = [t.upper() for t in silk_texts(d, "front")]
    assert not any("JUNIPER" in t or "MIST" in t for t in drawn) and "NETWORKS" not in drawn
    zones = [r for r in d["views"]["front"].get("regions") or [] if r.get("id") == "logo-zone"]
    assert len(zones) == 1
    z = zones[0]
    assert z["at"][0] < 6 and z["at"][1] < 5
    assert 18 <= z["size"]["w"] <= 30 and 5 <= z["size"]["h"] <= 9


@pytest.mark.parametrize("name", DEVICES)
def test_the_sources_are_cited_with_their_hashes(name):
    d = load_device(name)
    refs = {r["title"].split(" (")[0]: r for r in d["references"]}
    assert set(refs) == {"EX4000 Switch Hardware Guide", "EX4000 Line of Ethernet Switches Datasheet"}
    assert refs["EX4000 Switch Hardware Guide"]["sha256"] == "a4faf391f19a72b69d4e61cf141a71fec81788a1480f894d563751157075e967"
    note = " ".join(d["provenance"]["sources"]["note"].split())
    assert "published 2026-01-20" in note and f"ex4000-{name.split('-')[1]}-front-high.jpg" in note


@pytest.mark.parametrize("name", DEVICES)
def test_the_estimated_positions_say_how(name):
    prov = load_device(name)["provenance"]
    for key in ("front-layout", "rear", "scale"):
        assert prov[key]["confidence"] in ("estimated", "photo-measured")
        assert "px" in " ".join(prov[key]["note"].split()) or "photograph" in prov[key]["note"]
    assert prov["scale"]["confidence"] == "photo-measured"
