"""The Juniper QFX5210-64C, from the QFX5210 Switch Hardware Guide (2026-03-09).

One device for the one front panel the guide shows. The AC and DC, front-to-back and back-to-front
builds are configurations of it: the AIR OUT and AIR IN builds are `orderable` (the guide names their
part numbers in its cautions), the chassis spare is `orderable` (Table 3), and the two DC builds are
examples because the guide gives no part number for them. Each field-replaceable unit is a component.

What the guide fixes, and so what these tests hold:
  Table 26   the envelope - 3.5 x 17.25 x 22.83 in, 2RU
  Table 3    the units and their part numbers, the chassis spare QFX5210-64C-CHAS
  Table 15   the fan modules, their airflow and handle colour; Table 17 the same for the AC supplies
  Figures 9, 10, 11   the ports, their count and numbering; Figure 8 the FRU side
The photograph of the real device overrules the drawing on two printed legends, and a test holds each.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4
NAME = "qfx5210-64c"

# Table 26: height, width, depth in inches (2RU)
ENVELOPE_IN = {"h": 3.5, "w": 17.25, "d": 22.83}

# configuration -> (orderable part number or None, supply, fan module, airflow)
VARIANTS = {
    "ac-afo": ("QFX5210-64C-AFO", "qfx5210-jpsu-1100w-ac-afo", "qfx5210-fan-afo", "front-to-back"),
    "ac-afi": ("QFX5210-64C-AFI", "qfx5210-jpsu-1100w-ac-afi", "qfx5210-fan-afi", "back-to-front"),
    "dc-afo": (None, "qfx5210-jpsu-1100w-dc-afo", "qfx5210-fan-afo", "front-to-back"),
    "dc-afi": (None, "qfx5210-jpsu-1100w-dc-afi", "qfx5210-fan-afi", "back-to-front"),
}
CHASSIS_SPARE = ("chas", "QFX5210-64C-CHAS")
PSUS = {"qfx5210-jpsu-1100w-ac-afo", "qfx5210-jpsu-1100w-ac-afi",
        "qfx5210-jpsu-1100w-dc-afo", "qfx5210-jpsu-1100w-dc-afi"}
FANS = {"qfx5210-fan-afo", "qfx5210-fan-afi"}
PARTS = sorted(PSUS | FANS)


def device():
    return yaml.safe_load((DEV / NAME / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def placements(view):
    return (device()["views"][view].get("components") or {}).get("placements") or []


def bays(view):
    return (device()["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


# --- the envelope ------------------------------------------------------------

def test_the_envelope_is_table_26():
    ch = device()["chassis"]
    assert ch["ru"] == 2
    assert ch["height"] == pytest.approx(ENVELOPE_IN["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(ENVELOPE_IN["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(ENVELOPE_IN["d"] * INCH, abs=0.1)
    assert device()["manufacturer"] == "Juniper"
    assert device()["model"] == "QFX5210-64C"
    assert device()["portfolio"] == {"line": "QFX Series", "family": "QFX5210"}


def test_the_faces_are_sized_from_the_envelope():
    d = device()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_front_is_the_body_and_not_the_rack_face():
    """Table 26 gives 17.25 in; the brackets of the rack kit make it 19 in, so the body is drawn."""
    assert device()["views"]["front"]["size"]["w"] < 480


# --- the ports, per face -----------------------------------------------------

def cages(kind):
    return [p for p in placements("front") if ref_name(p["ref"]) == kind]


def test_64_qsfp28_cages_numbered_0_to_63_as_printed():
    q = cages("qsfp-ganged")
    assert sorted(int(p["id"].split("-")[1]) for p in q) == list(range(64))
    printed = {s["text"] for s in device()["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(64)} <= printed


def test_the_cages_are_sixteen_columns_of_four_in_eight_gangs():
    """Figure 10: ports 2k and 2k+1 over 32+2k and 33+2k, two columns to a gang."""
    at = {int(p["id"].split("-")[1]): p["at"] for p in cages("qsfp-ganged")}
    xs = sorted({round(a[0], 1) for a in at.values()})
    assert len(xs) == 16
    pitch = {round(b - a, 1) for a, b in zip(xs, xs[1:])}
    assert pitch == {19.0, 26.6}, "19.0 mm inside a gang, a 7.6 mm gutter between gangs"
    for k in range(16):
        x = at[2 * k][0]
        col = [at[2 * k], at[2 * k + 1], at[32 + 2 * k], at[33 + 2 * k]]
        assert all(abs(c[0] - x) < 0.01 for c in col)
        ys = [c[1] for c in col]
        assert ys == sorted(ys), "top to bottom: 2k, 2k+1, 32+2k, 33+2k"
    assert max(p["at"][0] + 18.5 for p in cages("qsfp-ganged")) < 392


def test_each_stack_turns_its_lower_cage_to_face_the_band_between_them():
    for p in cages("qsfp-ganged") + cages("sfp-ganged"):
        n = p["id"].split("-")[-1]
        lower_of_stack = (p["id"].startswith("port-") and int(n) % 2 == 1) or p["id"] == "tengig-1"
        assert p.get("rotate", 0) == (180 if lower_of_stack else 0), p["id"]


def test_two_sfp_plus_cages_printed_0_and_1_not_the_drawings_64_and_65():
    """The guide's figures print 64 and 65; the studio photograph of the real device prints 0 and 1."""
    s = cages("sfp-ganged")
    assert sorted(p["id"] for p in s) == ["tengig-0", "tengig-1"]
    assert s[0]["at"][1] < s[1]["at"][1]
    for p in s:
        assert p["at"][0] > max(q["at"][0] for q in cages("qsfp-ganged"))
    sil = {x["text"]: x for x in device()["views"]["front"]["silkscreen"] if x.get("for", "").startswith("tengig")}
    assert set(sil) == {"0", "1"}


def test_the_groups_say_what_the_ports_are():
    g = device()["groups"]
    assert g["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["qsfp28"]["role"] == g["sfp-plus"]["role"] == "traffic"
    assert g["qsfp28"]["index-origin"] == 0


def test_the_front_has_the_management_jacks_usb_reset_and_four_chassis_lamps():
    by_id = {p["id"]: p for p in placements("front")}
    assert ref_name(by_id["mgmt-eth"]["ref"]) == "rj45-eth"
    assert by_id["mgmt-eth"]["attrs"]["speed"] == "1g"
    assert ref_name(by_id["console"]["ref"]) == "rj45"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert by_id["mgmt-eth"]["at"][1] < by_id["console"]["at"][1], "MGMT is the upper jack, CON the lower"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a" and by_id["usb"]["skin"] == "usb2"
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "esd-front-jack"} <= set(by_id)
    legends = {s["text"] for s in device()["views"]["front"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON", "RESET", "ALM", "SYS", "MST", "ID", "QFX5210-64C"} <= legends


def test_four_round_lamps_over_each_outer_column_edge():
    """Table 10 and Figure 9: four lamps a column, above ports 0 to 30 (even) and below ports 33 to 63 (odd)."""
    lamps = {p["id"]: p for p in placements("front") if ref_name(p["ref"]) == "qfx5210-lane-leds"}
    want = {f"led-port-{n}" for n in list(range(0, 32, 2)) + list(range(33, 64, 2))}
    assert set(lamps) == want
    for lid, p in lamps.items():
        assert p["for"] == "port-" + lid.split("-")[-1]
    assert len(load_component("qfx5210-lane-leds")["elements"]) == 4


def test_the_makers_logos_are_reserved_and_not_drawn():
    d = device()
    for view in ("front", "rear"):
        assert any(r["id"].startswith("logo-zone") for r in d["views"][view].get("regions") or [])
        text = " ".join(s.get("text", "") for s in d["views"][view]["silkscreen"]).upper()
        assert "JUNIPER" not in text and "JUNOS" not in text and "NETWORKS" not in text


def test_the_rear_has_four_fan_slots_two_supply_slots_and_the_earthing_terminal():
    b = {x["id"]: x for x in bays("rear")}
    assert sorted(i for i in b if i.startswith("fan-")) == [f"fan-{n}" for n in range(4)]
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    xs = [b[f"fan-{n}"]["at"][0] for n in range(4)]
    assert xs == sorted(xs) and b["psu-0"]["at"][0] < xs[0] and b["psu-1"]["at"][0] > xs[-1]
    by_id = {p["id"]: p for p in placements("rear")}
    assert ref_name(by_id["ground-plate"]["ref"]) == "qfx5210-ground-plate"


def test_the_supply_legend_is_the_photographs_and_not_the_drawings():
    """Figure 8 prints 12-6A and 25A; the photograph of the device prints 12-7A and 34A."""
    text = " ".join(s.get("text", "") for s in device()["views"]["rear"]["silkscreen"])
    assert "12-7A" in text and "34A Max" in text
    assert "12-6A" not in text and "25A" not in text


# --- the configurations ------------------------------------------------------

def test_the_orderable_configurations_carry_the_guides_part_numbers():
    cfgs = device()["configurations"]
    assert set(cfgs) == set(VARIANTS) | {CHASSIS_SPARE[0]}
    for cid, (part, *_rest) in VARIANTS.items():
        if part:
            assert cfgs[cid]["kind"] == "orderable"
            assert set(cfgs[cid]["part-numbers"]) == {part}
        else:
            assert cfgs[cid]["kind"] == "example" and "part-numbers" not in cfgs[cid]
    spare = cfgs[CHASSIS_SPARE[0]]
    assert spare["kind"] == "orderable" and set(spare["part-numbers"]) == {CHASSIS_SPARE[1]}


def test_the_default_is_ac_front_to_back():
    defaults = [c for c, v in device()["configurations"].items() if v.get("default")]
    assert defaults == ["ac-afo"]


def seated(dev, cid):
    cfg = dev["configurations"][cid]
    out = {}
    for b in dev["views"]["rear"]["components"]["bays"]:
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref) if ref else None
    return out


@pytest.mark.parametrize("cid", sorted(VARIANTS))
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(cid):
    d = device()
    _part, psu, fan, airflow = VARIANTS[cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(4)} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    cfg_airflow = d["configurations"][cid].get("airflow", d["chassis"]["airflow"])
    assert cfg_airflow == airflow
    power = d["configurations"][cid].get("power", d["chassis"]["power"])
    assert power == ("dc" if "dc" in cid else "ac")


def test_the_chassis_spare_leaves_every_bay_open():
    assert set(seated(device(), "chas").values()) == {None}


def test_a_bay_accepts_the_modules_the_guide_lists():
    for b in bays("rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = FANS if b["id"].startswith("fan-") else PSUS
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got


def test_bays_reserve_one_size_for_each_module_they_accept():
    for b in bays("rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", PARTS)
def test_a_unit_is_a_module_whose_model_is_the_guides_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    assert "field-replaceable" in " ".join(c["description"].split())
    if "jpsu" in part:
        assert c["attrs"]["model"] == part.replace("qfx5210-", "").upper()
    else:
        assert c["attrs"]["model"] == "QFX5210-64C-FAN" + part[-3:].upper()


@pytest.mark.parametrize("part", sorted(PSUS))
def test_a_supply_states_the_1100_w_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 1100
    assert not any(k.startswith("power-draw") for k in attrs)
    assert attrs["role"] == ("dc-power-supply" if "-dc-" in part else "ac-power-supply")


@pytest.mark.parametrize("part", sorted(FANS))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [("qfx5210-jpsu-1100w-ac-afo", "qfx5210-jpsu-1100w-ac-afi"),
                                          ("qfx5210-jpsu-1100w-dc-afo", "qfx5210-jpsu-1100w-dc-afi"),
                                          ("qfx5210-fan-afo", "qfx5210-fan-afi")])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_a_gold_one(front, back):
    """Tables 15 and 17: AIR OUT with a Juniper Gold handle (orange in the photograph), AIR IN azure blue."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"


def test_the_fan_modules_print_their_direction_on_the_chip():
    for part, word in (("qfx5210-fan-afo", "AIR OUT"), ("qfx5210-fan-afi", "AIR IN")):
        svg = (COMP / part / "v1/skins/default.svg").read_text()
        assert f">{word}</text>" in svg


# --- the DCIM export ---------------------------------------------------------

EXPORTED = ["QFX5210-64C-AFO", "QFX5210-64C-AFI", "QFX5210-64C-CHAS"]


@pytest.mark.parametrize("part", EXPORTED)
def test_the_dcim_device_types_export_one_per_orderable_configuration_at_2u(part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {NAME}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 2.0


def test_no_other_juniper_qfx5210_export_exists():
    for target in ("netbox", "nautobot"):
        got = {p.stem for p in (EXPORTS / target / "device-types/Juniper").glob("QFX5210-*.yaml")}
        assert got == set(EXPORTED)
