"""The Cisco Nexus 9348GC-FX3PH and 92348GC-FX3 fixed switches, Nexus 9000 fixed switches batch 5.

The expected figures are Cisco's, read from the hardware installation guides: Cisco N9348GC-FX3PH
(First Published 2023-08-18, Last Modified 2026-07-22) and Cisco N92348GC-FX3 (2024-10-21,
2026-08-04): the Overview port lists, supply lists and callout tables, the PoE paragraph, and the
Switch Dimensions, weights and power-input tables of appendix B. Each test reads the YAML a
contributor edits, or the generated export a DCIM user imports.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

from portrayal import devicelock

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PH = "n9k-c9348gc-fx3ph"
GC = "n9k-c92348gc-fx3"
DEVICES = [PH, GC]
PN = {PH: "N9K-C9348GC-FX3PH", GC: "N9K-C92348GC-FX3"}

# device -> (width, height, depth, rack units, weight kg): each guide's Switch Dimensions table,
# 17.3 in = 43.9 cm wide, 1.72 in (1 RU) high, "Chassis without PSUs - 18.0 in (45.72 cm)" deep
# (the depth with supplies is 19.7 in with the 350 W AC or PHV, 21.0 in with the 440 W DC and, on
# the PH only, 21.1 in with the 1900 W: the library's depth is the chassis), and each guide's
# own weights row: PH 14.33 lb (6.49 kg), 92348GC 14.5 lb (6.57 kg)
ENVELOPE = {
    PH: (439.4, 43.7, 457.2, 1, 6.49),
    GC: (439.4, 43.7, 457.2, 1, 6.57),
}

PAC350 = "cisco/nxa-pac-350w@1"
PHV350 = "cisco/nxa-phv-350w@1"
PDC440 = "cisco/nxa-pdc-440w@1"
PAC1900 = "cisco/nxa-pac-1900w@1"
SFAN30 = "cisco/nxa-sfan-30cfm@1"
KIT1 = "cisco/nxk-acc-kit-1ru@1"
KIT2 = "cisco/nxk-acc-kit2-2ru@1"

BLUE = "#50a2cf"

# configuration -> (supply, power feed, port-side exhaust?). The PH guide lists an intake and an
# exhaust build of the 350 W AC, 1900 W AC, 350 W PHV and 440 W DC supplies; the 92348GC guide
# lists the same without the 1900 W
BUILDS_PH = {
    "ac-350w-port-side-intake": (PAC350, None, False),
    "ac-350w-port-side-exhaust": (PAC350, None, True),
    "ac-1900w-port-side-intake": (PAC1900, None, False),
    "ac-1900w-port-side-exhaust": (PAC1900, None, True),
    "hvac-hvdc-350w-port-side-intake": (PHV350, ["ac", "hvdc"], False),
    "hvac-hvdc-350w-port-side-exhaust": (PHV350, ["ac", "hvdc"], True),
    "dc-440w-port-side-intake": (PDC440, "dc", False),
    "dc-440w-port-side-exhaust": (PDC440, "dc", True),
}
BUILDS_GC = {k: v for k, v in BUILDS_PH.items() if "1900w" not in k}


def load(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def source(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "layout.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/cisco" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in (d["views"][view].get("components") or {}).get("placements") or []}


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"].get("decor") or []}


def provenance_text(name):
    return " ".join(str(v.get("note", "")) for v in source(name)["provenance"].values())


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_the_guides_dimension_table(name):
    w, h, dp, ru, kg = ENVELOPE[name]
    c = load(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, dp, ru)
    assert c["weight-kg"] == pytest.approx(kg, abs=0.005)


@pytest.mark.parametrize("name", DEVICES)
def test_the_depth_by_supply_is_declared_and_only_the_chassis_depth_is_carried(name):
    text = provenance_text(name)
    for depth in ("18.0 in (45.72 cm)", "19.7 in (49.9 cm)", "21.0 in (53.34 cm)"):
        assert depth in text, (name, depth)
    assert ("21.1 in (53.6 cm)" in text) == (name == PH)
    assert load(name)["chassis"]["depth"] == 457.2


@pytest.mark.parametrize("name", DEVICES)
def test_every_face_is_sized_from_the_envelope(name):
    d = load(name)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


@pytest.mark.parametrize("name", DEVICES)
def test_the_four_faces_no_guide_draws_are_left_empty(name):
    v = load(name)["views"]
    for face in ("top", "bottom", "left", "right"):
        assert v[face].get("empty"), (name, face)
        assert not v[face].get("components"), (name, face)
    text = " ".join(str(g.get("what", "")) for g in source(name)["gaps"])
    assert "the-four-undrawn-faces" in text


@pytest.mark.parametrize("name", DEVICES)
def test_the_names_and_the_family_are_as_printed(name):
    d = load(name)
    assert d["manufacturer"] == "Cisco"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "Nexus 9000", "family": "Nexus 9300", "series": "Nexus 9300-FX3"}
    assert d["maturity"] == "modelled"
    assert d["chassis"].get("mount", "rack") == "rack"
    assert d["aliases"] == [{"name": {PH: "Nexus 9348GC-FX3PH", GC: "Nexus 92348GC-FX3"}[name],
                             "kind": "marketing"}]


# ------------------------------------------------------------------ the ports


def _copper_columns(p, ports=48):
    return [p[f"port-{n}"]["at"][0] for n in range(1, ports + 1, 2)]


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_48_copper_4_sfp28_and_2_qsfp28_numbered_down_each_column(name):
    p = placements(load(name), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "common/rj45-ganged-eth-plain@1", n
    for n in range(49, 53):
        assert p[f"port-{n}"]["ref"] == "std/sfp-ganged@1", n
    for n in range(53, 55):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-55" not in p and "port-0" not in p
    # odd on the upper row, as the figure prints "1 up down 2" over each column
    for n in range(1, 54, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = _copper_columns(p)
    # four boxed groups of six columns on the ganged-jack pitch with a gutter between them
    for g in range(4):
        for i in range(5):
            assert xs[6 * g + i + 1] - xs[6 * g + i] == pytest.approx(13.97, abs=0.01), (g, i)
    for g in (1, 2, 3):
        assert xs[6 * g] - xs[6 * g - 1] > 13.97 + 5.0
    assert p["port-49"]["at"][0] > xs[-1] + 13.0
    assert p["port-53"]["at"][0] > p["port-51"]["at"][0] > p["port-49"]["at"][0]
    for n in range(1, 55):
        assert f"led-port-{n}" in p, n
    for n in range(1, 49):
        assert p[f"led-port-{n}"]["ref"] == "common/led-rect@1", n
        assert p[f"led-port-{n}"]["at"][1] > p[f"port-{n}"]["at"][1] + 11.0, n


def test_the_ph_ports_41_to_48_are_their_own_group_at_the_guides_100m_rate():
    """Callout 5: 100M RJ45 ports (8); the Overview note: ports 41-48 support 10M/100M half-duplex
    only. Ports 1-40 are 10M/100M/1G, and a group has one rate."""
    d = load(PH)
    g = d["groups"]
    assert g["rj45"]["attrs"]["speed"] == "1g"
    assert g["rj45-100m"]["attrs"]["speed"] == "100m"
    assert "half-duplex" in g["rj45-100m"]["attrs"]["rate-note"]
    p = placements(d, "front")
    assert [n for n in range(1, 49) if p[f"port-{n}"]["group"] == "rj45"] == list(range(1, 41))
    assert [n for n in range(1, 49) if p[f"port-{n}"]["group"] == "rj45-100m"] == list(range(41, 49))


def test_the_gc_copper_ports_are_all_one_group_at_1g():
    d = load(GC)
    assert d["groups"]["rj45"]["attrs"]["speed"] == "1g"
    assert "rj45-100m" not in d["groups"]
    p = placements(d, "front")
    assert {p[f"port-{n}"]["group"] for n in range(1, 49)} == {"rj45"}


def test_the_ph_front_draws_the_four_chassis_lamps_with_the_p_lamp_and_the_shaded_ports():
    d = load(PH)
    p = placements(d, "front")
    for lamp in ("led-bcn", "led-sts", "led-env", "led-p"):
        assert lamp in p, lamp
    ys = [p[f"led-{k}"]["at"][1] for k in ("bcn", "sts", "env", "p")]
    assert ys == sorted(ys)
    assert [s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("for") == "led-p"] == ["P"]
    # the P lamp is read as the PoE lamp: Appendix C lists a "PoE" row beside BCN, STS and ENV
    assert {s["name"] for s in p["led-p"]["states"] if isinstance(s, dict)} == {"poe-on", "poe-fault"}
    dec = decor(d, "front")
    for k in ("shade-top-41-48", "shade-num-41-48"):
        assert k in dec, k
    top = dec["shade-top-41-48"]
    cols = _copper_columns(p)
    # the band stands over the last four columns (ports 41 to 48) and no other
    assert top["at"][0] == pytest.approx(cols[20], abs=1.0)
    assert top["at"][0] + top["size"][0] > cols[23] + 12.0
    assert top["at"][0] > cols[19] + 12.0


def test_the_gc_front_draws_three_chassis_lamps_and_no_p_lamp_and_no_shade():
    d = load(GC)
    p = placements(d, "front")
    for lamp in ("led-bcn", "led-sts", "led-env"):
        assert lamp in p, lamp
    assert "led-p" not in p
    assert not [k for k in decor(d, "front") if k.startswith("shade")]


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_out_of_band_block_at_the_left_then_fans_then_supplies(name):
    d = load(name)
    p = placements(d, "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1"
    assert p["usb"]["ref"] == "std/usb-a@1"
    assert "led-bcn-rear" in p and "led-sts-rear" in p
    assert {"ground-screw-1", "ground-screw-2"} <= set(p)
    b = bays(d, "rear")
    assert p["console"]["at"][0] < p["usb"]["at"][0] < p["mgmt-sfp"]["at"][0] < b["fan-1"]["at"][0]
    assert p["console"]["at"][1] < p["mgmt-rj45"]["at"][1]


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_three_fan_bays_and_two_supply_bays_left_to_right(name):
    b = bays(load(name), "rear")
    assert [k for k in b if k.startswith("psu-")] == ["psu-1", "psu-2"]
    assert [k for k in b if k.startswith("fan-")] == ["fan-1", "fan-2", "fan-3"]
    xs = [b[f"fan-{i}"]["at"][0] for i in (1, 2, 3)]
    assert xs == sorted(xs)
    assert b["psu-1"]["at"][0] > xs[-1] and b["psu-1"]["at"][0] < b["psu-2"]["at"][0]
    assert max(xs[i + 1] - xs[i] for i in (0, 1)) - min(xs[i + 1] - xs[i] for i in (0, 1)) < 0.05
    assert all(b[f"fan-{i}"]["group"] == "fans" for i in (1, 2, 3))


@pytest.mark.parametrize("name", DEVICES)
def test_no_ear_and_no_logo_is_drawn_and_a_logo_zone_is_reserved(name):
    d = load(name)
    for view in ("front", "rear"):
        for p in placements(d, view).values():
            assert p["ref"] != "common/rack-ear@1"
        for s in d["views"][view].get("silkscreen") or []:
            # the maker's name is text in the model legend, as on the 9348GC-FX3; no artwork
            if "cisco" in str(s.get("text", "")).lower():
                assert s["id"] == "silk-model" and s["text"] == "CISCO NEXUS " + PN[name], s
            assert "logo" not in str(s.get("mark", "")).lower(), s
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1


# ------------------------------------------------------------ configurations


def _check_builds(name, builds):
    d = load(name)
    cf = d["configurations"]
    assert d["chassis"]["airflow"] == "front-to-back"
    # the guides state no default, so the first build is the base, as the 9348GC-FX3 does
    defaults = [n for n, c in cf.items() if c.get("default")]
    assert defaults == ["ac-350w-port-side-intake"] and cf[defaults[0]]["kind"] == "base"
    for cname, (psu, power, exhaust) in builds.items():
        c = cf[cname]
        assert list(c["part-numbers"]) == [PN[name]], cname
        assert c["part-numbers"][PN[name]] == {"part": PN[name]}, cname
        assert c["kind"] == ("base" if cname == defaults[0] else "orderable"), cname
        seated = c.get("bays") or {}
        if psu != bays(d, "rear")["psu-1"]["default"]:
            assert seated == {"psu-1": psu, "psu-2": psu}, cname
        else:
            assert not seated, cname
        assert c.get("power") == power, cname
        for bay in [b for b in bays(d, "rear") if b.startswith("fan-")]:
            assert bay not in seated
        attrs = c.get("component-attrs") or {}
        psu_name = psu.split("/")[1].split("@")[0]
        if exhaust:
            assert c["airflow"] == "back-to-front", cname
            for part in ("nxa-sfan-30cfm", psu_name):
                assert attrs[part]["latch-finish"] == BLUE, (cname, part)
                assert attrs[part]["airflow"] == "back-to-front", (cname, part)
        else:
            assert "airflow" not in c, cname
            assert "nxa-sfan-30cfm" not in attrs, cname
            assert psu_name not in attrs, cname
    assert set(cf) == set(builds)
    assert bays(d, "rear")["fan-1"]["default"] == SFAN30


def test_the_ph_builds_seat_matching_supplies_and_fans_with_matching_airflow():
    _check_builds(PH, BUILDS_PH)


def test_the_gc_builds_seat_matching_supplies_and_fans_with_matching_airflow():
    _check_builds(GC, BUILDS_GC)


@pytest.mark.parametrize("name,supplies", [
    (PH, {PAC350, PHV350, PDC440, PAC1900}),
    (GC, {PAC350, PHV350, PDC440}),
])
def test_the_bays_accept_only_the_supplies_and_fans_the_guide_names(name, supplies):
    b = bays(load(name), "rear")
    for k in ("psu-1", "psu-2"):
        assert set(b[k]["accepts"]) == supplies
        assert b[k]["default"] == PAC350
    for k in [k for k in b if k.startswith("fan-")]:
        assert b[k]["accepts"] == [SFAN30]


def test_the_92348gc_takes_no_1900w_supply_and_the_ph_takes_it_in_both_airflows():
    gc = load(GC)
    assert not [c for c in gc["configurations"] if "1900" in c]
    for k in ("psu-1", "psu-2"):
        assert PAC1900 not in bays(gc, "rear")[k]["accepts"]
    assert "1900" not in " ".join(str(c) for c in gc["configurations"].values())
    ph = load(PH)["configurations"]
    assert {"ac-1900w-port-side-intake", "ac-1900w-port-side-exhaust"} <= set(ph)


def test_the_ph_1900w_exhaust_build_is_written_with_component_attrs_and_the_component_is_untouched():
    """The PH guide lists NXA-PAC-1900W-PE; cisco/nxa-pac-1900w@1 says the FX3P guide lists no
    port-side exhaust version. The component keeps saying so (it is another guide's reading and
    is not edited here); the device writes the exhaust build as an attribute override."""
    c = load(PH)["configurations"]["ac-1900w-port-side-exhaust"]
    assert c["airflow"] == "back-to-front"
    assert c["component-attrs"]["nxa-pac-1900w"] == {"latch-finish": BLUE, "latch-edge": "#2c6f96",
                                                     "airflow": "back-to-front"}
    k = contract("nxa-pac-1900w")
    assert "lists no port-side exhaust version" in k["provenance"]["model"]
    assert k["attrs"]["airflow"] == "front-to-back" and k["attrs"]["weight-kg"] == 1.63
    assert [p.name for p in (LIB / "components/cisco").iterdir() if p.name.startswith("nxa-pac-1900w")] \
        == ["nxa-pac-1900w"]
    text = provenance_text(PH)
    for claim in ("NXA-PAC-1900W-PE", "lists no port-side exhaust", "3.6 lb (1.63 kg)", "2.64 lb (1.2 kg)"):
        assert claim in text, claim


def test_the_ph_one_weight_row_for_all_eight_supplies_is_declared_and_carried_on_no_component():
    d = load(PH)
    assert "2.64 lb (1.2 kg)" in d["attrs"]["physical"]["weight-note"]
    assert "14.33 lb (6.49 kg)" in d["attrs"]["physical"]["weight-note"]
    assert contract("nxa-pac-1900w")["attrs"]["weight-kg"] == 1.63  # the FX3P guide's, unedited


def test_each_supply_and_fan_is_one_component_named_by_its_part_number_and_nothing_is_added():
    root = LIB / "components/cisco"
    for part, model, watts, feed in (("nxa-pac-350w", "NXA-PAC-350W", 350, "ac"),
                                     ("nxa-phv-350w", "NXA-PHV-350W", 350, "hvac-hvdc"),
                                     ("nxa-pdc-440w", "NXA-PDC-440W", 440, "dc"),
                                     ("nxa-pac-1900w", "NXA-PAC-1900W", 1900, "ac")):
        assert [p.name for p in root.iterdir() if p.name.startswith(part)] == [part]
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model
        assert c["class"] == "psu" and c["attrs"]["power-output-w"] == watts and c["attrs"]["input"] == feed
    fan = contract("nxa-sfan-30cfm")
    assert fan["attrs"]["model"] == "NXA-SFAN-30CFM" and fan["attrs"]["rotors"] == 2
    # no twin for the airflow suffix, the revision mark or a supply label
    assert not [p.name for p in root.iterdir() if "pe2" in p.name or "pi2" in p.name or "c3kx" in p.name]


def test_the_supply_part_numbers_in_the_text_are_what_the_builds_name():
    """The text prints NXA-PAC-350W-PI2 and -PE2 (the 2 is a revision mark, not a part), and -PI
    and -PE for the others; each build's description names its guide's spelling."""
    for name in DEVICES:
        cf = load(name)["configurations"]
        assert "NXA-PAC-350W-PI2" in cf["ac-350w-port-side-intake"]["description"]
        assert "NXA-PAC-350W-PE2" in cf["ac-350w-port-side-exhaust"]["description"]
        assert "NXA-PHV-350W-PI " in cf["hvac-hvdc-350w-port-side-intake"]["description"] + " "
        assert "NXA-PDC-440W-PE" in cf["dc-440w-port-side-exhaust"]["description"]
        assert "NXA-SFAN-30CFM-PE" in cf["dc-440w-port-side-exhaust"]["description"]
    assert "NXA-PAC-1900W-PI" in load(PH)["configurations"]["ac-1900w-port-side-intake"]["description"]
    assert "NXA-PAC-1900W-PE" in load(PH)["configurations"]["ac-1900w-port-side-exhaust"]["description"]


def test_the_92348gc_rear_supply_label_is_declared_against_the_text_and_adds_no_part():
    text = provenance_text(GC)
    assert "C3KX-PWR-" in text and "WAC" in text and "not one of the six" in text
    assert "C3KX" not in " ".join(c["description"] for c in load(GC)["configurations"].values())
    # the PH rear prints no label on its supplies
    assert "C3KX" not in provenance_text(PH)


# ------------------------------------------------- power, PoE, fans, mixing


def test_the_power_input_tables_are_each_guides_own_row():
    ph, gc = load(PH)["attrs"]["power"], load(GC)["attrs"]["power"]
    assert (ph["power-typical-w"], ph["power-max-w"], ph["heat-dissipation-btu-hr"]) == (238, 251, 856)
    assert (gc["power-typical-w"], gc["power-max-w"], gc["heat-dissipation-btu-hr"]) == (226, 242, 826)


def test_the_poe_paragraph_is_stated_as_the_guide_states_it_and_no_budget_is_carried():
    d = load(PH)
    text = d["attrs"]["power"]["poe-power-supplies"]
    for phrase in ("48 PoE++ (60W ports) - two 1900W power supplies needed",
                   "21 PoE++ (60W ports) - one 1900W power supplies needed",
                   "Non-PoE - one or two 350W power supplies needed"):
        assert phrase in text, phrase
    flat = yaml.safe_dump(d["attrs"])
    assert "poe-budget" not in flat and "poe-watts" not in flat
    assert "poe-power-supplies" not in load(GC)["attrs"]["power"]


@pytest.mark.parametrize("name", DEVICES)
def test_the_fans_are_stated_as_the_guide_states_them(name):
    d = load(name)
    f = d["groups"]["fans"]["attrs"]
    assert f["redundancy"] == "2+1"
    for phrase in ("fewer than 2 fans are operational", "more than one rotor", "two minutes"):
        assert phrase in f["redundancy-note"], phrase
    assert d["groups"]["psus"]["attrs"]["redundancy"] == "1+1"


@pytest.mark.parametrize("name", DEVICES)
def test_a_mix_of_ac_and_dc_supplies_is_a_gap_and_no_configuration(name):
    d = source(name)
    gaps = {g["what"]: g for g in d["gaps"]}
    assert "mixed-ac-dc-supplies" in gaps
    assert gaps["mixed-ac-dc-supplies"]["scope"] == ["rear"]
    for c in load(name)["configurations"].values():
        assert len({b for b in (c.get("bays") or {}).values()}) <= 1, c  # one supply type per build


def test_the_shared_default_is_a_declared_choice():
    for name in DEVICES:
        gaps = {g["what"] for g in source(name)["gaps"]}
        assert "default-configuration" in gaps, name


# ------------------------------------------------------ ears, kits


@pytest.mark.parametrize("name", DEVICES)
def test_the_ears_state_the_two_ways_without_a_number_and_without_a_default(name):
    ears = load(name)["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["recessed", "recessed"], name
    assert len({p["label"] for p in ears["positions"]}) == 2, name
    for p in ears["positions"]:
        assert "at" not in p and not p.get("default"), (name, p)


@pytest.mark.parametrize("name", DEVICES)
def test_the_listed_kits_are_the_ones_the_guide_gives_a_procedure_for_and_each_resolves(name):
    """Both guides give an install procedure for NXK-ACC-KIT-1RU (with its contents) and for
    NXK-ACC-KIT2-2RU; each is a kit on main. N3K-C3064-ACC-KIT is named, not described: a gap."""
    d = load(name)
    assert [k["ref"] for k in d["chassis"]["kits"]] == [KIT1, KIT2]
    for ref in ("nxk-acc-kit-1ru", "nxk-acc-kit2-2ru"):
        k = contract(ref)
        assert k["kind"] == "kit" and k["configurations"][0]["racks"] == ["4-post"]
    gaps = {g["what"] for g in source(name)["gaps"]}
    assert "kit-named-without-contents" in gaps
    assert not [p.name for p in (LIB / "components/cisco").iterdir() if "c3064" in p.name]


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_chassis_part_number_one_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Cisco"
    for pn in PN.values():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Cisco" and doc["model"] == pn
        assert doc["u_height"] == 1.0
    # the part-number-per-build rule: one type per chassis, the builds are configurations
    assert not list(folder.glob("N9K-C9348GC-FX3PH-*.yaml"))
    assert not list(folder.glob("N9K-C92348GC-FX3-*.yaml"))


def _types(pn):
    doc = yaml.safe_load((LIB / f"exports/netbox/device-types/Cisco/{pn}.yaml").read_text())
    return {i["name"]: i["type"] for i in doc["interfaces"]}


def test_the_exported_ph_type_types_ports_41_to_48_as_100m_and_the_rest_as_the_guide_says():
    types = _types(PN[PH])
    assert {f"port-{n}" for n in range(1, 55)} <= set(types)
    assert "port-55" not in types
    assert {types[f"port-{n}"] for n in range(1, 41)} == {"1000base-t"}
    assert {types[f"port-{n}"] for n in range(41, 49)} == {"100base-tx"}
    assert {types[f"port-{n}"] for n in range(49, 53)} == {"25gbase-x-sfp28"}
    assert {types[f"port-{n}"] for n in range(53, 55)} == {"100gbase-x-qsfp28"}


def test_the_exported_gc_type_lists_48_copper_4_sfp28_and_2_qsfp28_ports():
    types = _types(PN[GC])
    assert {f"port-{n}" for n in range(1, 55)} <= set(types)
    assert "port-55" not in types
    assert {types[f"port-{n}"] for n in range(1, 49)} == {"1000base-t"}
    assert {types[f"port-{n}"] for n in range(49, 53)} == {"25gbase-x-sfp28"}
    assert {types[f"port-{n}"] for n in range(53, 55)} == {"100gbase-x-qsfp28"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_committed_exports_equal_the_exporters_own_output_image_flags_included(name, tmp_path):
    dist = LIB / "dist"
    if not (dist / "listings.json").exists():
        pytest.skip("library/dist not built")
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/dcim_export.py"),
                        "--dist", str(dist), "--out", str(tmp_path), "--no-raster", "--images",
                        "--device", name], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    for target in ("netbox", "nautobot"):
        rel = f"{target}/device-types/Cisco/{PN[name]}.yaml"
        assert (tmp_path / rel).read_text() == (LIB / "exports" / rel).read_text(), rel


@pytest.mark.parametrize("name", DEVICES)
def test_the_lock_file_agrees_with_the_device_at_1_0_0(name):
    problems = [f for f in devicelock.check(LIB) if f[0] == f"cisco/{name}"]
    assert not problems, problems
    assert load(name)["version"] == "1.0.0"
