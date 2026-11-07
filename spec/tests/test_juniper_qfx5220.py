"""The Juniper QFX5220-32CD and QFX5220-128C, from the QFX5220 Switch Hardware Guide (2026-10-14).

One device per front panel. Each model's power, airflow and spare-chassis variants are `orderable`
configurations of the one device, because the guide shows one panel for all of them. Each
field-replaceable unit is a component. The 32CD seats the supplies and fan modules the QFX5130-32CD
already carries, because the part numbers are the same. The 128C seats the QFX10002's JPSU-1600W
supplies, which carry the same part numbers, and a fan module of its own.

What the guide fixes, and so what these tests hold:
  Table 32   the envelope - 1.72 x 17.26 x 21.1 in for the 32CD, 6.88 x 17.32 x 29.25 in for the 128C
  Tables 3, 16, 18, 25   the part numbers of the supplies and fan modules and the airflow of each
  Juniper's Hardware Compatibility Tool   the part numbers of the orderable variants
  figures 12 to 15, 17, 21, 22, 32, 33   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 32: height, width, depth in inches, and the rack units the figure shows
ENVELOPE_IN = {
    "qfx5220-32cd": (1.72, 17.26, 21.1),
    "qfx5220-128c": (6.88, 17.32, 29.25),
}
RU = {"qfx5220-32cd": 1, "qfx5220-128c": 4}

# configuration -> (power, airflow, part number); the 128C is not sold with back-to-front airflow (Table 3)
VARIANTS = {
    "qfx5220-32cd": {
        "ac-f2b": ("ac", "front-to-back", "QFX5220-32CD-AFO"),
        "ac-b2f": ("ac", "back-to-front", "QFX5220-32CD-AFI"),
        "dc-f2b": ("dc", "front-to-back", "QFX5220-32CD-D-AFO"),
        "dc-b2f": ("dc", "back-to-front", "QFX5220-32CD-D-AFI"),
    },
    "qfx5220-128c": {
        "ac-f2b": ("ac", "front-to-back", "QFX5220-128C-AFO"),
        "dc-f2b": ("dc", "front-to-back", "QFX5220-128C-D-AFO"),
    },
}
CHAS = {"qfx5220-32cd": "QFX5220-32CD-CHAS", "qfx5220-128c": "QFX5220-128C-CHAS"}

PSU = {
    "qfx5220-32cd": {
        ("ac", "front-to-back"): "qfx5130-jpsu-1600-ac-afo",
        ("ac", "back-to-front"): "qfx5130-jpsu-1600-ac-afi",
        ("dc", "front-to-back"): "qfx5130-jpsu-1600-dc-afo",
        ("dc", "back-to-front"): "qfx5130-jpsu-1600-dc-afi",
    },
    "qfx5220-128c": {
        ("ac", "front-to-back"): "qfx10002-jpsu-1600w-ac-afo",
        ("dc", "front-to-back"): "qfx10002-jpsu-1600w-dc-afo",
    },
}
FAN = {
    "qfx5220-32cd": {"front-to-back": "qfx5130-32cd-fan-afo", "back-to-front": "qfx5130-32cd-fan-afi"},
    "qfx5220-128c": {"front-to-back": "qfx5220-128c-fan-afo"},
}
FAN_BAYS = {"qfx5220-32cd": 6, "qfx5220-128c": 6}
PSU_BAYS = {"qfx5220-32cd": 2, "qfx5220-128c": 4}

# the part numbers the guide prints for each unit (Tables 3, 16, 18 and 25)
PSU_PARTS = {"qfx5130-jpsu-1600-ac-afo": "JPSU-1600W-1UACAFO", "qfx5130-jpsu-1600-ac-afi": "JPSU-1600W-1UACAFI",
             "qfx5130-jpsu-1600-dc-afo": "JPSU-1600W-1UDCAFO", "qfx5130-jpsu-1600-dc-afi": "JPSU-1600W-1UDCAFI",
             "qfx10002-jpsu-1600w-ac-afo": "JPSU-1600W-AC-AFO", "qfx10002-jpsu-1600w-dc-afo": "JPSU-1600W-DC-AFO"}
FAN_PARTS = {"qfx5130-32cd-fan-afo": "QFX5220-32CD-FANAO", "qfx5130-32cd-fan-afi": "QFX5220-32CD-FANAI",
             "qfx5220-128c-fan-afo": "QFX5220-128C-FANAO"}

DEVICES = sorted(ENVELOPE_IN)
ALL_VARIANTS = [(d, c) for d in DEVICES for c in sorted(VARIANTS[d])]


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


def numbered(dev, view, ref):
    """The port number of every placement of one cage, from its id."""
    return sorted(int(p["id"].split("-")[1]) for p in placements(dev, view)
                  if ref_name(p["ref"]) == ref and p["id"].startswith("port-"))


def seated(dev, cid):
    """bay id -> component name (or None when empty), as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for b in bays(dev, "rear"):
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref) if ref else None
    return out


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_32(name):
    h, w, d = ENVELOPE_IN[name]
    ch = load_device(name)["chassis"]
    assert ch["ru"] == RU[name]
    assert ch["height"] == pytest.approx(h * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(w * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(d * INCH, abs=0.1)


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
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


def test_each_front_panel_is_a_device_of_its_own():
    assert {p.name for p in DEV.glob("qfx5220-*")} == set(DEVICES)


# --- the ports of the 32CD, per face ----------------------------------------

def test_32cd_has_32_qsfp_dd_cages_and_two_sfp_plus_on_the_front_and_none_on_the_rear():
    d = load_device("qfx5220-32cd")
    assert numbered(d, "front", "qsfp-dd") == list(range(0, 32))
    assert numbered(d, "front", "sfp") == [32, 33]
    assert not [p for p in placements(d, "rear") if ref_name(p["ref"]) in ("qsfp-dd", "sfp", "sfp-ganged")]


def test_32cd_groups_say_what_the_ports_are():
    g = load_device("qfx5220-32cd")["groups"]
    assert g["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["qsfpdd-400g"]["role"] == g["sfp-plus"]["role"] == "traffic"


def test_32cd_ports_are_numbered_from_0_as_printed_and_the_numerals_are_on_the_face():
    printed = {s["text"] for s in load_device("qfx5220-32cd")["views"]["front"]["silkscreen"]
               if s.get("text", "").isdigit()}
    assert {str(n) for n in range(34)} <= printed


def test_32cd_has_two_rows_with_even_ports_above_odd():
    d = load_device("qfx5220-32cd")
    y = {int(p["id"].split("-")[1]): p["at"][1] for p in placements(d, "front")
         if ref_name(p["ref"]) in ("qsfp-dd", "sfp") and p["id"].startswith("port-")}
    assert all(y[n] < y[n + 1] for n in range(0, 34, 2))


def test_32cd_cages_stand_in_eight_pairs_of_columns_and_the_sfp_plus_pair_is_at_the_right():
    d = load_device("qfx5220-32cd")
    xs = sorted({p["at"][0] for p in placements(d, "front")
                 if ref_name(p["ref"]) == "qsfp-dd" and p["id"].startswith("port-")})
    assert len(xs) == 16
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert gaps[0::2] == pytest.approx([19.0] * 8, abs=0.02)
    assert gaps[1::2] == pytest.approx([gaps[1]] * 7, abs=0.02) and gaps[1] > 19.5
    sfp = min(p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "sfp")
    assert sfp > xs[-1]


def test_32cd_lamps_follow_the_guide():
    """One bicolour lamp a QSFP-DD port (Table 6); two lamps an SFP+ port (Table 7)."""
    ids = {p["id"] for p in placements(load_device("qfx5220-32cd"), "front") if ref_name(p["ref"]) == "led-dot"}
    assert {f"led-port-{n}" for n in range(32)} <= ids
    for n in (32, 33):
        assert {f"led-port-{n}-link", f"led-port-{n}-status"} <= ids


def test_32cd_management_and_timing_parts_are_on_the_front():
    by_id = {p["id"]: p for p in placements(load_device("qfx5220-32cd"), "front")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-ganged-eth"
    assert by_id["console"]["at"][1] < by_id["mgmt"]["at"][1], "CON is the upper jack, MGMT the lower"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert ref_name(by_id["tod"]["ref"]) == "rj45" and by_id["tod"]["attrs"]["media"] == "rj45-tod"
    clocks = sorted(i for i in by_id if i.startswith("clk-"))
    assert clocks == ["clk-10m-in", "clk-10m-out", "clk-pps-in", "clk-pps-out"]
    assert {ref_name(by_id[i]["ref"]) for i in clocks} == {"sma"}
    assert {"reset-btn", "esd-front-jack", "led-alm", "led-sys", "led-id"} <= set(by_id)


# --- the ports of the 128C, per face ----------------------------------------

def test_128c_has_128_qsfp28_cages_and_two_sfp_plus_on_the_front_and_none_on_the_rear():
    d = load_device("qfx5220-128c")
    assert numbered(d, "front", "qsfp-ganged") == list(range(0, 128))
    assert numbered(d, "front", "sfp") == [128, 129]
    assert not [p for p in placements(d, "rear") if ref_name(p["ref"]) in ("qsfp-ganged", "qsfp28", "sfp")]


def test_128c_groups_say_what_the_ports_are():
    g = load_device("qfx5220-128c")["groups"]
    rows = [k for k in g if k.startswith("qsfp28-") and not k.endswith("leds")]
    assert len(rows) == 4
    for k in rows:
        assert g[k]["attrs"] == {"media": "qsfp28", "speed": "100g"} and g[k]["role"] == "traffic"
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["sfp-plus"]["role"] == "traffic"


def test_128c_ports_are_numbered_as_printed_and_the_numerals_are_on_the_face():
    printed = {s["text"] for s in load_device("qfx5220-128c")["views"]["front"]["silkscreen"]
               if s.get("text", "").isdigit()}
    assert {str(n) for n in range(130)} <= printed


def test_128c_cages_stand_in_four_rows_of_sixteen_columns_in_eight_pairs():
    """Two stacked cages a cell, two cells a row of the block, and two blocks (figure 17)."""
    d = load_device("qfx5220-128c")
    cages = [p for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-ganged" and p["id"].startswith("port-")]
    xs = sorted({p["at"][0] for p in cages})
    ys = sorted({p["at"][1] for p in cages})
    assert len(xs) == 16 and len(ys) == 8
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert gaps[0::2] == pytest.approx([19.0] * 8, abs=0.02)
    assert gaps[1::2] == pytest.approx([gaps[1]] * 7, abs=0.02) and gaps[1] > 19.5
    # upper port above lower in a cell, cells in order down the face
    y = {int(p["id"].split("-")[1]): p["at"][1] for p in cages}
    assert all(y[n] < y[n + 1] for n in range(0, 128, 2))
    assert y[0] < y[32] < y[64] < y[96]
    # the sfp pair is right of the last column and in the lower block
    sfp = [p for p in placements(d, "front") if ref_name(p["ref"]) == "sfp"]
    assert min(p["at"][0] for p in sfp) > xs[-1]
    assert min(p["at"][1] for p in sfp) > y[64] - 1


def test_128c_lamps_follow_the_guide():
    """QSFP28 lamps are one a port or channel, so a strip of four a port (Table 9); two lamps an SFP+ port (Table 10)."""
    strips = {p["id"] for p in placements(load_device("qfx5220-128c"), "front")
              if ref_name(p["ref"]) == "qfx5220-128c-port-lamps"}
    assert strips == {f"led-port-{n}" for n in range(128)}
    assert len(load_component("qfx5220-128c-port-lamps")["elements"]) == 4
    for n in (128, 129):
        led = {p["id"] for p in placements(load_device("qfx5220-128c"), "front")
               if ref_name(p["ref"]) == "led-dot" and p["id"].startswith(f"led-port-{n}-")}
        assert led == {f"led-port-{n}-link", f"led-port-{n}-status"}


def test_128c_management_and_timing_parts_are_on_the_front():
    by_id = {p["id"]: p for p in placements(load_device("qfx5220-128c"), "front")}
    assert by_id["console"]["attrs"]["role"] == "console"
    assert by_id["console"]["at"][1] < by_id["mgmt"]["at"][1], "CON is the upper jack, MGMT the lower"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert ref_name(by_id["tod"]["ref"]) == "rj45" and by_id["tod"]["attrs"]["media"] == "rj45-tod"
    clocks = sorted(i for i in by_id if i.startswith("clk-"))
    assert clocks == ["clk-10m-in", "clk-10m-out", "clk-pps-in", "clk-pps-out"]
    assert {"reset-btn", "esd-front-jack", "led-alm", "led-sys", "led-id"} <= set(by_id)


# --- both ---------------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_no_logo_is_drawn_and_a_zone_is_reserved(name):
    d = load_device(name)
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    zones = [r["id"] for v in ("front", "rear") for r in d["views"][v].get("regions") or []]
    assert "logo-zone" in zones


@pytest.mark.parametrize("name", DEVICES)
def test_the_model_name_is_printed_as_plain_text(name):
    texts = [s.get("text") for s in load_device(name)["views"]["front"]["silkscreen"]]
    assert name.upper() in texts


def test_32cd_has_six_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them():
    """Fan modules 0 to 5, counting from the left (Table 16), with a supply at each end."""
    b = {x["id"]: x for x in bays(load_device("qfx5220-32cd"), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(6)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0] and b["psu-1"]["at"][0] > b["fan-5"]["at"][0]


def test_128c_has_six_fan_slots_in_two_rows_and_four_supply_slots_numbered_as_figure_32_prints_them():
    """Fans 0 to 2 on the top row and 3 to 5 below; supplies 0 and 1 on the top row, 2 and 3 below."""
    b = {x["id"]: x for x in bays(load_device("qfx5220-128c"), "rear")}
    assert sorted(i for i in b if i.startswith("fan-")) == [f"fan-{n}" for n in range(6)]
    assert sorted(i for i in b if i.startswith("psu-")) == [f"psu-{n}" for n in range(4)]
    top = [b[f"fan-{n}"]["at"] for n in range(3)]
    low = [b[f"fan-{n}"]["at"] for n in range(3, 6)]
    assert [p[0] for p in top] == sorted(p[0] for p in top) == [p[0] for p in low]
    assert len({p[1] for p in top}) == 1 and len({p[1] for p in low}) == 1 and top[0][1] < low[0][1]
    at = {f"psu-{n}": b[f"psu-{n}"]["at"] for n in range(4)}
    assert at["psu-0"][0] == at["psu-2"][0] < b["fan-0"]["at"][0]
    assert at["psu-1"][0] == at["psu-3"][0] > b["fan-2"]["at"][0]
    assert at["psu-0"][1] == at["psu-1"][1] < at["psu-2"][1] == at["psu-3"][1]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_variant_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name]) | {"chas"}
    for cid, (_p, _a, part) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}
    assert cfgs["chas"]["kind"] == "orderable"
    assert set(cfgs["chas"]["part-numbers"]) == {CHAS[name]}


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


@pytest.mark.parametrize("name,cid", ALL_VARIANTS)
def test_each_configuration_seats_its_supplies_and_fan_modules_with_matching_airflow(name, cid):
    d = load_device(name)
    power, airflow, _part = VARIANTS[name][cid]
    s = seated(d, cid)
    psus = {s[f"psu-{n}"] for n in range(PSU_BAYS[name])}
    fans = {s[f"fan-{n}"] for n in range(FAN_BAYS[name])}
    assert psus == {PSU[name][(power, airflow)]}
    assert fans == {FAN[name][airflow]}
    for comp in (PSU[name][(power, airflow)], FAN[name][airflow]):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == power


@pytest.mark.parametrize("name", DEVICES)
def test_the_spare_chassis_shows_every_bay_open(name):
    s = seated(load_device(name), "chas")
    assert set(s.values()) == {None} and len(s) == PSU_BAYS[name] + FAN_BAYS[name]


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = set(FAN[name].values()) if b["id"].startswith("fan-") else set(PSU[name].values())
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    for b in bays(load_device(name), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.5)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.5)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    assert c["attrs"]["model"] == FAN_PARTS[part]
    assert "part-numbers" not in c, "a contract states attrs.model or part-numbers, never both"


@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_is_described_as_the_unit(part):
    assert "field-replaceable" in " ".join(load_component(part)["description"].split())


@pytest.mark.parametrize("part", sorted(PSU_PARTS))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 1600
    assert not any(k.startswith("power-draw") for k in attrs)
    model = attrs.get("model") or next(iter(load_component(part)["part-numbers"]))
    assert model == PSU_PARTS[part]


def test_the_128c_fan_module_says_what_the_guide_says_about_its_power():
    """The cooling description calls the six fan modules 80-W modules, so 80 W is a draw (Fan Modules, 128C)."""
    attrs = load_component("qfx5220-128c-fan-afo")["attrs"]
    assert attrs["power-draw-max-w"] == 80
    assert attrs["airflow"] == "front-to-back"
    assert not any(k.startswith("power-output") for k in attrs)


@pytest.mark.parametrize("part", ["qfx5130-32cd-fan-afo", "qfx5220-128c-fan-afo"])
def test_the_front_to_back_fan_is_marked_air_out_with_a_gold_handle(part):
    """Tables 16 and 18: AIR OUT with a Juniper gold handle."""
    feats = load_component(part)["relief"]["features"]
    handle = next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    assert handle.lower() == "#e8731f"
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert ">AIR</text>" in svg and ">OUT</text>" in svg


def test_the_back_to_front_fan_has_a_blue_handle_and_is_marked_air_in():
    """Table 16: AIR IN with a Juniper azure blue handle."""
    part = "qfx5130-32cd-fan-afi"
    feats = load_component(part)["relief"]["features"]
    colour = next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    assert b > r and b > g
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert ">AIR</text>" in svg and ">IN</text>" in svg


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid", [(d, c) for d in DEVICES for c in sorted(VARIANTS[d]) + ["chas"]])
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, cid):
    part = CHAS[name] if cid == "chas" else VARIANTS[name][cid][2]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == float(RU[name])


@pytest.mark.parametrize("name", DEVICES)
def test_no_other_qfx5220_export_exists(name):
    prefix = name.upper()
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob(f"{prefix}*.yaml")}
    assert got == {v[2] for v in VARIANTS[name].values()} | {CHAS[name]}
