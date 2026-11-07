"""The Juniper QFX5120-32C, -48T, -48Y and -48YM, from the QFX5120 Switch Hardware Guide (2026-09-30).

One device per front panel: no two of the four models share one (the 32C has 32 QSFP28 and two SFP+
with its management ports on the port side; the 48T has 48 BASE-T jacks and six QSFP28; the 48YM
puts its eight QSFP28 ports between two blocks of SFP28 and prints one lamp a port). Each model's
power and airflow variants are `orderable` configurations of its device, because the guide shows the
same panel for all of them. Each field-replaceable unit is a component named by its Juniper part
number, and the 32C and 48T seat parts that other Juniper lines already carry.

What the guide fixes, and so what these tests hold:
  Table 9    the envelope - the 32C is 1.7 x 17.26 x 20.27 in, the others 1.72 x 17.36 x 20.48 in, 1RU
  Table 7    the variants, the part numbers and the supplies and fan modules each ships with
  Table 23   the fan module part numbers and the airflow of each
  Tables 25, 26, 35, 36   the supply part numbers (650 W AC and DC for the 32C, 48T and 48Y, 850 W
             for the 48YM) and their airflow
  figures 19 to 40   the ports, their count and numbering, and what is on the rear
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 9: height, width, depth in inches (1RU); the 48T, 48Y and 48YM share one row of figures
ENVELOPE_IN = {"h": 1.72, "w": 17.36, "d": 20.48}
# the 32C row is 1.7 in (4.33 cm), 17.26 in (43.84 cm), 20.27 in (51.5 cm); the metric figure is the
# one the table gives to two places, so it is the one held (1.7 in is 43.18 mm, 0.12 under 4.33 cm)
ENVELOPE_32C_MM = {"h": 43.3, "w": 438.4, "d": 515.0}

# Table 7: configuration -> (part number, power supply, fan module, airflow)
VARIANTS = {
    "qfx5120-32c": {
        "ac-f2b": ("QFX5120-32C-AFO", "qfx5200-48y-apsu-ao", "qfx5200-48y-fan-afo", "front-to-back"),
        "ac-b2f": ("QFX5120-32C-AFI", "qfx5200-48y-apsu-ai", "qfx5200-48y-fan-afi", "back-to-front"),
        "dc-f2b": ("QFX5120-32C-DC-AFO", "qfx5200-48y-dpsu-ao", "qfx5200-48y-fan-afo", "front-to-back"),
        "dc-b2f": ("QFX5120-32C-DC-AFI", "qfx5200-48y-dpsu-ai", "qfx5200-48y-fan-afi", "back-to-front"),
    },
    "qfx5120-48t": {
        "ac-f2b": ("QFX5120-48T-AFO", "jpsu-650w-ac-ao", "qfx5110-fanafo", "front-to-back"),
        "ac-b2f": ("QFX5120-48T-AFI", "jpsu-650w-ac-ai", "qfx5110-fanafi", "back-to-front"),
        "dc-f2b": ("QFX5120-48T-DC-AFO", "qfx5100-jpsu-650w-dc-afo", "qfx5110-fanafo", "front-to-back"),
        "dc-b2f": ("QFX5120-48T-DC-AFI", "qfx5100-jpsu-650w-dc-afi", "qfx5110-fanafi", "back-to-front"),
    },
    "qfx5120-48y": {
        "ac-f2b": ("QFX5120-48Y-AFO2", "jpsu-650w-ac-ao", "qfx5110-fanafo", "front-to-back"),
        "ac-b2f": ("QFX5120-48Y-AFI2", "jpsu-650w-ac-ai", "qfx5110-fanafi", "back-to-front"),
    },
    "qfx5120-48ym": {
        "ac-f2b": ("QFX5120-48YM-AFO", "jpsu-850w-ac-afo", "qfx5110-fanafo", "front-to-back"),
        "ac-b2f": ("QFX5120-48YM-AFI", "jpsu-850w-ac-afi", "qfx5110-fanafi", "back-to-front"),
    },
}
DEVICES = sorted(VARIANTS)
SFP28_DEVICES = ["qfx5120-48y", "qfx5120-48ym"]
CONFIGS = [(n, c) for n in DEVICES for c in VARIANTS[n]]
# Tables 25 and 35: the supplies each model's bays accept. The 32C takes the QFX5200-48Y's parts
# by their shared part number; the 48T takes the 48Y's AC supplies and the QFX5100's DC ones.
ACCEPTS = {
    "qfx5120-32c": {"psu": {"qfx5200-48y-apsu-ao", "qfx5200-48y-apsu-ai",
                            "qfx5200-48y-dpsu-ao", "qfx5200-48y-dpsu-ai"},
                    "fan": {"qfx5200-48y-fan-afo", "qfx5200-48y-fan-afi"}},
    "qfx5120-48t": {"psu": {"jpsu-650w-ac-ao", "jpsu-650w-ac-ai",
                            "qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"},
                    "fan": {"qfx5110-fanafo", "qfx5110-fanafi"}},
    "qfx5120-48y": {"psu": {"jpsu-650w-ac-ao", "jpsu-650w-ac-ai"},
                    "fan": {"qfx5110-fanafo", "qfx5110-fanafi"}},
    "qfx5120-48ym": {"psu": {"jpsu-850w-ac-afo", "jpsu-850w-ac-afi"},
                     "fan": {"qfx5110-fanafo", "qfx5110-fanafi"}},
}
# Table 7: six fan modules in the 32C (5+1), five in the others (4+1)
FAN_COUNT = {"qfx5120-32c": 6, "qfx5120-48t": 5, "qfx5120-48y": 5, "qfx5120-48ym": 5}
# Table 8/guide: the supply and fan power figures are not published, the supply rating is its name
PSU_WATTS = {"jpsu-650w-ac-ao": 650, "jpsu-650w-ac-ai": 650,
             "jpsu-850w-ac-afo": 850, "jpsu-850w-ac-afi": 850}


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


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_9(name):
    ch = load_device(name)["chassis"]
    env = ENVELOPE_32C_MM if name == "qfx5120-32c" else {k: v * INCH for k, v in ENVELOPE_IN.items()}
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(env["h"], abs=0.1)
    assert ch["width"] == pytest.approx(env["w"], abs=0.1)
    assert ch["depth"] == pytest.approx(env["d"], abs=0.1)


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
    """Table 9: the brackets extend 17.36 in to 19 in, so the body is what is drawn."""
    d = load_device(name)
    assert d["views"]["front"]["size"]["w"] < 480


# --- the ports, per face -----------------------------------------------------

def ports_by_cage(dev):
    out = {"sfp": [], "qsfp": []}
    for p in placements(dev, "front"):
        name = ref_name(p["ref"])
        if name == "sfp-ganged":
            out["sfp"].append(p)
        elif name == "qsfp-ganged":
            out["qsfp"].append(p)
    return out


@pytest.mark.parametrize("name", SFP28_DEVICES)
def test_48_sfp28_and_8_qsfp28_cages_on_the_front(name):
    cages = ports_by_cage(load_device(name))
    assert len(cages["sfp"]) == 48
    assert len(cages["qsfp"]) == 8


@pytest.mark.parametrize("name", SFP28_DEVICES)
def test_ports_are_numbered_0_to_55_as_printed(name):
    d = load_device(name)
    cages = ports_by_cage(d)
    sfp = sorted(int(p["id"].split("-")[1]) for p in cages["sfp"])
    qsfp = sorted(int(p["id"].split("-")[1]) for p in cages["qsfp"])
    assert sfp == list(range(0, 48))
    assert qsfp == list(range(48, 56))
    # the numeral printed beside each cage is its number
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(56)} <= printed


@pytest.mark.parametrize("name", SFP28_DEVICES)
def test_the_groups_say_what_the_ports_are(name):
    g = load_device(name)["groups"]
    assert g["sfp28"]["attrs"] == {"media": "sfp28", "speed": "25g"}
    assert g["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    assert g["sfp28"]["role"] == g["qsfp28"]["role"] == "traffic"


def test_48y_ports_sit_in_three_blocks_of_sfp28_then_the_qsfp28_block():
    d = load_device("qfx5120-48y")
    cages = ports_by_cage(d)
    sfp_x = max(p["at"][0] for p in cages["sfp"])
    qsfp_x = min(p["at"][0] for p in cages["qsfp"])
    assert qsfp_x > sfp_x, "the QSFP28 block is at the right of the SFP28 block"
    # two rows, upper cages even and lower odd: the printed column order
    y = {int(p["id"].split("-")[1]): p["at"][1] for p in cages["sfp"]}
    assert all(y[2 * c] < y[2 * c + 1] for c in range(24))


def test_48ym_puts_the_qsfp28_between_two_sfp28_blocks():
    d = load_device("qfx5120-48ym")
    cages = ports_by_cage(d)
    x = {int(p["id"].split("-")[1]): p["at"][0] for p in cages["sfp"] + cages["qsfp"]}
    assert max(x[n] for n in range(0, 24)) < min(x[n] for n in range(48, 56))
    assert max(x[n] for n in range(48, 56)) < min(x[n] for n in range(24, 48))


def test_the_lamps_follow_the_guide_tables():
    """48Y: two lamps a SFP28 port and four a QSFP28 port (Tables 18, 19); 48YM: one each (20, 21)."""
    y = load_device("qfx5120-48y")
    ids = {p["id"] for p in placements(y, "front") if ref_name(p["ref"]) == "led-dot"}
    for n in range(48):
        assert f"led-port-{n}" in ids and f"led-port-{n}-speed" in ids
    for n in range(48, 56):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= ids
    assert len(ids) == 96 + 32
    ym = load_device("qfx5120-48ym")
    ids = {p["id"] for p in placements(ym, "front") if ref_name(p["ref"]) == "led-dot"}
    assert ids == {f"led-port-{n}" for n in range(56)}


def test_48ym_prints_one_numeral_strip_under_the_lower_row():
    d = load_device("qfx5120-48ym")
    ys = {s["at"][1] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert len(ys) == 1 and min(ys) > 36.0


@pytest.mark.parametrize("name", SFP28_DEVICES)
def test_the_rear_has_console_usb_and_two_management_jacks(name):
    d = load_device(name)
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    for jack in ("mgmt-c0", "mgmt-c1"):
        assert ref_name(by_id[jack]["ref"]) == "rj45-ganged-eth"
        assert by_id[jack]["attrs"]["speed"] == "1g"
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "esd-rear-jack"} <= set(by_id)


def test_c0_and_c1_are_printed_the_other_way_up_on_the_48ym():
    """48Y prints C0 above C1; the 48YM prints C1 above C0 (the photographs, not the callouts)."""
    y = {p["id"]: p["at"][1] for p in placements(load_device("qfx5120-48y"), "rear")}
    ym = {p["id"]: p["at"][1] for p in placements(load_device("qfx5120-48ym"), "rear")}
    assert y["mgmt-c0"] < y["mgmt-c1"]
    assert ym["mgmt-c1"] < ym["mgmt-c0"]


def test_only_the_48ym_has_the_timing_outputs():
    y = {p["id"] for p in placements(load_device("qfx5120-48y"), "rear")}
    ym = {p["id"]: p for p in placements(load_device("qfx5120-48ym"), "rear")}
    assert not ({"pps-out", "out-10m"} & y)
    assert ref_name(ym["pps-out"]["ref"]) == ref_name(ym["out-10m"]["ref"]) == "din-1-0-2-3-jack"


@pytest.mark.parametrize("name", DEVICES)
def test_the_fan_and_supply_slots_are_numbered_as_the_guide_numbers_them(name):
    """Fan slots 0 to 4 (0 to 5 in the 32C) and supply slots 0 and 1, left to right. The 32C puts
    one supply at each end of the rear (PS0, PS1); the others put both at the right."""
    d = load_device(name)
    b = {x["id"]: x for x in bays(d, "rear")}
    n_fans = FAN_COUNT[name]
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(n_fans)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["psu-1"]["at"][0]
    last = b[f"fan-{n_fans - 1}"]["at"][0]
    assert b["psu-1"]["at"][0] > last
    if name == "qfx5120-32c":
        assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0]
    else:
        assert b["psu-0"]["at"][0] > last


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
    defaults = [c for c, v in cfgs.items() if v.get("default")]
    assert defaults == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name, as the configuration leaves it (default where unstated)."""
    cfg = dev["configurations"][cid]
    out = {}
    for b in bays(dev, "rear"):
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref)
    return out


@pytest.mark.parametrize("name,cid", CONFIGS)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    _part, psu, fan, airflow = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(FAN_COUNT[name])} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    # the chassis states the default airflow; a configuration states it only where it differs
    cfg_airflow = d["configurations"][cid].get("airflow", d["chassis"]["airflow"])
    assert cfg_airflow == airflow
    # a DC configuration says so; an AC one leaves the chassis default
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == cid.split("-")[0]


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = ACCEPTS[name]["fan" if b["id"].startswith("fan-") else "psu"]
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got


def test_the_48ym_does_not_take_the_650_w_supplies():
    """Table 25: the 48T and 48Y take the 650 W part, the 48YM the 850 W one."""
    y = {ref_name(r) for b in bays(load_device("qfx5120-48y"), "rear") if b["id"].startswith("psu-") for r in b["accepts"]}
    ym = {ref_name(r) for b in bays(load_device("qfx5120-48ym"), "rear") if b["id"].startswith("psu-") for r in b["accepts"]}
    assert all("650w" in n for n in y) and all("850w" in n for n in ym)


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            # a bay holds the largest module it accepts, and none is more than 0.5 mm smaller than
            # it: the 48T's AC and DC supplies are 54.6 x 40.2 and 54.8 x 39.8 mm
            for axis in ("w", "h"):
                assert b["size"][axis] >= c[axis] - 0.05
                assert b["size"][axis] == pytest.approx(c[axis], abs=0.5)


# --- the field-replaceable units ---------------------------------------------

PARTS = ["jpsu-650w-ac-ao", "jpsu-650w-ac-ai", "jpsu-850w-ac-afo", "jpsu-850w-ac-afi",
         "qfx5110-fanafo", "qfx5110-fanafi"]


@pytest.mark.parametrize("part", PARTS)
def test_a_unit_is_named_by_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part
    assert c["attrs"]["model"] == part.upper()
    assert c["kind"] == "module"


@pytest.mark.parametrize("part", PARTS)
def test_a_unit_is_described_as_the_unit_and_names_the_lines_that_take_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "field-replaceable" in text
    assert "QFX5120-48Y" in text
    if "850w" in part:
        assert "QFX5120-48YM" in text and "QFX5120-48Y " not in text.replace("QFX5120-48YM", "")
    elif part.startswith("qfx5110"):
        assert "QFX5120-48YM" in text and "QFX5120-48T" in text


@pytest.mark.parametrize("part,watts", sorted(PSU_WATTS.items()))
def test_a_supply_states_the_power_it_provides_as_an_output(part, watts):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == watts
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", ["qfx5110-fanafo", "qfx5110-fanafi"])
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [("jpsu-650w-ac-ao", "jpsu-650w-ac-ai"),
                                          ("jpsu-850w-ac-afo", "jpsu-850w-ac-afi"),
                                          ("qfx5110-fanafo", "qfx5110-fanafi")])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_a_gold_one(front, back):
    """Tables 23, 26: AIR OUT with a Juniper Gold handle, AIR IN with a Juniper Azure Blue handle."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f != b
    assert f.lower() == "#e8731f"                       # the photographed orange
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"
    if front.startswith("qfx5110"):
        # the fan module prints its direction on the chip; the supplies' photograph shows no label
        for part, word in ((front, "AIR OUT"), (back, "AIR IN")):
            svg = (COMP / part / "v1/skins/default.svg").read_text()
            assert f">{word.split()[1]}</text>" in svg and ">AIR</text>" in svg


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid", CONFIGS)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, cid):
    part = VARIANTS[name][cid][0]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_juniper_qfx5120_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5120-*.yaml")}
    want = {v[0] for per in VARIANTS.values() for v in per.values()}
    assert got == want


# --- the QFX5120-32C ---------------------------------------------------------

def by_id(dev, view):
    return {p["id"]: p for p in placements(dev, view)}


def number(pid):
    return int(pid.split("-")[1])


def test_32c_has_32_qsfp28_cages_numbered_0_to_31_in_four_gangs_of_four_columns():
    """Figure 21 and the photograph: 16 columns, the even port above the odd, ganged four columns
    to a block, the cages on the registry's 19.0 mm pitch and a gutter between blocks."""
    d = load_device("qfx5120-32c")
    cages = {number(p["id"]): p for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-ganged"}
    assert sorted(cages) == list(range(32))
    assert all(p["group"] == "qsfp28" and p["rel-pos"] == n for n, p in cages.items())
    for c in range(16):
        assert cages[2 * c]["at"][1] < cages[2 * c + 1]["at"][1]
        assert cages[2 * c]["at"][0] == cages[2 * c + 1]["at"][0]
    xs = [cages[2 * c]["at"][0] for c in range(16)]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(19.0) == 12
    assert [s for s in steps if s != 19.0] == [pytest.approx(22.7, abs=0.2)] * 3
    # the lower cage is turned over, the library's stack convention
    assert all(cages[n].get("rotate") == 180 for n in range(1, 32, 2))
    assert not any(cages[n].get("rotate") for n in range(0, 32, 2))
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}


def test_32c_has_two_sfp_plus_cages_32_and_33_stacked_at_the_right_of_the_front():
    d = load_device("qfx5120-32c")
    cages = {number(p["id"]): p for p in placements(d, "front") if ref_name(p["ref"]) == "sfp-ganged"}
    assert sorted(cages) == [32, 33]
    assert cages[32]["at"][0] == cages[33]["at"][0]
    assert cages[32]["at"][1] < cages[33]["at"][1]
    assert cages[32]["at"][0] > max(p["at"][0] for p in placements(d, "front")
                                    if ref_name(p["ref"]) == "qsfp-ganged")
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}


def test_32c_lamps_are_four_to_a_qsfp28_port_and_one_to_an_sfp_plus_port():
    """Tables 14 and 15: the first lamp of a QSFP28 port is the unchannelized link, the other three
    are channels; each SFP+ port has one."""
    d = load_device("qfx5120-32c")
    ids = {p["id"] for p in placements(d, "front") if ref_name(p["ref"]) == "led-dot"}
    for n in range(32):
        assert {f"led-port-{n}", f"led-port-{n}-lane-2", f"led-port-{n}-lane-3",
                f"led-port-{n}-lane-4"} <= ids
    assert {"led-port-32", "led-port-33"} <= ids
    assert len([i for i in ids if i.startswith("led-port-")]) == 32 * 4 + 2


def test_32c_prints_every_port_numeral():
    printed = {s["text"] for s in load_device("qfx5120-32c")["views"]["front"]["silkscreen"] if "text" in s}
    assert {str(n) for n in range(34)} <= printed
    assert {"MGMT", "CON", "RESET", "ID"} <= printed


def test_32c_management_ports_are_on_the_port_side_not_the_rear():
    """Figure 21: MGMT, CON, USB, the ID lamp and the reset button are on the same face as the
    ports; the rear carries only the supplies, the fans and the earthing screws."""
    d = load_device("qfx5120-32c")
    front, rear = by_id(d, "front"), by_id(d, "rear")
    assert ref_name(front["mgmt"]["ref"]) == "rj45-ganged-eth" and front["mgmt"]["attrs"]["role"] == "mgmt"
    assert ref_name(front["console"]["ref"]) == "rj45-ganged" and front["console"]["attrs"]["role"] == "console"
    assert ref_name(front["usb"]["ref"]) == "usb-a"
    assert {"led-id", "reset-btn"} <= set(front)
    assert front["mgmt"]["at"][1] < front["console"]["at"][1]
    assert not ({"mgmt", "console", "usb", "led-id", "reset-btn"} & set(rear))
    assert {f"led-fan-{n}" for n in range(6)} <= set(rear)
    assert {"ground-0", "ground-1"} <= set(rear)


def test_32c_prints_a_single_chassis_lamp_not_the_four_of_the_48_port_models():
    """Table 10 gives the 32C one chassis lamp, ID, which is yellow; the others have ALM, SYS, MST, ID."""
    d = load_device("qfx5120-32c")
    lamps = {p["id"] for p in placements(d, "front") + placements(d, "rear")}
    assert "led-id" in lamps and not ({"led-alm", "led-sys", "led-mst"} & lamps)
    states = next(p for p in placements(d, "front") if p["id"] == "led-id")["states"]
    assert any(isinstance(s, dict) and s["color"].lower() in ("#eab308", "#f59e0b", "#facc15", "#fbbf24")
               for s in states)


def test_32c_has_no_timing_ports():
    d = load_device("qfx5120-32c")
    assert not ({"pps-out", "out-10m"} & (set(by_id(d, "front")) | set(by_id(d, "rear"))))


# --- the QFX5120-48T ---------------------------------------------------------

def test_48t_has_48_basest_jacks_numbered_0_to_47_in_four_blocks_of_six_columns():
    """Figure 26 and the photograph: the even port above the odd, six columns to a block, two blocks
    each side of the six QSFP28 ports; the jacks are the library's bare ganged Ethernet jack."""
    d = load_device("qfx5120-48t")
    jacks = {number(p["id"]): p for p in placements(d, "front") if ref_name(p["ref"]) == "rj45-ganged-eth-plain"}
    assert sorted(jacks) == list(range(48))
    assert all(p["group"] == "rj45" and p["rel-pos"] == n for n, p in jacks.items())
    for c in range(24):
        assert jacks[2 * c]["at"][1] < jacks[2 * c + 1]["at"][1]
    xs = [jacks[2 * c]["at"][0] for c in range(24)]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    within = [s for s in steps if s < 16]
    # 14.08 mm is measured from the photograph, not the maker's figure
    assert len(within) == 20 and all(s == pytest.approx(14.08, abs=0.1) for s in within)
    # the ports 0 to 23 are all left of the QSFP28 block, 24 to 47 all right of it
    qx = [p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-ganged"]
    assert max(jacks[n]["at"][0] for n in range(24)) < min(qx)
    assert min(jacks[n]["at"][0] for n in range(24, 48)) > max(qx)
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "10g"}


def test_48t_has_six_qsfp28_cages_48_to_53_in_three_columns_of_two():
    d = load_device("qfx5120-48t")
    cages = {number(p["id"]): p for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-ganged"}
    assert sorted(cages) == list(range(48, 54))
    assert all(p["group"] == "qsfp28" and p["rel-pos"] == n for n, p in cages.items())
    assert len({cages[n]["at"][0] for n in range(48, 54)}) == 3
    for n in (48, 50, 52):
        assert cages[n]["at"][1] < cages[n + 1]["at"][1]
        assert cages[n]["at"][0] == cages[n + 1]["at"][0]
    assert cages[50]["at"][0] - cages[48]["at"][0] == pytest.approx(19.6, abs=0.1)
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}


def test_48t_has_one_lamp_a_port_and_prints_every_numeral():
    """Tables 16 and 17: one lamp for each BASE-T port and each QSFP28 port."""
    d = load_device("qfx5120-48t")
    ids = {p["id"] for p in placements(d, "front") if ref_name(p["ref"]) in ("led-arrow-sm", "led-dot")}
    assert ids == {f"led-port-{n}" for n in range(54)}
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {str(n) for n in range(54)} <= printed


def test_48t_rear_has_one_management_jack_the_timing_ports_and_no_c0_c1():
    """Figure 27: one RJ-45 management port (MGMT), console, USB, PPS OUT and 10M OUT, the ESD point
    and the reset button. The 48Y prints C0 and C1 on two jacks; the 48T does not."""
    d = load_device("qfx5120-48t")
    r = by_id(d, "rear")
    assert ref_name(r["mgmt"]["ref"]) == "rj45-ganged-eth" and r["mgmt"]["attrs"]["role"] == "mgmt"
    assert ref_name(r["console"]["ref"]) == "rj45-ganged" and r["console"]["attrs"]["role"] == "console"
    assert ref_name(r["usb"]["ref"]) == "usb-a"
    assert ref_name(r["pps-out"]["ref"]) == ref_name(r["out-10m"]["ref"]) == "din-1-0-2-3-jack"
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "esd-rear-jack"} <= set(r)
    assert not ({"mgmt-c0", "mgmt-c1"} & set(r))
    printed = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON", "RESET", "PPS OUT", "10M OUT", "ALM", "SYS", "MST", "ID"} <= printed


# --- the parts the 32C and 48T seat, named by their part numbers -------------

REUSED = {
    "qfx5200-48y-apsu-ao": "QFX520048Y-APSU-AO", "qfx5200-48y-apsu-ai": "QFX520048Y-APSU-AI",
    "qfx5200-48y-dpsu-ao": "QFX520048Y-DPSU-AO", "qfx5200-48y-dpsu-ai": "QFX520048Y-DPSU-AI",
    "qfx5200-48y-fan-afo": "QFX520048Y-FAN-AO", "qfx5200-48y-fan-afi": "QFX520048Y-FAN-AI",
    "qfx5100-jpsu-650w-dc-afo": "JPSU-650W-DC-AFO", "qfx5100-jpsu-650w-dc-afi": "JPSU-650W-DC-AFI",
}


@pytest.mark.parametrize("part,model", sorted(REUSED.items()))
def test_a_reused_unit_carries_the_part_number_the_guide_names(part, model):
    """Tables 25 and 35 name these parts for the 32C and the 48T; the library already holds each,
    so this slice reuses it and does not add a second copy."""
    c = load_component(part)
    assert c["attrs"]["model"] == model
    assert c["kind"] == "module"


def test_this_slice_adds_no_component_the_library_already_has_by_part_number():
    """The 32C and 48T add no component: every part they seat resolves to a contract that exists."""
    for name in ("qfx5120-32c", "qfx5120-48t"):
        d = load_device(name)
        for b in bays(d, "rear"):
            for ref in b["accepts"]:
                assert (COMP / ref_name(ref) / "v1" / "contract.yaml").exists(), ref
