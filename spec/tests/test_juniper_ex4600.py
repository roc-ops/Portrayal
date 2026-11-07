"""The Juniper EX4600-40F, from the EX4600 Switch Hardware Guide (published 2025-08-12).

One device per front panel. The guide shows one port panel for all five models in its Table 3
(-AFI, -AFO, -DC-AFI, -DC-AFO and the spare chassis -S), so each is an `orderable` configuration of
`juniper/ex4600-40f`. Each field-replaceable unit is a component named for its Juniper part number
and prefixed with the family, because the same parts appear in the QFX5100 guide.

What the guide and the datasheet fix, and so what these tests hold:
  Table 4        the envelope - 1.72 x 17.36 x 20.48 in, 1RU
  Table 3        the models, their power supply, airflow and the two expansion bays
  Table 11       the fan modules: QFX5100-FAN-AFI (AIR IN, blue) and QFX5100-FAN-AFO (AIR OUT, orange)
  Table 14       the AC supplies: JPSU-650W-AC-AFI (blue handle) and JPSU-650W-AC-AFO (orange handle)
  Figure 9       24 SFP+ ports (0 to 23), 4 QSFP+ ports (24 to 27), two expansion bays, the ESD terminal
  Figures 10, 11 two lamps on an SFP+ port, four on a QSFP+ port
  Figure 13      the management panel on the FRU side
  Datasheet      the ordering table: part numbers of the supplies, the fan modules and the modules
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper/ex4600-40f"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 4: 1.72 in high, 17.36 in wide, 20.48 in deep, 1RU
ENVELOPE_IN = {"h": 1.72, "w": 17.36, "d": 20.48}

# Table 3 and the datasheet ordering table:
# configuration -> (part number, supply, fan module, airflow, input)
VARIANTS = {
    "ac-f2b": ("EX4600-40F-AFO", "ex4600-jpsu-650-ac-afo", "ex4600-fan-afo", "front-to-back"),
    "ac-b2f": ("EX4600-40F-AFI", "ex4600-jpsu-650-ac-afi", "ex4600-fan-afi", "back-to-front"),
    "dc-f2b": ("EX4600-40F-DC-AFO", "ex4600-jpsu-650-dc-afo", "ex4600-fan-afo", "front-to-back"),
    "dc-b2f": ("EX4600-40F-DC-AFI", "ex4600-jpsu-650-dc-afi", "ex4600-fan-afi", "back-to-front"),
}
SPARE = ("s", "EX4600-40F-S")
SUPPLIES = {"ex4600-jpsu-650-ac-afo", "ex4600-jpsu-650-ac-afi",
            "ex4600-jpsu-650-dc-afo", "ex4600-jpsu-650-dc-afi"}
FANS = {"ex4600-fan-afo", "ex4600-fan-afi"}
MODULES = {"ex4600-em-blnk", "ex4600-em-8f", "ex4600-em-4q"}
# The Juniper part number each unit is ordered under (datasheet, Modules and Spares)
PART_NUMBER = {
    "ex4600-jpsu-650-ac-afo": "JPSU-650W-AC-AFO", "ex4600-jpsu-650-ac-afi": "JPSU-650W-AC-AFI",
    "ex4600-jpsu-650-dc-afo": "JPSU-650W-DC-AFO", "ex4600-jpsu-650-dc-afi": "JPSU-650W-DC-AFI",
    "ex4600-fan-afo": "QFX5100-FAN-AFO", "ex4600-fan-afi": "QFX5100-FAN-AFI",
    "ex4600-em-blnk": "QFX5100-EM-BLNK", "ex4600-em-8f": "EX4600-EM-8F", "ex4600-em-4q": "QFX-EM-4Q",
}


def load_device():
    return yaml.safe_load((DEV / "device.yaml").read_text())


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

def test_the_envelope_is_table_4():
    ch = load_device()["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(ENVELOPE_IN["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(ENVELOPE_IN["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(ENVELOPE_IN["d"] * INCH, abs=0.1)


def test_the_faces_are_sized_from_the_envelope():
    d = load_device()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_front_is_the_body_and_not_the_rack_face():
    """Table 23: the brackets extend 17.36 in to 19 in, so the body is what is drawn."""
    assert load_device()["views"]["front"]["size"]["w"] < 480


def test_the_device_is_named_as_the_guide_prints_it():
    d = load_device()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "EX4600-40F"
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4600"}


# --- the ports, per face -----------------------------------------------------

def cages(dev):
    out = {"sfp": [], "qsfp": []}
    for p in placements(dev, "front"):
        name = ref_name(p["ref"])
        if name == "sfp-ganged":
            out["sfp"].append(p)
        elif name == "qsfp-ganged":
            out["qsfp"].append(p)
    return out


def test_24_sfp_plus_and_4_qsfp_plus_cages_on_the_front():
    c = cages(load_device())
    assert len(c["sfp"]) == 24
    assert len(c["qsfp"]) == 4


def test_ports_are_numbered_0_to_27_as_printed():
    d = load_device()
    c = cages(d)
    assert sorted(number(p["id"]) for p in c["sfp"]) == list(range(24))
    assert sorted(number(p["id"]) for p in c["qsfp"]) == list(range(24, 28))
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(28)} <= printed


def test_the_groups_say_what_the_ports_are():
    g = load_device()["groups"]
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert g["sfp-plus"]["role"] == g["qsfp-plus"]["role"] == "traffic"


def test_sfp_ports_sit_in_two_rows_of_two_blocks_of_six_with_even_numbers_above():
    c = cages(load_device())
    by = {number(p["id"]): p["at"] for p in c["sfp"]}
    assert all(by[2 * k][1] < by[2 * k + 1][1] for k in range(12))
    assert all(by[2 * k][0] == by[2 * k + 1][0] for k in range(12))
    xs = [by[2 * k][0] for k in range(12)]
    gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert all(g == 14.25 for i, g in enumerate(gaps) if i != 5)
    assert gaps[5] > 14.25 + 3, "a gutter between ports 10/11 and 12/13"
    q = {number(p["id"]): p["at"] for p in c["qsfp"]}
    assert min(a[0] for a in q.values()) > max(a[0] for a in by.values())
    assert q[24][1] < q[25][1] and q[26][1] < q[27][1]
    assert q[24][0] == q[25][0] and q[26][0] == q[27][0] and q[26][0] > q[24][0]


def test_the_lamps_follow_figures_10_and_11():
    """Two lamps on each SFP+ port (link/activity, status), four on each QSFP+ port."""
    ids = {p["id"] for p in placements(load_device(), "front") if ref_name(p["ref"]) == "led-dot"}
    for n in range(24):
        assert {f"led-port-{n}", f"led-port-{n}-status"} <= ids
    for n in range(24, 28):
        assert {f"led-port-{n}"} | {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= ids
    assert len(ids) == 24 * 2 + 4 * 4


def test_the_two_expansion_bays_are_at_the_right_of_the_port_panel():
    d = load_device()
    b = {x["id"]: x for x in bays(d, "front")}
    assert sorted(b) == ["em-0", "em-1"]
    assert b["em-0"]["at"][0] < b["em-1"]["at"][0]
    assert b["em-0"]["at"][0] > max(p["at"][0] for p in cages(d)["qsfp"])
    assert b["em-0"]["size"] == b["em-1"]["size"]


def test_the_front_has_an_esd_terminal_and_no_logo_is_drawn():
    d = load_device()
    assert any(ref_name(p["ref"]) == "esd-jack" for p in placements(d, "front"))
    # the rear carries the maker's mark (figure 13); the front prints none (photograph)
    assert any(r["id"] == "logo-zone" for r in d["views"]["rear"]["regions"])
    for view in ("front", "rear"):
        words = " ".join(s.get("text", "") for s in d["views"][view].get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words


def test_the_rear_carries_the_management_panel_of_figure_13():
    d = load_device()
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt-c0"]["ref"]) == "rj45-ganged-eth"
    assert ref_name(by_id["mgmt-c1"]["ref"]) == "sfp"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn"} <= set(by_id)
    # the console is above the C0 jack in one shell
    assert by_id["console"]["at"][1] < by_id["mgmt-c0"]["at"][1]


def test_five_fan_slots_and_two_supply_slots_numbered_left_to_right():
    """Fan slots 0 to 4 'from left to right' (Fan Modules); two supply slots next to them."""
    b = {x["id"]: x for x in bays(load_device(), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(5)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["psu-1"]["at"][0]
    assert b["psu-0"]["at"][0] > b["fan-4"]["at"][0]


# --- the configurations ------------------------------------------------------

def test_each_variant_is_an_orderable_configuration_with_its_part_number():
    cfgs = load_device()["configurations"]
    want = {cid: v[0] for cid, v in VARIANTS.items()}
    want[SPARE[0]] = SPARE[1]
    orderable = {c for c, v in cfgs.items() if v["kind"] == "orderable"}
    assert orderable == set(want)
    for cid, part in want.items():
        assert set(cfgs[cid]["part-numbers"]) == {part}


def test_the_default_is_ac_front_to_back():
    cfgs = load_device()["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name or '' for an empty bay, as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for view in ("front", "rear"):
        for b in bays(dev, view):
            ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
            out[b["id"]] = ref_name(ref) if ref else ""
    return out


@pytest.mark.parametrize("cid", sorted(VARIANTS))
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(cid):
    d = load_device()
    _part, psu, fan, airflow = VARIANTS[cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(5)} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    cfg_airflow = d["configurations"][cid].get("airflow", d["chassis"]["airflow"])
    assert cfg_airflow == airflow


def test_the_spare_chassis_ships_with_empty_power_and_fan_bays():
    """Table 3: -S has no supplies and no fan modules; both are ordered separately."""
    s = seated(load_device(), SPARE[0])
    assert all(s[b] == "" for b in ("psu-0", "psu-1", *[f"fan-{n}" for n in range(5)]))


def test_the_modules_are_not_shipped_so_the_bays_are_covered_by_default():
    """Figure 9: 'expansion module bays with cover panels'; the modules are ordered separately."""
    d = load_device()
    for cid in list(VARIANTS) + [SPARE[0]]:
        s = seated(d, cid)
        assert s["em-0"] == s["em-1"] == "ex4600-em-blnk"


@pytest.mark.parametrize("module", ["ex4600-em-8f", "ex4600-em-4q"])
def test_a_module_can_sit_in_either_bay_and_in_any_combination(module):
    d = load_device()
    for cid, cfg in d["configurations"].items():
        if cfg["kind"] == "example" and module in str(cfg.get("bays")):
            assert {ref_name(cfg["bays"]["em-0"]), ref_name(cfg["bays"]["em-1"])} == {module}
            break
    else:
        pytest.fail(f"no example configuration seats {module} in the bays")


def test_a_bay_accepts_the_units_the_guide_lists():
    d = load_device()
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        if b["id"].startswith("fan-"):
            assert got == FANS, b["id"]
        else:
            # the guide's blank cover panel for a slot with no supply is a fifth occupant
            assert got == SUPPLIES | {"ex4600-psu-blank"}, b["id"]
        assert ref_name(b["default"]) in got
    for b in bays(d, "front"):
        assert {ref_name(r) for r in b["accepts"]} == MODULES, b["id"]
        assert ref_name(b["default"]) == "ex4600-em-blnk"


def test_bays_reserve_one_size_for_each_unit_they_accept():
    d = load_device()
    for view in ("front", "rear"):
        for b in bays(d, view):
            for ref in b["accepts"]:
                c = load_component(ref_name(ref))["size"]
                assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), (b["id"], ref)
                assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), (b["id"], ref)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", sorted(PART_NUMBER))
def test_a_unit_is_ordered_under_its_juniper_part_number_and_prefixed_with_the_family(part):
    c = load_component(part)
    assert c["name"] == part
    assert c["kind"] == "module"
    assert [v["part"] for v in c["part-numbers"].values()] == [PART_NUMBER[part]]


@pytest.mark.parametrize("part", sorted(PART_NUMBER))
def test_a_unit_is_described_as_the_unit_and_names_the_switch_that_takes_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "field-replaceable" in text or "expansion module" in text.lower()
    assert "EX4600" in text


@pytest.mark.parametrize("part", sorted(SUPPLIES))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 650
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", sorted(FANS))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


def handle_finish(part):
    return load_component(part)["fields"]["handle-finish"]["default"].lower()


@pytest.mark.parametrize("front,back", [("ex4600-jpsu-650-ac-afo", "ex4600-jpsu-650-ac-afi"),
                                          ("ex4600-jpsu-650-dc-afo", "ex4600-jpsu-650-dc-afi"),
                                          ("ex4600-fan-afo", "ex4600-fan-afi")])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_an_orange_one(front, back):
    """Tables 11 and 14: orange with AIR OUT / AFO, blue with AIR IN / AFI."""
    f, b = handle_finish(front), handle_finish(back)
    fr, fg, fb = (int(f[i:i + 2], 16) for i in (1, 3, 5))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert fr > fb and fr > fg, "orange: red is the dominant channel"
    assert bb > br and bb > bg, "blue: blue is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"


@pytest.mark.parametrize("part,word", [("ex4600-fan-afo", "OUT"), ("ex4600-fan-afi", "IN"),
                                       ("ex4600-jpsu-650-ac-afo", "AFO"),
                                       ("ex4600-jpsu-650-ac-afi", "AFI")])
def test_a_unit_prints_its_airflow_label(part, word):
    """Fan modules carry AIR IN / AIR OUT (Table 11); the supplies carry AFI / AFO on the handle."""
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert f">{word}</text>" in svg


def test_the_dc_supply_has_four_terminals_and_three_lamps():
    """Figure 25: V-, V-, V+, V+ on two feeds, and the IN, OUT and ! lamps."""
    c = load_component("ex4600-jpsu-650-dc-afo")
    names = set(c["elements"])
    assert {"led-in", "led-out", "led-fault"} <= names
    terminals = [n for n, e in c["elements"].items() if n.startswith("term-") and e["class"] == "screw"]
    assert sorted(terminals) == ["term-neg-a", "term-neg-b", "term-pos-a", "term-pos-b"]


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("part", [v[0] for v in VARIANTS.values()] + [SPARE[1]])
def test_the_dcim_device_types_export_one_per_orderable_configuration(part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for ex4600-40f"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_ex4600_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("EX4600-*.yaml")}
    assert got == {v[0] for v in VARIANTS.values()} | {SPARE[1]}


@pytest.mark.parametrize("part", sorted(PART_NUMBER))
def test_each_unit_exports_a_module_type_carrying_its_juniper_part_number(part):
    found = []
    for target in ("netbox", "nautobot"):
        for f in (EXPORTS / target / "module-types" / "Juniper").glob("*.yaml"):
            doc = yaml.safe_load(f.read_text())
            if doc.get("part_number") == PART_NUMBER[part] and doc["model"].startswith(PART_NUMBER[part]) \
                    and doc["model"] in (PART_NUMBER[part], PART_NUMBER[part] + " (EX4600)"):
                found.append(f.name)
    assert len(found) == 2, found
