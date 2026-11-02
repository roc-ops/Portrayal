"""The Juniper EX2300-24T, -24P, -48T and -48P, from the EX2300 Switch Hardware Guide (2025-08-12).

One device per front panel: the PoE and non-PoE models do not share a rear (the PoE models have a
second fan and a deeper chassis) and the 24- and 48-port models differ in their jacks. Each model's
-TAA and -VC part numbers, and the 24T's -DC, are `orderable` configurations of its device, because
the guide shows the same front panel for all of them.

What the guide fixes, and so what these tests hold:
  Table 3    the envelope - 1.75 in high, 17.4 in wide, 10.2 in deep without PoE and 12.2 in with it, and
             the weight of each model
  Table 1    the part numbers of each model and its variants
  Figures 3 to 13   the ports, their count and numbering, and what is on the rear
  Power Supply, Cooling System   the supply and the fans are built into the chassis, so no bay and no
             module is modelled for them

The second half of the file holds the rest of the family: the compact EX2300-C-12P and -12T and the
Multigigabit EX2300-24MP and -48MP (see the banner above `NEW`).
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# Table 3 (centimetres as printed), Table 1 (part numbers), Figures 3 to 13 (the rest)
MODELS = {
    "ex2300-24t": {"ports": 24, "poe": False, "depth_cm": 25.9, "weight_kg": 3.29, "fans": 1, "mode_leds": 3,
                   "configs": {"ac": "EX2300-24T", "dc": "EX2300-24T-DC", "taa": "EX2300-24T-TAA",
                               "vc": "EX2300-24T-VC"}},
    "ex2300-24p": {"ports": 24, "poe": True, "depth_cm": 30.98, "weight_kg": 4.49, "fans": 2, "mode_leds": 4,
                   "configs": {"ac": "EX2300-24P", "taa": "EX2300-24P-TAA", "vc": "EX2300-24P-VC"}},
    "ex2300-48t": {"ports": 48, "poe": False, "depth_cm": 25.9, "weight_kg": 3.76, "fans": 1, "mode_leds": 3,
                   "configs": {"ac": "EX2300-48T", "taa": "EX2300-48T-TAA", "vc": "EX2300-48T-VC"}},
    "ex2300-48p": {"ports": 48, "poe": True, "depth_cm": 30.98, "weight_kg": 5.02, "fans": 2, "mode_leds": 4,
                   "configs": {"ac": "EX2300-48P", "taa": "EX2300-48P-TAA", "vc": "EX2300-48P-VC"}},
}
DEVICES = sorted(MODELS)
PART_NUMBERS = [(name, cid, pn) for name, m in MODELS.items() for cid, pn in m["configs"].items()]


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def by_id(dev, view):
    return {p["id"]: p for p in placements(dev, view)}


def rear_of(dev, cid="ac"):
    """The rear panel the configuration wears."""
    cfg = dev["configurations"][cid]
    return (cfg.get("views") or {}).get("rear", "rear")


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_3(name):
    ch = load_device(name)["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(44.45, abs=0.1)
    assert ch["width"] == pytest.approx(441.9, abs=0.1)
    assert ch["depth"] == pytest.approx(MODELS[name]["depth_cm"] * 10, abs=0.3)
    assert ch["weight-kg"] == pytest.approx(MODELS[name]["weight_kg"], abs=0.01)


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
    # the printed numbers are on the silkscreen, one per jack, under its column
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"] if str(s.get("for", "")).startswith("port-")}
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
    n = MODELS[name]["ports"] // 2
    assert len(xs) == n
    # 13.97 within a shell of six, a 5.0 mm gutter between shells
    assert steps.count(13.97) == n - n // 6
    assert steps.count(18.97) == n // 6 - 1
    assert len([x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell"]) == n // 6


@pytest.mark.parametrize("name", DEVICES)
def test_four_uplinks_numbered_zero_to_three_in_one_row(name):
    d = load_device(name)
    pl = by_id(d, "front")
    ups = [pl[f"uplink-{i}"] for i in range(4)]
    assert not [i for i in pl if i.startswith("uplink-") and int(i.split("-")[1]) > 3]
    assert {u["ref"] for u in ups} == {"std/sfp-ganged@1"}
    assert len({u["at"][1] for u in ups}) == 1
    assert [u["rel-pos"] for u in ups] == [0, 1, 2, 3]
    xs = [u["at"][0] for u in ups]
    assert xs == sorted(xs) and xs[0] > max(p["at"][0] for i, p in pl.items() if i.startswith("port-"))
    # two lamps beside each numeral
    lamps = [i for i in pl if i.startswith("led-uplink-")]
    assert len(lamps) == 8


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_guides_status_lamps_button_and_console(name):
    d = load_device(name)
    m = MODELS[name]
    pl = by_id(d, "front")
    assert {"led-sys", "led-alm", "led-mst"} <= set(pl)
    modes = {i for i in pl if i in ("led-spd", "led-dx", "led-en", "led-poe")}
    assert len(modes) == m["mode_leds"]
    assert ("led-poe" in modes) == m["poe"]
    assert pl["btn-mode"]["ref"] == "common/reset-button@1"
    # the mini-USB console is the placed registry receptacle, and no decor draws it any more
    decor = {x.get("id") for x in d["views"]["front"]["panel"]["decor"]}
    assert not {"console", "console-opening", "console-pins"} & decor
    assert pl["console-usb"]["ref"] == "std/mini-usb@1" and pl["console-usb"]["attrs"]["role"] == "console"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"SYS", "ALM", "MST", "SPD", "DX", "EN", "CON", "0", "1", "2", "3"} <= legends
    assert ("POE" in legends) == m["poe"] and ("PoE+" in legends) == m["poe"]


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
    # the earthing terminal is a placed pair of bare 10-32 holes on the 5/8 in. pitch of its lug; the plate behind it is still drawn
    assert "earth-terminal" in decor and not {"earth-hole-1", "earth-hole-2"} & decor
    assert pl["ground-pair"]["ref"] == "common/ground-hole-pair-5-8-10-32@1"


@pytest.mark.parametrize("name", DEVICES)
def test_the_power_input_and_fans(name):
    d = load_device(name)
    fans = [x for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert len(fans) == MODELS[name]["fans"]
    assert by_id(d, "rear")["ac-inlet"]["ref"] == "std/c14-inlet@1"


def test_the_dc_rear_has_the_terminal_block_and_one_fan():
    d = load_device("ex2300-24t")
    assert d["configurations"]["dc"]["views"] == {"rear": "rear-dc"}
    assert d["views"]["rear-dc"]["face"] == "rear"
    pl = by_id(d, "rear-dc")
    decor = {x.get("id"): x for x in d["views"]["rear-dc"]["panel"]["decor"]}
    assert decor["dc-terminal"]["size"] == [52.6, 17.5]
    assert len([i for i in decor if i.startswith("dc-pole-") and not i.endswith("-screw")]) == 4
    assert "ac-inlet" not in pl and "dc-terminal" not in pl
    assert len([x for x in d["views"]["rear-dc"]["panel"]["decor"] if x.get("kind") == "fan-grille"]) == 1
    # the management cluster is the AC rear's
    for i in ("mgmt", "usb", "console-rj45", "esd-rear-jack"):
        assert i in pl
    assert d["views"]["rear-dc"]["size"] == d["views"]["rear"]["size"]


@pytest.mark.parametrize("name", [n for n in DEVICES if n != "ex2300-24t"])
def test_only_the_24t_has_a_dc_configuration(name):
    assert "dc" not in load_device(name)["configurations"]


# --- the built-in supply and fans are the chassis, not bays ------------------

@pytest.mark.parametrize("name", DEVICES)
def test_no_bay_and_no_supply_or_fan_component_is_modelled(name):
    d = load_device(name)
    for view in d["views"]:
        assert not bays(d, view), f"{name} {view}: the guide's supply and fans are built in"
        for p in placements(d, view):
            ref = p["ref"].split("/")[-1]
            assert not any(w in ref for w in ("psu", "fan", "jpsu")), (name, view, p["id"])
    assert "built-in" in d["provenance"]["built-in-power-and-fans"]["note"]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name,cid,part", PART_NUMBERS)
def test_each_configuration_carries_its_part_number(name, cid, part):
    cfg = load_device(name)["configurations"][cid]
    assert set(cfg["part-numbers"]) == {part}
    assert cfg["kind"] in ("base", "orderable")


@pytest.mark.parametrize("name", DEVICES)
def test_the_configurations_are_the_guides_and_one_is_default(name):
    d = load_device(name)
    assert set(d["configurations"]) == set(MODELS[name]["configs"])
    defaults = [c for c, v in d["configurations"].items() if v.get("default")]
    assert defaults == ["ac"]
    assert [c for c, v in d["configurations"].items() if v["kind"] == "base"] == ["ac"]


@pytest.mark.parametrize("name", DEVICES)
def test_the_variants_share_the_front_and_only_the_dc_changes_the_rear(name):
    d = load_device(name)
    for cid, cfg in d["configurations"].items():
        assert "bays" not in cfg
        assert (cfg.get("views") or {}).get("front") is None
        assert rear_of(d, cid) == ("rear-dc" if cid == "dc" else "rear")


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid,part", PART_NUMBERS)
def test_the_dcim_device_types_export_one_per_configuration(name, cid, part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0
        assert not doc.get("module-bays")


# --- review of the first look: the logo, the DC symbol, the screws, the sources ----------

def silk_texts(dev, view):
    return [s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")]


def layout_of(name):
    return yaml.safe_load((DEV / name / "layout.yaml").read_text())


@pytest.mark.parametrize("name", DEVICES)
def test_the_vendor_wordmark_is_a_reserved_zone_not_text(name):
    """The maker's lockup is a logo, so it is reserved with a logo-zone and never typed as text."""
    d = load_device(name)
    drawn = [t.upper() for t in silk_texts(d, "front")]
    assert not any("JUNIPER" in t and "RUNNING" not in t for t in drawn)
    assert "NETWORKS" not in drawn
    for x in d["views"]["front"]["panel"].get("decor") or []:
        assert "JUNIPER" not in str(x.get("text", "")).upper() and "NETWORKS" not in str(x.get("text", "")).upper()
    zones = [r for r in d["views"]["front"].get("regions") or [] if r.get("id") == "logo-zone"]
    assert len(zones) == 1
    z = zones[0]
    assert z["at"][0] < 10 and z["at"][1] < 6
    assert 18 <= z["size"]["w"] <= 30 and 5 <= z["size"]["h"] <= 9
    # what the unit prints as type stays
    assert "EX2300" in drawn and any(t.startswith("RUNNING") for t in drawn)
    if MODELS[name]["poe"]:
        assert "POE+" in [t.upper() for t in drawn]


def test_the_dc_legend_carries_the_dc_symbol():
    d = load_device("ex2300-24t")
    legend = [t for t in silk_texts(d, "rear-dc") if t.startswith("DC INPUT")]
    assert len(legend) == 1 and "⎓" in legend[0]


def test_the_dc_note_records_the_figure_13_conflict_and_the_winner():
    note = " ".join(load_device("ex2300-24t")["provenance"]["rear-dc"]["note"].split())
    assert "Figure 13 draws the earth symbol beside the plate" in note
    assert "the photograph does not" in note and "the photograph won" in note
    assert "Figure 13 draws the same arrangement" not in note


# the nine, eight and five screws the guide draws along the lower edge of the AC rears (Figures 11, 9, 12)
AC_SCREWS = {"ex2300-24t": 9, "ex2300-24p": 8, "ex2300-48t": 5}


@pytest.mark.parametrize("name,count", sorted(AC_SCREWS.items()))
def test_the_ac_rear_has_the_guides_edge_screws(name, count):
    d = load_device(name)
    screws = [p for p in placements(d, "rear") if p["ref"] == "common/screw-head@1"]
    assert len(screws) == count
    xs = [p["at"][0] for p in screws]
    assert xs == sorted(xs)
    assert all(36 <= p["at"][1] <= 39 for p in screws)
    assert all(0 < x < d["views"]["rear"]["size"]["w"] - 3.6 for x in xs)
    note = " ".join(d["provenance"]["rear-layout"]["note"].split())
    assert "estimated" in note and "edge screws" in note


@pytest.mark.parametrize("name,photo", [
    ("ex2300-24t", "juniper-ex2300-24t.front.png"),
    ("ex2300-24t", "juniper-ex2300-24t.rear.png"),
    ("ex2300-48p", "juniper-ex2300-48p.front.png"),
    ("ex2300-48p", "juniper-ex2300-48p.rear.png"),
])
def test_the_held_netbox_elevations_are_cited(name, photo):
    text = " ".join(str(v) for v in load_device(name)["provenance"].values())
    assert photo in text


def test_the_24t_ac_legend_discrepancy_and_the_top_face_photo_are_noted():
    prov = load_device("ex2300-24t")["provenance"]
    text = " ".join(" ".join(str(v) for v in prov.values()).split())
    assert "12A Max" in text and "2.5 A" in text
    top = " ".join(load_device("ex2300-48p")["views"]["top"]["empty"].split())
    assert "ex2300-48p-frontwtop-high.jpg" in top


# --- the components ----------------------------------------------------------

def test_this_slice_adds_no_component():
    """Every part is a registry or common one: the guide's supply and fans are built in, the mini-USB
    console is the registry's receptacle, and the one piece of metalwork no library part covers (the DC
    terminal block) is chassis art, because the DCIM export has no row that could carry a part of that
    kind."""
    assert not list(COMP.glob("ex2300-*"))


# =============================================================================================
# The rest of the family: the EX2300-C-12P and -12T (compact, fanless) and the EX2300-24MP and
# -48MP (Multigigabit, side-cooled), from the same EX2300 Switch Hardware Guide (2025-08-12).
#
#   Table 3    the envelope: the C models are 10.98 in wide, 1.72 in high and 9.45 in deep; the MP models
#              are 17.36 in wide and 1.7 in high, 10 in deep (24MP) and 14.45 in deep (48MP)
#   Table 1    the part numbers (the C models have -TAA and -VC; the MP models only the bare number)
#   Figures 1, 2, 5, 6 and 7, 8, 14, 15   the faces
#   Cooling system   the C models are fanless; the 24MP has three fans and the 48MP four, along the
#              right side panel; the supply is built in on all of them, so no bay and no module
# =============================================================================================

NEW = {
    "ex2300-c-12p": {"w": 279.0, "h": 43.6, "d": 238.0, "kg": 3.17, "airflow": "passive", "fans": 0, "poe": True,
                     "configs": {"ac": "EX2300-C-12P", "taa": "EX2300-C-12P-TAA", "vc": "EX2300-C-12P-VC"}},
    "ex2300-c-12t": {"w": 279.0, "h": 43.6, "d": 238.0, "kg": 2.48, "airflow": "passive", "fans": 0, "poe": False,
                     "configs": {"ac": "EX2300-C-12T", "taa": "EX2300-C-12T-TAA", "vc": "EX2300-C-12T-VC"}},
    "ex2300-24mp": {"w": 440.9, "h": 43.3, "d": 254.0, "kg": 4.0, "airflow": "side", "fans": 3, "poe": True,
                    "configs": {"ac": "EX2300-24MP"}},
    "ex2300-48mp": {"w": 440.9, "h": 43.3, "d": 367.1, "kg": 6.5, "airflow": "side", "fans": 4, "poe": True,
                    "configs": {"ac": "EX2300-48MP"}},
}
COMPACT = ["ex2300-c-12p", "ex2300-c-12t"]
MP = ["ex2300-24mp", "ex2300-48mp"]
NEW_PART_NUMBERS = [(n, c, p) for n, m in NEW.items() for c, p in m["configs"].items()]
# per device: the RJ-45 port count, the uplink count, the system lamps the guide names, and the speed of
# each run of jacks (first number, last number, speed) - the Multigigabit shell is the first on the
# 24MP (Figure 5, callout 4) and the middle one on the 48MP (Figure 6, callout 4)
FRONT = {
    "ex2300-c-12p": {"ports": 12, "uplinks": 2, "lamps": {"led-sys", "led-alm", "led-mst", "led-spd", "led-dx", "led-en", "led-poe"},
                     "speeds": [(0, 11, "1g")]},
    "ex2300-c-12t": {"ports": 12, "uplinks": 2, "lamps": {"led-sys", "led-alm", "led-mst", "led-spd", "led-dx", "led-en"},
                     "speeds": [(0, 11, "1g")]},
    "ex2300-24mp": {"ports": 24, "uplinks": 4, "lamps": {"led-mgt", "led-fan", "led-pw"},
                    "speeds": [(0, 7, "2.5g"), (8, 23, "1g")]},
    "ex2300-48mp": {"ports": 48, "uplinks": 6, "lamps": {"led-mgt", "led-fan", "led-pw", "led-act", "led-link"},
                    "speeds": [(0, 15, "1g"), (16, 31, "2.5g"), (32, 47, "1g")]},
}


def rotation(p):
    return p.get("rotate", 0)


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_envelope_is_table_3(name):
    d = load_device(name)
    ch, m = d["chassis"], NEW[name]
    assert ch["ru"] == 1 and "mount" not in ch
    assert ch["width"] == pytest.approx(m["w"], abs=0.1)
    assert ch["height"] == pytest.approx(m["h"], abs=0.1)
    assert ch["depth"] == pytest.approx(m["d"], abs=0.3)
    assert ch["weight-kg"] == pytest.approx(m["kg"], abs=0.01)
    assert ch["airflow"] == m["airflow"]
    assert ch["power"] == "ac"
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_compact_models_are_not_nineteen_inches_wide_and_the_mp_models_are_the_other_height():
    """Table 3's two columns: the C value (10.98 in wide, 1.72 in high) and the two MP exceptions to the
    EX2300 value (17.36 in not 17.4, 1.7 in not 1.75)."""
    for name in COMPACT:
        assert load_device(name)["chassis"]["width"] < 300
    old = load_device("ex2300-24p")["chassis"]
    for name in MP:
        ch = load_device(name)["chassis"]
        assert ch["width"] < old["width"] and ch["height"] < old["height"]


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_front_has_the_guides_jacks_numbered_from_zero_as_printed(name):
    d = load_device(name)
    n = FRONT[name]["ports"]
    pl = by_id(d, "front")
    ports = [pl[f"port-{i}"] for i in range(n)]
    assert not [i for i in pl if i.startswith("port-") and int(i.split("-")[1]) >= n]
    for i, p in enumerate(ports):
        assert p["ref"] in ("common/rj45-ganged-eth@1", "common/rj45-ganged-eth-plain@1")
        assert p["rel-pos"] == i
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"] if str(s.get("for", "")).startswith("port-")}
    assert texts == {f"port-{i}": str(i) for i in range(n)}


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_jacks_stand_in_two_rows_with_the_even_number_on_top(name):
    pl = by_id(load_device(name), "front")
    n = FRONT[name]["ports"]
    for col in range(n // 2):
        upper, lower = pl[f"port-{2 * col}"], pl[f"port-{2 * col + 1}"]
        assert upper["at"][0] == lower["at"][0]
        assert upper["at"][1] < lower["at"][1]
        assert rotation(upper) == 180 and not rotation(lower)
    assert len({p["at"][1] for i, p in pl.items() if i.startswith("port-") and int(i[5:]) % 2 == 0}) == 1


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_jack_runs_carry_the_guides_speeds(name):
    """The Multigigabit ports are their own group with the 2.5g speed; the others say 1g."""
    d = load_device(name)
    pl = by_id(d, "front")
    for first, last, speed in FRONT[name]["speeds"]:
        for i in range(first, last + 1):
            grp = d["groups"][pl[f"port-{i}"]["group"]]
            assert grp["attrs"]["speed"] == speed and grp["attrs"]["media"] == "rj45", (name, i)
            assert ("poe" in grp["attrs"]) == NEW[name]["poe"]


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_jacks_are_one_shell_of_six_columns_on_the_registry_pitch(name):
    pl = by_id(load_device(name), "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    assert len(xs) == 6
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [13.97] * 5


@pytest.mark.parametrize("name,shells,cols", [("ex2300-24mp", 3, 4), ("ex2300-48mp", 3, 8)])
def test_the_mp_jacks_stand_in_three_shells(name, shells, cols):
    d = load_device(name)
    pl = by_id(d, "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    assert len(xs) == shells * cols
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if s > min(steps) + 1.0]) == shells - 1
    assert len([x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell" and x["size"][0] > 40]) == shells


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_uplinks_are_numbered_from_zero_and_use_the_registry_cage(name):
    pl = by_id(load_device(name), "front")
    n = FRONT[name]["uplinks"]
    ups = [pl[f"uplink-{i}"] for i in range(n)]
    assert not [i for i in pl if i.startswith("uplink-") and int(i.split("-")[1]) >= n]
    assert {u["ref"] for u in ups} == {"std/sfp-ganged@1"}
    assert [u["rel-pos"] for u in ups] == list(range(n))
    assert min(u["at"][0] for u in ups) > max(p["at"][0] for i, p in pl.items() if i.startswith("port-"))


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_uplinks_are_two_cages_in_one_row_with_a_lamp_pair_each(name):
    pl = by_id(load_device(name), "front")
    ups = [pl["uplink-0"], pl["uplink-1"]]
    assert len({u["at"][1] for u in ups}) == 1
    assert not any(rotation(u) for u in ups)
    lamps = [i for i in pl if i.startswith("led-uplink-")]
    assert len(lamps) == 4


@pytest.mark.parametrize("name", MP)
def test_the_mp_uplinks_are_stacked_pairs_upper_upright_lower_turned(name):
    """docs/pluggables-slotting-design.md: the upper cage of a pair upright, the lower turned 180."""
    pl = by_id(load_device(name), "front")
    n = FRONT[name]["uplinks"]
    for col in range(n // 2):
        upper, lower = pl[f"uplink-{2 * col}"], pl[f"uplink-{2 * col + 1}"]
        assert upper["at"][0] == lower["at"][0]
        assert upper["at"][1] < lower["at"][1]
        assert not rotation(upper) and rotation(lower) == 180
    assert len([i for i in pl if i.startswith("led-uplink-")]) == n


@pytest.mark.parametrize("name", MP)
def test_each_mp_port_and_uplink_has_one_lamp(name):
    """Tables 13: one Link/Activity lamp per RJ-45 port and per uplink."""
    pl = by_id(load_device(name), "front")
    for i in range(FRONT[name]["ports"]):
        lamp = pl[f"led-port-{i}"]
        assert lamp["for"] == f"port-{i}" and lamp["ref"] == "common/led-rect-sm@1"
    # the even port's lamp is left of the odd port's, over their shared column
    for col in range(FRONT[name]["ports"] // 2):
        assert pl[f"led-port-{2 * col}"]["at"][0] < pl[f"led-port-{2 * col + 1}"]["at"][0]


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_front_has_the_guides_lamps_and_management_ports(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert FRONT[name]["lamps"] <= set(pl)
    assert pl["usb"]["ref"] == "std/usb-a@1" and rotation(pl["usb"]) == 90
    assert "console-rj45" in pl and pl["console-rj45"]["ref"] in ("std/rj45@2", "std/rj45-ganged@2")
    assert pl["mgmt"]["ref"] in ("common/rj45-eth@1", "common/rj45-ganged-eth-plain@1")
    assert rotation(pl["mgmt"]) == 180
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON"} <= legends


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_front_has_the_status_lamps_button_and_console(name):
    d = load_device(name)
    pl = by_id(d, "front")
    modes = {i for i in pl if i in ("led-spd", "led-dx", "led-en", "led-poe")}
    assert len(modes) == (4 if NEW[name]["poe"] else 3)
    assert pl["btn-mode"]["ref"] == "common/reset-button@1"
    assert pl["esd-jack"]["ref"] == "common/esd-jack@1"
    decor = {x.get("id") for x in d["views"]["front"]["panel"]["decor"]}
    assert not {"console", "console-opening", "console-pins"} & decor
    assert pl["console-usb"]["ref"] == "std/mini-usb@1" and pl["console-usb"]["attrs"]["role"] == "console"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"SYS", "ALM", "MST", "SPD", "DX", "EN", "CON", "LINK", "ST", "EX2300-C"} <= legends
    # the photograph of the 12T prints the PoE legend with no lamp behind it: the legend, not the lamp
    assert "PoE" in legends
    assert ("PoE+" in legends) == NEW[name]["poe"]


@pytest.mark.parametrize("name", MP)
def test_the_mp_front_has_no_mode_button_and_no_mini_usb_console(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert not [i for i in pl if i.startswith("btn-")]
    assert not [x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind", "").startswith("console")]
    assert not {"led-sys", "led-alm", "led-mst", "led-spd", "led-dx", "led-en", "led-poe"} & set(pl)


# --- the rear and the cooling ----------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_rear_has_the_ac_inlet_and_the_earthing_terminal(name):
    d = load_device(name)
    pl = by_id(d, "rear")
    assert pl["ac-inlet"]["ref"] == "std/c14-inlet@1"
    # the earth symbol: a library part on the dark MP rears, a stroked mark on the compact rears (the
    # part's skin is drawn light and would vanish on the silver plate the photograph shows)
    marks = [s for s in d["views"]["rear"].get("silkscreen") or [] if s.get("path", "").startswith("M 0 -")]
    assert "earth-mark" in pl or marks
    # the earthing terminal is a placed part: one M4 screw on the MP rears, a pair of bare 10-32 holes on the compact rears
    placed = {k: p["ref"] for k, p in pl.items() if k in ("earth-screw", "ground-pair")}
    assert placed == ({"earth-screw": "common/ground-screw-m4@1"} if name in MP
                      else {"ground-pair": "common/ground-hole-pair-5-8-10-32@1"})
    assert not [x for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") in ("earth-hole", "earth-stud")]
    assert not any(x.get("kind") == "fan-grille" for x in d["views"]["rear"]["panel"]["decor"])


def test_only_the_poe_compact_rear_has_the_heatsink():
    """Figure 7 callout 4: the heatsink is "only in PoE models"; Figure 8 has none."""
    def sinks(name):
        return [x for x in load_device(name)["views"]["rear"]["panel"]["decor"] if x.get("kind") == "heatsink"]
    assert len(sinks("ex2300-c-12p")) == 1 and not sinks("ex2300-c-12t")


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_models_are_fanless(name):
    d = load_device(name)
    for view in d["views"]:
        assert not [x for x in (d["views"][view].get("panel") or {}).get("decor") or [] if x.get("kind") == "fan-grille"]
    assert d["chassis"]["airflow"] == "passive"
    assert "fanless" in d["attrs"]["thermal"]["cooling"]


@pytest.mark.parametrize("name", MP)
def test_the_mp_fans_are_on_the_right_panel_and_the_airflow_is_side_to_side(name):
    d = load_device(name)
    fans = [x for x in d["views"]["right"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert len(fans) == NEW[name]["fans"]
    xs = [f["at"][0] for f in fans]
    assert xs == sorted(xs) and 0 < xs[0] and xs[-1] + 38.7 < d["chassis"]["depth"]
    assert d["chassis"]["airflow"] == "side"
    assert not (d["views"]["left"].get("panel") or {}).get("decor")


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_supply_and_fans_are_built_in_so_there_is_no_bay_and_no_module(name):
    d = load_device(name)
    for view in d["views"]:
        assert not bays(d, view), f"{name} {view}: the guide's supply and fans are built in"
        for p in placements(d, view):
            ref = p["ref"].split("/")[-1]
            assert not any(w in ref for w in ("psu", "fan", "jpsu", "module")), (name, view, p["id"])
    assert "built in" in " ".join(d["provenance"]["built-in-power-and-fans"]["note"].split())
    for cfg in d["configurations"].values():
        assert "bays" not in cfg


# --- the configurations and the DCIM export --------------------------------------------------

@pytest.mark.parametrize("name,cid,part", NEW_PART_NUMBERS)
def test_each_new_configuration_carries_its_part_number(name, cid, part):
    cfg = load_device(name)["configurations"][cid]
    assert set(cfg["part-numbers"]) == {part}
    assert cfg["kind"] in ("base", "orderable")


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_configurations_are_the_guides_and_one_is_default(name):
    d = load_device(name)
    assert set(d["configurations"]) == set(NEW[name]["configs"])
    assert [c for c, v in d["configurations"].items() if v.get("default")] == ["ac"]
    assert [c for c, v in d["configurations"].items() if v["kind"] == "base"] == ["ac"]
    for cfg in d["configurations"].values():
        assert not cfg.get("views")


@pytest.mark.parametrize("name,cid,part", NEW_PART_NUMBERS)
def test_the_new_dcim_device_types_export_one_per_configuration(name, cid, part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0
        assert not doc.get("module-bays")
        names = {i["name"] for i in doc["interfaces"]}
        assert {f"port-{i}" for i in range(FRONT[name]["ports"])} <= names
        assert {f"uplink-{i}" for i in range(FRONT[name]["uplinks"])} <= names


def test_the_export_never_claims_front_to_rear_for_a_side_cooled_or_fanless_box():
    """The exporter has no NetBox airflow value for `side`, and says nothing for `passive`; what matters is
    that it does not borrow the front-to-rear of the other EX2300 types."""
    for part in ("EX2300-24MP", "EX2300-48MP", "EX2300-C-12P", "EX2300-C-12T-VC"):
        doc = yaml.safe_load((EXPORTS / "netbox" / "device-types" / "Juniper" / f"{part}.yaml").read_text())
        assert doc.get("airflow") in (None, "passive"), part


# --- logos, sources and the figures the guide gets wrong ------------------------------------

@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_vendor_wordmark_is_reserved_not_typed(name):
    d = load_device(name)
    for view in ("front", "rear"):
        drawn = [t.upper() for t in silk_texts(d, view)]
        assert not any("JUNIPER" in t and "RUNNING" not in t for t in drawn)
        assert "NETWORKS" not in drawn
    # the 24MP prints the lockup on the front and nothing on the rear; the 48MP prints it on the rear only
    zones = {v: [r for r in d["views"][v].get("regions") or [] if r.get("id") == "logo-zone"] for v in ("front", "rear")}
    where = {"ex2300-c-12p": "front", "ex2300-c-12t": "front", "ex2300-24mp": "front", "ex2300-48mp": "rear"}[name]
    assert len(zones[where]) == 1
    assert not zones["rear" if where == "front" else "front"]


@pytest.mark.parametrize("name", sorted(NEW))
def test_the_new_devices_cite_the_guide_and_say_what_is_estimated(name):
    d = load_device(name)
    assert any(r["title"].startswith("EX2300 Switch Hardware Guide") and
               r["sha256"] == "a67d6985f5e2227b14e1b8998feef4ef75eab2c5f72967bdbc0ada8fee8dc0e3" for r in d["references"])
    assert "https://www.juniper.net/documentation/us/en/hardware/ex2300/ex2300.pdf" in d["provenance"]["sources"]["note"]
    assert d["provenance"]["front-layout"]["confidence"] == "estimated"
    assert d["provenance"]["rear-layout"]["confidence"] == "estimated"
    assert "estimated" in " ".join(d["provenance"]["front-layout"]["note"].split())


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_datasheet_is_cited_and_its_depth_conflict_recorded(name):
    d = load_device(name)
    assert d["datasheet"]["sha256"] == "d33aa2a83d20f5ebdde9b65a74b1b29048e2447c9e73dba9e4c4e4e82298c98b"
    note = " ".join(d["provenance"]["chassis"]["note"].split())
    assert "23.9" in note and "23.8" in note and "9.45" in note
    mount = " ".join(d["provenance"]["mounting"]["note"].split())
    assert "rubber feet" in mount and "separately orderable" in mount and "desk" in mount and "wall" in mount


def test_the_12t_photograph_wins_on_the_printed_poe_legend():
    note = " ".join(load_device("ex2300-c-12t")["provenance"]["lamps"]["note"].split())
    assert "photograph of the real unit wins" in note


@pytest.mark.parametrize("name", MP)
def test_the_mp_rear_earthing_terminal_conflict_is_recorded(name):
    note = " ".join(load_device(name)["provenance"]["rear-layout"]["note"].split())
    assert "ESD point" in note and "Table 36" in note and "earthing terminal" in note


@pytest.mark.parametrize("name", MP)
def test_the_mp_fan_side_conflict_is_recorded(name):
    note = " ".join(load_device(name)["provenance"]["side-fans"]["note"].split())
    assert "left of the plan" in note and "right panel" in note


def test_the_12t_rear_legend_and_table_15_disagree_and_both_are_kept():
    d = load_device("ex2300-c-12t")
    note = " ".join(d["provenance"]["rear-legend"]["note"].split())
    assert "2.5 A" in note and "0.5 A" in note
    assert d["attrs"]["power"]["power-current-max"] == "1 A at 100 VAC; 0.5 A at 240 VAC"
    assert any("2.5A Max" in t for t in silk_texts(d, "rear"))


def test_this_slice_still_adds_no_component():
    assert not list(COMP.glob("ex2300-*")) and not list(COMP.glob("ex2300m-*"))
