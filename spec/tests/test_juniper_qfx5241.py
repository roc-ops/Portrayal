"""The Juniper QFX5241-32OD, QFX5241-64OD and QFX5241-64QD, from their hardware guides.

Sources: QFX5241-32OD Switch Hardware Guide (published 2026-10-11) and QFX5241-64OD and QFX5241-64QD Switches
Hardware Guide (published 2026-09-28), both Juniper Networks, from juniper.net; the maker's studio photographs
of the three models from juniper.net's image library.

One device per front panel. Each model's AC and DC builds and its spare chassis are `orderable` configurations of
the one device, because the guide shows one panel for all of them. The ORv3 switch-tray assemblies (-DO-T1, -DO-T2
and the -TCHAS spares) are 21.14 in wide and are not modelled. Each field-replaceable unit is a component named
for the family and its Juniper part number, or the existing QFX5240 component where the QFX5241 guide names the
same part number.

What the guides fix, and so what these tests hold:
  32OD guide Table 10       the envelope - 1.72 x 17.26 x 23.19 in, 1U
  64OD/QD guide Table 9     the envelope - 3.46 x 19.03 x 25.51 in, 2U; the 19.03 in is the width over the front
                            brackets, and the body is the 17.26 in the QFX5240 sibling carries
  32OD Tables 4, 6-8, 64 Tables 4, 6-8   the part numbers of the supplies and fan modules and their airflow
  32OD figures 15-21, 64 figures 12-22   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# guide envelope: height, depth in inches; the width is the 17.26 in body on all three (see the docstring)
ENVELOPE_IN = {
    "qfx5241-32od": (1.72, 17.26, 23.19),
    "qfx5241-64od": (3.46, 17.26, 25.51),
    "qfx5241-64qd": (3.46, 17.26, 25.51),
}
RU = {"qfx5241-32od": 1, "qfx5241-64od": 2, "qfx5241-64qd": 2}
PORTS = {"qfx5241-32od": 32, "qfx5241-64od": 64, "qfx5241-64qd": 64}
FANS = {"qfx5241-32od": 7, "qfx5241-64od": 4, "qfx5241-64qd": 4}
CAGE = {"qfx5241-32od": "osfp", "qfx5241-64od": "osfp", "qfx5241-64qd": "qsfp-dd"}

# model -> (power, airflow) -> supply; airflow -> fan module
PSU = {
    "qfx5241-32od": {("ac", "front-to-back"): "qfx5241-1u-pwr-ao"},
    "qfx5241-64od": {("ac", "front-to-back"): "qfx5240-pwr-ac-ao", ("dc", "front-to-back"): "qfx524x-2ru-pwr-do"},
    "qfx5241-64qd": {("ac", "front-to-back"): "qfx5240-pwr-ac-ao", ("dc", "front-to-back"): "qfx524x-2ru-pwr-do"},
}
FAN = {
    "qfx5241-32od": {("ac", "front-to-back"): "qfx5241-1u-fan-o"},
    "qfx5241-64od": {("ac", "front-to-back"): "qfx5240-2u-fanao", ("dc", "front-to-back"): "qfx524x-2ru-fan-o"},
    "qfx5241-64qd": {("ac", "front-to-back"): "qfx5240-2u-fanao", ("dc", "front-to-back"): "qfx524x-2ru-fan-o"},
}

# guide Table 4 (and the spare chassis table): configuration -> (power, airflow, part number)
VARIANTS = {
    "qfx5241-32od": {"ac-f2b": ("ac", "front-to-back", "QFX5241-32OD-AO")},
    "qfx5241-64od": {"ac-f2b": ("ac", "front-to-back", "QFX5241-64OD-AO"),
                     "dc-f2b": ("dc", "front-to-back", "QFX5241-64OD-DO")},
    "qfx5241-64qd": {"ac-f2b": ("ac", "front-to-back", "QFX5241-64QD-AO"),
                     "dc-f2b": ("dc", "front-to-back", "QFX5241-64QD-DO")},
}
CHAS = {"qfx5241-32od": "QFX5241-32OD-CHAS", "qfx5241-64od": "QFX5241-64OD-CHAS",
        "qfx5241-64qd": "QFX5241-64QD-CHAS"}

# the units this slice adds; the two QFX5240 ones are reused as they are
NEW_PSU = {"qfx5241-1u-pwr-ao": ("QFX5241-1U-PWR-AO", 2400), "qfx524x-2ru-pwr-do": ("QFX524X-2RU-PWR-DO", 3000)}
NEW_FAN = {"qfx5241-1u-fan-o": "QFX5241-1U-FAN-O", "qfx524x-2ru-fan-o": "QFX524X-2RU-FAN-O"}
REUSED = {"qfx5240-pwr-ac-ao": "QFX5240-PWR-AC-AO", "qfx5240-2u-fanao": "QFX5240-2U-FANAO"}
ALL_UNITS = sorted(list(NEW_PSU) + list(NEW_FAN) + list(REUSED))

MODELS = sorted(ENVELOPE_IN)
M64 = ["qfx5241-64od", "qfx5241-64qd"]


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
    assert ch["ru"] == RU[name]
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
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5240"}


# --- the ports, per face -----------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_the_network_cages_and_the_two_sfp_ports_are_numbered_as_printed(name):
    d = load_device(name)
    n = PORTS[name]
    assert numbered(d, "front", CAGE[name]) == list(range(0, n))
    assert numbered(d, "front", "sfp") == [n, n + 1]
    assert not [p for p in placements(d, "rear")
                if ref_name(p["ref"]) in ("qsfp-dd", "osfp", "sfp", "sfp-ganged")]


@pytest.mark.parametrize("name", MODELS)
def test_the_groups_say_what_the_ports_are(name):
    g = load_device(name)["groups"]
    media = {"qsfp-dd": "qsfp-dd", "osfp": "osfp"}[CAGE[name]]
    traffic = [k for k, v in g.items() if v.get("attrs") == {"media": media, "speed": "800g"}]
    assert len(traffic) == 1 and g[traffic[0]]["role"] == "traffic"
    small = {"qfx5241-32od": {"media": "sfp28", "speed": "25g"}}.get(name, {"media": "sfp-plus", "speed": "10g"})
    assert [k for k, v in g.items() if v.get("attrs") == small and v["role"] == "traffic"]


@pytest.mark.parametrize("name", MODELS)
def test_the_numerals_are_on_the_face(name):
    printed = {s["text"] for s in load_device(name)["views"]["front"]["silkscreen"]
               if s.get("text", "").isdigit()}
    assert {str(n) for n in range(PORTS[name] + 2)} <= printed


def rows_of(d, name):
    """port number -> (x, y) of the cage placements."""
    return {int(p["id"].split("-")[1]): tuple(p["at"]) for p in placements(d, "front")
            if ref_name(p["ref"]) == CAGE[name] and p["id"].startswith("port-")}


def test_the_32od_stacks_two_rows_in_sixteen_columns_in_four_groups_of_four():
    """Figure 15 and the photograph: a column holds ports 2c (upper) and 2c+1 (lower)."""
    at = rows_of(load_device("qfx5241-32od"), "qfx5241-32od")
    assert len({x for x, _ in at.values()}) == 16
    for c in range(16):
        assert at[2 * c][0] == at[2 * c + 1][0] and at[2 * c][1] < at[2 * c + 1][1]
    assert all(at[n][0] < at[n + 2][0] for n in range(0, 30))
    xs = sorted({x for x, _ in at.values()})
    gaps = [round(b - a, 1) for a, b in zip(xs, xs[1:])]
    assert max(gaps[0:3]) - min(gaps[0:3]) < 0.2 and gaps[3] > gaps[0] + 2 and gaps[11] > gaps[0] + 2


@pytest.mark.parametrize("name", M64)
def test_the_64_port_boxes_number_four_rows_down_each_column(name):
    """Figures 12 and 13: a column holds ports 4c to 4c+3 from the top, the first two in the upper band."""
    at = rows_of(load_device(name), name)
    assert len({x for x, _ in at.values()}) == 16
    for c in range(16):
        col = [at[4 * c + r] for r in range(4)]
        assert len({x for x, _ in col}) == 1
        ys = [y for _, y in col]
        assert ys == sorted(ys) and len(set(ys)) == 4
    assert all(at[n][0] < at[n + 4][0] for n in range(0, 60))


@pytest.mark.parametrize("name", MODELS)
def test_the_lamps_follow_the_guide(name):
    """One lamp a network port (32OD Table 11, 64 Table 10), and the three chassis lamps."""
    ids = {p["id"] for p in placements(load_device(name), "front") if ref_name(p["ref"]) == "led-dot"}
    assert {f"led-port-{n}" for n in range(PORTS[name])} <= ids
    assert {"led-alm", "led-sys", "led-id"} <= ids


@pytest.mark.parametrize("name", MODELS)
def test_the_management_cluster_is_on_the_front(name):
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-eth"
    assert {"reset-btn", "led-alm", "led-sys", "led-id"} <= set(by_id)
    assert ref_name(by_id["usb"]["ref"]) == ("usb-c" if name == "qfx5241-32od" else "usb-a")


@pytest.mark.parametrize("name", M64)
def test_the_64_port_boxes_carry_the_clock_and_time_of_day_jacks(name):
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert by_id["tod"]["at"][1] > by_id["console"]["at"][1]
    clocks = [i for i in by_id if i.startswith("out-")]
    assert len(clocks) == 2 and all(ref_name(by_id[i]["ref"]) == "sma" for i in clocks)


def test_the_32od_has_no_clock_or_time_of_day_jack():
    by_id = {p["id"] for p in placements(load_device("qfx5241-32od"), "front")}
    assert "tod" not in by_id and not [i for i in by_id if i.startswith("out-")]


@pytest.mark.parametrize("name", MODELS)
def test_no_logo_is_drawn_and_a_zone_is_reserved(name):
    d = load_device(name)
    for view in ("front", "rear"):
        texts = " ".join(str(s.get("text", "")) for s in d["views"][view].get("silkscreen") or [])
        assert "JUNIPER" not in texts.upper() and "NETWORKS" not in texts.upper()
    zones = [r["id"] for v in ("front", "rear") for r in d["views"][v].get("regions") or []]
    assert "logo-zone" in zones


# --- the bays ----------------------------------------------------------------

@pytest.mark.parametrize("name", MODELS)
def test_the_fan_and_supply_slots_are_numbered_as_the_photograph_numbers_them(name):
    b = {x["id"]: x for x in bays(load_device(name), "rear")}
    got = sorted(i for i in b if i.startswith("fan-"))
    assert got == [f"fan-{n}" for n in range(FANS[name])]
    assert [b[f]["at"][0] for f in got] == sorted(b[f]["at"][0] for f in got)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    if name == "qfx5241-32od":
        # PSU0 at the left end and PSU1 at the right end of the one row, the fans between
        assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0] < b[f"fan-{FANS[name] - 1}"]["at"][0] < b["psu-1"]["at"][0]
    else:
        assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0], "both supplies stand at the left end"
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
    psu, fan = PSU[name][(power, airflow)], FAN[name][(power, airflow)]
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(FANS[name])} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == power


@pytest.mark.parametrize("name", MODELS)
def test_the_spare_chassis_shows_every_bay_open(name):
    s = seated(load_device(name), "chas")
    assert set(s.values()) == {None} and len(s) == FANS[name] + 2


@pytest.mark.parametrize("name", MODELS)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = set((FAN if b["id"].startswith("fan-") else PSU)[name].values())
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
def test_a_unit_is_named_for_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    model = {**{k: v[0] for k, v in NEW_PSU.items()}, **NEW_FAN, **REUSED}[part]
    assert c["attrs"]["model"] == model
    assert "part-numbers" not in c, "a contract states attrs.model or part-numbers, never both"


@pytest.mark.parametrize("part", ALL_UNITS)
def test_a_unit_is_described_as_the_unit(part):
    text = " ".join(load_component(part)["description"].split())
    assert "hot-removable" in text and "hot-insertable" in text and "front-to-back" in text


@pytest.mark.parametrize("part", sorted(NEW_PSU))
def test_a_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == NEW_PSU[part][1]
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", sorted(NEW_FAN))
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


def test_the_qfx5240_units_the_guide_names_again_are_reused_and_not_copied():
    """64 guide Table 8 names QFX5240-PWR-AC-AO and QFX5240-2U-FANAO for the AC models."""
    names = {p.name for p in COMP.iterdir()}
    assert not [n for n in names if n.startswith("qfx5241-") and ("pwr-ac-ao" in n and "1u" not in n)]
    assert {"qfx5240-pwr-ac-ao", "qfx5240-2u-fanao"} <= names


@pytest.mark.parametrize("part", ["qfx5241-1u-fan-o", "qfx524x-2ru-fan-o"])
def test_a_front_to_back_fan_module_has_an_orange_handle_and_the_label_air_out(part):
    feats = load_component(part)["relief"]["features"]
    assert next(f for f in feats if f["node"] == "handle")["color"].lower() == "#e8731f"
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert ">OUT</text>" in svg and ">AIR</text>" in svg


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
            assert doc["u_height"] == float(RU[name])


def test_no_other_qfx5241_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5241*.yaml")}
    want = {v[2] for m in MODELS for v in VARIANTS[m].values()} | set(CHAS.values())
    assert got == want
