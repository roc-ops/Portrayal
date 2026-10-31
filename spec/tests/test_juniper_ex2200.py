"""The Juniper EX2200 and EX2200-C: the 24- and 48-port models and the compact 12-port ones, from the
EX2200 and EX2200-C Switches Hardware Guide (published 2022-02-02).

One device per front panel. The PoE and non-PoE models do not share a rear (the PoE models expose a third
exhaust opening) and the 24- and 48-port models differ in their jacks, so each is its own device. The
EX2200-24T-4G-DC is the one variant the guide shows with the 24T's front panel and a different rear (its
terminals), so it is the 24T's `dc` configuration.

What the guide fixes, and so what these tests hold:
  Table 5     the envelope - 1.75 in high, 17.5 in (EX2200) or 10.6 in (EX2200-C) wide, the depth and the weight
  Table 3     the part numbers: each carries its uplink count (-4G, -2G)
  Figures 1 to 6   the ports, their count and numbering, and what is on the rear
  Power Supply, Cooling System   the supply and the fans are built into the chassis, so no bay and no
             module is modelled for them
"""
import os
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# Table 5 (centimetres as printed; the inch figures agree), Table 3 (part numbers), Figures 1 to 6 (the rest)
MODELS = {
    "ex2200-24t": {"ports": 24, "poe": False, "compact": False, "depth_cm": 26.7, "weight_kg": 2.7,
                   "configs": {"ac": "EX2200-24T-4G", "dc": "EX2200-24T-4G-DC"}},
    "ex2200-24p": {"ports": 24, "poe": True, "compact": False, "depth_cm": 26.7, "weight_kg": 3.6,
                   "configs": {"ac": "EX2200-24P-4G"}},
    "ex2200-48t": {"ports": 48, "poe": False, "compact": False, "depth_cm": 26.7, "weight_kg": 3.6,
                   "configs": {"ac": "EX2200-48T-4G"}},
    "ex2200-48p": {"ports": 48, "poe": True, "compact": False, "depth_cm": 26.7, "weight_kg": 4.5,
                   "configs": {"ac": "EX2200-48P-4G"}},
    "ex2200-c-12t": {"ports": 12, "poe": False, "compact": True, "depth_cm": 22.8, "weight_kg": 2.1,
                     "configs": {"ac": "EX2200-C-12T-2G"}},
    "ex2200-c-12p": {"ports": 12, "poe": True, "compact": True, "depth_cm": 23.8, "weight_kg": 2.9,
                     "configs": {"ac": "EX2200-C-12P-2G"}},
}
DEVICES = sorted(MODELS)
FULL = [n for n in DEVICES if not MODELS[n]["compact"]]
COMPACT = [n for n in DEVICES if MODELS[n]["compact"]]
PART_NUMBERS = [(name, cid, pn) for name, m in MODELS.items() for cid, pn in m["configs"].items()]


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def layout_of(name):
    return yaml.safe_load((DEV / name / "layout.yaml").read_text())


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


def silk_texts(dev, view):
    return [s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")]


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_5(name):
    ch = load_device(name)["chassis"]
    m = MODELS[name]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(44.45, abs=0.1)
    assert ch["width"] == pytest.approx(269.2 if m["compact"] else 445.0, abs=0.6)
    assert ch["depth"] == pytest.approx(m["depth_cm"] * 10, abs=0.3)
    assert ch["weight-kg"] == pytest.approx(m["weight_kg"], abs=0.01)


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


@pytest.mark.parametrize("name", DEVICES)
def test_the_airflow_is_the_guides(name):
    """EX2200: two fans along the rear, side-to-rear (the enum's `side`); EX2200-C: fanless, no airflow."""
    d = load_device(name)
    assert d["chassis"]["airflow"] == ("passive" if MODELS[name]["compact"] else "side")
    assert d["chassis"]["power"] == "ac"
    for cfg in d["configurations"].values():
        assert "airflow" not in cfg


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
    # the printed numbers are on the silkscreen, one per jack
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


@pytest.mark.parametrize("name", FULL)
def test_the_full_width_jacks_pitch_and_shells(name):
    d = load_device(name)
    pl = by_id(d, "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    n = MODELS[name]["ports"] // 2
    assert len(xs) == n
    # 13.97 within a shell of six, a 6.27 mm gutter between shells
    assert sum(abs(s - 13.97) < 0.02 for s in steps) == n - n // 6
    assert sum(abs(s - 20.24) < 0.02 for s in steps) == n // 6 - 1
    assert len([x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell"]) == n // 6
    # the 24-port models are the 48-port face's right-hand half: their first jack is where the 48's third shell's is
    if MODELS[name]["ports"] == 24:
        assert xs[0] == pytest.approx(10.4 + 2 * (6 * 13.97 + 6.27), abs=0.05)


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_jacks_stand_apart_in_one_shell(name):
    d = load_device(name)
    pl = by_id(d, "front")
    xs = sorted({p["at"][0] for i, p in pl.items() if i.startswith("port-")})
    assert len(xs) == 6
    assert {round(b - a, 2) for a, b in zip(xs, xs[1:])} == {15.75}
    assert len([x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell"]) == 1


@pytest.mark.parametrize("name", FULL)
def test_four_sfp_uplinks_numbered_zero_to_three_in_one_row(name):
    d = load_device(name)
    pl = by_id(d, "front")
    ups = [pl[f"uplink-{i}"] for i in range(4)]
    assert not [i for i in pl if i.startswith("uplink-") and i[7:].isdigit() and int(i[7:]) > 3]
    assert {u["ref"] for u in ups} == {"std/sfp-ganged@1"}
    assert len({u["at"][1] for u in ups}) == 1
    assert [u["rel-pos"] for u in ups] == [0, 1, 2, 3]
    xs = [u["at"][0] for u in ups]
    assert xs == sorted(xs) and xs[0] > max(p["at"][0] for i, p in pl.items() if i.startswith("port-"))
    assert {u["group"] for u in ups} == {"uplink"}
    assert d["groups"]["uplink"]["attrs"] == {"media": "sfp", "speed": "1g"}
    # a Link/Activity and a Status lamp either side of each numeral
    assert len([i for i in pl if i.startswith("led-uplink-")]) == 8
    legends = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"] if str(s.get("for", "")).startswith("uplink-")}
    assert legends == {f"uplink-{i}": str(i) for i in range(4)}


@pytest.mark.parametrize("name", COMPACT)
def test_two_dual_purpose_uplinks_each_an_rj45_and_an_sfp_port(name):
    d = load_device(name)
    pl = by_id(d, "front")
    rj = [pl[f"uplink-{i}-rj45"] for i in range(2)]
    sfp = [pl[f"uplink-{i}-sfp"] for i in range(2)]
    assert {p["ref"] for p in rj} == {"std/rj45-ganged@2"}
    assert {p["ref"] for p in sfp} == {"std/sfp-ganged@1"}
    assert [p["group"] for p in rj] == ["uplink-rj45"] * 2 and [p["group"] for p in sfp] == ["uplink-sfp"] * 2
    assert d["groups"]["uplink-rj45"]["attrs"]["media"] == "rj45"
    assert d["groups"]["uplink-sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    # the SFP port stands to the right of its RJ-45 port, the same 43.3 mm apart on both uplinks
    for r, s in zip(rj, sfp):
        assert 20 < s["at"][0] - r["at"][0] < 30
    assert sfp[1]["at"][0] - sfp[0]["at"][0] == pytest.approx(43.3, abs=0.05)
    # LINK and ST for each of the four ports of the two uplinks
    assert len([i for i in pl if i.startswith("led-uplink-")]) == 8
    legends = [s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text") in ("LINK", "ST")]
    # LINK and ST over each of the four uplink ports, and one of each beside the management port
    assert legends.count("LINK") == 5 and legends.count("ST") == 5


@pytest.mark.parametrize("name", FULL)
def test_the_full_width_front_has_the_guides_status_lamps_and_button(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert {"led-sys", "led-alm"} <= set(pl) and "led-mst" not in pl
    # the guide lists four port-mode lamps on every non-compact model, PoE or not
    assert {"led-spd", "led-dx", "led-en", "led-poe"} <= set(pl)
    assert pl["btn-mode"]["ref"] == "common/reset-button@1"
    legends = set(silk_texts(d, "front"))
    assert {"SYS", "ALM", "SPD", "DX", "EN", "POE"} <= legends
    # the console is on the rear of these models
    assert "CON" not in legends


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_front_has_the_management_ports_lamps_and_button(name):
    d = load_device(name)
    m = MODELS[name]
    pl = by_id(d, "front")
    assert {"led-sys", "led-alm"} <= set(pl)
    # 4 port-mode lamps on the PoE+ model, 3 on the non-PoE one (the guide's list)
    modes = {i for i in pl if i in ("led-spd", "led-dx", "led-en", "led-poe")}
    assert len(modes) == (4 if m["poe"] else 3) and (("led-poe" in modes) == m["poe"])
    assert pl["btn-mode"]["ref"] == "common/reset-button@1"
    assert pl["mgmt"]["ref"] == "std/rj45@2" and pl["mgmt"]["attrs"]["role"] == "mgmt"
    assert pl["console-rj45"]["ref"] == "std/rj45@2" and pl["console-rj45"]["attrs"]["role"] == "console"
    assert pl["usb"]["ref"] == "std/usb-a@1" and pl["usb"]["rotate"] == 90
    # the mini-USB console is chassis art with its own opening, not a placed part (nothing in the DCIM
    # export could carry it)
    decor = {x.get("id"): x for x in d["views"]["front"]["panel"]["decor"]}
    assert decor["console"]["size"] == [8.6, 5.1]
    assert "console" not in pl
    legends = set(silk_texts(d, "front"))
    assert {"SYS", "ALM", "SPD", "DX", "EN", "CON", "MGMT", "LINK", "ST", "0", "1"} <= legends
    assert ("PoE" in legends) == m["poe"] and ("PoE+" in legends) == m["poe"]


@pytest.mark.parametrize("name", DEVICES)
def test_poe_is_stated_on_the_jacks_of_the_poe_models_only(name):
    g = load_device(name)["groups"]["rj45"]["attrs"]
    assert g["media"] == "rj45" and g["speed"] == "1g"
    assert ("poe" in g) == MODELS[name]["poe"]


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", FULL)
def test_the_full_width_rear_has_the_management_console_usb_and_esd_ports(name):
    d = load_device(name)
    pl = by_id(d, "rear")
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert pl["usb"]["ref"] == "std/usb-a@1"
    assert pl["console-rj45"]["ref"] == "std/rj45@2"
    assert pl["esd-rear-jack"]["ref"] == "common/esd-jack@1"
    assert pl["console-rj45"]["attrs"]["role"] == "console"
    decor = {x.get("id"): x for x in d["views"]["rear"]["panel"]["decor"]}
    assert {"earth-terminal", "earth-hole-1", "earth-hole-2"} <= set(decor)
    # the RPS port is a placed part, no longer panel art (test_rps_interfaces.py holds the detail)
    assert not {"rps-plate", "rps-opening"} & set(decor)
    assert pl["rps"]["ref"] == "juniper/ex2200-rps-port@1"


@pytest.mark.parametrize("name", FULL)
def test_the_rear_has_three_exhaust_openings_the_third_open_on_poe_models_only(name):
    d = load_device(name)
    decor = d["views"]["rear"]["panel"]["decor"]
    fans = [x for x in decor if x.get("kind") == "fan-grille"]
    assert len(fans) == 2
    third = [x for x in decor if x.get("kind") in ("exhaust-grille", "sealed-exhaust")]
    assert len(third) == 1
    if MODELS[name]["poe"]:
        assert third[0]["kind"] == "exhaust-grille" and third[0].get("pattern") == "vent"
    else:
        assert third[0]["kind"] == "sealed-exhaust" and "pattern" not in third[0]
    # the three openings stand left to right at 142, 192 and 237 mm
    xs = sorted(x["at"][0] + x["size"][0] / 2 for x in fans + third)
    assert [round(v) for v in xs] == [142, 192, 237]
    assert by_id(d, "rear")["ac-inlet"]["ref"] == "std/c14-inlet@1"


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_rear_is_fanless_with_a_heatsink_on_the_poe_model_only(name):
    d = load_device(name)
    decor = d["views"]["rear"]["panel"]["decor"]
    assert not [x for x in decor if x.get("kind") in ("fan-grille", "exhaust-grille")]
    heat = [x for x in decor if x.get("kind") == "heatsink"]
    assert len(heat) == (1 if MODELS[name]["poe"] else 0)
    # the heatsink is a solid block: the guide says EX2200-C switches have no exhaust openings, so no rear
    # decor on a compact model may be a vent, and the heatsink carries no pattern either
    for x in heat:
        assert "pattern" not in x and "vent" not in x
    assert not [x for x in decor if x.get("pattern") == "vent" or "vent" in x]
    pl = by_id(d, "rear")
    assert pl["ac-inlet"]["ref"] == "std/c14-inlet@1"
    assert pl["esd-rear-jack"]["ref"] == "common/esd-jack@1"
    assert {"earth-hole-1", "earth-hole-2"} <= {x.get("id") for x in decor}
    assert d["chassis"]["airflow"] == "passive"


@pytest.mark.parametrize("name", COMPACT)
def test_the_compact_rear_has_the_oblong_slotted_plate_above_the_first_earth_hole(name):
    # Figure 6: an oblong plate about 22 x 6 mm at the left, over the first of the two earthing holes
    d = load_device(name)
    decor = {x.get("id"): x for x in d["views"]["rear"]["panel"]["decor"]}
    plate = decor["slotted-plate"]
    assert plate["kind"] == "slotted-plate"
    assert 20 <= plate["size"][0] <= 24 and 5 <= plate["size"][1] <= 8
    hole = decor["earth-hole-1"]
    assert plate["at"][0] < hole["at"][0] < plate["at"][0] + plate["size"][0]
    assert plate["at"][1] + plate["size"][1] < hole["at"][1]


def test_the_dc_rear_has_the_four_terminals_and_no_inlet():
    d = load_device("ex2200-24t")
    assert d["configurations"]["dc"]["views"] == {"rear": "rear-dc"}
    assert d["configurations"]["dc"]["power"] == "dc"
    assert d["views"]["rear-dc"]["face"] == "rear"
    pl = by_id(d, "rear-dc")
    decor = {x.get("id"): x for x in d["views"]["rear-dc"]["panel"]["decor"]}
    poles = [i for i in decor if i.startswith("dc-pole-") and not i.endswith("-screw")]
    assert len(poles) == 4
    assert "ac-inlet" not in pl and "dc-terminal" not in pl
    # B-, A-, B+ and A+ left to right (Figure 48), one under each pole
    legends = [s["text"] for s in d["views"]["rear-dc"]["silkscreen"] if s.get("text") in ("B-", "A-", "B+", "A+")]
    xs = [s["at"][0] for s in d["views"]["rear-dc"]["silkscreen"] if s.get("text") in ("B-", "A-", "B+", "A+")]
    assert legends == ["B-", "A-", "B+", "A+"] and xs == sorted(xs)
    # the rest of the rear is the AC rear's
    for i in ("mgmt", "usb", "console-rj45", "esd-rear-jack"):
        assert i in pl
    assert d["views"]["rear-dc"]["size"] == d["views"]["rear"]["size"]
    assert len([x for x in d["views"]["rear-dc"]["panel"]["decor"] if x.get("kind") == "fan-grille"]) == 2


@pytest.mark.parametrize("name", [n for n in DEVICES if n != "ex2200-24t"])
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
    assert "built in" in d["provenance"]["built-in-power-and-fans"]["note"]
    assert "module-bays" not in d


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


@pytest.mark.parametrize("name", DEVICES)
def test_the_export_lists_the_guides_interfaces(name):
    m = MODELS[name]
    part = m["configs"]["ac"]
    doc = yaml.safe_load((EXPORTS / "netbox" / "device-types" / "Juniper" / f"{part}.yaml").read_text())
    ifaces = doc["interfaces"]
    names = [i["name"] for i in ifaces]
    assert len(names) == len(set(names))
    # the jacks, the four uplink ports (four SFP, or two RJ-45 and two SFP on the compact models) and the
    # management port; the console ports are not network interfaces
    assert len(ifaces) == m["ports"] + 4 + 1


# --- the faces: logo, the reference, the sources -----------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_no_vendor_wordmark_is_drawn(name):
    """The maker's lockup is a logo and is never typed as text; the compact front reserves its place."""
    d = load_device(name)
    drawn = [t.upper() for t in silk_texts(d, "front")]
    assert not any("JUNIPER" in t or "NETWORKS" in t or "JUNOS" in t for t in drawn)
    zones = [r["id"] for r in d["views"]["front"].get("regions") or []]
    if MODELS[name]["compact"]:
        assert "logo-zone" in zones
        assert "EX2200-C" in drawn
    else:
        assert not zones


@pytest.mark.parametrize("name", DEVICES)
def test_the_provenance_names_the_guide_and_every_position_is_estimated(name):
    d = load_device(name)
    prov = d["provenance"]
    text = " ".join(" ".join(str(v) for v in prov.values()).split())
    assert "2022-02-02" in text and "ex-series-doc-archives.zip" in text
    assert prov["front-layout"]["confidence"] == "estimated"
    assert prov["rear-layout"]["confidence"] == "estimated"
    assert prov["colour"]["confidence"] == "borrowed"
    assert d["references"][0]["sha256"] == "b2c8347c37f02eeaed2033ffd5b64f3d40511f8d335e6088f4a5633bd7d89ff5"
    assert d["maturity"] == "modelled"
    assert d["manufacturer"] == "Juniper" and d["portfolio"] == {"line": "EX Series", "family": "EX2200"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_is_generated_from_its_layout(name):
    """device.yaml is the expansion of layout.yaml; the pair cannot drift."""
    lay, dev = layout_of(name), load_device(name)
    assert lay["name"] == dev["name"] == name
    assert lay["configurations"] == dev["configurations"]
    assert lay["chassis"] == dev["chassis"]
    # the whole file: the tool the repository uses re-expands the layout and compares it with device.yaml
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/expand.py"), "--check",
                        str(DEV / name / "layout.yaml")], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "spec/tools")))
    assert r.returncode == 0, r.stdout + r.stderr


# --- the components ----------------------------------------------------------

def test_this_slice_adds_only_the_rps_port_component():
    """Every part but one is a registry or common one: the guide's supply and fans are built in, and the
    pieces of metalwork no library part covers (the mini-USB console, the four-pole DC terminal block) are
    chassis art, because the DCIM export has no row that could carry a part of either kind. The RPS port is
    the one component, a placed part that presents no interface."""
    assert sorted(p.name for p in COMP.glob("ex2200-*")) == ["ex2200-rps-port"]
