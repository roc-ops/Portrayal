"""The Juniper QFX5100-48S and QFX5100-48T, from the QFX5100 Switch Hardware Guide (2023-02-26).

One device per front panel. The 48S has 48 SFP+ cages and six QSFP+ cages, the 48T 48 RJ-45 jacks
and the same six QSFP+ cages, so they are two devices. Each one's power and airflow variants are
`orderable` configurations of it, because the guide shows one panel for all of them. Each
field-replaceable unit is a component named by its Juniper part number, prefixed with the family.

What the guide fixes, and so what these tests hold:
  Table 3    the envelope - 1.72 x 17.36 x 20.48 in (48S) and 21.47 in deep (48T), 1RU
  Table 1    the variants and their part numbers
  Table 13   the 650 W AC supplies, their airflow and handle colour; the datasheet's ordering table
             names the 650 W DC supplies
  Table 19   the fan modules, their airflow and colour
  Table 8    the port lamps: two for an SFP+ port, one for a 10GBASE-T port, four for a QSFP+ port
  figures 14, 15, 22   the ports, their count and numbering, and the management panel
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 3: height, width, depth in inches (1RU)
ENVELOPE_IN = {
    "qfx5100-48s": {"h": 1.72, "w": 17.36, "d": 20.48},
    "qfx5100-48t": {"h": 1.72, "w": 17.36, "d": 21.47},
}
DEVICES = sorted(ENVELOPE_IN)

# Table 1 and the datasheet's ordering table: configuration -> (part number, supply, fan, airflow, feed)
VARIANTS = {
    "qfx5100-48s": {
        "ac-f2b": ("QFX5100-48S-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "ac-b2f": ("QFX5100-48S-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
        "dc-f2b": ("QFX5100-48S-DC-AFO", "qfx5100-jpsu-650w-dc-afo", "qfx5100-fan-afo", "front-to-back", "dc"),
        "dc-b2f": ("QFX5100-48S-DC-AFI", "qfx5100-jpsu-650w-dc-afi", "qfx5100-fan-afi", "back-to-front", "dc"),
        # the three-management-port models (Table 1) and the Junos Fusion satellites 48SH (same panel)
        "ac-3mgmt-f2b": ("QFX5100-48S-3AFO", "qfx5100-jpsu-650w-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "ac-3mgmt-b2f": ("QFX5100-48S-3AFI", "qfx5100-jpsu-650w-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
        "sh-ac-f2b": ("QFX5100-48SH-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "sh-ac-b2f": ("QFX5100-48SH-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
    },
    "qfx5100-48t": {
        "ac-f2b": ("QFX5100-48T-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "ac-b2f": ("QFX5100-48T-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
        "dc-f2b": ("QFX5100-48T-DC-AFO", "qfx5100-jpsu-650w-dc-afo", "qfx5100-fan-afo", "front-to-back", "dc"),
        "dc-b2f": ("QFX5100-48T-DC-AFI", "qfx5100-jpsu-650w-dc-afi", "qfx5100-fan-afi", "back-to-front", "dc"),
        "th-ac-f2b": ("QFX5100-48TH-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "th-ac-b2f": ("QFX5100-48TH-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
    },
}
CASES = [(n, c) for n in sorted(VARIANTS) for c in VARIANTS[n]]
# Table 1: management ports a variant has (the 48S-AFO/-AFI and DC variants two, the others three)
THREE_PORT = {"ac-3mgmt-f2b", "ac-3mgmt-b2f", "sh-ac-f2b", "sh-ac-b2f"}
FANS = {"qfx5100-fan-afo", "qfx5100-fan-afi"}
PSUS = {"qfx5100-jpsu-650w-ac-afo", "qfx5100-jpsu-650w-ac-afi",
        "qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"}
PARTS = sorted(FANS | PSUS)
MODEL = {  # the part number the guide and the datasheet print
    "qfx5100-fan-afo": "QFX5100-FAN-AFO", "qfx5100-fan-afi": "QFX5100-FAN-AFI",
    "qfx5100-jpsu-650w-ac-afo": "JPSU-650W-AC-AFO", "qfx5100-jpsu-650w-ac-afi": "JPSU-650W-AC-AFI",
    "qfx5100-jpsu-650w-dc-afo": "JPSU-650W-DC-AFO", "qfx5100-jpsu-650w-dc-afi": "JPSU-650W-DC-AFI",
}


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def number(pid):
    return int(pid.split("-")[1])


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_3(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)


def test_the_48t_is_a_deeper_box_than_the_48s():
    """Table 3 gives the 48T 21.47 in and the 48S 20.48 in; they are not one row of figures."""
    s, t = load_device("qfx5100-48s")["chassis"], load_device("qfx5100-48t")["chassis"]
    assert t["depth"] - s["depth"] == pytest.approx(0.99 * INCH, abs=0.1)


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
    """The mounting brackets are not in Table 3's 17.36 in, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_names_are_as_printed_and_the_portfolio_is_the_family(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5100"}
    assert d["chassis"]["airflow"] == "front-to-back"
    assert d["chassis"]["power"] == "ac"


# --- the ports, per face -----------------------------------------------------

def cages(dev, *names):
    return [p for p in placements(dev, "front") if ref_name(p["ref"]) in names]


def test_48s_has_48_sfp_plus_and_6_qsfp_plus_cages_numbered_as_printed():
    d = load_device("qfx5100-48s")
    sfp, qsfp = cages(d, "sfp-ganged"), cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in sfp) == list(range(0, 48))
    assert sorted(number(p["id"]) for p in qsfp) == list(range(48, 54))
    assert not cages(d, "rj45-ganged-eth-plain")
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(54)} <= printed


def test_48t_has_48_rj45_jacks_and_6_qsfp_plus_cages_numbered_as_printed():
    d = load_device("qfx5100-48t")
    jacks, qsfp = cages(d, "rj45-ganged-eth-plain"), cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in jacks) == list(range(0, 48))
    assert sorted(number(p["id"]) for p in qsfp) == list(range(48, 54))
    assert not cages(d, "sfp-ganged")
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(54)} <= printed


@pytest.mark.parametrize("name", DEVICES)
def test_the_groups_say_what_the_ports_are(name):
    g = load_device(name)["groups"]
    assert g["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert g["qsfp-plus"]["role"] == "traffic"
    if name == "qfx5100-48s":
        assert g["sfp-plus"]["attrs"]["media"] == "sfp-plus"
        assert g["sfp-plus"]["attrs"]["speed"] == "10g"
        assert g["sfp-plus"]["role"] == "traffic"
    else:
        assert g["rj45"]["attrs"]["media"] == "rj45"
        assert g["rj45"]["attrs"]["speed"] == "10g"
        assert g["rj45"]["role"] == "traffic"


@pytest.mark.parametrize("name", DEVICES)
def test_the_qsfp_block_is_to_the_right_of_the_access_ports_in_two_rows_upper_even(name):
    d = load_device(name)
    access = cages(d, "sfp-ganged", "rj45-ganged-eth-plain")
    qsfp = cages(d, "qsfp-ganged")
    assert min(p["at"][0] for p in qsfp) > max(p["at"][0] for p in access)
    y = {number(p["id"]): p["at"][1] for p in access + qsfp}
    assert all(y[2 * c] < y[2 * c + 1] for c in range(24, 27)), "the QSFP+ pairs"
    assert all(y[2 * c] < y[2 * c + 1] for c in range(24)), "the access pairs"


def test_48s_access_ports_stand_in_four_blocks_of_six_columns():
    xs = sorted({p["at"][0] for p in cages(load_device("qfx5100-48s"), "sfp-ganged")})
    assert len(xs) == 24
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 14.25) < 0.02]) == 20
    assert len([s for s in steps if s > 14.3]) == 3, "three gutters between four blocks"


def test_48t_access_ports_stand_in_three_blocks_of_eight_columns():
    xs = sorted({p["at"][0] for p in cages(load_device("qfx5100-48t"), "rj45-ganged-eth-plain")})
    assert len(xs) == 24
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 13.97) < 0.02]) == 21
    assert len([s for s in steps if s > 14.0]) == 2, "two gutters between three blocks"


def lamps(dev):
    return {p["id"]: p for p in placements(dev, "front")
            if ref_name(p["ref"]) in ("led-dot", "led-arrow-sm")}


def test_48s_lamps_follow_table_8_two_an_sfp_plus_port_and_four_a_qsfp_plus_port():
    ids = lamps(load_device("qfx5100-48s"))
    for n in range(48):
        assert f"led-port-{n}" in ids and f"led-port-{n}-status" in ids
    for n in range(48, 54):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= set(ids)
    assert len(ids) == 96 + 24
    for lamp in ids.values():
        assert lamp["for"].startswith("port-")


def test_48t_lamps_are_one_link_activity_triangle_a_jack():
    """Table 8 gives the 48T a Link lamp and no Status lamp (Table 9: 'Not applicable for QFX5100-48T')."""
    ids = lamps(load_device("qfx5100-48t"))
    assert {i for i in ids if i.startswith("led-port-") and number(i[4:]) < 48} == \
        {f"led-port-{n}" for n in range(48)}
    assert not [i for i in ids if i.endswith("-status")]
    skins = {ids[f"led-port-{n}"].get("skin") for n in range(48)}
    assert skins == {"up", "down"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_carries_the_esd_terminal(name):
    """Figures 14 and 15, callout 1."""
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert ref_name(by_id["esd-front-jack"]["ref"]) == "esd-jack"
    assert by_id["esd-front-jack"]["group"] == "esd"


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_four_chassis_lamps_the_console_usb_reset_and_management(name):
    """Figure 22: status LEDs, em1 SFP (C1), reset, em0 RJ-45 (C0), console, USB."""
    d = load_device(name)
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "console", "usb",
            "mgmt-c0", "mgmt-c1"} <= set(by_id)
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert by_id["mgmt-c0"]["attrs"]["speed"] == "1g"
    assert by_id["mgmt-c1"]["attrs"]["role"] == "mgmt"


def test_48s_has_two_management_ports_and_the_48t_three():
    """Table 1: the 48S-AFO and -AFI have two management ports; the 48T has three, a second SFP above C1."""
    s = {p["id"] for p in placements(load_device("qfx5100-48s"), "rear")}
    t = {p["id"] for p in placements(load_device("qfx5100-48t"), "rear")}
    assert "mgmt-c0-sfp" not in s
    assert "mgmt-c0-sfp" in t
    for pid in ("mgmt-c1", "mgmt-c0-sfp"):
        by_id = {p["id"]: p for p in placements(load_device("qfx5100-48t"), "rear")}
        assert ref_name(by_id[pid]["ref"]) == "sfp-ganged"


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_says_the_model_and_leaves_the_logo_to_a_zone(name):
    d = load_device(name)
    rear = d["views"]["rear"]
    texts = [s.get("text", "") for s in rear["silkscreen"]]
    assert d["model"] in texts
    assert "RUNNING JUNOS" in texts
    assert not [t for t in texts if "JUNIPER" in t.upper() or "NETWORKS" in t.upper()]
    assert [r["id"] for r in rear["regions"]] == ["logo-zone"]


@pytest.mark.parametrize("name", DEVICES)
def test_five_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them(name):
    """Fan slots 0 to 4 left to right (Fan Modules); two supplies at the right."""
    b = {x["id"]: x for x in bays(load_device(name), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(5)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["psu-1"]["at"][0]
    assert b["psu-0"]["at"][0] > b["fan-4"]["at"][0]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_variant_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name])
    for cid, (part, *_rest) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name, as the configuration leaves it (default where unstated)."""
    cfg = dev["configurations"][cid]
    return {b["id"]: ref_name((cfg.get("bays") or {}).get(b["id"], b.get("default")))
            for b in bays(dev, "rear")}


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    _part, psu, fan, airflow, feed = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(5)} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == feed


@pytest.mark.parametrize("cid", sorted(VARIANTS["qfx5100-48s"]))
def test_48s_variants_wear_the_management_panel_table_1_gives_them(cid):
    """Two ports for the -AFO, -AFI and DC models; three (a second SFP, C0, above C1) for -3AFO, -3AFI and 48SH."""
    d = load_device("qfx5100-48s")
    rear = d["configurations"][cid].get("views", {}).get("rear", "rear")
    ids = {p["id"] for p in placements({"views": {"rear": d["views"][rear]}}, "rear")}
    assert ("mgmt-c0-sfp" in ids) == (cid in THREE_PORT)
    assert {"mgmt-c0", "mgmt-c1", "console", "usb"} <= ids
    assert d["views"][rear]["face"] == "rear" if rear != "rear" else True


def test_the_two_rear_panels_of_the_48s_seat_the_same_modules():
    d = load_device("qfx5100-48s")
    a = {(b["id"], tuple(b["at"])) for b in bays(d, "rear")}
    b = {(x["id"], tuple(x["at"])) for x in (d["views"]["rear-3mgmt"]["components"]["bays"])}
    assert {i for i, _ in a} == {i for i, _ in b}


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == (FANS if b["id"].startswith("fan-") else PSUS), b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    for b in bays(load_device(name), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", PARTS)
def test_a_unit_is_named_for_its_family_and_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and part.startswith("qfx5100-")
    assert c["attrs"]["model"] == MODEL[part]
    assert c["kind"] == "module"


@pytest.mark.parametrize("part", PARTS)
def test_a_unit_is_described_as_the_unit_and_names_the_models_that_take_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "field-replaceable" in text
    assert "QFX5100-48S" in text and "QFX5100-48T" in text


@pytest.mark.parametrize("part", sorted(PSUS))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 650
    assert not any(k.startswith("power-draw") for k in attrs)
    assert attrs["role"] == ("dc-power-supply" if "-dc-" in part else "ac-power-supply")


@pytest.mark.parametrize("part", sorted(FANS))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [
    ("qfx5100-jpsu-650w-ac-afo", "qfx5100-jpsu-650w-ac-afi"),
    ("qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"),
    ("qfx5100-fan-afo", "qfx5100-fan-afi"),
])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_a_gold_one(front, back):
    """Tables 13 and 19: AFO (port-to-FRU) is Juniper Gold, AFI (FRU-to-port) is Juniper Azure Blue."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"


@pytest.mark.parametrize("part", sorted(FANS))
def test_a_fan_module_prints_its_direction_as_the_guide_labels_it(part):
    """Table 19: AIR OUT on the gold module, AIR IN on the blue one."""
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    word = "OUT" if part.endswith("afo") else "IN"
    assert f">{word}</text>" in svg and ">AIR</text>" in svg


@pytest.mark.parametrize("part", sorted(p for p in PSUS if "-ac-" in p))
def test_an_ac_supply_prints_its_direction_on_the_handle(part):
    """Figures 26 and 27, and the photographs: the AC handle is lettered AFO or AFI."""
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert f">{part[-3:].upper()}</text>" in svg


@pytest.mark.parametrize("part", sorted(p for p in PSUS if "-dc-" in p))
def test_a_dc_supply_has_four_terminals_in_the_order_the_guide_prints(part):
    """Figure 33: V- V- V+ V+ left to right, then the IN, OUT and ! lamps."""
    import re
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    legends = re.findall(r'<text x="([\d.]+)" y="[\d.]+" font-size="[\d.]+">(V[-+])</text>', svg)
    assert [t for _x, t in legends] == ["V-", "V-", "V+", "V+"]
    xs = [float(x) for x, _t in legends]
    assert xs == sorted(xs)
    c = load_component(part)
    assert {"led-in", "led-out", "led-fault"} <= set(c["elements"])


@pytest.mark.parametrize("part", sorted(p for p in PSUS if "-ac-" in p))
def test_an_ac_supply_has_the_ac_dc_and_fault_lamps_and_a_c14_inlet(part):
    """Table 16: AC OK, DC OK and Fault."""
    c = load_component(part)
    assert {"led-ac", "led-dc", "led-fault"} <= set(c["elements"])
    assert [p["ref"] for p in c["parts"]] == ["std/c14-inlet@1"]


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid", CASES)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, cid):
    part = VARIANTS[name][cid][0]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_juniper_qfx5100_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5100-48*.yaml")}
    want = {v[0] for per in VARIANTS.values() for v in per.values()}
    assert got == want
