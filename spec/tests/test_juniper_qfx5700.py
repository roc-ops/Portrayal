"""The Juniper QFX5700, from its hardware guide and datasheet.

Sources: QFX5700 Switch Hardware Guide (published 2026-09-30) and the QFX5700 Switch datasheet (Juniper
document 1000719-009, September 2024).

One device for one front panel. The AC and DC builds, the QFX5700E builds (which differ only in an internal
forwarding engine board that no face shows) and the spare chassis are `orderable` configurations of it. The
line cards (QFX5K-FPC-16C, -20Y, -4CD) are a family of their own and are not built here: every slot holds its
blank. The supplies are the QFX5230's, because the guide names the same part numbers; the routing and control
board, the blanks and the fan tray are components named for the family.

What the documents fix, and so what these tests hold:
  guide Table 5, datasheet Table 2   the envelope - 22.2 x 48.2 x 81.5 cm, 5RU (48.2 cm is over the brackets)
  guide Table 27, datasheet          the part numbers of the builds and what the base configuration ships
  guide figures 14 to 17             two RCB slots, nine FPC slots (0 to 8), four supplies, two fan trays
  guide Tables 5, 6, 13, 27          the module part numbers and the sizes
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper/qfx5700"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# guide Table 5 and the datasheet: height, width over the brackets, depth, in centimetres
HEIGHT_CM, WIDTH_CM, DEPTH_CM = 22.2, 48.2, 81.5
RACK_FACE_MM = 482.6

# configuration -> (power, part number)
BUILDS = {
    "ac": ("ac", "QFX5700-BASE-AC"),
    "dc": ("dc", "QFX5700-BASE-DC"),
    "e-ac": ("ac", "QFX5700E-BASE-AC"),
    "e-dc": ("dc", "QFX5700E-BASE-DC"),
}
CHAS = "QFX5700-CHAS"

PSU = {"ac": "qfx5230-jnp-3000w-ac-afo", "dc": "qfx5230-jnp-3000w-dc-afo"}
PSU_PARTS = {"qfx5230-jnp-3000w-ac-afo": "JNP-3000W-AC-AFO", "qfx5230-jnp-3000w-dc-afo": "JNP-3000W-DC-AFO"}
FPC_BLANK, RCB_BLANK, PSU_BLANK = "qfx5700-fpc-blnk", "qfx5700-rcb-blnk", "qfx5700-psu-blank"
RCB, FAN = "qfx5700-rcb", "qfx5700-fan"

# component -> the part number the datasheet or guide gives it (None: the guide gives none)
MODULE_PARTS = {FPC_BLANK: "JNP5K-FPC-BLNK", RCB_BLANK: "JNP5K-RCB-BLNK", RCB: "QFX5700-RCB",
                FAN: "JNP5700-FAN", PSU_BLANK: None}


def device():
    return yaml.safe_load((DEV / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def seated(dev, cid):
    """bay id -> component name (None when open), as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for view in ("front", "rear"):
        for b in bays(dev, view):
            ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
            out[b["id"]] = ref_name(ref) if ref else None
    return out


# --- the envelope ------------------------------------------------------------

def test_the_envelope_is_the_guides_table():
    ch = device()["chassis"]
    assert ch["ru"] == 5
    assert ch["height"] == pytest.approx(HEIGHT_CM * 10, abs=0.5)
    assert ch["depth"] == pytest.approx(DEPTH_CM * 10, abs=0.5)
    assert 5 * 44.45 == pytest.approx(ch["height"], abs=0.1), "five rack units"


def test_the_width_is_the_body_and_the_brackets_make_up_the_guides_482():
    """Table 5's 48.2 cm is over the front brackets: the figure measures 482.6 ear to ear and 440.8 between folds."""
    d = device()
    w = d["chassis"]["width"]
    assert w < 480 and w == pytest.approx(440.8, abs=0.5)
    assert 440.0 < w < RACK_FACE_MM - 2 * 20.0
    assert WIDTH_CM * 10 == pytest.approx(RACK_FACE_MM, abs=1.0)


def test_the_faces_are_sized_from_the_envelope():
    d = device()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_naming_follows_the_other_juniper_boxes():
    d = device()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "QFX5700"
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5700"}


# --- the slots and bays, per face --------------------------------------------

def test_the_port_side_has_two_rcb_slots_and_nine_fpc_slots_numbered_0_to_8():
    """Figure 16: RCB 0 and RCB 1 across the top, FPC 0 to 7 and the unsupported slot 8 below."""
    b = {x["id"]: x for x in bays(device(), "front")}
    assert sorted(i for i in b if i.startswith("rcb-")) == ["rcb-0", "rcb-1"]
    fpcs = [f"fpc-{n}" for n in range(9)]
    assert sorted(i for i in b if i.startswith("fpc-")) == sorted(fpcs)
    xs = [b[f]["at"][0] for f in fpcs]
    assert xs == sorted(xs) and len(set(xs)) == 9
    assert len({b[f]["at"][1] for f in fpcs}) == 1, "one row"
    pitch = {round(b - a, 2) for a, b in zip(xs, xs[1:])}
    assert pitch == {44.95}
    assert b["rcb-0"]["at"][0] < b["rcb-1"]["at"][0]
    assert b["rcb-0"]["at"][1] < b[fpcs[0]]["at"][1], "the boards are above the cards"


def test_no_port_is_placed_on_the_chassis_faces_themselves():
    """Every network port is on a line card, and the line cards are not built here. The management jacks are the
    routing board's."""
    d = device()
    for view in ("front", "rear"):
        for p in placements(d, view):
            assert ref_name(p["ref"]) in ("esd-jack", "esd-warning", "ground-stud-pair-5-8-m6"), p["id"]


def test_the_fpc_bays_accept_only_the_blank_because_the_cards_are_a_family_of_their_own():
    d = device()
    for n in range(9):
        b = next(x for x in bays(d, "front") if x["id"] == f"fpc-{n}")
        assert [ref_name(r) for r in b["accepts"]] == [FPC_BLANK]
        assert ref_name(b["default"]) == FPC_BLANK
        assert b["group"] == "fpcs" and b["rel-pos"] == n
    assert d["groups"]["fpcs"]["role"] == "traffic"
    names = {p.name for p in COMP.iterdir()}
    assert not [n for n in names if "fpc-16c" in n or "fpc-20y" in n or "fpc-4cd" in n or "fpc16c" in n]


def test_the_left_out_cards_and_board_are_listed_by_part_number():
    note = " ".join(device()["provenance"]["left-out"]["note"].split())
    for part in ("QFX5K-FPC-16C", "QFX5K-FPC-20Y", "QFX5K-FPC-4CD", "QFX5700-FEB", "QFX5700E-FEB", "JNP5K-FEB-BLNK",
                 "QFX5K-EMI", "JNP5K-RMK-4POST"):
        assert part in note, part


def test_the_rear_has_four_supply_bays_in_a_row_and_two_fan_trays_stacked_below():
    b = {x["id"]: x for x in bays(device(), "rear")}
    assert sorted(i for i in b if i.startswith("psu-")) == [f"psu-{n}" for n in range(4)]
    xs = [b[f"psu-{n}"]["at"][0] for n in range(4)]
    assert xs == sorted(xs), "PSU 0 to 3 run left to right (figure 17)"
    assert len({b[f"psu-{n}"]["at"][1] for n in range(4)}) == 1
    assert all(y - x == pytest.approx(100.3, abs=0.2) for x, y in zip(xs, xs[1:])), "the figure's 100.4 mm pitch"
    assert sorted(i for i in b if i.startswith("fan-")) == ["fan-0", "fan-1"]
    assert b["fan-1"]["at"][1] < b["fan-0"]["at"][1], "tray 1 is the upper one (figure 17)"
    assert all(b[f"psu-{n}"]["at"][1] < b["fan-1"]["at"][1] for n in range(4)), "the supplies are above the trays"


def test_the_groups_say_what_the_slots_are():
    g = device()["groups"]
    assert g["res"]["role"] == "service" and g["res"]["attrs"]["redundancy"] == "n+0"
    assert g["psus"]["role"] == "service" and g["psus"]["attrs"]["redundancy"] == "n+1"
    assert g["fans"]["role"] == "service" and g["fans"]["attrs"]["redundancy"] == "n+1"


def test_the_routing_board_carries_the_management_jacks_and_lamps_of_figure_37():
    c = component(RCB)
    parts = {p["id"]: p for p in c["parts"]}
    assert ref_name(parts["usb"]["ref"]) == "usb-a"
    assert ref_name(parts["mgmt"]["ref"]) == "rj45-eth" and parts["mgmt"]["attrs"]["speed"] == "1g"
    assert ref_name(parts["con"]["ref"]) == "rj45" and parts["con"]["attrs"]["media"] == "rj45-serial"
    assert ref_name(parts["bits"]["ref"]) == "rj45" and parts["bits"]["attrs"]["media"] == "rj48"
    smb = sorted(i for i in parts if ref_name(parts[i]["ref"]) == "smb")
    assert smb == ["mhz-in", "mhz-out", "pps-in", "pps-out"]
    assert {"led-ssd0", "led-ssd1", "led-pwr", "led-sts", "led-alm", "led-mst", "reset", "online"} <= set(c["elements"])
    assert c["attrs"]["power-draw-max-w"] == 80


# --- the configurations ------------------------------------------------------

def test_each_build_is_an_orderable_configuration_with_its_part_number():
    cfgs = device()["configurations"]
    assert set(cfgs) == {"base", *BUILDS, "chas"}
    for cid, (power, part) in BUILDS.items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}
        assert cfgs[cid]["power"] == power
    assert cfgs["chas"]["kind"] == "orderable" and set(cfgs["chas"]["part-numbers"]) == {CHAS}


def test_the_default_is_the_chassis_as_the_base_configuration_ships_it_and_carries_no_sku():
    cfgs = device()["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base" and "part-numbers" not in cfgs["base"]
    assert seated(device(), "base") == seated(device(), "ac")


def test_no_redundant_build_is_invented():
    """Neither the guide nor the datasheet lists one: the four-supply population is not a SKU."""
    cfgs = device()["configurations"]
    assert not [c for c in cfgs if "redund" in c]
    parts = [p for v in cfgs.values() for p in (v.get("part-numbers") or {})]
    assert not [p for p in parts if "REDUND" in p]


@pytest.mark.parametrize("cid", sorted(BUILDS))
def test_each_build_seats_the_base_configuration_of_table_27(cid):
    """Table 27: one RCB and a blank for the other RCB slot, two supplies and two blanks for the other two power
    slots, two fan trays and a blank over each of the nine FPC slots."""
    power, _part = BUILDS[cid]
    s = seated(device(), cid)
    assert s["rcb-0"] == RCB and s["rcb-1"] == RCB_BLANK
    assert [s[f"psu-{n}"] for n in range(4)] == [PSU[power], PSU[power], PSU_BLANK, PSU_BLANK]
    assert s["fan-0"] == s["fan-1"] == FAN
    assert [s[f"fpc-{n}"] for n in range(9)] == [FPC_BLANK] * 9


@pytest.mark.parametrize("cid", sorted(BUILDS))
def test_the_supply_and_the_fan_tray_airflow_matches_and_is_front_to_back(cid):
    """The QFX5700 is front to back only (air out, AFO): there is no back-to-front build."""
    power, _part = BUILDS[cid]
    for name in (PSU[power], FAN):
        assert component(name)["attrs"]["airflow"] == "front-to-back"
    cfgs = device()["configurations"][cid]
    assert cfgs.get("airflow", "front-to-back") == "front-to-back"


def test_the_ac_supply_handle_is_orange_as_the_guide_says():
    """Figure 30 callout 4, the orange handle."""
    feats = component(PSU["ac"])["relief"]["features"]
    colour = next(f for f in feats if f["node"] == "latch")["color"]
    assert colour.lower() == "#e8731f"


def test_the_spare_chassis_shows_every_bay_open():
    s = seated(device(), "chas")
    assert set(s.values()) == {None} and len(s) == 2 + 9 + 4 + 2


def test_a_bay_accepts_the_modules_the_guide_lists():
    d = device()
    for b in bays(d, "front"):
        got = {ref_name(r) for r in b["accepts"]}
        want = {RCB, RCB_BLANK} if b["id"].startswith("rcb-") else {FPC_BLANK}
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = {FAN} if b["id"].startswith("fan-") else {PSU["ac"], PSU["dc"], PSU_BLANK}
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got


def test_bays_reserve_one_size_for_each_module_they_accept():
    d = device()
    for view in ("front", "rear"):
        for b in bays(d, view):
            for ref in b["accepts"]:
                c = component(ref_name(ref))["size"]
                assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), (b["id"], ref)
                assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), (b["id"], ref)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("name,part", sorted(MODULE_PARTS.items()))
def test_a_module_is_named_for_the_family_and_carries_the_part_number_the_guide_gives(name, part):
    c = component(name)
    assert c["name"] == name and c["kind"] == "module"
    if part:
        assert set(c["part-numbers"]) == {part}
        assert c["part-numbers"][part] == {"part": part}
    else:
        assert "part-numbers" not in c, "the guide gives the power blank no code"


@pytest.mark.parametrize("name", sorted(PSU_PARTS))
def test_the_supplies_are_the_ones_the_qfx5230_uses_because_the_guide_names_the_same_part(name):
    c = component(name)
    assert c["attrs"]["model"] == PSU_PARTS[name]
    assert c["attrs"]["power-output-w"] == 3000


def test_the_fan_tray_says_its_power_is_not_published_and_the_board_states_its_draw():
    assert component(FAN)["attrs"]["power-absent"] == "not-published"
    assert component(RCB)["attrs"]["power-draw-max-w"] == 80


def test_the_blanks_are_the_size_of_what_they_cover_and_draw_no_lamp():
    assert component(FPC_BLANK)["size"] == {"w": 44.3, "h": 168.2}
    assert component(RCB_BLANK)["size"] == component(RCB)["size"]
    assert component(PSU_BLANK)["size"] == component(PSU["ac"])["size"]
    for name in (FPC_BLANK, RCB_BLANK, PSU_BLANK):
        assert component(name)["class"] == "blank" and not component(name).get("elements")


def test_the_fan_tray_is_wide_enough_for_four_fans_and_has_a_lamp_for_each_and_one_for_the_feb():
    c = component(FAN)
    assert {"led-fan0", "led-fan1", "led-fan2", "led-fan3", "led-feb"} <= set(c["elements"])
    svg = (COMP / FAN / "v1/skins/default.svg").read_text()
    for label in ("FAN 0", "FAN 3", "FEB", "STATUS", "JNP5700-FAN"):
        assert f">{label}</text>" in svg, label


# --- what is printed ---------------------------------------------------------

def test_no_logo_is_drawn_and_a_zone_is_reserved():
    d = device()
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    assert [r["id"] for r in d["views"]["front"].get("regions") or []] == ["logo-zone"]
    for name in MODULE_PARTS:
        svg = (COMP / name / "v1/skins/default.svg").read_text()
        assert "JUNIPER" not in svg.upper()


def test_the_slot_and_supply_legends_are_the_ones_printed_on_the_metal():
    d = device()
    front = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"RCB 0", "RCB 1", "FPC 0", *(str(n) for n in range(1, 9))} <= front
    rear = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"PSU 0", "PSU 1", "PSU 2", "PSU 3"} <= rear


def test_the_photograph_wins_over_the_drawing_on_what_is_printed_and_the_note_says_so():
    notes = device()["provenance"]
    assert "rear-vs-photo" in notes and "sources-disagree" in " ".join(notes["rear-vs-photo"]["note"].split())
    assert "JNP5700-RCB" in (COMP / RCB / "v1/skins/default.svg").read_text()


# --- the DCIM export ---------------------------------------------------------

def test_the_dcim_device_types_export_one_per_orderable_configuration():
    parts = [v[1] for v in BUILDS.values()] + [CHAS]
    for part in parts:
        for target in ("netbox", "nautobot"):
            f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f} is missing - run dcim_export.py for qfx5700"
            doc = yaml.safe_load(f.read_text())
            assert doc["manufacturer"] == "Juniper"
            assert doc["model"] == part
            assert doc["u_height"] == 5.0


def test_no_other_qfx5700_device_type_exists_and_the_base_without_a_sku_exports_nothing():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5700*.yaml")}
    assert got == {v[1] for v in BUILDS.values()} | {CHAS}


def test_the_dcim_module_types_export_the_family_modules_by_part_number():
    for part in ("JNP5700-FAN", "QFX5700-RCB", "JNP5K-FPC-BLNK", "JNP5K-RCB-BLNK"):
        for target in ("netbox", "nautobot"):
            f = EXPORTS / target / "module-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f} is missing"
            assert yaml.safe_load(f.read_text())["part_number"] == part
