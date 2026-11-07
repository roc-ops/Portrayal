"""The Juniper QFX3500-48S4Q and QFX3600-16Q, from the two hardware guides (modified 2018-07-03).

One device per front panel. Each guide's airflow and bundle variants are configurations of the one
device: the guide draws one port side and one FRU side for them. The QFX3600-I Interconnect is not
here, because its front panel is drawn in a document this slice does not hold.

Both guides call the FRU side the front of a QFX3500 and the port side its rear, and the QFX3600
guide the reverse. The library puts the ports on the `front` face of both, as the QFX5100 does, so
these tests read ports on `front` and the supplies, fans and management board on `rear`.

What the guides fix, and so what these tests hold:
  QFX3500 Table 5     1.74 x 17.4 x 28 in, 1RU; Table 12 the three models and their airflow
  QFX3500 Table 13    the fan trays, management boards and supplies, with their airflow
  QFX3600 Table 5     1.74 x 16.9 x 19.3 in, 1RU; Table 11 the models; Table 12 the fan trays and supplies
  figure 7 / 5        the QFX3500 port side and its FRU side (48 SFP+ cages numbered 0 to 47, four QSFP+
                      cages Q0 to Q3; two supplies, two fan trays, the management board)
  figure 3 / 4        the QFX3600 port side (16 QSFP+ cages Q0 to Q15, two RJ-45 and two SFP management
                      ports, console, USB) and its FRU side (two supplies, three fan trays)
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 5 of each guide: height, width, depth in inches, without brackets or FRU handles (1RU)
ENVELOPE_IN = {
    "qfx3500-48s4q": {"h": 1.74, "w": 17.4, "d": 28.0},
    "qfx3600-16q": {"h": 1.74, "w": 16.9, "d": 19.3},
}
DEVICES = sorted(ENVELOPE_IN)
FAMILY = {"qfx3500-48s4q": "QFX3500", "qfx3600-16q": "QFX3600"}

PSU_AC = ("qfx5100-jpsu-650w-ac-afo", "qfx5100-jpsu-650w-ac-afi")
PSU_DC = ("qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi")
PSUS = set(PSU_AC + PSU_DC)
FANS = {
    "qfx3500-48s4q": {"qfx3500-fan-afo", "qfx3500-fanai"},
    "qfx3600-16q": {"qfx3600-qfxc01-fanbo", "qfx3600-qfxc01-fanbi"},
}
BOARDS = {"qfx3500-mb", "qfx3500-mb-rj45-afo", "qfx3500-mb-sfp-afi", "qfx3500-mb-sfp-afo"}
FAN_COUNT = {"qfx3500-48s4q": 2, "qfx3600-16q": 3}

# configuration -> (part number or None, supply, fan, board, airflow, feed, kind)
#   Table 12 of the QFX3500 guide names three models; Table 11 of the QFX3600 guide names two. No DC
#   chassis model is named by either guide, so a DC build is an illustration, not an orderable.
VARIANTS = {
    "qfx3500-48s4q": {
        "ac-f2b": ("QFX3500-48S4Q-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx3500-fan-afo", "qfx3500-mb-rj45-afo",
                   "front-to-back", "ac", "orderable"),
        "ac-b2f": ("QFX3500-48S4Q-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx3500-fanai", "qfx3500-mb",
                   "back-to-front", "ac", "orderable"),
        "ac-b2f-acr": ("QFX3500-48S4Q-ACR", "qfx5100-jpsu-650w-ac-afi", "qfx3500-fanai", "qfx3500-mb",
                       "back-to-front", "ac", "orderable"),
        "dc-f2b": (None, "qfx5100-jpsu-650w-dc-afo", "qfx3500-fan-afo", "qfx3500-mb-rj45-afo",
                   "front-to-back", "dc", "example"),
        "dc-b2f": (None, "qfx5100-jpsu-650w-dc-afi", "qfx3500-fanai", "qfx3500-mb",
                   "back-to-front", "dc", "example"),
    },
    "qfx3600-16q": {
        "ac-f2b": ("QFX3600-16Q-AFO", "qfx5100-jpsu-650w-ac-afo", "qfx3600-qfxc01-fanbo", None,
                   "front-to-back", "ac", "orderable"),
        "ac-b2f": ("QFX3600-16Q-AFI", "qfx5100-jpsu-650w-ac-afi", "qfx3600-qfxc01-fanbi", None,
                   "back-to-front", "ac", "orderable"),
        "dc-f2b": (None, "qfx5100-jpsu-650w-dc-afo", "qfx3600-qfxc01-fanbo", None,
                   "front-to-back", "dc", "example"),
        "dc-b2f": (None, "qfx5100-jpsu-650w-dc-afi", "qfx3600-qfxc01-fanbi", None,
                   "back-to-front", "dc", "example"),
    },
}
CASES = [(n, c) for n in sorted(VARIANTS) for c in VARIANTS[n]]
ORDERABLE = [(n, c) for n, c in CASES if VARIANTS[n][c][6] == "orderable"]

# the part number each component prints (guide tables 10 and 13 of the 3500, 12 of the 3600)
MODEL = {
    "qfx3500-fan-afo": "QFX3500-FAN-AFO", "qfx3500-fanai": "QFX3500-FANAI",
    "qfx3500-mb": "QFX3500-MB", "qfx3500-mb-rj45-afo": "QFX3500-MB-RJ45-AFO",
    "qfx3500-mb-sfp-afi": "QFX3500-MB-SFP-AFI", "qfx3500-mb-sfp-afo": "QFX3500-MB-SFP-AFO",
    "qfx3600-qfxc01-fanbo": "QFXC01-FANBO", "qfx3600-qfxc01-fanbi": "QFXC01-FANBI",
}
AIRFLOW = {
    "qfx3500-fan-afo": "front-to-back", "qfx3500-fanai": "back-to-front",
    "qfx3500-mb": "back-to-front", "qfx3500-mb-rj45-afo": "front-to-back",
    "qfx3500-mb-sfp-afi": "back-to-front", "qfx3500-mb-sfp-afo": "front-to-back",
    "qfx3600-qfxc01-fanbo": "front-to-back", "qfx3600-qfxc01-fanbi": "back-to-front",
}
NEW_PARTS = sorted(MODEL)


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
    return int(pid.split("-")[-1])


def silk_texts(dev, view):
    return {s["text"] for s in dev["views"][view].get("silkscreen", []) if "text" in s}


def of_ref(dev, view, *names):
    return [p for p in placements(dev, view) if ref_name(p["ref"]) in names]


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_5(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)


def test_the_qfx3600_is_a_narrower_and_shallower_box_than_the_qfx3500():
    """Table 5 of the two guides: 16.9 against 17.4 in wide, 19.3 against 28 in deep."""
    a, b = load_device("qfx3500-48s4q")["chassis"], load_device("qfx3600-16q")["chassis"]
    assert a["width"] - b["width"] == pytest.approx(0.5 * INCH, abs=0.1)
    assert a["depth"] - b["depth"] == pytest.approx(8.7 * INCH, abs=0.1)


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
    """The mounting brackets are not in Table 5's width, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_names_are_as_printed_and_the_portfolio_is_the_family(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": FAMILY[name]}
    assert d["chassis"]["airflow"] == "front-to-back"
    assert d["chassis"]["power"] == "ac"


# --- the ports, per face -----------------------------------------------------

def test_3500_has_48_sfp_plus_cages_and_4_qsfp_plus_cages_numbered_as_printed():
    """Figure 7: 0 to 47 on the access ports, Q0 to Q3 on the uplink ports."""
    d = load_device("qfx3500-48s4q")
    sfp, qsfp = of_ref(d, "front", "sfp-ganged"), of_ref(d, "front", "qsfp-ganged")
    assert sorted(number(p["id"]) for p in sfp) == list(range(48))
    assert {p["id"] for p in qsfp} == {f"uplink-{n}" for n in range(4)}
    printed = silk_texts(d, "front")
    assert {str(n) for n in range(48)} <= printed
    assert {f"Q{n}" for n in range(4)} <= printed
    assert not of_ref(d, "front", "rj45-ganged-eth-plain")


def test_3600_has_16_qsfp_plus_cages_numbered_q0_to_q15():
    """Figure 3: sixteen 40 Gbps ports, Q0 to Q15, the even ones on the upper row."""
    d = load_device("qfx3600-16q")
    qsfp = of_ref(d, "front", "qsfp-ganged")
    assert sorted(number(p["id"]) for p in qsfp) == list(range(16))
    assert {f"Q{n}" for n in range(16)} <= silk_texts(d, "front")
    assert not of_ref(d, "front", "sfp-ganged")[2:]
    y = {number(p["id"]): p["at"][1] for p in qsfp}
    assert all(y[2 * c] < y[2 * c + 1] for c in range(8))
    xs = sorted({p["at"][0] for p in qsfp})
    assert len(xs) == 8
    steps = {round(b - a, 2) for a, b in zip(xs, xs[1:])}
    assert steps == {33.47}, "eight columns on one pitch, wide enough for the lamps between them"


def test_3600_front_carries_the_four_management_ports_the_console_and_usb():
    """Figure 3 callouts 5 to 10: C1 and C0 (RJ-45), C0S and C1S (SFP), CON and USB."""
    d = load_device("qfx3600-16q")
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert {"mgmt-c0", "mgmt-c1", "mgmt-c0s", "mgmt-c1s", "console", "usb"} <= set(by_id)
    for pid in ("mgmt-c0", "mgmt-c1"):
        assert ref_name(by_id[pid]["ref"]) == "rj45-ganged-eth"
        assert by_id[pid]["attrs"]["speed"] == "1g"
    for pid in ("mgmt-c0s", "mgmt-c1s"):
        assert ref_name(by_id[pid]["ref"]) == "sfp-ganged"
        assert by_id[pid]["attrs"]["media"] == "sfp"
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert {"C0", "C1", "C0S", "C1S", "CON"} <= silk_texts(d, "front")


@pytest.mark.parametrize("name", DEVICES)
def test_the_groups_say_what_the_ports_are(name):
    g = load_device(name)["groups"]
    assert g["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert g["qsfp-plus"]["role"] == "traffic"
    if name == "qfx3500-48s4q":
        assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
        assert g["sfp-plus"]["role"] == "traffic"


def test_3500_access_ports_stand_in_six_blocks_of_four_columns_with_the_uplinks_between():
    """Figure 7: dotted dividers every four columns, the four QSFP+ cages between columns 11 and 12."""
    d = load_device("qfx3500-48s4q")
    sfp = of_ref(d, "front", "sfp-ganged")
    xs = sorted({p["at"][0] for p in sfp})
    assert len(xs) == 24
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 14.62) < 0.02]) == 18
    assert len([s for s in steps if 17.0 < s < 18.5]) == 4, "four gutters between the access blocks"
    assert len([s for s in steps if s > 70]) == 1, "the uplink block sits in one wide gap"
    uplinks = of_ref(d, "front", "qsfp-ganged")
    assert min(p["at"][0] for p in uplinks) > max(p["at"][0] for p in sfp if number(p["id"]) < 24)
    assert max(p["at"][0] for p in uplinks) < min(p["at"][0] for p in sfp if number(p["id"]) >= 24)
    y = {p["id"]: p["at"][1] for p in sfp + uplinks}
    assert all(y[f"port-{2 * c}"] < y[f"port-{2 * c + 1}"] for c in range(24)), "the even ports are above"
    assert all(y[f"uplink-{2 * c}"] < y[f"uplink-{2 * c + 1}"] for c in range(2))


def lamps(dev):
    return {p["id"]: p for p in placements(dev, "front") if ref_name(p["ref"]) == "led-dot"}


def test_3500_lamps_are_a_link_activity_and_a_status_lamp_each():
    """Tables 7 and 8, figures 8 and 9: two lamps on each access port and each uplink port."""
    ids = lamps(load_device("qfx3500-48s4q"))
    for n in range(48):
        assert f"led-port-{n}" in ids and f"led-port-{n}-status" in ids
        assert ids[f"led-port-{n}"]["for"] == f"port-{n}"
    for n in range(4):
        assert f"led-uplink-{n}" in ids and f"led-uplink-{n}-status" in ids
        assert ids[f"led-uplink-{n}-status"]["for"] == f"uplink-{n}"
    assert len(ids) == 2 * 52


def test_3600_lamps_are_a_link_activity_and_a_status_lamp_each_and_three_chassis_lamps():
    """Tables 7 to 9, figures 5 and 6: LA and ST by every port; Power, Status and Fan by the LCD."""
    ids = lamps(load_device("qfx3600-16q"))
    for n in range(16):
        assert f"led-port-{n}" in ids and f"led-port-{n}-status" in ids
        assert ids[f"led-port-{n}-status"]["for"] == f"port-{n}"
    chassis = {i for i, p in ids.items() if p["for"] == "chassis"}
    assert chassis == {"led-power", "led-status", "led-fan"}
    assert len(ids) == 2 * 16 + 3


def test_each_lamp_says_what_the_guide_says_it_means():
    for name in DEVICES:
        d = load_device(name)
        g = d["groups"]
        for key in ("sfp-plus-status-leds", "qsfp-plus-status-leds"):
            if key not in g:
                continue
            assert g[key]["role"] == "indicator"
        names = {s["name"] for gr in g.values() for s in gr.get("states", []) if isinstance(s, dict)}
        assert {"link", "activity"} <= names


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_says_the_model_and_leaves_the_logo_to_a_zone(name):
    d = load_device(name)
    views = [d["views"][v] for v in ("front", "rear")]
    texts = {s.get("text", "") for v in views for s in v.get("silkscreen", [])}
    texts |= {t.upper() for t in texts}
    assert not [t for t in texts if "JUNIPER" in t.upper() or "NETWORKS" in t.upper()]
    # the model name is printed on the management board (3500) or beside the LCD (3600)
    if name == "qfx3600-16q":
        assert d["model"] in texts
        assert [r["id"] for r in d["views"]["front"]["regions"]] == ["logo-zone"]
    else:
        for part in ("qfx3500-mb", "qfx3500-mb-rj45-afo", "qfx3500-mb-sfp-afi", "qfx3500-mb-sfp-afo"):
            svg = (COMP / part / "v1/skins/default.svg").read_text()
            assert f">{d['model']}</text>" in svg
            assert 'id="logo-zone"' in svg and "JUNIPER" not in svg.upper()


# --- the FRU side ------------------------------------------------------------

def test_3500_fru_side_has_two_supplies_two_fan_trays_and_the_management_board():
    """Figure 5: supply 0, fan tray 0, the management board, fan tray 1, supply 1."""
    b = {x["id"]: x for x in bays(load_device("qfx3500-48s4q"), "rear")}
    assert sorted(b) == ["fan-0", "fan-1", "mgmt-board", "psu-0", "psu-1"]
    order = sorted(b, key=lambda i: b[i]["at"][0])
    assert order == ["psu-0", "fan-0", "mgmt-board", "fan-1", "psu-1"]
    for i, x in b.items():
        assert x["default"]
    # the board centres between the trays and the whole row is symmetric about the chassis centre
    centre = load_device("qfx3500-48s4q")["chassis"]["width"] / 2
    for a, c in (("psu-0", "psu-1"), ("fan-0", "fan-1")):
        mid = (b[a]["at"][0] + b[c]["at"][0] + b[c]["size"]["w"]) / 2
        assert mid == pytest.approx(centre, abs=0.6)


def test_3600_fru_side_has_two_supplies_and_three_fan_trays_between_them():
    """Figure 4: supply 0, the grounding point, fan trays 0 to 2, supply 1."""
    d = load_device("qfx3600-16q")
    b = {x["id"]: x for x in bays(d, "rear")}
    assert sorted(b) == ["fan-0", "fan-1", "fan-2", "psu-0", "psu-1"]
    order = sorted(b, key=lambda i: b[i]["at"][0])
    assert order == ["psu-0", "fan-0", "fan-1", "fan-2", "psu-1"]
    stride = [b[f"fan-{n + 1}"]["at"][0] - b[f"fan-{n}"]["at"][0] for n in range(2)]
    assert stride[0] == pytest.approx(stride[1], abs=0.2), "three trays on one pitch"
    ground = [x for x in d["views"]["rear"]["panel"]["decor"] if x["id"] == "ground-plate"]
    assert len(ground) == 1
    assert b["psu-0"]["at"][0] + b["psu-0"]["size"]["w"] < ground[0]["at"][0] < b["fan-0"]["at"][0]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_model_the_guide_names_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name])
    for cid, (part, *_rest, kind) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == kind
        if part:
            assert set(cfgs[cid]["part-numbers"]) == {part}
        else:
            assert "part-numbers" not in cfgs[cid]


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
def test_each_configuration_seats_its_supply_fans_and_board_with_matching_airflow(name, cid):
    d = load_device(name)
    _part, psu, fan, board, airflow, feed, _kind = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(FAN_COUNT[name])} == {fan}
    if board:
        assert s["mgmt-board"] == board
    for comp in (psu, fan) + ((board,) if board else ()):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == feed


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        if b["id"].startswith("fan-"):
            assert got == FANS[name], b["id"]
        elif b["id"].startswith("psu-"):
            assert got == PSUS, b["id"]
        else:
            assert got == BOARDS, b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    for b in bays(load_device(name), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3)


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", NEW_PARTS)
def test_a_unit_is_named_for_its_family_and_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and part.startswith(("qfx3500-", "qfx3600-"))
    assert c["attrs"]["model"] == MODEL[part]
    assert c["kind"] == "module"
    assert c["attrs"]["airflow"] == AIRFLOW[part]
    assert c["attrs"]["power-absent"] == "not-published"


@pytest.mark.parametrize("part", NEW_PARTS)
def test_a_unit_is_described_as_the_unit_and_names_the_models_that_take_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "field-replaceable" in text
    assert ("QFX3500-48S4Q" if part.startswith("qfx3500") else "QFX3600-16Q") in text


@pytest.mark.parametrize("part", sorted(PSUS))
def test_the_supplies_are_the_650w_units_reused_from_the_qfx5100_by_part_number(part):
    """The three guides call one part number the same 650 W unit; the library holds it once."""
    c = load_component(part)
    assert c["attrs"]["model"] == "JPSU-650W-" + part.split("650w-")[1].upper()
    assert c["attrs"]["power-output-w"] == 650
    assert not (COMP / part.replace("qfx5100-", "qfx3500-")).exists()
    assert not (COMP / part.replace("qfx5100-", "qfx3600-")).exists()


def test_the_back_to_front_units_are_the_ones_the_guides_call_fru_to_port():
    """AFI is airflow in, FRU-to-port; AFO is airflow out, port-to-FRU (QFX3500 Table 12 note)."""
    fru_to_port = {"qfx3500-fanai", "qfx3500-mb", "qfx3500-mb-sfp-afi", "qfx3600-qfxc01-fanbi"}
    assert {p for p, flow in AIRFLOW.items() if flow == "back-to-front"} == fru_to_port
    assert {p for p, flow in AIRFLOW.items() if flow == "front-to-back"} == set(AIRFLOW) - fru_to_port


@pytest.mark.parametrize("part", [p for p in NEW_PARTS if "-mb" in p])
def test_a_management_board_carries_the_lamps_lcd_usb_console_and_two_management_ports(part):
    c = load_component(part)
    assert {"led-power", "led-status", "led-fan", "logo-zone"} <= set(c["elements"])
    parts = {p["id"]: p for p in c["parts"]}
    assert set(parts) == {"usb", "c0", "c1", "console"}
    assert ref_name(parts["usb"]["ref"]) == "usb-a"
    assert ref_name(parts["console"]["ref"]) == "rj45-ganged"
    want = "sfp-ganged" if "-sfp-" in part else "rj45-ganged-eth"
    assert ref_name(parts["c0"]["ref"]) == want and ref_name(parts["c1"]["ref"]) == want
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert 'id="lcd"' in svg and ">CON</text>" in svg and ">C0</text>" in svg and ">C1</text>" in svg


@pytest.mark.parametrize("part", [p for p in NEW_PARTS if "fan" in p])
def test_a_fan_tray_has_its_lamp_and_handle(part):
    c = load_component(part)
    assert {"led-fan", "handle"} <= set(c["elements"])
    assert c["class"] == "fan"


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid", ORDERABLE)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, cid):
    part = VARIANTS[name][cid][0]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_qfx3500_or_qfx3600_export_exists_and_none_for_an_example():
    for prefix, name in (("QFX3500-", "qfx3500-48s4q"), ("QFX3600-", "qfx3600-16q")):
        got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob(f"{prefix}*.yaml")}
        want = {v[0] for v in VARIANTS[name].values() if v[0]}
        assert got == want
