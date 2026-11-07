"""The Juniper QFX5130-32CD, from the QFX5130 Switch Hardware Guide (2026-10-14).

One device per front panel. The 32CD's power, airflow and spare-chassis variants are `orderable`
configurations of the one device, because the guide shows one panel for all of them. Each
field-replaceable unit is a component named for the family and its Juniper part number.

The QFX5130-48C and QFX5130-48CM are not here: they are `juniper/qfx5130-48c`, held by
test_juniper_qfx5130_48c.py.

What the guide fixes, and so what these tests hold:
  Table 31   the envelope - 1.72 x 17.26 x 21.1 in, 1RU
  Tables 3, 17, 24   the part numbers of the supplies and fan modules and the airflow of each
  datasheet ordering tables   the part numbers of the orderable variants
  figures 14, 15, 20 to 28   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4
NAME = "qfx5130-32cd"

# Table 31: height, width, depth in inches
ENVELOPE_IN = (1.72, 17.26, 21.1)

PSU = {
    ("ac", "front-to-back"): "qfx5130-jpsu-1600-ac-afo",
    ("ac", "back-to-front"): "qfx5130-jpsu-1600-ac-afi",
    ("dc", "front-to-back"): "qfx5130-jpsu-1600-dc-afo",
    ("dc", "back-to-front"): "qfx5130-jpsu-1600-dc-afi",
}
FAN = {"front-to-back": "qfx5130-32cd-fan-afo", "back-to-front": "qfx5130-32cd-fan-afi"}

# datasheet ordering table: configuration -> (power, airflow, part number)
VARIANTS = {
    "ac-f2b": ("ac", "front-to-back", "QFX5130-32CD-AFO"),
    "ac-b2f": ("ac", "back-to-front", "QFX5130-32CD-AFI"),
    "dc-f2b": ("dc", "front-to-back", "QFX5130-32CD-D-AFO"),
    "dc-b2f": ("dc", "back-to-front", "QFX5130-32CD-D-AFI"),
}
CHAS = "QFX5130-32CD-CHAS"

PSU_PARTS = {"qfx5130-jpsu-1600-ac-afo": "JPSU-1600W-1UACAFO", "qfx5130-jpsu-1600-ac-afi": "JPSU-1600W-1UACAFI",
             "qfx5130-jpsu-1600-dc-afo": "JPSU-1600W-1UDCAFO", "qfx5130-jpsu-1600-dc-afi": "JPSU-1600W-1UDCAFI"}
FAN_PARTS = {"qfx5130-32cd-fan-afo": "QFX5220-32CD-FANAO", "qfx5130-32cd-fan-afi": "QFX5220-32CD-FANAI"}
ALL_UNITS = sorted(list(PSU_PARTS) + list(FAN_PARTS))


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


def test_the_front_is_the_body_and_not_the_rack_face():
    assert load_device()["views"]["front"]["size"]["w"] < 480


# --- the ports, per face -----------------------------------------------------

def test_32_qsfp_dd_cages_and_two_sfp_plus_on_the_front_and_none_on_the_rear():
    d = load_device()
    assert numbered(d, "front", "qsfp-dd") == list(range(0, 32))
    assert numbered(d, "front", "sfp") == [32, 33]
    assert not [p for p in placements(d, "rear") if ref_name(p["ref"]) in ("qsfp-dd", "sfp", "sfp-ganged")]


def test_the_groups_say_what_the_ports_are():
    g = load_device()["groups"]
    assert g["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["qsfpdd-400g"]["role"] == g["sfp-plus"]["role"] == "traffic"


def test_ports_are_numbered_from_0_as_printed_and_the_numerals_are_on_the_face():
    printed = {s["text"] for s in load_device()["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(34)} <= printed


def test_two_rows_with_even_ports_above_odd():
    d = load_device()
    y = {int(p["id"].split("-")[1]): p["at"][1] for p in placements(d, "front")
         if ref_name(p["ref"]) in ("qsfp-dd", "sfp") and p["id"].startswith("port-")}
    assert all(y[n] < y[n + 1] for n in range(0, 34, 2))


def test_the_cages_stand_in_eight_pairs_of_columns():
    d = load_device()
    xs = sorted({p["at"][0] for p in placements(d, "front")
                 if ref_name(p["ref"]) == "qsfp-dd" and p["id"].startswith("port-")})
    assert len(xs) == 16
    gaps = [round(b - a, 1) for a, b in zip(xs, xs[1:])]
    assert gaps[0::2] == [19.0] * 8 and set(gaps[1::2]) == {gaps[1]} and gaps[1] > 19.0
    sfp = min(p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "sfp")
    assert sfp > xs[-1], "the SFP+ pair is at the right of the last pair of columns"


def test_the_lamps_follow_the_guide():
    """One bicolour lamp a QSFP-DD port (Table 8); two lamps an SFP+ port (Table 9)."""
    ids = {p["id"] for p in placements(load_device(), "front") if ref_name(p["ref"]) == "led-dot"}
    assert {f"led-port-{n}" for n in range(32)} <= ids
    for n in (32, 33):
        assert {f"led-port-{n}-link", f"led-port-{n}-status"} <= ids


def test_the_management_cluster_is_on_the_front():
    by_id = {p["id"]: p for p in placements(load_device(), "front")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-ganged-eth"
    assert by_id["console"]["at"][1] < by_id["mgmt"]["at"][1], "CON is the upper jack, MGMT the lower"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"out-10m", "out-pps", "reset-btn", "esd-front-jack", "led-alm", "led-sys", "led-id"} <= set(by_id)
    assert ref_name(by_id["out-10m"]["ref"]) == "sma"


def test_no_logo_is_drawn_and_a_zone_is_reserved():
    d = load_device()
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    zones = [r["id"] for v in ("front", "rear") for r in d["views"][v].get("regions") or []]
    assert "logo-zone" in zones


def test_six_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them():
    """Fan modules 0 to 5, left to right, with a supply at each end (Cooling System, Power System)."""
    b = {x["id"]: x for x in bays(load_device(), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(6)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0] and b["psu-1"]["at"][0] > b["fan-5"]["at"][0]


# --- the configurations ------------------------------------------------------

def test_each_variant_is_an_orderable_configuration_with_its_part_number():
    cfgs = load_device()["configurations"]
    assert set(cfgs) == set(VARIANTS) | {"chas"}
    for cid, (_p, _a, part) in VARIANTS.items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}
    assert cfgs["chas"]["kind"] == "orderable"
    assert set(cfgs["chas"]["part-numbers"]) == {CHAS}


def test_the_default_is_ac_front_to_back():
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


def test_the_spare_chassis_shows_every_bay_open():
    s = seated(load_device(), "chas")
    assert set(s.values()) == {None} and len(s) == 8


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

@pytest.mark.parametrize("part", ALL_UNITS)
def test_a_unit_is_named_for_the_family_and_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    assert c["attrs"]["model"] == (PSU_PARTS.get(part) or FAN_PARTS[part])
    assert "part-numbers" not in c, "a contract states attrs.model or part-numbers, never both"


@pytest.mark.parametrize("part", ALL_UNITS)
def test_a_unit_is_described_as_the_unit_and_names_the_model_that_takes_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "field-replaceable" in text
    assert "QFX5130-32CD" in text


@pytest.mark.parametrize("part", sorted(PSU_PARTS))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 1600
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [("qfx5130-jpsu-1600-ac-afo", "qfx5130-jpsu-1600-ac-afi"),
                                          ("qfx5130-jpsu-1600-dc-afo", "qfx5130-jpsu-1600-dc-afi"),
                                          ("qfx5130-32cd-fan-afo", "qfx5130-32cd-fan-afi")])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_a_gold_one(front, back):
    """Tables 17, 24: AIR OUT with a Juniper gold handle, AIR IN with a Juniper azure blue handle."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f != b and f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"
    if "fan" in front:
        for part, word in ((front, "OUT"), (back, "IN")):
            svg = (COMP / part / "v1/skins/default.svg").read_text()
            assert f">{word}</text>" in svg and ">AIR</text>" in svg


# --- the DCIM export ---------------------------------------------------------

def test_the_dcim_device_types_export_one_per_orderable_configuration():
    parts = [v[2] for v in VARIANTS.values()] + [CHAS]
    for part in parts:
        for target in ("netbox", "nautobot"):
            f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f} is missing - run dcim_export.py for {NAME}"
            doc = yaml.safe_load(f.read_text())
            assert doc["manufacturer"] == "Juniper"
            assert doc["model"] == part
            assert doc["u_height"] == 1.0


def test_no_other_qfx5130_32cd_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5130*32CD*.yaml")}
    assert got == {v[2] for v in VARIANTS.values()} | {CHAS}
