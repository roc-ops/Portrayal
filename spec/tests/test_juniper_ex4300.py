"""The Juniper EX4300 1G copper switches: EX4300-24T, -24P, -48T and -48P (#39), and, below them,
the 32-port fibre EX4300-32F and the multigigabit EX4300-48MP, each with its own front panel.

One device per front panel, each with its power, airflow and spare-chassis builds as
`kind: orderable` configurations. The expected figures below are the hardware guide's
(EX4300 Switch Hardware Guide, published 2025-08-12): Table 10 for the envelope, Tables 1, 3
and 8 for what each model ships with, Tables 27, 28, 30, 31, 47 and 48 for the field-replaceable
units and their airflow, and the datasheet's Table 2 for the spare chassis. Each test reads the
YAML a contributor edits, or the generated export a DCIM user imports; none reads a table the
exporter holds, because a table that says so proves nothing about the file.
"""
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INCH = 25.4

# the units the guide lists, by component name: part number, output watts, airflow, feed
PSUS = {
    "ex4300-jpsu-350-ac-afo": ("JPSU-350-AC-AFO-A", 350, "front-to-back", "ac"),
    "ex4300-jpsu-350-ac-afi": ("JPSU-350-AC-AFI-A", 350, "back-to-front", "ac"),
    "ex4300-jpsu-715-ac-afo": ("JPSU-715-AC-AFO-A", 715, "front-to-back", "ac"),
    "ex4300-jpsu-1100-ac-afo": ("JPSU-1100-AC-AFO-A", 1100, "front-to-back", "ac"),
    "ex4300-jpsu-550-dc-afo": ("JPSU-550-DC-AFO-A", 550, "front-to-back", "dc"),
    "ex4300-jpsu-550-dc-afi": ("JPSU-550-DC-AFI-A", 550, "back-to-front", "dc"),
}
FANS = {
    "ex4300-fan-afo": ("EX4300-FAN", "front-to-back"),
    "ex4300-fan-afi": ("EX4300-FAN-AFI", "back-to-front"),
}
BLANKS = ["ex4300-psu-blank", "ex4300-uplink-blank"]

# device: (model, built-in jacks, PoE+, the supply it ships with, configurations -> part numbers)
DEVICES = {
    "ex4300-24t": ("EX4300-24T", 24, False, "ex4300-jpsu-350-ac-afo",
                   {"ac": ["EX4300-24T"], "s": ["EX4300-24T-S"]}),
    "ex4300-24p": ("EX4300-24P", 24, True, "ex4300-jpsu-715-ac-afo",
                   {"ac": ["EX4300-24P"], "s": ["EX4300-24P-S"]}),
    "ex4300-48t": ("EX4300-48T", 48, False, "ex4300-jpsu-350-ac-afo",
                   {"ac": ["EX4300-48T"], "afi": ["EX4300-48T-AFI"], "dc": ["EX4300-48T-DC"],
                    "dc-afi": ["EX4300-48T-DC-AFI"], "s": ["EX4300-48T-S"]}),
    "ex4300-48p": ("EX4300-48P", 48, True, "ex4300-jpsu-1100-ac-afo",
                   {"ac": ["EX4300-48P"], "s": ["EX4300-48P-S"]}),
}
# what each non-spare build seats: (supply, fan, airflow, feed)
BUILDS = {
    "ac": ("default", "ex4300-fan-afo", "front-to-back", "ac"),
    "afi": ("ex4300-jpsu-350-ac-afi", "ex4300-fan-afi", "back-to-front", "ac"),
    "dc": ("ex4300-jpsu-550-dc-afo", "ex4300-fan-afo", "front-to-back", "dc"),
    "dc-afi": ("ex4300-jpsu-550-dc-afi", "ex4300-fan-afi", "back-to-front", "dc"),
}


def load(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load(
        (LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def name_of(ref):
    return ref.split("/")[1].split("@")[0]


def seated(d, cfg):
    """Bay id -> the component name seated in that configuration, '' for an open bay."""
    out = {}
    for view in ("front", "rear"):
        for bid, b in bays(d, view).items():
            out[bid] = name_of(b["default"]) if b.get("default") else ""
    for bid, ref in ((d["configurations"][cfg].get("bays")) or {}).items():
        out[bid] = name_of(ref) if ref else ""
    return out


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("dev", DEVICES)
def test_the_envelope_is_table_10(dev):
    """Table 10: 1.72 in high, 17.36 in wide (the 19 in figure is over the brackets), 17.51 in
    deep with a power supply fitted, one rack unit."""
    c = load(dev)["chassis"]
    assert c["ru"] == 1
    assert c["height"] == pytest.approx(1.72 * INCH, abs=0.1)
    assert c["width"] == pytest.approx(17.36 * INCH, abs=0.2)
    assert c["depth"] == pytest.approx(44.47 * 10, abs=0.2)
    assert c["depth"] == pytest.approx(17.51 * INCH, abs=0.2)


@pytest.mark.parametrize("dev", DEVICES)
def test_every_face_is_sized_from_the_envelope(dev):
    d = load(dev)
    c = d["chassis"]
    for v in ("front", "rear"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["height"]}
    for v in ("top", "bottom"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["depth"]}
    for v in ("left", "right"):
        assert d["views"][v]["size"] == {"w": c["depth"], "h": c["height"]}


@pytest.mark.parametrize("dev", DEVICES)
def test_the_maker_and_the_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == DEVICES[dev][0]
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4300"}
    assert d["maturity"] == "modelled"


# ------------------------------------------------------------------ the faces


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_has_the_jacks_the_guide_counts_numbered_as_printed(dev):
    _, n, poe, *_ = DEVICES[dev]
    d = load(dev)
    jacks = [p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth@1"]
    assert sorted(int(p["id"].split("-")[1]) for p in jacks) == list(range(n))
    for p in jacks:
        k = int(p["id"].split("-")[1])
        assert p["rel-pos"] == k and p["group"] == "rj45"
        # numbering runs down each column: the even number is the upper jack, turned 180
        assert p.get("rotate", 0) == (180 if k % 2 == 0 else 0)
    group = d["groups"]["rj45"]
    assert group["attrs"]["media"] == "rj45" and group["attrs"]["speed"] == "1g"
    assert ("poe" in group["attrs"]) is poe
    # the printed numbers: one numeral per jack, spelled as the metal spells it
    numerals = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
                if s.get("for", "").startswith("port-")}
    assert numerals == {f"port-{k}": str(k) for k in range(n)}
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert {f"port-{k}" for k in range(n)} <= cut


@pytest.mark.parametrize("dev", DEVICES)
def test_the_jacks_stand_in_columns_of_six_on_the_registry_pitch(dev):
    _, n, *_ = DEVICES[dev]
    d = load(dev)
    top = {int(p["id"].split("-")[1]): p["at"] for p in placements(d, "front")
           if p["ref"] == "common/rj45-ganged-eth@1" and p.get("rotate") == 180}
    xs = [top[k][0] for k in sorted(top)]
    assert len(xs) == n // 2
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    # 13.97 within a block of six columns; wider between blocks
    assert steps.count(13.97) == n // 2 - n // 12
    assert all(s > 13.97 for s in steps if s != 13.97)


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_carries_the_console_lcd_buttons_lamps_and_the_uplink_slot(dev):
    d = load(dev)
    ids = {p["id"]: p["ref"] for p in placements(d, "front")}
    assert ids["console"] == "juniper/ex4300-console-usb-mini@1"
    assert ids["btn-menu"] == ids["btn-enter"] == "juniper/ex4300-lcd-button@1"
    for lamp in ("led-alm", "led-sys", "led-mst"):
        assert ids[lamp] == "common/led-dot@1"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"]}
    assert {"EX4300", "CON1"} <= legends
    # the photograph prints no legend by the chassis lamps; the guide's names are not invented
    assert not legends & {"ALM", "SYS", "MST"}
    slot = bays(d, "front")["uplink"]
    assert slot["accepts"] == ["juniper/ex4300-uplink-blank@1"]
    assert slot["default"] == "juniper/ex4300-uplink-blank@1"


@pytest.mark.parametrize("dev", DEVICES)
def test_the_rear_has_four_qsfp_ports_the_management_jacks_and_four_bays(dev):
    d = load(dev)
    rear = {p["id"]: p for p in placements(d, "rear")}
    for k in range(4):
        assert rear[f"vcp-{k}"]["ref"] == "std/qsfp-ganged@1"
        assert rear[f"vcp-{k}"]["rel-pos"] == k
        assert rear[f"led-vcp-{k}-a"]["for"] == rear[f"led-vcp-{k}-b"]["for"] == f"vcp-{k}"
    assert rear["mgmt"]["ref"] == "common/rj45-eth@1"
    assert rear["con2"]["ref"] == "std/rj45@2"
    assert rear["usb"]["ref"] == "std/usb-a@1"
    assert set(bays(d, "rear")) == {"fan-0", "fan-1", "psu-0", "psu-1"}
    assert d["groups"]["vcp"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert d["groups"]["fans"]["attrs"]["redundancy"] == "n+0"


# ------------------------------------------------- the field-replaceable units


@pytest.mark.parametrize("comp", sorted(PSUS))
def test_a_power_supply_states_its_part_number_output_and_airflow(comp):
    pn, watts, flow, feed = PSUS[comp]
    c = contract(comp)
    assert c["class"] == "psu" and c["kind"] == "module"
    assert c["attrs"]["part-number"] == pn
    assert c["attrs"]["power-output-w"] == watts
    assert c["attrs"]["airflow"] == flow
    assert c["attrs"]["airflow-label"] == ("AIR OUT (AFO)" if flow == "front-to-back"
                                           else "AIR IN (AFI)")
    if feed == "dc":
        assert c["attrs"]["inlet"] == "dc-terminal"
    else:
        assert any(p["ref"] == "std/c14-inlet@1" for p in c["parts"])
    # the guide's Tables 30 and 47: every supply weighs 2.43 lb
    assert c["attrs"]["weight-kg"] == 1.1


@pytest.mark.parametrize("comp", sorted(FANS))
def test_a_fan_module_states_its_part_number_and_airflow(comp):
    pn, flow = FANS[comp]
    c = contract(comp)
    assert c["class"] == "fan" and c["attrs"]["part-number"] == pn
    assert c["attrs"]["airflow"] == flow


@pytest.mark.parametrize("dev", DEVICES)
def test_the_bays_accept_what_the_guide_lists(dev):
    d = load(dev)
    psus = {f"juniper/{c}@1" for c in PSUS} | {"juniper/ex4300-psu-blank@1"}
    fans = {f"juniper/{c}@1" for c in FANS}
    for bid in ("psu-0", "psu-1"):
        assert set(bays(d, "rear")[bid]["accepts"]) == psus
    for bid in ("fan-0", "fan-1"):
        assert set(bays(d, "rear")[bid]["accepts"]) == fans


@pytest.mark.parametrize("dev", DEVICES)
def test_the_default_build_ships_what_the_guide_says(dev):
    """Tables 1, 3 and 8: one supply, a cover panel over the other slot, two AIR OUT fans."""
    _, _, _, psu, _ = DEVICES[dev]
    d = load(dev)
    s = seated(d, "ac")
    assert s == {"uplink": "ex4300-uplink-blank", "psu-0": psu, "psu-1": "ex4300-psu-blank",
                 "fan-0": "ex4300-fan-afo", "fan-1": "ex4300-fan-afo"}


# ------------------------------------------------------------- configurations


@pytest.mark.parametrize("dev", DEVICES)
def test_each_configuration_lists_its_part_numbers(dev):
    d = load(dev)
    want = DEVICES[dev][4]
    assert set(d["configurations"]) == set(want)
    for cfg, pns in want.items():
        got = d["configurations"][cfg]
        assert got["kind"] == "orderable"
        assert list(got["part-numbers"]) == pns
    defaults = [c for c, v in d["configurations"].items() if v.get("default")]
    assert defaults == ["ac"]


@pytest.mark.parametrize("dev", DEVICES)
def test_a_built_configuration_seats_a_matching_set(dev):
    """The guide's caution (Tables 27, 28): never mix AIR IN and AIR OUT parts, never mix AC
    and DC. Every build seats a supply and two fans whose airflow and feed agree with the build's."""
    d = load(dev)
    for cfg in DEVICES[dev][4]:
        if cfg == "s":
            continue
        supply, fan, flow, feed = BUILDS[cfg]
        s = seated(d, cfg)
        if supply == "default":
            supply = DEVICES[dev][3]
        assert s["psu-0"] == supply and s["fan-0"] == s["fan-1"] == fan
        c = d["configurations"][cfg]
        assert c.get("airflow", d["chassis"]["airflow"]) == flow
        assert c.get("power", d["chassis"]["power"]) == feed
        assert contract(supply)["attrs"]["airflow"] == flow == contract(fan)["attrs"]["airflow"]
        assert PSUS[supply][3] == feed
        # the cover panel keeps the empty slot closed
        assert s["psu-1"] == "ex4300-psu-blank"


@pytest.mark.parametrize("dev", DEVICES)
def test_the_spare_chassis_shows_its_bays_open(dev):
    d = load(dev)
    s = seated(d, "s")
    assert s["psu-0"] == s["psu-1"] == s["fan-0"] == s["fan-1"] == ""
    assert s["uplink"] == "ex4300-uplink-blank"


def test_only_the_48t_has_airflow_and_dc_builds():
    """Tables 1, 3 and 8 list AFI and DC builds for the 48T alone among these four panels."""
    for dev in ("ex4300-24t", "ex4300-24p", "ex4300-48p"):
        assert set(load(dev)["configurations"]) == {"ac", "s"}
    d = load("ex4300-48t")
    assert d["configurations"]["afi"]["airflow"] == "back-to-front"
    assert d["configurations"]["dc"]["power"] == "dc"
    assert d["configurations"]["dc-afi"]["power"] == "dc"
    assert d["configurations"]["dc-afi"]["airflow"] == "back-to-front"


# ------------------------------------------------------------------- the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", DEVICES)
def test_the_dcim_types_export_one_per_orderable_configuration(target, dev):
    d = load(dev)
    want = {pn for v in d["configurations"].values() if v["kind"] == "orderable"
            for pn in v["part-numbers"]}
    folder = LIB / "exports" / target / "device-types" / "Juniper"
    got = {p.stem for p in folder.glob("EX4300-*.yaml")
           if p.stem == DEVICES[dev][0] or p.stem.startswith(DEVICES[dev][0] + "-")}
    # EX4300-48T-S must not be taken for a 48T family member's sibling, so compare exactly
    assert want <= got
    for pn in want:
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == pn
        assert doc["u_height"] == 1.0


@pytest.mark.parametrize("dev", DEVICES)
def test_the_exported_type_lists_the_jacks_and_the_qsfp_ports(dev):
    _, n, *_ = DEVICES[dev]
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Juniper" / f"{DEVICES[dev][0]}.yaml").read_text())
    names = {i["name"] for i in doc["interfaces"]}
    assert {f"port-{k}" for k in range(n)} <= names
    assert {f"vcp-{k}" for k in range(4)} <= names
    assert not {f"port-{k}" for k in range(n, 48)} & names


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", DEVICES)
def test_the_exported_type_lists_both_consoles(target, dev):
    """CON1 on the front is a mini-USB console and CON2 on the rear an RJ-45 one."""
    doc = yaml.safe_load(
        (LIB / "exports" / target / "device-types/Juniper" / f"{DEVICES[dev][0]}.yaml").read_text())
    consoles = {(c["name"], c["type"]) for c in doc["console-ports"]}
    assert consoles == {("Console (mini-USB)", "usb-mini-b"), ("Console", "rj-45")}


# ------------------------------------------------------------- the components


def test_the_new_components_are_family_prefixed():
    """This slice adds no shared Juniper EX/QFX component: every juniper/ part its devices
    place or seat is the EX4300's own."""
    refs = set()
    for dev in DEVICES:
        d = load(dev)
        for view in ("front", "rear"):
            for p in placements(d, view):
                refs.add(p["ref"])
            for b in bays(d, view).values():
                refs.update(b["accepts"])
    mine = {r for r in refs if r.startswith("juniper/")}
    assert mine and all(r.startswith("juniper/ex4300-") for r in mine)


@pytest.mark.parametrize("comp", sorted(PSUS) + sorted(FANS) + BLANKS +
                         ["ex4300-console-usb-mini", "ex4300-lcd-button"])
def test_each_component_states_where_its_size_came_from(comp):
    c = contract(comp)
    assert c["size-confidence"]
    assert all(isinstance(v, str) for v in c["provenance"].values())


# ------------------------------------------------- review fixes: logo, DC face, airflow label


def skin(comp):
    text = (LIB / "components/juniper" / comp / "v1/skins/default.svg").read_text()
    return ET.fromstring(text.replace(' xmlns="http://www.w3.org/2000/svg"', "", 1))


def nums(s):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", s)]


@pytest.mark.parametrize("dev", DEVICES)
def test_no_face_draws_the_vendor_logo_and_the_front_reserves_its_place(dev):
    """A vendor logo is never drawn; the front holds a logo-zone over where the mark sits, and the
    plain EX4300 legend stays."""
    d = load(dev)
    for name, view in d["views"].items():
        drawn = [i for k in ("silkscreen",) for i in view.get(k) or []]
        drawn += (view.get("panel") or {}).get("decor") or []
        words = {str(i.get("text", "")).upper() for i in drawn}
        assert not words & {"JUNIPER", "NETWORKS"}, name
    front = d["views"]["front"]
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1
    z = zones[0]
    x, y = z["at"]
    # the mark in the 24T photograph: about 6.5 to 29.6 mm across, 1.5 to 8.1 mm down
    assert 5.5 <= x <= 7.5 and 1.0 <= y <= 2.5
    assert 22.0 <= z["size"]["w"] <= 24.5 and 5.5 <= z["size"]["h"] <= 7.5
    assert x + z["size"]["w"] <= 29.8 and y + z["size"]["h"] <= 10.3
    assert "not drawn" in z["label"]
    assert "EX4300" in {s.get("text") for s in front["silkscreen"]}


DC_SUPPLIES = ["ex4300-jpsu-550-dc-afo", "ex4300-jpsu-550-dc-afi"]


@pytest.mark.parametrize("comp", DC_SUPPLIES)
def test_the_dc_supply_has_the_five_terminals_figure_45_prints(comp):
    """Figure 45 (g022081): a five-way block printed + - earth - +."""
    root = skin(comp)
    block = root.find(".//g[@id='terminal-block']")
    screws = block.findall(".//circle[@class='terminal']")
    assert len(screws) == 5
    xs = [float(c.get("cx")) for c in screws]
    assert xs == sorted(xs)
    marks = [(float(t.get("x")), t.text) for t in root.iter("text")
             if t.get("class") == "polarity"]
    earth = block.find("g[@id='earth']")
    marks.append((nums(earth.get("transform"))[0], "earth"))
    marks.sort()
    assert [m for _, m in marks] == ["+", "−", "earth", "−", "+"]
    for (mx, _), sx in zip(marks, xs):
        assert abs(mx - sx) < 0.5
    pitch = [b - a for a, b in zip(xs, xs[1:])]
    assert max(pitch) - min(pitch) < 0.5
    c = contract(comp)
    assert c["elements"]["terminal-block"]["size"][0] > 40.0
    prov = " ".join(c["provenance"].values()) + c["description"]
    assert "Figure 45" in prov and "five" in prov
    for stale in ("no DC rear drawing", "four screw terminals", "four-way", "not legible"):
        assert stale not in prov


def _text_box(t):
    fs = float(t.get("font-size"))
    w = 0.62 * fs * len(t.text) * (1.08 if t.get("font-weight") == "bold" else 1.0)
    x, y, a = float(t.get("x")), float(t.get("y")), t.get("text-anchor", "start")
    x0 = x - w / 2 if a == "middle" else x
    x1, y0, y1 = x0 + w, y - 0.75 * fs, y + 0.25 * fs
    tr = t.get("transform")
    if tr and tr.startswith("rotate"):
        _, px, py = nums(tr)
        pts = [(px + (yy - py), py - (xx - px)) for xx in (x0, x1) for yy in (y0, y1)]
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))
    return (x0, y0, x1, y1)


def _label_parts(comp):
    root = skin(comp)
    face = root.find(".//rect[@id='face']")
    group = root.find(".//g[@id='airflow-label']")
    plate = group.find("rect[@id='plate']")
    rect = lambda r: (float(r.get("x")), float(r.get("y")),
                      float(r.get("x")) + float(r.get("width")),
                      float(r.get("y")) + float(r.get("height")))
    glyph = group.find("g[@id='fan-glyph']")
    gx, gy, s = nums(glyph.get("transform"))
    texts = [t for t in root.iter("text") if t.get("class") == "airflow"]
    boxes = [_text_box(t) for t in texts]
    boxes.append((gx - 0.9 * s, gy - 0.9 * s, gx + 0.9 * s, gy + 0.9 * s))
    return root, texts, rect(face), rect(plate), boxes


@pytest.mark.parametrize("comp", sorted(PSUS) + sorted(FANS))
def test_the_airflow_label_is_the_guides_two_line_box_with_a_fan_glyph(comp):
    """Figures 38, 43 and 45: AIR OUT over (AFO), or AIR IN over (AFI), a fan glyph at the start
    of the second line; inside its plate and touching nothing."""
    out = (PSUS.get(comp) or FANS[comp])[-2 if comp in PSUS else -1] == "front-to-back"
    root, texts, face, plate, boxes = _label_parts(comp)
    want = ["AIR OUT", "(AFO)"] if out else ["AIR IN", "(AFI)"]
    assert [t.text for t in texts] == want
    assert len(root.findall(".//g[@id='airflow-label']/g[@id='fan-glyph']")) == 1
    # printed text sits in a silkscreen group, as the lint requires
    silk = {id(t) for g in root.iter("g") if g.get("id") == "silkscreen" for t in g.iter("text")}
    assert all(id(t) in silk for t in root.iter("text"))
    everything = "".join(t.text or "" for t in root.iter("text"))
    assert "⊕" not in everything and "+" not in "".join(t.text for t in texts)
    assert not any(" (AF" in (t.text or "") for t in root.iter("text"))
    assert plate[0] >= face[0] and plate[1] >= face[1]
    assert plate[2] <= face[2] and plate[3] <= face[3]
    for b in boxes:
        assert b[0] >= plate[0] + 0.2 and b[1] >= plate[1] + 0.2
        assert b[2] <= plate[2] - 0.2 and b[3] <= plate[3] - 0.2
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            gap_x = max(a[0] - b[2], b[0] - a[2])
            gap_y = max(a[1] - b[3], b[1] - a[3])
            assert max(gap_x, gap_y) >= 0.3, (a, b)


# ------------------------------------- the rest of the line: the 32-port fibre and the multigigabit
#
# Their own front panels, so their own devices: the EX4300-32F (32 SFP, four SFP+, two QSFP+) and the
# EX4300-48MP (24 + 24 copper jacks, four dedicated QSFP+). Figures are the guide's (published
# 2025-08-12): Table 10 for the envelope (each has its own line there), Tables 2, 3 and 8 for what
# each ships with, Tables 30 and 31 and the datasheet's ordering information for the supplies and fans.

# device: (model, Table 10 depth in cm with a power supply fitted, configurations -> part numbers)
MORE = {
    "ex4300-32f": ("EX4300-32F", 48.28,
                   {"ac": ["EX4300-32F", "EX4300-32F-TAA"],
                    "dc": ["EX4300-32F-DC", "EX4300-32F-DC-TAA"],
                    "s": ["EX4300-32F-S"]}),
    "ex4300-48mp": ("EX4300-48MP", 49.88,
                    {"ac": ["EX4300-48MP"], "s": ["EX4300-48MP-S"]}),
}
MORE_PSUS = {"ex4300-jpsu-1400-ac-afo": ("JPSU-1400-AC-AFO", 1400, "front-to-back", "ac")}
MORE_FANS = {"ex4300-48mp-fan-afo": ("EX4300-48MP-FAN", "front-to-back")}
MORE_BLANKS = {"ex4300-32f": "ex4300-32f-uplink-blank", "ex4300-48mp": "ex4300-48mp-uplink-blank"}
# the uplink modules the guide lists for each (Tables 5 and 6): none is in the library yet
MORE_UPLINKS = {"ex4300-32f": ["EX-UM-2QSFP", "EX-UM-8X8SFP"],
                "ex4300-48mp": ["EX-UM-2QSFP-MR", "EX-UM-4SFPP-MR"]}


def xs_of_top_row(d, ref, mod):
    """Left edges of one row of a stacked block, one per column, in order."""
    row = {int(p["id"].split("-")[1]): p["at"][0] for p in placements(d, "front")
           if p["ref"] == ref and p["id"].startswith("port-")
           and int(p["id"].split("-")[1]) % 2 == mod}
    return [row[k] for k in sorted(row)]


@pytest.mark.parametrize("dev", MORE)
def test_the_more_envelope_is_table_10(dev):
    """Table 10 gives the 32F and the 48MP their own depths; the width and height are the family's."""
    _, depth_cm, _ = MORE[dev]
    d = load(dev)
    c = d["chassis"]
    assert c["ru"] == 1
    assert c["height"] == pytest.approx(1.72 * INCH, abs=0.1)
    assert c["width"] == pytest.approx(17.36 * INCH, abs=0.2)
    assert c["depth"] == pytest.approx(depth_cm * 10, abs=0.2)
    for v in ("front", "rear"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["height"]}
    for v in ("top", "bottom"):
        assert d["views"][v]["size"] == {"w": c["width"], "h": c["depth"]}
    for v in ("left", "right"):
        assert d["views"][v]["size"] == {"w": c["depth"], "h": c["height"]}


def test_the_depths_are_not_the_24_and_48_port_depth():
    assert load("ex4300-32f")["chassis"]["depth"] == pytest.approx(19.0 * INCH, abs=0.3)
    assert load("ex4300-48mp")["chassis"]["depth"] == pytest.approx(19.64 * INCH, abs=0.3)


@pytest.mark.parametrize("dev", MORE)
def test_the_more_maker_and_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == MORE[dev][0]
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4300"}
    assert d["maturity"] == "modelled"


def test_the_32f_front_has_32_sfp_ports_in_four_gangs_and_four_sfp_plus_ports():
    d = load("ex4300-32f")
    cages = {p["id"]: p for p in placements(d, "front") if p["ref"] == "std/sfp-ganged@1"}
    sfp = {int(i.split("-")[1]): p for i, p in cages.items() if i.startswith("port-")}
    assert sorted(sfp) == list(range(32))
    for k, p in sfp.items():
        assert p["rel-pos"] == k and p["group"] == "sfp"
        # a stacked pair: the upper cage upright (even number), the lower turned 180
        assert p.get("rotate", 0) == (180 if k % 2 else 0)
    # four columns to a gang at the figure's 14.8 pitch, a 5.0 gutter between gangs
    xs = xs_of_top_row(d, "std/sfp-ganged@1", 0)
    assert len(xs) == 16
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(14.8) == 12 and sorted(s for s in steps if s != 14.8) == [19.8] * 3
    uplinks = {int(i.split("-")[1]): p for i, p in cages.items() if i.startswith("uplink-")}
    assert sorted(uplinks) == [0, 1, 2, 3]
    assert all(p["group"] == "sfp-plus" and p["rel-pos"] == k for k, p in uplinks.items())
    assert d["groups"]["sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert "poe" not in d["groups"]["sfp"]["attrs"]
    # the printed numbers, spelled as the metal spells them
    numerals = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
                if s.get("for", "").startswith(("port-", "uplink-")) and "text" in s}
    assert numerals == {**{f"port-{k}": str(k) for k in range(32)},
                        **{f"uplink-{k}": str(k) for k in range(4)}}
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert {f"port-{k}" for k in range(32)} | {f"uplink-{k}" for k in range(4)} <= cut


def test_each_32f_sfp_port_has_a_link_and_a_status_lamp():
    d = load("ex4300-32f")
    lamps = {}
    for p in placements(d, "front"):
        if p["id"].startswith("led-port-"):
            lamps.setdefault(p["for"], []).append(p["id"])
    assert set(lamps) == {f"port-{k}" for k in range(32)}
    assert all(len(v) == 2 for v in lamps.values())


def test_the_32f_front_has_the_console_lcd_buttons_lamps_and_the_large_uplink_slot():
    d = load("ex4300-32f")
    ids = {p["id"]: p["ref"] for p in placements(d, "front")}
    assert ids["console"] == "juniper/ex4300-console-usb-mini@1"
    assert ids["btn-menu"] == ids["btn-enter"] == "juniper/ex4300-lcd-button@1"
    for lamp in ("led-alm", "led-sys", "led-mst"):
        assert ids[lamp] == "common/led-dot@1"
    slot = bays(d, "front")["uplink"]
    # Figure 10 callout 1: the cover panel is the large opening at the left end, not the 74 mm one
    assert slot["size"]["w"] > 80
    assert slot["accepts"] == ["juniper/ex4300-32f-uplink-blank@1"]
    assert slot["default"] == "juniper/ex4300-32f-uplink-blank@1"
    assert {"EX4300-32F", "CON1"} <= {s.get("text") for s in d["views"]["front"]["silkscreen"]}


def test_the_48mp_front_has_24_plus_24_jacks_poe_plus_plus_numbered_as_printed():
    d = load("ex4300-48mp")
    jacks = {int(p["id"].split("-")[1]): p for p in placements(d, "front")
             if p["ref"] == "common/rj45-ganged-eth@1"}
    assert sorted(jacks) == list(range(48))
    for k, p in jacks.items():
        assert p["rel-pos"] == k
        assert p["group"] == ("rj45" if k < 24 else "rj45-10g")
        assert p.get("rotate", 0) == (180 if k % 2 == 0 else 0)
    g = d["groups"]
    # Table 3: 24 10/100/1000BASE-T and 24 100/1000/2500/5000/10000BASE-T, all up to 95 W
    assert g["rj45"]["attrs"] == {"media": "rj45", "speed": "1g", "poe": "802.3bt"}
    assert g["rj45-10g"]["attrs"] == {"media": "rj45", "speed": "10g", "poe": "802.3bt"}
    numerals = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
                if s.get("for", "").startswith("port-")}
    assert numerals == {f"port-{k}": str(k) for k in range(48)}
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert {f"port-{k}" for k in range(48)} <= cut


def test_the_48mp_jacks_stand_on_the_ganged_pitch_with_three_unequal_gutters():
    """Columns of six on the registry's 13.97; the photograph's three gaps between blocks differ."""
    d = load("ex4300-48mp")
    xs = xs_of_top_row(d, "common/rj45-ganged-eth@1", 0)
    assert len(xs) == 24
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(13.97) == 20
    assert sorted(round(s - 13.97, 2) for s in steps if s != 13.97) == [5.2, 7.27, 9.65]


def test_the_48mp_status_block_prints_the_photographs_legends_in_its_order():
    d = load("ex4300-48mp")
    front = d["views"]["front"]
    ids = {p["id"]: p for p in placements(d, "front")}
    for lamp in ("led-sys", "led-alm", "led-mst", "led-spd", "led-dx", "led-en", "led-poe"):
        assert ids[lamp]["ref"] == "common/led-dot@1"
    ys = lambda names: [ids[n]["at"][1] for n in names]
    # the photograph prints SYS, ALM, MST top to bottom (the guide names them ALM, SYS, MST)
    assert ys(["led-sys", "led-alm", "led-mst"]) == sorted(ys(["led-sys", "led-alm", "led-mst"]))
    assert ys(["led-spd", "led-dx", "led-en", "led-poe"]) == sorted(ys(["led-spd", "led-dx", "led-en", "led-poe"]))
    legends = {s["for"]: s["text"] for s in front["silkscreen"]
               if s.get("for", "").startswith("led-")}
    assert legends == {"led-sys": "SYS", "led-alm": "ALM", "led-mst": "MST", "led-spd": "SPD",
                       "led-dx": "DX", "led-en": "EN", "led-poe": "POE"}
    assert ids["btn-mode"]["group"] == "mode-button"
    assert ids["console"]["ref"] == "juniper/ex4300-console-usb-mini@1"
    assert "EX4300-48MP" in {s.get("text") for s in front["silkscreen"]}
    slot = bays(d, "front")["uplink"]
    assert slot["accepts"] == ["juniper/ex4300-48mp-uplink-blank@1"]


@pytest.mark.parametrize("dev,ports", [("ex4300-32f", 2), ("ex4300-48mp", 4)])
def test_the_more_rear_has_the_qsfp_ports_the_management_jacks_and_four_bays(dev, ports):
    d = load(dev)
    rear = {p["id"]: p for p in placements(d, "rear")}
    for k in range(ports):
        assert rear[f"vcp-{k}"]["ref"] == "std/qsfp-ganged@1" and rear[f"vcp-{k}"]["rel-pos"] == k
    assert f"vcp-{ports}" not in rear
    assert rear["mgmt"]["ref"] == "common/rj45-eth@1"
    assert rear["usb"]["ref"] == "std/usb-a@1"
    assert rear["con2" if dev == "ex4300-32f" else "con"]["ref"] == "std/rj45@2"
    assert set(bays(d, "rear")) == {"fan-0", "fan-1", "psu-0", "psu-1"}
    assert d["groups"]["vcp"]["attrs"] == {"media": "qsfp", "speed": "40g"}


def test_the_48mp_qsfp_ports_stand_on_the_figures_wider_pitch():
    d = load("ex4300-48mp")
    at = {p["id"]: p["at"][0] for p in placements(d, "rear") if p["id"].startswith("vcp-")
          and p["ref"] == "std/qsfp-ganged@1"}
    steps = [round(at[f"vcp-{k + 1}"] - at[f"vcp-{k}"], 2) for k in range(3)]
    assert all(s == pytest.approx(22.57, abs=0.05) for s in steps)


@pytest.mark.parametrize("comp", sorted(MORE_PSUS))
def test_the_1400_w_supply_states_its_part_number_output_and_airflow(comp):
    pn, watts, flow, _ = MORE_PSUS[comp]
    c = contract(comp)
    assert c["class"] == "psu" and c["kind"] == "module"
    assert c["attrs"]["part-number"] == pn and c["attrs"]["power-output-w"] == watts
    assert c["attrs"]["airflow"] == flow and c["attrs"]["airflow-label"] == "AIR OUT (AFO)"
    # Table 30: the 1400 W supply weighs 3.06 lb, the others 2.43
    assert c["attrs"]["weight-kg"] == 1.39
    assert any(p["ref"] == "std/c14-inlet@1" for p in c["parts"])


@pytest.mark.parametrize("comp", sorted(MORE_FANS))
def test_the_48mp_fan_is_its_own_part(comp):
    pn, flow = MORE_FANS[comp]
    c = contract(comp)
    assert c["class"] == "fan" and c["attrs"]["part-number"] == pn and c["attrs"]["airflow"] == flow
    # the datasheet orders EX4300-48MP-FAN beside EX4300-FAN, so the 24/48-port fan is not it
    assert pn != contract("ex4300-fan-afo")["attrs"]["part-number"]
    assert c["size"]["w"] < contract("ex4300-fan-afo")["size"]["w"]


@pytest.mark.parametrize("dev", MORE)
def test_the_more_bays_accept_what_the_guide_lists(dev):
    d = load(dev)
    if dev == "ex4300-32f":
        # Table 40: the 350 W AC supply; Table 2: the 550 W DC supply (the -DC); the AFI parts per
        # the datasheet's matrix and Table 2's -S row. Not the 715, 1100 or 1400 W supplies.
        psus = {"juniper/ex4300-jpsu-350-ac-afo@1", "juniper/ex4300-jpsu-350-ac-afi@1",
                "juniper/ex4300-jpsu-550-dc-afo@1", "juniper/ex4300-jpsu-550-dc-afi@1",
                "juniper/ex4300-psu-blank@1"}
        fans = {"juniper/ex4300-fan-afo@1", "juniper/ex4300-fan-afi@1"}
    else:
        # the guide: 715, 1100 and 1400 W AC, front-to-back only; no DC, no 350 W
        psus = {"juniper/ex4300-jpsu-715-ac-afo@1", "juniper/ex4300-jpsu-1100-ac-afo@1",
                "juniper/ex4300-jpsu-1400-ac-afo@1", "juniper/ex4300-psu-blank@1"}
        fans = {"juniper/ex4300-48mp-fan-afo@1"}
    for bid in ("psu-0", "psu-1"):
        assert set(bays(d, "rear")[bid]["accepts"]) == psus
    for bid in ("fan-0", "fan-1"):
        assert set(bays(d, "rear")[bid]["accepts"]) == fans


@pytest.mark.parametrize("dev", MORE)
def test_the_more_configurations_list_their_part_numbers(dev):
    d = load(dev)
    want = MORE[dev][2]
    assert set(d["configurations"]) == set(want)
    for cfg, pns in want.items():
        assert d["configurations"][cfg]["kind"] == "orderable"
        assert list(d["configurations"][cfg]["part-numbers"]) == pns
    assert [c for c, v in d["configurations"].items() if v.get("default")] == ["ac"]


def test_the_32f_builds_seat_a_matching_supply_and_fan_set():
    d = load("ex4300-32f")
    ac = seated(d, "ac")
    assert ac == {"uplink": "ex4300-32f-uplink-blank", "psu-0": "ex4300-jpsu-350-ac-afo",
                  "psu-1": "ex4300-psu-blank", "fan-0": "ex4300-fan-afo", "fan-1": "ex4300-fan-afo"}
    dc = seated(d, "dc")
    assert dc["psu-0"] == "ex4300-jpsu-550-dc-afo" and dc["psu-1"] == "ex4300-psu-blank"
    assert dc["fan-0"] == dc["fan-1"] == "ex4300-fan-afo"
    assert d["configurations"]["dc"]["power"] == "dc"
    for cfg, supply in (("ac", "ex4300-jpsu-350-ac-afo"), ("dc", "ex4300-jpsu-550-dc-afo")):
        s = seated(d, cfg)
        # Table 2: every shipped 32-port build is AIR OUT, supply and fans alike, front-to-back
        assert contract(supply)["attrs"]["airflow"] == contract(s["fan-0"])["attrs"]["airflow"]
        assert d["configurations"][cfg].get("airflow", d["chassis"]["airflow"]) == "front-to-back"
    s = seated(d, "s")
    assert s["psu-0"] == s["psu-1"] == s["fan-0"] == s["fan-1"] == ""
    assert s["uplink"] == "ex4300-32f-uplink-blank"


def test_the_48mp_builds_seat_the_1400_w_supply_and_its_own_fan():
    d = load("ex4300-48mp")
    assert seated(d, "ac") == {"uplink": "ex4300-48mp-uplink-blank", "psu-0": "ex4300-jpsu-1400-ac-afo",
                               "psu-1": "ex4300-psu-blank", "fan-0": "ex4300-48mp-fan-afo",
                               "fan-1": "ex4300-48mp-fan-afo"}
    s = seated(d, "s")
    assert s["psu-0"] == s["psu-1"] == s["fan-0"] == s["fan-1"] == ""
    assert s["uplink"] == "ex4300-48mp-uplink-blank"
    # Tables 7 and 28: AC only and front-to-back only, so neither a DC nor an AFI build exists
    assert d["chassis"]["airflow"] == "front-to-back" and d["chassis"]["power"] == "ac"
    assert not {"dc", "afi", "dc-afi"} & set(d["configurations"])


@pytest.mark.parametrize("dev", MORE)
def test_the_uplink_bay_takes_only_the_modules_the_library_holds(dev):
    """The guide lists two uplink modules for each of these (Tables 5 and 6). None is in the library, so
    the bay takes its cover panel alone and the gap names the modules left for a later slice."""
    d = load(dev)
    slot = bays(d, "front")["uplink"]
    assert slot["accepts"] == [f"juniper/{MORE_BLANKS[dev]}@1"]
    for ref in slot["accepts"]:
        assert (LIB / "components" / ref.split("@")[0] / "v1/contract.yaml").exists()
    gap = [g for g in d["gaps"] if g["what"] == "uplink-modules"]
    assert len(gap) == 1
    for module in MORE_UPLINKS[dev]:
        assert module in gap[0]["wanted"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", MORE)
def test_the_more_dcim_types_export_one_per_orderable_configuration(target, dev):
    """One device type per configuration, named by its first part number, one rack unit tall. The
    Trade Agreement Act SKUs share their configuration's type."""
    d = load(dev)
    folder = LIB / "exports" / target / "device-types" / "Juniper"
    for cfg, pns in MORE[dev][2].items():
        doc = yaml.safe_load((folder / f"{pns[0]}.yaml").read_text())
        assert doc["manufacturer"] == "Juniper" and doc["model"] == pns[0]
        assert doc["u_height"] == 1.0
        assert d["configurations"][cfg]["kind"] == "orderable"


@pytest.mark.parametrize("dev,n", [("ex4300-32f", 36), ("ex4300-48mp", 48)])
def test_the_more_exported_type_lists_the_front_ports(dev, n):
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Juniper" /
                          f"{MORE[dev][0]}.yaml").read_text())
    names = {i["name"] for i in doc["interfaces"]}
    front = ({f"port-{k}" for k in range(32)} | {f"uplink-{k}" for k in range(4)}
             if dev == "ex4300-32f" else {f"port-{k}" for k in range(48)})
    assert len(front) == n and front <= names
    assert {f"vcp-{k}" for k in range(2 if dev == "ex4300-32f" else 4)} <= names


@pytest.mark.parametrize("dev", MORE)
def test_the_more_devices_draw_no_logo_and_reserve_its_place(dev):
    d = load(dev)
    for name, view in d["views"].items():
        drawn = list(view.get("silkscreen") or []) + list((view.get("panel") or {}).get("decor") or [])
        words = {str(i.get("text", "")).upper() for i in drawn}
        assert not words & {"JUNIPER", "NETWORKS", "RUNNING JUNOS", "JUNOS"}, name
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"].startswith("logo-zone")]
    assert zones and all("not drawn" in z["label"] for z in zones)


def test_the_more_new_components_are_family_prefixed_and_state_their_size_source():
    refs = set()
    for dev in MORE:
        d = load(dev)
        for view in ("front", "rear"):
            refs |= {p["ref"] for p in placements(d, view)}
            for b in bays(d, view).values():
                refs.update(b["accepts"])
    mine = {r for r in refs if r.startswith("juniper/")}
    # the one part reused from another EX line: the 48MP's rear reset pinhole is the EX4100's
    assert mine and all(r.startswith("juniper/ex4300-") for r in mine - {"juniper/ex4100-reset-pinhole@1"})
    for comp in (sorted(MORE_PSUS) + sorted(MORE_FANS) + sorted(MORE_BLANKS.values())):
        c = contract(comp)
        assert c["size-confidence"]
        assert all(isinstance(v, str) for v in c["provenance"].values())
    assert contract("ex4300-48mp-mode-button")["size-confidence"]
