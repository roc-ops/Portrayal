"""The Juniper QFX10008 and QFX10016, from the QFX10008 and QFX10016 Switch Hardware Guides (2025-12-11).

One device per chassis. The base, redundant, high-voltage and DC builds of each are configurations of the one
chassis, because the guides draw one front and one rear for them. The QFX line cards are a family of their own and
are not built here: the line-card bays seat the cover each configuration ships, and name no card.

What the guides fix, and so what these tests hold:
  Table 63   the envelope - 22.6 x 17.4 x 32 in (QFX10008, 13U), 36.6 x 17.4 x 35 in (QFX10016, 21U)
  Table 2/3  the configurations and the supplies, fan trays and covers each ships
  Table 1    the four power supplies and what they put out
  Table 64   the draw of the RCB and of the fan trays
  figures 1, 2, 42   the slots, their numbering and what the RCB faceplate carries
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 63: height, width, depth in inches; rack units
ENVELOPE_IN = {
    "qfx10008": {"h": 22.6, "w": 17.4, "d": 32.0, "ru": 13},
    "qfx10016": {"h": 36.6, "w": 17.4, "d": 35.0, "ru": 21},
}
DEVICES = sorted(ENVELOPE_IN)
SLOTS = {"qfx10008": {"fpc": 8, "psu": 6, "psu-base": 3}, "qfx10016": {"fpc": 16, "psu": 10, "psu-base": 5}}
FAN = {"qfx10008": "qfx10008-fan", "qfx10016": "qfx10016-fan"}

# configuration -> (part number, power feed, supply, supplies fitted, RCBs fitted)
VARIANTS = {
    "qfx10008": {
        "base": ("QFX10008-BASE", "ac", "qfx10000-pwr-ac", 3, 1),
        "base-h": ("QFX10008-BASE-H", ["ac", "hvdc"], "jnp10k-pwr-ac2", 3, 1),
        "redund": ("QFX10008-REDUND", "ac", "qfx10000-pwr-ac", 6, 2),
        "redund-h": ("QFX10008-REDUND-H", ["ac", "hvdc"], "jnp10k-pwr-ac2", 6, 2),
        "redund-dc": ("QFX10008-REDUND-DC", "dc", "qfx10000-pwr-dc", 6, 2),
    },
    "qfx10016": {
        "base": ("QFX10016-BASE", "ac", "qfx10000-pwr-ac", 5, 1),
        "redund": ("QFX10016-REDUND", "ac", "qfx10000-pwr-ac", 10, 2),
        "redund-dc": ("QFX10016-REDUND-DC", "dc", "qfx10000-pwr-dc", 10, 2),
    },
}
# the supplies every supply bay accepts: the four of Table 1, and the cover
# (the JNP10K-PWR-AC2 is version 2 of juniper/jnp10k-pwr-ac2 in both)
PSU_ACCEPTS = {
    "qfx10008": {"qfx10000-pwr-ac", "jnp10k-pwr-ac2", "qfx10000-pwr-dc", "qfx10000-jnp10k-pwr-dc2", "qfx10000-pwr-cover"},
    "qfx10016": {"qfx10000-pwr-ac", "jnp10k-pwr-ac2", "qfx10000-pwr-dc", "qfx10000-jnp10k-pwr-dc2", "qfx10000-pwr-cover"},
}
FAN_ACCEPTS = {
    "qfx10008": {"qfx10008-fan", "jnp10008-fan", "jnp10008-fan2"},
    "qfx10016": {"qfx10016-fan"},
}
# the part number each new component is named by in the guides
MODEL = {
    "qfx10000-pwr-ac": "QFX10000-PWR-AC",
    "qfx10000-pwr-dc": "QFX10000-PWR-DC",
    "qfx10000-jnp10k-pwr-dc2": "JNP10K-PWR-DC2",
    "qfx10000-re": "QFX10000-RE",
    "qfx10008-fan": "QFX10008-FAN",
    "qfx10016-fan": "QFX10016-FAN",
}
COVERS = ["qfx10000-lc-cover", "qfx10000-re-cover", "qfx10000-pwr-cover"]
NEW_PARTS = sorted(list(MODEL) + COVERS)
# Table 1 and Tables 24 and 27: the output of each new supply
PSU_WATTS = {"qfx10000-pwr-ac": 2700, "qfx10000-pwr-dc": 2500, "qfx10000-jnp10k-pwr-dc2": 5500}
# the line cards the guides list and that are left out, by part number
LEFT_OUT = ["QFX10000-36Q", "QFX10000-30C", "QFX10000-30C-M", "QFX10000-60S-6Q", "QFX10K-12C-DWDM"]


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def load_component(name, major=1):
    return yaml.safe_load((COMP / name / f"v{major}" / "contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_63_and_the_rack_units_are_the_datasheets(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == want["ru"]
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)


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
def test_the_front_is_the_body_and_not_the_rack_face(name):
    """The mounting-bracket flange extends the body to 19 in, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_is_named_and_filed_as_the_guide_names_it(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX10000"}
    assert d["chassis"]["airflow"] == "front-to-back"


# --- the slots and the ports, per face ----------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_line_card_slots_are_numbered_top_to_bottom_at_the_guides_pitch(name):
    b = [x for x in bays(load_device(name), "front") if x["id"].startswith("fpc")]
    assert [x["id"] for x in b] == [f"fpc{k}" for k in range(SLOTS[name]["fpc"])]
    ys = [x["at"][1] for x in b]
    assert ys == sorted(ys)
    # Table 63: a line card is 1.89 in (48 mm) high and 17.2 in (437 mm) wide
    assert all(x["size"] == {"w": 437.0, "h": 48.0} for x in b)
    assert all(48.0 < y2 - y1 < 56.0 for y1, y2 in zip(ys, ys[1:]))


@pytest.mark.parametrize("name", DEVICES)
def test_the_rcb_slots_are_cb0_over_cb1_above_the_line_cards(name):
    d = load_device(name)
    b = {x["id"]: x for x in bays(d, "front")}
    assert b["cb0"]["at"][1] < b["cb1"]["at"][1] < b["fpc0"]["at"][1]
    assert b["cb0"]["size"] == b["cb1"]["size"] == {"w": 389.0, "h": 38.1}


@pytest.mark.parametrize("name", DEVICES)
def test_a_line_card_bay_names_no_qfx_line_card_and_accepts_the_cover(name):
    """The QFX line cards are a family of their own; none shares a part number with a JNP10K card on main."""
    d = load_device(name)
    for b in bays(d, "front"):
        if b["id"].startswith("fpc"):
            assert {ref_name(r) for r in b["accepts"]} == {"qfx10000-lc-cover"}
            assert ref_name(b["default"]) == "qfx10000-lc-cover"
    text = " ".join(str(g.get("wanted")) for g in d["gaps"] if g["what"] == "line-cards")
    for part in LEFT_OUT:
        assert part in text, f"{part} is left out and must be named"


@pytest.mark.parametrize("name", DEVICES)
def test_the_chassis_faces_carry_no_ports_and_the_rcb_carries_them(name):
    """The ports of a QFX10000 chassis are on its RCBs and line cards, never on the chassis face."""
    d = load_device(name)
    for view in ("front", "rear"):
        refs = {ref_name(p["ref"]) for p in placements(d, view)}
        assert not refs & {"sfp", "sfp-ganged", "qsfp-ganged", "qsfp28", "rj45", "rj45-eth", "usb-a", "smb"}


def test_the_rcb_has_the_figure_42_faceplate():
    c = load_component("qfx10000-re")
    parts = {p["id"]: p for p in c["parts"]}
    assert ref_name(parts["con"]["ref"]) == "rj45"
    assert ref_name(parts["mgmt"]["ref"]) == "rj45-eth" and parts["mgmt"]["attrs"]["speed"] == "1g"
    assert ref_name(parts["mgmt-sfp"]["ref"]) == "sfp"
    assert ref_name(parts["usb"]["ref"]) == "usb-a"
    smb = [i for i in parts if ref_name(parts[i]["ref"]) == "smb"]
    assert sorted(smb) == ["mhz-in", "mhz-out", "pps-in", "pps-out"]
    # four SFP+ cages numbered 0 to 3, left to right, all 10g and reserved
    xge = sorted((i for i in parts if i.startswith("xge-")), key=lambda i: parts[i]["at"][0])
    assert xge == [f"xge-{k}" for k in range(4)]
    assert all(ref_name(parts[i]["ref"]) == "sfp" and parts[i]["attrs"]["media"] == "sfp-plus" for i in xge)
    assert c["groups"]["xge"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    # the order the figure draws, left to right
    order = ["con", "pps-in", "pps-out", "mhz-in", "mhz-out", "mgmt", "mgmt-sfp", "usb", "xge-0"]
    xs = [parts[i]["at"][0] for i in order]
    assert xs == sorted(xs)
    svg = (COMP / "qfx10000-re/v1/skins/default.svg").read_text()
    for legend in ("PWR", "STS", "MST", "OFF", "CON", "1PPS", "10MHz", "MGMT", "SSD", "RESET"):
        assert f">{legend}</text>" in svg


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_panel_has_the_five_status_lamps_in_the_figure_13_order(name):
    d = load_device(name)
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-")]
    assert [p["id"] for p in lamps] == ["led-psus", "led-fans", "led-sibs", "led-lcs", "led-cbs"]
    ys = [p["at"][1] for p in lamps]
    assert ys == sorted(ys)
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text")}
    assert {"POWER SUPPLIES", "FANS", "SIBS", "LINE CARDS", "CONTROL BOARDS"} <= printed


@pytest.mark.parametrize("name", DEVICES)
def test_no_vendor_logo_is_drawn_and_a_zone_is_reserved(name):
    d = load_device(name)
    texts = {str(s.get("text", "")).upper() for s in d["views"]["front"]["silkscreen"]}
    assert not {t for t in texts if "JUNIPER" in t or "NETWORKS" in t}
    assert name.upper() in texts
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])


# --- the supplies and the fan trays -------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_supply_slots_are_numbered_top_to_bottom_and_clear_of_the_earthing_terminal(name):
    d = load_device(name)
    b = [x for x in bays(d, "rear") if x["id"].startswith("psu")]
    assert [x["id"] for x in b] == [f"psu{k}" for k in range(SLOTS[name]["psu"])]
    ys = [x["at"][1] for x in b]
    assert ys == sorted(ys)
    # Table 13: a supply is 3.6 in wide and 3.5 in high; the stack leaves room below it for the earthing terminal
    assert all(x["size"] == {"w": 91.4, "h": 88.9} for x in b)
    assert ys[-1] + 88.9 + 30 < d["chassis"]["height"]
    holes = [x for x in d["views"]["rear"]["panel"]["decor"] if x.get("shape") == "circle"]
    assert len(holes) == 2 and holes[0]["at"][1] > ys[-1] + 88.9
    assert holes[1]["at"][0] - holes[0]["at"][0] == pytest.approx(16.0, abs=0.01)


@pytest.mark.parametrize("name", DEVICES)
def test_a_supply_bay_accepts_the_supplies_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        if b["id"].startswith("psu"):
            assert {ref_name(r) for r in b["accepts"]} == PSU_ACCEPTS[name], b["id"]
            assert ref_name(b["default"]) == "qfx10000-pwr-ac"


@pytest.mark.parametrize("name", DEVICES)
def test_two_fan_trays_stand_side_by_side_and_accept_the_trays_the_guide_names(name):
    d = load_device(name)
    b = [x for x in bays(d, "rear") if x["id"].startswith("fan")]
    assert [x["id"] for x in b] == ["fan0", "fan1"]
    assert b[0]["at"][0] < b[1]["at"][0]
    assert all(x["size"]["w"] == 168.0 for x in b), "Table 8: 6.6 in wide"
    for x in b:
        assert {ref_name(r) for r in x["accepts"]} == FAN_ACCEPTS[name]
        assert ref_name(x["default"]) == FAN[name]


def test_the_qfx10008_reuses_the_mx_fan_trays_the_guide_names_and_copies_none():
    """Table 4 names JNP10008-FAN2 and Figure 104 names JNP10008-FAN as QFX10008 fan trays."""
    assert load_component("jnp10008-fan")["attrs"]["model"] == "JNP10008-FAN"
    assert load_component("jnp10008-fan2")["attrs"]["model"] == "JNP10008-FAN2"
    assert not (COMP / "qfx10008-jnp10008-fan").exists()
    assert not (COMP / "qfx10008-jnp10008-fan2").exists()


def test_both_chassis_seat_version_2_of_the_jnp10k_pwr_ac2_drawn_to_table_16_and_leave_version_1_as_it_was():
    """Table 16 (and the MX10008 guide's Table 55): 3.6 x 3.5 in. Version 1, 84 x 97 mm, is retired and not edited."""
    v1, v2 = load_component("jnp10k-pwr-ac2"), load_component("jnp10k-pwr-ac2", 2)
    assert v1["attrs"]["model"] == v2["attrs"]["model"] == "JNP10K-PWR-AC2"
    assert (v2["size"]["w"], v2["size"]["h"]) == (91.4, 88.9)
    assert v2["attrs"]["power-output-w"] == 5500
    assert (v1["size"]["w"], v1["size"]["h"]) == (84.0, 97.0)
    assert not (COMP / "qfx10008-pwr-ac2").exists()
    d = load_device("qfx10008")
    refs = [r for b in bays(d, "rear") if b["id"].startswith("psu") for r in b["accepts"]]
    assert "juniper/jnp10k-pwr-ac2@2" in refs and "juniper/jnp10k-pwr-ac2@1" not in refs
    for cid in ("base-h", "redund-h"):
        seats = [r for k, r in d["configurations"][cid]["bays"].items() if k.startswith("psu")]
        assert "juniper/jnp10k-pwr-ac2@2" in seats and "juniper/jnp10k-pwr-ac2@1" not in seats
    refs16 = [r for b in bays(load_device("qfx10016"), "rear") if b["id"].startswith("psu") for r in b["accepts"]]
    assert "juniper/jnp10k-pwr-ac2@2" in refs16 and "juniper/jnp10k-pwr-ac2@1" not in refs16


# --- the configurations -------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_configuration_is_the_one_the_guide_names(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name])
    for cid, (part, *_rest) in VARIANTS[name].items():
        assert set(cfgs[cid]["part-numbers"]) == {part}
        assert cfgs[cid]["kind"] == ("base" if cid == "base" else "orderable")


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_the_base_ac_build(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["base"]


def seated(dev, cid, view):
    cfg = dev["configurations"][cid]
    return {b["id"]: ref_name((cfg.get("bays") or {}).get(b["id"], b.get("default"))) for b in bays(dev, view)}


CASES = [(n, c) for n in DEVICES for c in VARIANTS[n]]


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_the_supplies_the_guide_counts_and_covers_the_rest(name, cid):
    d = load_device(name)
    _part, _feed, psu, count, _rcbs = VARIANTS[name][cid]
    s = seated(d, cid, "rear")
    got = [s[f"psu{k}"] for k in range(SLOTS[name]["psu"])]
    assert got == [psu] * count + ["qfx10000-pwr-cover"] * (SLOTS[name]["psu"] - count)


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_its_rcbs_a_cover_over_the_second_and_a_cover_in_every_line_card_slot(name, cid):
    d = load_device(name)
    rcbs = VARIANTS[name][cid][4]
    s = seated(d, cid, "front")
    assert s["cb0"] == "qfx10000-re"
    assert s["cb1"] == ("qfx10000-re" if rcbs == 2 else "qfx10000-re-cover")
    assert {s[f"fpc{k}"] for k in range(SLOTS[name]["fpc"])} == {"qfx10000-lc-cover"}


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_the_fan_tray_of_the_chassis_with_matching_airflow(name, cid):
    d = load_device(name)
    s = seated(d, cid, "rear")
    assert {s["fan0"], s["fan1"]} == {FAN[name]}
    assert load_component(FAN[name])["attrs"]["airflow"] == "front-to-back"
    psu = VARIANTS[name][cid][2]
    # the reused JNP10K-PWR-AC2 states no airflow and is not edited; every new supply states the chassis's
    assert load_component(psu)["attrs"].get("airflow", "front-to-back") == "front-to-back"
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == "front-to-back"


@pytest.mark.parametrize("name,cid", CASES)
def test_the_power_feed_follows_the_supplies_seated(name, cid):
    d = load_device(name)
    assert d["configurations"][cid]["power"] == VARIANTS[name][cid][1]


# --- the field-replaceable units ----------------------------------------------

@pytest.mark.parametrize("part", sorted(MODEL))
def test_a_unit_is_named_by_its_juniper_part_number(part):
    c = load_component(part)
    assert c["attrs"]["model"] == MODEL[part]
    assert c["kind"] == "module"


@pytest.mark.parametrize("part", NEW_PARTS)
def test_a_new_component_carries_the_family_prefix_and_its_own_skin(part):
    assert part.startswith(("qfx10000-", "qfx10008-", "qfx10016-"))
    assert (COMP / part / "v1" / "skins" / "default.svg").exists()


@pytest.mark.parametrize("part,watts", sorted(PSU_WATTS.items()))
def test_a_supply_states_the_power_it_provides_as_an_output(part, watts):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == watts
    assert not any(k.startswith("power-draw") for k in attrs)
    assert attrs["airflow"] == "front-to-back"


def test_the_rcb_and_the_fan_trays_state_the_power_they_draw_from_table_64():
    assert load_component("qfx10000-re")["attrs"]["power-draw-typical-w"] == 50
    assert load_component("qfx10000-re")["attrs"]["power-draw-max-w"] == 100
    assert load_component("qfx10008-fan")["attrs"]["power-draw-typical-w"] == 225
    assert load_component("qfx10008-fan")["attrs"]["power-draw-max-w"] == 475
    assert load_component("qfx10016-fan")["attrs"]["power-draw-typical-w"] == 475
    assert load_component("qfx10016-fan")["attrs"]["power-draw-max-w"] == 975


def test_the_fan_trays_have_the_guides_size_and_fan_counts():
    f8, f16 = load_component("qfx10008-fan"), load_component("qfx10016-fan")
    assert (f8["size"]["w"], f8["size"]["h"]) == (168.0, 569.0)
    assert (f16["size"]["w"], f16["size"]["h"]) == (168.0, 929.6)
    assert f8["attrs"]["fans-per-tray"] == 11 and f16["attrs"]["fans-per-tray"] == 21


def test_the_supplies_have_table_13_25_28_size():
    for part in PSU_WATTS:
        assert load_component(part)["size"]["w"] == 91.4
        assert load_component(part)["size"]["h"] == 88.9


@pytest.mark.parametrize("name", DEVICES)
def test_each_cover_is_the_size_of_the_bay_it_fills(name):
    d = load_device(name)
    want = {"qfx10000-lc-cover": "fpc", "qfx10000-re-cover": "cb", "qfx10000-pwr-cover": "psu"}
    for cover, prefix in want.items():
        c = load_component(cover)["size"]
        for b in [b for v in ("front", "rear") for b in bays(d, v)]:
            if b["id"].startswith(prefix) and b["id"] != "cb":
                assert (b["size"]["w"], b["size"]["h"]) == (c["w"], c["h"]), (cover, b["id"])


def test_the_covers_are_not_the_mx_covers_whose_part_numbers_the_qfx_guides_never_print():
    """Reuse only where the guide names the same part number: the guides name none for a cover."""
    for part, mx in zip(COVERS, ("JNP10K-LC-BLNK", "JNP10K-RE-BLNK", "JNP10K-PWR-BLNK")):
        c = load_component(part)
        assert c["attrs"]["model"].startswith("QFX10000")
        note = " ".join(c["provenance"]["part-number"].split())
        assert "part number" in note and "no part number" in note.replace("None prints a", "no")
        assert mx not in str(c["attrs"])


def test_the_existing_mx_components_are_untouched():
    """Each is reused as it is: the QFX10008 accepts the MX10008 trays at the guide's size, version 2."""
    for part in ("jnp10008-fan", "jnp10008-fan2"):
        assert load_component(part, 2)["version"] == "2.0.0"
        assert load_component(part, 1)["superseded-by"] == f"juniper/{part}@2"


# --- the DCIM export ----------------------------------------------------------

ORDERABLE = [(n, v[0], ENVELOPE_IN[n]["ru"]) for n in DEVICES for v in VARIANTS[n].values()]


@pytest.mark.parametrize("name,part,ru", ORDERABLE)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, part, ru):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == float(ru)


def test_no_other_juniper_qfx10000_chassis_export_exists():
    folder = EXPORTS / "netbox/device-types/Juniper"
    got = {p.stem for pat in ("QFX10008-*.yaml", "QFX10016-*.yaml") for p in folder.glob(pat)}
    assert got == {part for _n, part, _ru in ORDERABLE}
