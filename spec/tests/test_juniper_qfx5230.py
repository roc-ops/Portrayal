"""The Juniper QFX5230-64CD, QFX5240-64OD and QFX5240-64QD, from their hardware guides.

Sources: QFX5230-64CD Switch Hardware Guide (published 2026-04-28), QFX5240 Switch Hardware Guide (published
2026-07-10) and the QFX5240 line of Switches datasheet (a00150802ENW, Rev. 2).

One device per front panel. Each model's power, airflow and spare-chassis variants are `orderable`
configurations of the one device, because the guide shows one panel for all of them. Each field-replaceable
unit is a component named for the family and its Juniper part number.

What the guides fix, and so what these tests hold:
  QFX5230 Table 8   the envelope - 3.43 x 17.4 x 25.6 in, 2RU
  QFX5240 datasheet Table 2   the envelope - 3.46 x 17.26 x 25.52 in, 2RU (guide Table 7 prints 19.03 in wide,
                              the width over the front brackets)
  QFX5230 Tables 3, 5, 6, 11, 12, 16   the part numbers of the supplies and fan modules and the airflow of each
  QFX5240 Tables 3, 5, 6   the same for the QFX5240 (airflow out only, AC only)
  figures 9 to 14 (QFX5230), 2 to 13 (QFX5240)   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# guide / datasheet envelope: height, width, depth in inches
ENVELOPE_IN = {
    "qfx5230-64cd": (3.43, 17.4, 25.6),
    "qfx5240-64od": (3.46, 17.26, 25.52),
    "qfx5240-64qd": (3.46, 17.26, 25.52),
}

# model -> (cage component, port speed token)
CAGE = {"qfx5230-64cd": "qsfp-dd", "qfx5240-64od": "osfp", "qfx5240-64qd": "qsfp-dd"}

PSU = {
    "qfx5230-64cd": {
        ("ac", "front-to-back"): "qfx5230-jnp-3000w-ac-afo",
        ("ac", "back-to-front"): "qfx5230-jnp-2700w-ac-afi",
        ("dc", "front-to-back"): "qfx5230-jnp-3000w-dc-afo",
        ("dc", "back-to-front"): "qfx5230-jnp-2400w-dc-afi",
    },
    "qfx5240-64od": {("ac", "front-to-back"): "qfx5240-pwr-ac-ao"},
    "qfx5240-64qd": {("ac", "front-to-back"): "qfx5240-pwr-ac-ao"},
}
FAN = {
    "qfx5230-64cd": {"front-to-back": "qfx5230-64cd-fan-afo", "back-to-front": "qfx5230-64cd-fan-afi"},
    "qfx5240-64od": {"front-to-back": "qfx5240-2u-fanao"},
    "qfx5240-64qd": {"front-to-back": "qfx5240-2u-fanao"},
}

# datasheet / guide ordering tables: configuration -> (power, airflow, part number)
VARIANTS = {
    "qfx5230-64cd": {
        "ac-f2b": ("ac", "front-to-back", "QFX5230-64CD-AFO"),
        "ac-b2f": ("ac", "back-to-front", "QFX5230-64CD-AFI"),
        "dc-f2b": ("dc", "front-to-back", "QFX5230-64CD-D-AFO"),
        "dc-b2f": ("dc", "back-to-front", "QFX5230-64CD-D-AFI"),
    },
    "qfx5240-64od": {"ac-f2b": ("ac", "front-to-back", "QFX5240-64OD-AO")},
    "qfx5240-64qd": {"ac-f2b": ("ac", "front-to-back", "QFX5240-64QD-AO")},
}
CHAS = {"qfx5230-64cd": "QFX5230-64CD-CHAS", "qfx5240-64od": "QFX5240-64OD-CHAS",
        "qfx5240-64qd": "QFX5240-64QD-CHAS"}

PSU_PARTS = {
    "qfx5230-jnp-3000w-ac-afo": "JNP-3000W-AC-AFO", "qfx5230-jnp-2700w-ac-afi": "JNP-2700W-AC-AFI",
    "qfx5230-jnp-3000w-dc-afo": "JNP-3000W-DC-AFO", "qfx5230-jnp-2400w-dc-afi": "JNP-2400W-DC-AFI",
    "qfx5240-pwr-ac-ao": "QFX5240-PWR-AC-AO",
}
PSU_WATTS = {"qfx5230-jnp-3000w-ac-afo": 3000, "qfx5230-jnp-2700w-ac-afi": 2700,
             "qfx5230-jnp-3000w-dc-afo": 3000, "qfx5230-jnp-2400w-dc-afi": 2400, "qfx5240-pwr-ac-ao": 3000}
FAN_PARTS = {"qfx5230-64cd-fan-afo": "QFX5230-64CD-FANAO", "qfx5230-64cd-fan-afi": "QFX5230-64CD-FANAI",
             "qfx5240-2u-fanao": "QFX5240-2U-FANAO"}
ALL_UNITS = sorted(list(PSU_PARTS) + list(FAN_PARTS))
TAKEN_BY = {u: ("QFX5240" if "5240" in u else "QFX5230-64CD") for u in ALL_UNITS}

MODELS = sorted(ENVELOPE_IN)


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


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_the_envelope_is_the_guides_table(name):
    h, w, d = ENVELOPE_IN[name]
    ch = load_device(name)["chassis"]
    assert ch["ru"] == 2
    assert ch["height"] == pytest.approx(h * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(w * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(d * INCH, abs=0.1)


@pytest.mark.parametrize("name", MODELS)
def test_the_faces_are_sized_from_the_envelope(name):
    d = load_device(name)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


@pytest.mark.parametrize("name", MODELS)
def test_the_front_is_the_body_and_not_the_rack_face(name):
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", MODELS)
def test_the_naming_follows_the_other_juniper_boxes(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"]["line"] == "QFX Series"
    assert d["portfolio"]["family"] == name.split("-")[0].upper()


# --- the ports, per face -----------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_64_cages_and_two_sfp_plus_on_the_front_and_none_on_the_rear(name):
    d = load_device(name)
    assert numbered(d, "front", CAGE[name]) == list(range(0, 64))
    assert numbered(d, "front", "sfp") == [64, 65]
    assert not [p for p in placements(d, "rear")
                if ref_name(p["ref"]) in ("qsfp-dd", "osfp", "sfp", "sfp-ganged")]


@pytest.mark.parametrize("name", MODELS)
def test_the_groups_say_what_the_ports_are(name):
    g = load_device(name)["groups"]
    media = {"qsfp-dd": "qsfp-dd", "osfp": "osfp"}[CAGE[name]]
    speed = "400g" if name == "qfx5230-64cd" else "800g"
    traffic = [k for k, v in g.items() if v.get("attrs") == {"media": media, "speed": speed}]
    assert len(traffic) == 1 and g[traffic[0]]["role"] == "traffic"
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}


@pytest.mark.parametrize("name", MODELS)
def test_ports_are_numbered_from_0_as_printed_and_the_numerals_are_on_the_face(name):
    printed = {s["text"] for s in load_device(name)["views"]["front"]["silkscreen"]
               if s.get("text", "").isdigit()}
    assert {str(n) for n in range(66)} <= printed


def rows_of(d, name):
    """port number -> (x, y) of the cage placements."""
    return {int(p["id"].split("-")[1]): tuple(p["at"]) for p in placements(d, "front")
            if ref_name(p["ref"]) == CAGE[name] and p["id"].startswith("port-")}


def test_qfx5230_stacks_two_rows_in_each_of_two_bands_numbered_down_the_columns():
    """Figure 11 and the photograph: a column holds the port pair (2c, 2c+1) in the upper band and
    (32+2c, 33+2c) in the lower one, so ports 0 to 31 are the upper band."""
    at = rows_of(load_device("qfx5230-64cd"), "qfx5230-64cd")
    assert len({x for x, _ in at.values()}) == 16
    for n in range(0, 64, 2):
        assert at[n][0] == at[n + 1][0] and at[n][1] < at[n + 1][1]
    assert max(at[n][1] for n in range(32)) < min(at[n][1] for n in range(32, 64))
    assert all(at[n][0] < at[n + 2][0] for n in range(0, 30, 2))


@pytest.mark.parametrize("name", ["qfx5240-64od", "qfx5240-64qd"])
def test_qfx5240_numbers_four_rows_down_each_column(name):
    """Figures 6 and 7: a column holds ports 4c to 4c+3 from the top, the first two in the upper band."""
    at = rows_of(load_device(name), name)
    assert len({x for x, _ in at.values()}) == 16
    for c in range(16):
        col = [at[4 * c + r] for r in range(4)]
        assert len({x for x, _ in col}) == 1
        ys = [y for _, y in col]
        assert ys == sorted(ys) and len(set(ys)) == 4
    assert all(at[n][0] < at[n + 4][0] for n in range(0, 60))


def test_the_osfp_columns_stand_in_four_groups_of_four():
    """Figure 6: 23.1 mm cages abutting inside a group, a wider gap between groups."""
    at = rows_of(load_device("qfx5240-64od"), "qfx5240-64od")
    xs = sorted({x for x, _ in at.values()})
    gaps = [round(b - a, 1) for a, b in zip(xs, xs[1:])]
    assert gaps[0:3] == [23.1] * 3 and gaps[3] > 23.1 and gaps[4:7] == [23.1] * 3


@pytest.mark.parametrize("name", MODELS)
def test_the_stacked_cages_face_the_band_between_them(name):
    """The library's stack convention: the lower cage of each pair turned 180."""
    d = load_device(name)
    turn = {p["id"]: p.get("rotate", 0) for p in placements(d, "front")
            if ref_name(p["ref"]) == CAGE[name] and p["id"].startswith("port-")}
    if name == "qfx5240-64od":
        # one OSFP a row, four rows: the library's OSFP art is drawn once and stood upright
        assert set(turn.values()) <= {0, 180}
    else:
        for n in range(0, 64, 2) if name == "qfx5230-64cd" else [m for c in range(16) for m in (4 * c, 4 * c + 2)]:
            assert turn[f"port-{n}"] == 0 and turn[f"port-{n + 1}"] == 180


@pytest.mark.parametrize("name", MODELS)
def test_the_lamps_follow_the_guide(name):
    """One lamp a network port (QFX5230 Table 9, QFX5240 Table 8), and the three chassis lamps."""
    ids = {p["id"] for p in placements(load_device(name), "front") if ref_name(p["ref"]) == "led-dot"}
    assert {f"led-port-{n}" for n in range(64)} <= ids
    assert {"led-alm", "led-sys", "led-id"} <= ids


@pytest.mark.parametrize("name", MODELS)
def test_the_management_cluster_is_on_the_front(name):
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-eth"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"reset-btn", "led-alm", "led-sys", "led-id"} <= set(by_id)
    clocks = [i for i in by_id if i.startswith("out-")]
    assert len(clocks) == 2 and all(ref_name(by_id[i]["ref"]) == "sma" for i in clocks)


@pytest.mark.parametrize("name", ["qfx5240-64od", "qfx5240-64qd"])
def test_the_qfx5240_has_a_time_of_day_jack_under_the_console(name):
    """Figure 6 callout 7: an RJ-45 TOD port."""
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert by_id["tod"]["at"][1] > by_id["console"]["at"][1]


@pytest.mark.parametrize("name", MODELS)
def test_no_logo_is_drawn_and_a_zone_is_reserved(name):
    d = load_device(name)
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    zones = [r["id"] for v in ("front", "rear") for r in d["views"][v].get("regions") or []]
    assert "logo-zone" in zones


def test_qfx5230_marks_the_sixteen_zr_ports_in_green():
    """Figure 9 note: ports 33 to 63, the odd ones, take 400G-ZR and 400G-ZRM."""
    decor = [x for x in load_device("qfx5230-64cd")["views"]["front"]["panel"]["decor"]
             if str(x.get("id", "")).startswith("zr-")]
    assert len(decor) == 16


@pytest.mark.parametrize("name,fans", [("qfx5230-64cd", 4), ("qfx5240-64od", 4), ("qfx5240-64qd", 4)])
def test_four_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them(name, fans):
    b = {x["id"]: x for x in bays(load_device(name), "rear")}
    got = sorted(i for i in b if i.startswith("fan-"))
    assert got == [f"fan-{n}" for n in range(fans)]
    assert [b[f]["at"][0] for f in got] == sorted(b[f]["at"][0] for f in got)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    left = b["psu-0"]["at"][0] < b["fan-0"]["at"][0]
    right = b["psu-0"]["at"][0] > b["fan-3"]["at"][0]
    assert left != right, "both supplies stand at one end"
    assert b["psu-0"]["at"][1] < b["psu-1"]["at"][1], "supply 0 is the upper one"


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_each_variant_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name]) | {"chas"}
    for cid, (_p, _a, part) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}
    assert cfgs["chas"]["kind"] == "orderable"
    assert set(cfgs["chas"]["part-numbers"]) == {CHAS[name]}


@pytest.mark.parametrize("name", MODELS)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name (or None when empty), as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for b in bays(dev, "rear"):
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref) if ref else None
    return out


CASES = [(n, cid) for n in MODELS for cid in sorted(VARIANTS[n])]


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    power, airflow, _part = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {PSU[name][(power, airflow)]}
    assert {s[f"fan-{n}"] for n in range(4)} == {FAN[name][airflow]}
    for comp in (PSU[name][(power, airflow)], FAN[name][airflow]):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == power


@pytest.mark.parametrize("name", MODELS)
def test_the_spare_chassis_shows_every_bay_open(name):
    s = seated(load_device(name), "chas")
    assert set(s.values()) == {None} and len(s) == 6


@pytest.mark.parametrize("name", MODELS)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = set(FAN[name].values()) if b["id"].startswith("fan-") else set(PSU[name].values())
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", MODELS)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    for b in bays(load_device(name), "rear"):
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
def test_a_unit_is_described_as_the_unit(part):
    text = " ".join(load_component(part)["description"].split())
    assert "hot-removable" in text and "hot-insertable" in text
    assert "AC and DC supplies" in text or "front-to-back" in text or "back-to-front" in text


@pytest.mark.parametrize("part", sorted(PSU_PARTS))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == PSU_WATTS[part]
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", sorted(FAN_PARTS))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [("qfx5230-jnp-3000w-ac-afo", "qfx5230-jnp-2700w-ac-afi"),
                                          ("qfx5230-jnp-3000w-dc-afo", "qfx5230-jnp-2400w-dc-afi"),
                                          ("qfx5230-64cd-fan-afo", "qfx5230-64cd-fan-afi")])
def test_the_back_to_front_unit_has_a_green_handle_and_the_front_to_back_a_gold_one(front, back):
    """QFX5230 Tables 3, 6, 11, 12: AIR OUT with a Juniper gold handle, AIR IN with a green handle."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f != b and f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert g > r and g > bl, "green is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"
    if "fan" in front:
        for part, word in ((front, "OUT"), (back, "IN")):
            svg = (COMP / part / "v1/skins/default.svg").read_text()
            assert f">{word}</text>" in svg and ">AIR</text>" in svg


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name):
    parts = [v[2] for v in VARIANTS[name].values()] + [CHAS[name]]
    for part in parts:
        for target in ("netbox", "nautobot"):
            f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
            doc = yaml.safe_load(f.read_text())
            assert doc["manufacturer"] == "Juniper"
            assert doc["model"] == part
            assert doc["u_height"] == 2.0


def test_no_other_qfx5230_or_qfx5240_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5[23]40*.yaml")}
    got |= {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5230*.yaml")}
    want = {v[2] for m in MODELS for v in VARIANTS[m].values()} | set(CHAS.values())
    assert got == want
