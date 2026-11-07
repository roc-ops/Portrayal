"""The Juniper QFX5130-48C and QFX5130-48CM, from the QFX5130 Switch Hardware Guide (2026-10-14).

One device per front panel. The guide draws the 48C and the 48CM with the same front panel (figures 16
and 18: 48 SFP56-DD ports in three groups of eight columns, and 8 QSFP-DD uplinks) and the same rear
(figures 17 and 19), so the 48CM (MACsec capable) is a set of `orderable` configurations of
`juniper/qfx5130-48c`, and so are its power, airflow and spare-chassis variants. The supplies are the
ones the QFX5130-32CD already seats (the guide's Table 4 names the same JPSU-1600W part numbers); the
fan modules are the 48C's own.

What the guide fixes, and so what these tests hold:
  Table 31   the envelope - 1.72 x 17.28 x 20.5 in, 1RU
  Table 4, Table 17   the part numbers of the supplies and fan modules and the airflow of each
  datasheet ordering table   the part numbers of the orderable variants
  figures 16 to 19, 21, 29   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4
NAME = "qfx5130-48c"

# Table 31: height, width, depth in inches
ENVELOPE_IN = (1.72, 17.28, 20.5)

PSU = {
    ("ac", "front-to-back"): "qfx5130-jpsu-1600-ac-afo",
    ("ac", "back-to-front"): "qfx5130-jpsu-1600-ac-afi",
    ("dc", "front-to-back"): "qfx5130-jpsu-1600-dc-afo",
    ("dc", "back-to-front"): "qfx5130-jpsu-1600-dc-afi",
}
FAN = {"front-to-back": "qfx5130-48c-fan-afo", "back-to-front": "qfx5130-48c-fan-afi"}
FAN_PARTS = {"qfx5130-48c-fan-afo": "QFX5130-48C-FANAO", "qfx5130-48c-fan-afi": "QFX5130-48C-FANAI"}

# datasheet ordering table: (power, airflow, suffix of the part number)
SUFFIX = {("ac", "front-to-back"): "AFO", ("ac", "back-to-front"): "AFI",
          ("dc", "front-to-back"): "D-AFO", ("dc", "back-to-front"): "D-AFI"}
# configuration id -> (power, airflow, part number)
VARIANTS = {}
for _model, _prefix in (("QFX5130-48C", ""), ("QFX5130-48CM", "cm-")):
    for (_p, _a), _s in SUFFIX.items():
        _cid = f"{_prefix}{_p}-{'f2b' if _a == 'front-to-back' else 'b2f'}"
        VARIANTS[_cid] = (_p, _a, f"{_model}-{_s}")
SPARES = {"chas": "QFX5130-48C-CHAS", "cm-chas": "QFX5130-48CM-CHAS"}
ALL_PARTS = [v[2] for v in VARIANTS.values()] + list(SPARES.values())


def load_device():
    return yaml.safe_load((DEV / NAME / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def numbered(dev, view, ref):
    """The port number of every placement of one cage, from its id."""
    return sorted(int(p["id"].split("-")[1]) for p in placements(dev, view)
                  if ref_name(p["ref"]) == ref and p["id"].startswith("port-"))


# --- one device per front panel ----------------------------------------------

def test_the_48cm_is_a_configuration_of_the_48c_and_not_a_second_device():
    assert (DEV / NAME / "device.yaml").exists()
    assert not (DEV / "qfx5130-48cm").exists()


# --- the envelope ------------------------------------------------------------

def test_the_envelope_is_table_31():
    h, w, d = ENVELOPE_IN
    ch = load_device()["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(h * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(w * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(d * INCH, abs=0.1)


def test_the_faces_are_sized_from_the_envelope():
    d = load_device()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_manufacturer_model_and_family_are_as_the_guide_names_them():
    d = load_device()
    assert d["manufacturer"] == "Juniper" and d["model"] == "QFX5130-48C"
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5130"}


# --- the ports, per face -----------------------------------------------------

def test_48_sfp_dd_cages_and_8_qsfp_dd_uplinks_on_the_front():
    d = load_device()
    assert numbered(d, "front", "sfp-dd-ganged") == list(range(0, 48))
    assert numbered(d, "front", "qsfp-dd") == list(range(48, 56))


def test_two_sfp_plus_cages_sit_on_the_rear_with_the_management_panel_and_none_on_the_front():
    d = load_device()
    assert numbered(d, "rear", "sfp") == [56, 57]
    assert not [p for p in placements(d, "front") if ref_name(p["ref"]) == "sfp"]
    assert not [p for p in placements(d, "rear") if ref_name(p["ref"]) in ("sfp-dd", "sfp-dd-ganged", "qsfp-dd")]


def test_the_groups_say_what_the_ports_are():
    g = load_device()["groups"]
    assert g["sfp-dd-100g"]["attrs"] == {"media": "sfp-dd", "speed": "100g"}
    assert g["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert {g[k]["role"] for k in ("sfp-dd-100g", "qsfpdd-400g", "sfp-plus")} == {"traffic"}


def test_ports_are_numbered_from_0_as_printed_and_the_numerals_are_on_the_faces():
    d = load_device()
    front = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(56)} <= front
    rear = {s["text"] for s in d["views"]["rear"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {"56", "57"} <= rear


def test_two_rows_with_even_ports_above_odd():
    d = load_device()
    y = {int(p["id"].split("-")[1]): p["at"][1] for p in placements(d, "front")
         if ref_name(p["ref"]) in ("sfp-dd-ganged", "qsfp-dd") and p["id"].startswith("port-")}
    assert all(y[n] < y[n + 1] for n in range(0, 56, 2))


def test_the_sfp_dd_cages_stand_in_three_groups_of_eight_columns_on_the_ganged_pitch():
    d = load_device()
    xs = sorted({p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "sfp-dd-ganged"})
    assert len(xs) == 24
    gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert gaps[0:7] == [14.25] * 7 and gaps[8:15] == [14.25] * 7 and gaps[16:] == [14.25] * 7
    assert gaps[7] == gaps[15] and gaps[7] > 14.25, "a gutter between groups"
    up = sorted({p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-dd"})
    assert [round(b - a, 2) for a, b in zip(up, up[1:])] == [19.0] * 3
    assert up[0] > xs[-1], "the uplinks are at the right of the last group"


def test_the_lower_row_is_the_upper_turned_over():
    by_id = {p["id"]: p for p in placements(load_device(), "front")}
    for n in range(0, 48, 2):
        assert by_id[f"port-{n}"].get("rotate", 0) == 0
        assert by_id[f"port-{n + 1}"]["rotate"] == 180


def test_the_lamps_follow_the_guide():
    """One bicolour lamp for every network port (Table 10, Table 11)."""
    d = load_device()
    front = {p["id"] for p in placements(d, "front") if ref_name(p["ref"]) == "led-dot"}
    assert {f"led-port-{n}" for n in range(56)} <= front
    rear = {p["id"] for p in placements(d, "rear") if ref_name(p["ref"]) == "led-dot"}
    assert {"led-port-56", "led-port-57", "led-alm", "led-sys", "led-id"} <= rear


def test_the_management_cluster_is_on_the_rear_with_mgmt_above_the_console():
    by_id = {p["id"]: p for p in placements(load_device(), "rear")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-ganged-eth"
    assert by_id["mgmt"]["at"][1] < by_id["console"]["at"][1], "MGMT is the upper jack, CON the lower"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"out-10m", "out-pps", "reset-btn", "esd-rear-jack"} <= set(by_id)
    assert ref_name(by_id["out-10m"]["ref"]) == "sma"


def test_no_logo_is_drawn_and_a_zone_is_reserved():
    d = load_device()
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    zones = [r["id"] for v in ("front", "rear") for r in d["views"][v].get("regions") or []]
    assert "logo-zone" in zones


def test_six_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them():
    """Fan modules 0 to 5 from the left, with the supplies at the right end (Cooling System)."""
    b = {x["id"]: x for x in bays(load_device(), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(6)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] > b["fan-5"]["at"][0] and b["psu-1"]["at"][0] > b["psu-0"]["at"][0]


# --- the configurations ------------------------------------------------------

def test_each_variant_is_an_orderable_configuration_with_its_part_number():
    cfgs = load_device()["configurations"]
    assert set(cfgs) == set(VARIANTS) | set(SPARES)
    for cid, (_p, _a, part) in VARIANTS.items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}
    for cid, part in SPARES.items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}


def test_the_default_is_the_48c_ac_front_to_back():
    cfgs = load_device()["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name (or None when empty), as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for b in bays(dev, "rear"):
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref) if ref else None
    return out


@pytest.mark.parametrize("cid", sorted(VARIANTS))
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(cid):
    d = load_device()
    power, airflow, _part = VARIANTS[cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {PSU[(power, airflow)]}
    assert {s[f"fan-{n}"] for n in range(6)} == {FAN[airflow]}
    for comp in (PSU[(power, airflow)], FAN[airflow]):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    cfg_airflow = d["configurations"][cid].get("airflow", d["chassis"]["airflow"])
    assert cfg_airflow == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == power


@pytest.mark.parametrize("cid", sorted(SPARES))
def test_the_spare_chassis_shows_every_bay_open(cid):
    s = seated(load_device(), cid)
    assert set(s.values()) == {None} and len(s) == 8


def test_the_supplies_are_the_ones_the_32cd_already_seats():
    """Table 4 names the same JPSU-1600W part numbers, so they are reused and none is added."""
    for comp in PSU.values():
        assert load_component(comp)["attrs"]["model"].startswith("JPSU-1600W-1U")
        assert not (COMP / comp.replace("qfx5130-", "qfx5130-48c-")).exists()


def test_a_bay_accepts_the_modules_the_guide_lists():
    d = load_device()
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == (set(FAN.values()) if b["id"].startswith("fan-") else set(PSU.values())), b["id"]
        assert ref_name(b["default"]) in got


def test_bays_reserve_one_size_for_each_module_they_accept():
    for b in bays(load_device(), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_is_named_for_the_family_and_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    assert c["attrs"]["model"] == FAN_PARTS[part]
    assert "part-numbers" not in c, "a contract states attrs.model or part-numbers, never both"
    text = " ".join(c["description"].split())
    assert "field-replaceable" in text and "QFX5130-48C" in text and "QFX5130-48CM" in text


@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_carries_its_own_status_lamp_and_says_its_power_is_not_published(part):
    """Guide, QFX5130 Fan Module LED: on the 48C the lamp is on the module, not on the chassis."""
    c = load_component(part)
    assert c["attrs"]["power-absent"] == "not-published"
    assert c["elements"]["led"]["class"] == "led"
    assert "led-fan-0" not in {p["id"] for p in placements(load_device(), "rear")}


def test_the_supplies_name_the_48c_and_48cm_among_the_chassis_that_take_them():
    for comp in PSU.values():
        assert "QFX5130-48C" in " ".join(load_component(comp)["description"].split())


def test_the_back_to_front_fan_has_a_blue_handle_and_the_front_to_back_a_gold_one():
    """Table 17: AIR OUT with a Juniper gold handle, AIR IN with a Juniper azure blue handle."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(FAN["front-to-back"]), handle(FAN["back-to-front"])
    assert f != b and f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component(FAN["front-to-back"])["attrs"]["airflow"] == "front-to-back"
    assert load_component(FAN["back-to-front"])["attrs"]["airflow"] == "back-to-front"
    for part, word in ((FAN["front-to-back"], "OUT"), (FAN["back-to-front"], "IN")):
        svg = (COMP / part / "v1/skins/default.svg").read_text()
        assert f">{word}</text>" in svg and ">AIR</text>" in svg


# --- the DCIM export ---------------------------------------------------------

def test_the_dcim_device_types_export_one_per_orderable_configuration():
    for part in ALL_PARTS:
        for target in ("netbox", "nautobot"):
            f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f} is missing - run dcim_export.py for {NAME}"
            doc = yaml.safe_load(f.read_text())
            assert doc["manufacturer"] == "Juniper"
            assert doc["model"] == part
            assert doc["u_height"] == 1.0


def test_the_fan_module_types_are_exported():
    for part in FAN_PARTS.values():
        assert (EXPORTS / "netbox/module-types/Juniper" / f"{part}.yaml").exists()
