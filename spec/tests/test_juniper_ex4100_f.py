"""The Juniper EX4100-F-24T, -24P, -48T and -48P, from the EX4100-F Switch Hardware Guide (PDF created 2026-10-01).

One device per front panel: the PoE and non-PoE models do not share a rear (the PoE models have a second fan,
a different earthing and ESD arrangement and a deeper chassis) and the 24- and 48-port models differ in their
jacks. Each model ships in one configuration, because the guide lists no other part number for any of them.

What the guide fixes, and so what these tests hold:
  Tables 11, 13, 15, 17, 18   the envelope - 1.72 in high, 17.36 in wide, the depth and weight of each model
  Tables 10, 12, 14, 16       the one part number of each model
  Figures 12 to 27            the ports, their count and numbering, and what is on the rear
  Tables 3, 10, 12, 14, 16    the supply and the fans are built into the chassis (the guide has no replacement
                              procedure for either), so no bay and no module is modelled for them
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# Tables 11/13/15/17/18 (centimetres as printed), 10/12/14/16 (part numbers), Figures 12 to 27 (the rest)
MODELS = {
    "ex4100-f-24t": {"part": "EX4100-F-24T", "ports": 24, "poe": False, "depth_cm": 25.65, "weight_kg": 3.52,
                     "fans": 1, "mode_leds": 3, "ac_legend": "2.5A Max"},
    "ex4100-f-24p": {"part": "EX4100-F-24P", "ports": 24, "poe": True, "depth_cm": 31.13, "weight_kg": 4.745,
                     "fans": 2, "mode_leds": 4, "ac_legend": "7A Max"},
    "ex4100-f-48t": {"part": "EX4100-F-48T", "ports": 48, "poe": False, "depth_cm": 25.65, "weight_kg": 3.885,
                     "fans": 1, "mode_leds": 3, "ac_legend": "1.2A Max"},
    "ex4100-f-48p": {"part": "EX4100-F-48P", "ports": 48, "poe": True, "depth_cm": 31.13, "weight_kg": 5.2,
                     "fans": 2, "mode_leds": 4, "ac_legend": "12A Max"},
}
DEVICES = sorted(MODELS)


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
def test_the_envelope_is_the_guides_table(name):
    ch = load_device(name)["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(43.7, abs=0.1)
    assert ch["width"] == pytest.approx(440.9, abs=0.1)
    assert ch["depth"] == pytest.approx(MODELS[name]["depth_cm"] * 10, abs=0.3)
    assert ch["weight-kg"] == pytest.approx(MODELS[name]["weight_kg"], abs=0.01)
    assert ch["airflow"] == "front-to-back"


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


# --- the front ports ---------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_guides_jacks_numbered_from_zero_as_printed(name):
    d = load_device(name)
    n = MODELS[name]["ports"]
    pl = by_id(d, "front")
    ports = [pl[f"port-{i}"] for i in range(n)]
    assert not [i for i in pl if i.startswith("port-") and int(i.split("-")[1]) >= n]
    for i, p in enumerate(ports):
        assert p["ref"] == "common/rj45-ganged-eth@1"
        assert p["rel-pos"] == i
        assert p["group"] == "rj45"
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
             if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert texts == {f"port-{i}": str(i) for i in range(n)}


@pytest.mark.parametrize("name", DEVICES)
def test_the_jacks_stand_in_two_rows_with_the_even_number_on_top(name):
    pl = by_id(load_device(name), "front")
    n = MODELS[name]["ports"]
    for col in range(n // 2):
        upper, lower = pl[f"port-{2 * col}"], pl[f"port-{2 * col + 1}"]
        assert upper["at"][0] == lower["at"][0]
        assert upper["at"][1] < lower["at"][1]
        assert upper.get("rotate") == 180 and not lower.get("rotate")
    assert len({p["at"][1] for i, p in pl.items() if i.startswith("port-") and int(i[5:]) % 2 == 0}) == 1


@pytest.mark.parametrize("name", DEVICES)
def test_the_jacks_pitch_and_shells(name):
    d = load_device(name)
    pl = by_id(d, "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    cols = MODELS[name]["ports"] // 2
    assert len(xs) == cols
    shells = [x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell"]
    if MODELS[name]["ports"] == 48:
        # three shells of eight on the registry's 13.97, a 5.6 mm gutter between shells
        assert steps.count(13.97) == 21 and steps.count(19.57) == 2
        assert len(shells) == 3
    else:
        # a shell of four on 15.83 (Figure 12 and 16 read 15.8) and a shell of eight on 13.97
        assert steps.count(15.83) == 3 and steps.count(13.97) == 7 and len(steps) == 11
        assert len(shells) == 2


def test_the_four_left_columns_of_a_24_port_model_are_wider_than_the_registry_pitch():
    for name in ("ex4100-f-24t", "ex4100-f-24p"):
        note = " ".join(load_device(name)["provenance"]["ports"]["note"].split())
        assert "NOT on that pitch" in note and "15.8 mm" in note


@pytest.mark.parametrize("name", DEVICES)
def test_two_groups_of_four_sfp_plus_cages_stand_two_by_two(name):
    pl = by_id(load_device(name), "front")
    for prefix in ("vcp", "uplink"):
        cages = [pl[f"{prefix}-{i}"] for i in range(4)]
        assert not [i for i in pl if i.startswith(prefix + "-") and "led" not in i and int(i.split("-")[1]) > 3]
        assert {c["ref"] for c in cages} == {"std/sfp-ganged@1"}
        assert [c["rel-pos"] for c in cages] == [0, 1, 2, 3]
        assert {c["group"] for c in cages} == {prefix}
        for col in range(2):
            upper, lower = cages[2 * col], cages[2 * col + 1]
            assert upper["at"][0] == lower["at"][0] and upper["at"][1] < lower["at"][1]
            # the stacked pair: upper upright, lower turned 180 (docs/pluggables-3d-design.md)
            assert not upper.get("rotate") and lower.get("rotate") == 180
        assert cages[2]["at"][0] - cages[0]["at"][0] == pytest.approx(14.25)
        assert lamps_of(pl, prefix) == 8
    assert pl["uplink-0"]["at"][0] > pl["vcp-3"]["at"][0]
    assert pl["vcp-0"]["at"][0] > max(p["at"][0] for i, p in pl.items() if i.startswith("port-"))


def lamps_of(pl, prefix):
    return len([i for i in pl if i.startswith(f"led-{prefix}-")])


@pytest.mark.parametrize("name", DEVICES)
def test_the_cage_groups_print_their_numbers_and_the_uplink_bracket(name):
    d = load_device(name)
    texts = silk_texts(d, "front")
    assert "UPLINK" in texts and "CON" in texts
    # the layout's named arrow marks are expanded to filled paths in device.yaml
    marked = {s["for"] for s in d["views"]["front"]["silkscreen"] if s.get("path") and s.get("filled")}
    for prefix in ("vcp", "uplink"):
        for i in range(4):
            assert f"{prefix}-{i}" in marked


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_guides_status_lamps_button_and_console(name):
    d = load_device(name)
    m = MODELS[name]
    pl = by_id(d, "front")
    assert {"led-sys", "led-alm", "led-mst", "led-cld"} <= set(pl)
    modes = {i for i in pl if i in ("led-spd", "led-dx", "led-en", "led-poe")}
    assert len(modes) == m["mode_leds"]
    assert ("led-poe" in modes) == m["poe"]
    assert pl["btn-mode"]["ref"] == "common/reset-button@1"
    assert pl["usb-c"]["ref"] == "std/usb-c@1" and pl["usb-c"]["attrs"]["role"] == "console"
    legends = set(silk_texts(d, "front"))
    assert {"SYS", "ALM", "MST", "CLD", "SPD", "DX", "EN", "CON", "EX4100-F"} <= legends
    assert ("PoE" in legends) == m["poe"] and ("PoE+" in legends) == m["poe"]


@pytest.mark.parametrize("name", DEVICES)
def test_poe_is_stated_on_the_jacks_of_the_poe_models_only(name):
    g = load_device(name)["groups"]["rj45"]["attrs"]
    assert g["media"] == "rj45" and g["speed"] == "1g"
    assert ("poe" in g) == MODELS[name]["poe"]


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_management_console_usb_and_esd_ports(name):
    d = load_device(name)
    pl = by_id(d, "rear")
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert pl["usb"]["ref"] == "std/usb-a@1"
    assert pl["console-rj45"]["ref"] == "std/rj45@2"
    assert pl["esd-rear-jack"]["ref"] == "common/esd-jack@1"
    assert pl["console-rj45"]["attrs"]["role"] == "console"
    decor = {x.get("id") for x in d["views"]["rear"]["panel"]["decor"]}
    assert "earth-terminal" in decor and not {"earth-hole-1", "earth-hole-2"} & decor
    plate = next(x for x in d["views"]["rear"]["panel"]["decor"] if x["id"] == "earth-terminal")
    # the two holes the figure reads 15.7 mm apart are a placed pair of bare M5 holes on the 5/8 in. pitch of the lug the guide names
    assert pl["ground-pair"]["ref"] == "common/ground-hole-pair-5-8-m5@1"
    assert plate["size"][0] == pytest.approx(31.6, abs=0.3)


@pytest.mark.parametrize("name", DEVICES)
def test_the_power_input_and_fans(name):
    d = load_device(name)
    fans = [x for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert len(fans) == MODELS[name]["fans"]
    assert by_id(d, "rear")["ac-inlet"]["ref"] == "std/c14-inlet@1"
    assert any(MODELS[name]["ac_legend"] in t for t in silk_texts(d, "rear"))


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_five_edge_screws(name):
    d = load_device(name)
    screws = [p for p in placements(d, "rear") if p["ref"] == "common/screw-head@1"]
    assert len(screws) == 5
    xs = [p["at"][0] for p in screws]
    assert xs == sorted(xs)
    assert all(34 <= p["at"][1] <= 38 for p in screws)


def test_the_poe_rears_have_the_earth_symbol_above_the_console_and_the_t_rears_beside_the_plate():
    for name in DEVICES:
        pl = by_id(load_device(name), "rear")
        plate_x = 54.0
        if MODELS[name]["poe"]:
            assert pl["earth-mark"]["at"][0] < plate_x
            assert pl["esd-rear-jack"]["at"][0] > 90
        else:
            assert pl["earth-mark"]["at"][0] > plate_x + 31
            assert pl["esd-rear-jack"]["at"][0] < 90


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
    assert "built-in" in note and "hot-removable" in note and "no removal or replacement procedure" in note


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_model_has_the_one_configuration_the_guide_lists(name):
    d = load_device(name)
    assert list(d["configurations"]) == ["ac"]
    cfg = d["configurations"]["ac"]
    assert cfg["kind"] == "orderable" and cfg["default"] is True
    assert set(cfg["part-numbers"]) == {MODELS[name]["part"]}
    assert "bays" not in cfg and "views" not in cfg


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_dcim_device_types_export_one_per_configuration(name):
    part = MODELS[name]["part"]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0
        assert not doc.get("module-bays")


# --- the logo, the sources and the components --------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_vendor_wordmark_is_a_reserved_zone_not_text(name):
    d = load_device(name)
    drawn = [t.upper() for t in silk_texts(d, "front")]
    assert not any("JUNIPER" in t for t in drawn) and "NETWORKS" not in drawn
    zones = [r for r in d["views"]["front"].get("regions") or [] if r.get("id") == "logo-zone"]
    assert len(zones) == 1
    z = zones[0]
    assert z["at"][0] < 10 and z["at"][1] < 6
    assert 18 <= z["size"]["w"] <= 30 and 5 <= z["size"]["h"] <= 9
    assert "EX4100-F" in drawn


@pytest.mark.parametrize("name", DEVICES)
def test_the_sources_are_cited_and_the_conflicts_recorded(name):
    d = load_device(name)
    prov = " ".join(" ".join(str(v) for v in d["provenance"].values()).split())
    assert "EX4100-F Switch Hardware Guide" in prov
    assert "a00150781enw" in prov and "did not answer" in prov
    assert d["references"][0]["url"].endswith("/ex4100-f.pdf") and len(d["references"][0]["sha256"]) == 64
    assert {g["what"] for g in d["gaps"]} >= {"vcp-speed", "four-faces"}
    if MODELS[name]["depth_cm"] > 30:
        assert "12.2 in" in prov and "311.3" in prov


def test_the_24_port_models_say_no_studio_photograph_exists():
    for name in ("ex4100-f-24t", "ex4100-f-24p"):
        note = " ".join(load_device(name)["provenance"]["sources"]["note"].split())
        assert "HTML 404" in note


def test_this_slice_adds_no_component():
    """Every part is a registry or common one: the guide's supply and fans are built in, and the earthing
    terminal is two bare holes in the metal."""
    assert not list(COMP.glob("ex4100-f-*"))
