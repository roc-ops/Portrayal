"""The Juniper QFX5200-32C and QFX5200-48Y, from the QFX5200 Switch Hardware Guide (2026-03-09).

One device per front panel. The QFX5200-32C (32 QSFP28 ports, the management panel on the FRU side) and the
QFX5200-48Y (48 SFP28 and 6 QSFP28 ports, the management ports on the port side) are two devices. The 32C's
power and airflow variants, and the QFX5200-32C-L (the same panel running Junos OS Evolved), are configurations of
the 32C, because the guide shows one port panel and one FRU panel for them. Each field-replaceable unit is a
component named by its Juniper part number; the 850 W AC supplies of the 32C are the library's existing ones.

What the guide fixes, and so what these tests hold:
  Table 31   the envelope - 1.72 x 17.36 x 20.48 in (32C), 1.71 x 17.25 x 20.27 in (48Y), 1RU
  Table 3    the fan and supply part numbers, and the chassis models
  Table 17   the fan modules, their labels and colours, and the airflow of each
  Table 19   the AC supply part numbers and the colour that marks the airflow
  figures 14, 16, 19, 20, 26   the ports, their count and numbering, and what is on each face
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 31: height, width, depth in inches
ENVELOPE_IN = {
    "qfx5200-32c": {"h": 1.72, "w": 17.36, "d": 20.48},
    "qfx5200-48y": {"h": 1.71, "w": 17.25, "d": 20.27},
}
DEVICES = sorted(ENVELOPE_IN)

# configuration -> (part number or None, power feed, bay occupants, airflow)
# kind `orderable` carries the part number the guide names; kind `example` is a build the guide
# names the units of but gives no chassis part number for
VARIANTS = {
    "qfx5200-32c": {
        "ac-afo": ("orderable", "QFX5200-32C-AFO", "jpsu-850w-ac-afo", "qfx5200-32c-fan-afo", "front-to-back"),
        "ac-afi": ("orderable", "QFX5200-32C-AFI", "jpsu-850w-ac-afi", "qfx5200-32c-fan-afi", "back-to-front"),
        "dc-afo": ("orderable", "QFX5200-32C-DC", "qfx5200-jpsu-850w-dc-afo", "qfx5200-32c-fan-afo", "front-to-back"),
        "dc-afi": ("example", None, "qfx5200-jpsu-850w-dc-afi", "qfx5200-32c-fan-afi", "back-to-front"),
        "l-ac-afo": ("orderable", "QFX5200-32C-LAFO", "jpsu-850w-ac-afo", "qfx5200-32c-fan-afo", "front-to-back"),
        "l-ac-afi": ("orderable", "QFX5200-32C-LAFI", "jpsu-850w-ac-afi", "qfx5200-32c-fan-afi", "back-to-front"),
    },
    "qfx5200-48y": {
        "ac-afo": ("orderable", "QFX5200-48Y", "qfx5200-48y-apsu-ao", "qfx5200-48y-fan-afo", "front-to-back"),
        "ac-afi": ("example", None, "qfx5200-48y-apsu-ai", "qfx5200-48y-fan-afi", "back-to-front"),
        "dc-afo": ("example", None, "qfx5200-48y-dpsu-ao", "qfx5200-48y-fan-afo", "front-to-back"),
        "dc-afi": ("example", None, "qfx5200-48y-dpsu-ai", "qfx5200-48y-fan-afi", "back-to-front"),
    },
}
FAN_SLOTS = {"qfx5200-32c": 5, "qfx5200-48y": 6}
# the supplies and fan modules each device's bays accept, from Tables 3 and 17
ACCEPTS = {
    "qfx5200-32c": {
        "psu": {"jpsu-850w-ac-afo", "jpsu-850w-ac-afi", "qfx5200-jpsu-850w-dc-afo", "qfx5200-jpsu-850w-dc-afi"},
        "fan": {"qfx5200-32c-fan-afo", "qfx5200-32c-fan-afi"},
    },
    "qfx5200-48y": {
        "psu": {"qfx5200-48y-apsu-ao", "qfx5200-48y-apsu-ai", "qfx5200-48y-dpsu-ao", "qfx5200-48y-dpsu-ai"},
        "fan": {"qfx5200-48y-fan-afo", "qfx5200-48y-fan-afi"},
    },
}
# the part number each component is named by in the guide's Table 3 (the spare Juniper model number)
MODEL = {
    "jpsu-850w-ac-afo": "JPSU-850W-AC-AFO",
    "jpsu-850w-ac-afi": "JPSU-850W-AC-AFI",
    "qfx5200-jpsu-850w-dc-afo": "JPSU-850W-DC-AFO",
    "qfx5200-jpsu-850w-dc-afi": "JPSU-850W-DC-AFI",
    "qfx5200-32c-fan-afo": "QFX5200-32C-FANAFO",
    "qfx5200-32c-fan-afi": "QFX5200-32C-FANAFI",
    "qfx5200-48y-fan-afo": "QFX520048Y-FAN-AO",
    "qfx5200-48y-fan-afi": "QFX520048Y-FAN-AI",
    "qfx5200-48y-apsu-ao": "QFX520048Y-APSU-AO",
    "qfx5200-48y-apsu-ai": "QFX520048Y-APSU-AI",
    "qfx5200-48y-dpsu-ao": "QFX520048Y-DPSU-AO",
    "qfx5200-48y-dpsu-ai": "QFX520048Y-DPSU-AI",
}
# the supplies' rated output: the 32C's by the part number, the 48Y's by the guide's text and CLI names
PSU_WATTS = {"jpsu-850w-ac-afo": 850, "jpsu-850w-ac-afi": 850, "qfx5200-jpsu-850w-dc-afo": 850,
             "qfx5200-jpsu-850w-dc-afi": 850, "qfx5200-48y-apsu-ao": 650, "qfx5200-48y-apsu-ai": 650,
             "qfx5200-48y-dpsu-ao": 650, "qfx5200-48y-dpsu-ai": 650}
NEW_PARTS = sorted(p for p in MODEL if p.startswith("qfx5200-"))


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
def test_the_envelope_is_table_31(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == 1
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
    """The brackets extend the body to 19 in, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_is_named_and_filed_as_the_guide_names_it(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5200"}


# --- the ports, per face -----------------------------------------------------

def cages(dev, kind):
    return [p for p in placements(dev, "front") if ref_name(p["ref"]) == kind]


def test_32c_has_32_qsfp28_cages_numbered_0_to_31_on_the_port_side():
    d = load_device("qfx5200-32c")
    q = cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in q) == list(range(32))
    assert not cages(d, "sfp-ganged")
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(32)} <= printed


def test_32c_ports_sit_in_two_rows_even_above_odd_in_four_gangs_of_four_columns():
    q = {number(p["id"]): p for p in cages(load_device("qfx5200-32c"), "qsfp-ganged")}
    assert all(q[2 * c]["at"][1] < q[2 * c + 1]["at"][1] for c in range(16))
    assert all(q[2 * c]["at"][0] == q[2 * c + 1]["at"][0] for c in range(16))
    xs = [q[2 * c]["at"][0] for c in range(16)]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(19.0) == 12, "a 19.0 mm pitch inside each gang of four"
    assert [s for s in steps if s != 19.0] == [25.0, 25.0, 25.0], "6.0 mm gutters between the gangs"
    # the lower row is turned 180 (the library's stack convention), the upper row is not
    assert all(q[2 * c + 1].get("rotate") == 180 and not q[2 * c].get("rotate") for c in range(16))


def test_32c_has_four_lamps_a_port_as_figure_15_draws_them():
    ids = {p["id"] for p in placements(load_device("qfx5200-32c"), "front") if ref_name(p["ref"]) == "led-dot"}
    for n in range(32):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= ids
    assert len(ids) == 128


def test_32c_has_the_clock_jack_and_two_clock_outputs_at_the_left():
    by_id = {p["id"]: p for p in placements(load_device("qfx5200-32c"), "front")}
    assert ref_name(by_id["gm"]["ref"]) == "rj45"
    assert ref_name(by_id["pps-out"]["ref"]) == ref_name(by_id["out-10m"]["ref"]) == "sma"
    assert max(by_id[i]["at"][0] for i in ("gm", "pps-out", "out-10m")) < min(
        p["at"][0] for p in cages(load_device("qfx5200-32c"), "qsfp-ganged"))
    assert ref_name(by_id["esd-front-jack"]["ref"]) == "esd-jack"
    assert by_id["esd-front-jack"]["at"][0] > 400


def test_48y_has_48_sfp28_and_6_qsfp28_cages_numbered_0_to_53():
    d = load_device("qfx5200-48y")
    assert sorted(number(p["id"]) for p in cages(d, "sfp-ganged")) == list(range(48))
    assert sorted(number(p["id"]) for p in cages(d, "qsfp-ganged")) == list(range(48, 54))
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(54)} <= printed


def test_48y_sfp28_ports_sit_in_two_rows_in_three_gangs_of_eight_columns():
    d = load_device("qfx5200-48y")
    s = {number(p["id"]): p for p in cages(d, "sfp-ganged")}
    assert all(s[2 * c]["at"][1] < s[2 * c + 1]["at"][1] for c in range(24))
    xs = sorted({p["at"][0] for p in s.values()})
    assert len(xs) == 24
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(14.25) == 21 and len([x for x in steps if x != 14.25]) == 2
    q = [p["at"][0] for p in cages(d, "qsfp-ganged")]
    assert min(q) > max(xs)


def test_48y_qsfp28_ports_are_two_columns_of_three_cages():
    q = {number(p["id"]): p for p in cages(load_device("qfx5200-48y"), "qsfp-ganged")}
    # left column 48, 49, 50 and right column 51, 52, 53, top to bottom
    assert q[48]["at"][0] == q[49]["at"][0] == q[50]["at"][0] < q[51]["at"][0] == q[52]["at"][0] == q[53]["at"][0]
    assert q[48]["at"][1] < q[49]["at"][1] < q[50]["at"][1]
    assert q[51]["at"][1] < q[52]["at"][1] < q[53]["at"][1]


def test_48y_has_a_lamp_a_sfp28_port_from_port_5_and_five_chassis_lamps_in_place_of_the_first_five():
    """The photograph prints PS0, PS1, Diag, Fan and Loc under the first five lamps (Table 16)."""
    ids = {p["id"] for p in placements(load_device("qfx5200-48y"), "front") if ref_name(p["ref"]).startswith("led-")}
    assert {f"led-port-{n}" for n in range(5, 48)} <= ids
    assert not ({f"led-port-{n}" for n in range(5)} & ids)
    assert {"led-ps0", "led-ps1", "led-diag", "led-fan", "led-loc"} <= ids


def test_48y_management_ports_are_on_the_port_side_and_the_rear_carries_none():
    d = load_device("qfx5200-48y")
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-ganged-eth"
    assert by_id["mgmt"]["attrs"]["speed"] == "1g"
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert by_id["mgmt"]["at"][1] < by_id["console"]["at"][1], "Mgmt above Console, as printed"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert "reset-btn" in by_id
    assert not [p for p in placements(d, "rear") if ref_name(p["ref"]) in ("rj45", "rj45-eth", "usb-a")]


def test_32c_management_panel_is_on_the_fru_side():
    d = load_device("qfx5200-32c")
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert ref_name(by_id["console"]["ref"]) == "rj45"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt-c0"]["ref"]) == "rj45-eth"
    assert by_id["mgmt-c0"]["attrs"]["speed"] == "1g"
    for cage in ("mgmt-sfp-c0", "mgmt-sfp-c1"):
        assert ref_name(by_id[cage]["ref"]) == "sfp"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn"} <= set(by_id)
    assert max(by_id[i]["at"][0] for i in by_id if i.startswith(("mgmt", "console", "usb", "led-alm"))) < 70


@pytest.mark.parametrize("name", DEVICES)
def test_the_fan_and_supply_slots_are_numbered_as_the_guide_numbers_them(name):
    """Fan modules 0 to 4 (32C) or 0 to 5 (48Y), supplies 0 and 1, left to right."""
    d = load_device(name)
    b = {x["id"]: x for x in bays(d, "rear")}
    n = FAN_SLOTS[name]
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{k}" for k in range(n)]
    xs = [b[f]["at"][0] for f in fans]
    assert xs == sorted(xs)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["fan-0"]["at"][0] if name == "qfx5200-48y" else True
    assert b["psu-1"]["at"][0] > b[f"fan-{n - 1}"]["at"][0]


def test_the_48y_has_a_supply_at_each_end_and_the_32c_has_both_at_the_right():
    y = {x["id"]: x["at"][0] for x in bays(load_device("qfx5200-48y"), "rear")}
    assert y["psu-0"] < y["fan-0"] and y["psu-1"] > y["fan-5"]
    c = {x["id"]: x["at"][0] for x in bays(load_device("qfx5200-32c"), "rear")}
    assert c["psu-0"] > c["fan-4"] and c["psu-1"] > c["psu-0"]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_configuration_is_the_kind_the_guide_supports(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name])
    for cid, (kind, part, *_rest) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == kind
        if kind == "orderable":
            assert set(cfgs[cid]["part-numbers"]) == {part}
        else:
            assert not cfgs[cid].get("part-numbers")


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-afo"]


def seated(dev, cid):
    """bay id -> component name, as the configuration leaves it (default where unstated)."""
    cfg = dev["configurations"][cid]
    return {b["id"]: ref_name((cfg.get("bays") or {}).get(b["id"], b.get("default"))) for b in bays(dev, "rear")}


CASES = [(n, c) for n in DEVICES for c in VARIANTS[n]]


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    _kind, _part, psu, fan, airflow = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{k}"] for k in range(FAN_SLOTS[name])} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    cfg_airflow = d["configurations"][cid].get("airflow", d["chassis"]["airflow"])
    assert cfg_airflow == airflow


@pytest.mark.parametrize("name,cid", CASES)
def test_the_power_feed_follows_the_supplies_seated(name, cid):
    d = load_device(name)
    psu = VARIANTS[name][cid][2]
    feed = "dc" if "dc" in psu.split("-") or "dpsu" in psu else "ac"
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == feed
    assert load_component(psu)["attrs"]["role"] == f"{feed}-power-supply"


def test_the_32c_l_is_ac_only_and_marks_the_second_management_interface_unsupported():
    d = load_device("qfx5200-32c")
    for cid in ("l-ac-afo", "l-ac-afi"):
        cfg = d["configurations"][cid]
        assert cfg.get("power", d["chassis"]["power"]) == "ac"
        assert "not supported" in cfg["component-attrs"]["mgmt-sfp-c1"]["support"]
    assert "component-attrs" not in d["configurations"]["ac-afo"]


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        want = ACCEPTS[name]["fan"] if b["id"].startswith("fan-") else ACCEPTS[name]["psu"]
        assert got == want, b["id"]
        assert ref_name(b["default"]) in got
        assert all(r.startswith("juniper/") for r in b["accepts"])


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    d = load_device(name)
    for b in bays(d, "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), ref
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), ref


def test_the_32c_reuses_the_existing_850_w_ac_supplies_and_does_not_copy_them():
    """Same part number, same arrangement; the library's own components are seated as they are."""
    for part in ("jpsu-850w-ac-afo", "jpsu-850w-ac-afi"):
        assert load_component(part)["attrs"]["model"] == MODEL[part]
    assert not (COMP / "qfx5200-jpsu-850w-ac-afo").exists()
    assert not (COMP / "qfx5200-jpsu-850w-ac-afi").exists()


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", sorted(MODEL))
def test_a_unit_is_named_by_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part
    assert c["attrs"]["model"] == MODEL[part]
    assert c["kind"] == "module"
    assert "field-replaceable" in " ".join(c["description"].split())


@pytest.mark.parametrize("part", NEW_PARTS)
def test_a_new_component_carries_the_family_prefix_and_its_own_skin(part):
    assert part.startswith("qfx5200-")
    assert (COMP / part / "v1" / "skins" / "default.svg").exists()


@pytest.mark.parametrize("part,watts", sorted(PSU_WATTS.items()))
def test_a_supply_states_the_power_it_provides_as_an_output(part, watts):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == watts
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("part", [p for p in MODEL if "fan" in p])
def test_a_fan_module_says_its_power_is_not_published(part):
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("front,back", [
    ("qfx5200-32c-fan-afo", "qfx5200-32c-fan-afi"),
    ("qfx5200-48y-fan-afo", "qfx5200-48y-fan-afi"),
    ("qfx5200-48y-apsu-ao", "qfx5200-48y-apsu-ai"),
    ("qfx5200-48y-dpsu-ao", "qfx5200-48y-dpsu-ai"),
    ("qfx5200-jpsu-850w-dc-afo", "qfx5200-jpsu-850w-dc-afi"),
])
def test_the_back_to_front_unit_is_blue_and_the_front_to_back_one_is_not(front, back):
    """Tables 17 and 19: Juniper Gold or red for airflow out, Juniper Azure Blue or blue for airflow in."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle(front), handle(back)
    assert f != b
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    r, g, bl = (int(f[i:i + 2], 16) for i in (1, 3, 5))
    assert not (bl > r and bl > g)
    assert load_component(front)["attrs"]["airflow"] == "front-to-back"
    assert load_component(back)["attrs"]["airflow"] == "back-to-front"


def test_the_fan_modules_print_the_guides_airflow_labels():
    """Table 17: AIR OUT and AIR IN on the 32C modules; the 48Y front-to-back module prints F2B on the photograph."""
    def svg(part):
        return (COMP / part / "v1/skins/default.svg").read_text()
    assert ">OUT</text>" in svg("qfx5200-32c-fan-afo") and ">IN</text>" in svg("qfx5200-32c-fan-afi")
    assert ">F2B</text>" in svg("qfx5200-48y-fan-afo")
    assert ">AIR IN</text>" in svg("qfx5200-48y-fan-afi")


def test_the_48y_supplies_are_not_the_qfx5120_ones():
    """Different part numbers and a different face (one lamp, not three): no reuse by name."""
    c = load_component("qfx5200-48y-apsu-ao")
    assert {e for e in c["elements"] if e.startswith("led")} == {"led"}
    assert c["attrs"]["model"] != load_component("jpsu-650w-ac-ao")["attrs"]["model"]


# --- the DCIM export ---------------------------------------------------------

ORDERABLE = [(n, v[1]) for n in DEVICES for v in VARIANTS[n].values() if v[0] == "orderable"]


@pytest.mark.parametrize("name,part", ORDERABLE)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_juniper_qfx5200_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5200-*.yaml")}
    assert got == {part for _n, part in ORDERABLE}
