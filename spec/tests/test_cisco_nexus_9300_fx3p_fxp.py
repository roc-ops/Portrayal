"""The Cisco Nexus 93108TC-FX3P (with the 93108TC-FX3H as configurations) and 9348GC-FX3 fixed
switches, Nexus 9000 fixed switches batch 2.

The expected figures are Cisco's, read from the hardware installation guides: Cisco N93108TC-FX3P
(First Published 2020-07-14, Last Modified 2026-07-16) and Cisco N9348GC-FX3 (2023-08-18,
2026-09-18): the Overview port lists and callout tables and the Switch Dimensions, weights and
power-supply tables of appendix B. Each test reads the YAML a contributor edits, or the
generated export a DCIM user imports. The 9348GC-FXP is not modelled in this batch.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

FX3P = "n9k-c93108tc-fx3p"
GC = "n9k-c9348gc-fx3"
DEVICES = [FX3P, GC]

# device -> (width, height, depth, rack units, weight kg): the guides' Switch Dimensions tables,
# inches converted (FX3P: 17.2 in = 43.68 cm; 18 in = 45.73 cm without fans or PSUs; GC-FX3:
# 17.3 in = 43.9 cm; 18.0 in = 45.72 cm chassis without PSUs), and the weights tables' metric
# figures as printed (16 lb, 7.26 kg; 14.5 lb, 6.57 kg)
ENVELOPE = {
    FX3P: (436.8, 43.7, 457.3, 1, 7.26),
    GC: (439.4, 43.7, 457.2, 1, 6.57),
}

PAC1100 = "cisco/nxa-pac-1100w@1"
PAC1900 = "cisco/nxa-pac-1900w@1"
PDC715 = "cisco/nxa-pdc-715w@1"
PAC350 = "cisco/nxa-pac-350w@1"
PHV350 = "cisco/nxa-phv-350w@1"
PDC440 = "cisco/nxa-pdc-440w@1"
FAN35 = "cisco/nxa-fan-35cfm@1"
SFAN30 = "cisco/nxa-sfan-30cfm@1"
KIT1 = "cisco/nxk-acc-kit-1ru@1"

BLUE = "#50a2cf"

# configuration -> (supply, power feed, port-side exhaust?). The guide lists a port-side
# intake and a port-side exhaust 1100 W AC supply and only a port-side intake 1900 W AC and
# 715 W DC supply
BUILDS_FX3P = {
    "ac-1100w-port-side-intake": (PAC1100, None, False),
    "ac-1100w-port-side-exhaust": (PAC1100, None, True),
    "ac-1900w-port-side-intake": (PAC1900, None, False),
    "dc-715w-port-side-intake": (PDC715, "dc", False),
}
# the 9348GC-FX3 guide lists an intake and an exhaust build of the 350 W AC, 350 W PHV and 440 W
# DC supplies and an intake build of the 715 W DC supply
BUILDS_GC = {
    "ac-350w-port-side-intake": (PAC350, None, False),
    "ac-350w-port-side-exhaust": (PAC350, None, True),
    "hvac-hvdc-350w-port-side-intake": (PHV350, ["ac", "hvdc"], False),
    "hvac-hvdc-350w-port-side-exhaust": (PHV350, ["ac", "hvdc"], True),
    "dc-440w-port-side-intake": (PDC440, "dc", False),
    "dc-440w-port-side-exhaust": (PDC440, "dc", True),
    "dc-715w-port-side-intake": (PDC715, "dc", False),
}


def load(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/cisco" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in (d["views"][view].get("components") or {}).get("placements") or []}


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_the_guides_dimension_table(name):
    w, h, dp, ru, kg = ENVELOPE[name]
    c = load(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, dp, ru)
    assert c["weight-kg"] == pytest.approx(kg, abs=0.005)


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
def test_the_names_and_the_family_are_as_printed(name):
    d = load(name)
    assert d["manufacturer"] == "Cisco"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "Nexus 9000", "family": "Nexus 9300", "series": "Nexus 9300-FX3"}
    assert d["maturity"] == "modelled"
    assert d["chassis"].get("mount", "rack") == "rack"


# ------------------------------------------------------------------ the ports


def test_the_93108tc_fx3p_front_has_48_rj45_then_6_qsfp28_numbered_down_each_column():
    p = placements(load(FX3P), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "common/rj45-ganged-eth-plain@1", n
    for n in range(49, 55):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-55" not in p and "port-0" not in p
    for n in range(1, 54, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 49, 2)]
    # four groups of six columns on the ganged-jack pitch, 13.97, with a gutter between: the
    # figure draws a boxed group per six columns, and the 93108TC-FX3 has three groups of eight
    for g in range(4):
        for i in range(5):
            assert xs[6 * g + i + 1] - xs[6 * g + i] == pytest.approx(13.97, abs=0.01)
    for g in (1, 2, 3):
        assert xs[6 * g] - xs[6 * g - 1] > 13.97 + 5.0


def test_the_9348gc_fx3_front_has_48_copper_4_sfp28_and_2_qsfp28_numbered_down_each_column():
    p = placements(load(GC), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "common/rj45-ganged-eth-plain@1", n
    for n in range(49, 53):
        assert p[f"port-{n}"]["ref"] == "std/sfp-ganged@1", n
    for n in range(53, 55):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-55" not in p and "port-0" not in p
    for n in range(1, 54, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 49, 2)]
    # four groups of six columns, as on the 93108TC-FX3P, with the uplinks right of the last
    for g in range(4):
        for i in range(5):
            assert xs[6 * g + i + 1] - xs[6 * g + i] == pytest.approx(13.97, abs=0.01)
    for g in (1, 2, 3):
        assert xs[6 * g] - xs[6 * g - 1] > 13.97 + 5.0
    assert p["port-49"]["at"][0] > xs[-1] + 13.0
    assert p["port-53"]["at"][0] > p["port-51"]["at"][0]
    # the figure's callout 1 is "LEDs": BCN, STS and ENV, and a lamp for every port
    for lamp in ("led-bcn", "led-sts", "led-env"):
        assert lamp in p, lamp
    assert "led-p" not in p
    for n in range(1, 55):
        assert f"led-port-{n}" in p, n


def test_the_9348gc_fx3_rear_has_the_out_of_band_block_at_the_left_then_fans_then_supplies():
    d = load(GC)
    p = placements(d, "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1"
    assert p["usb"]["ref"] == "std/usb-a@1"
    assert "led-bcn-rear" in p and "led-sts-rear" in p
    b = bays(d, "rear")
    assert p["console"]["at"][0] < p["usb"]["at"][0] < p["mgmt-sfp"]["at"][0] < b["fan-1"]["at"][0]


def test_the_93108tc_fx3p_has_a_square_lamp_per_port_and_the_four_chassis_lamps():
    """Callout 1 is 'BCN, STS, ENV, and P LEDs'; the copper lamps are squares under the jacks."""
    p = placements(load(FX3P), "front")
    for lamp in ("led-bcn", "led-sts", "led-env", "led-p"):
        assert lamp in p, lamp
    for n in range(1, 49):
        lamp = p[f"led-port-{n}"]
        assert lamp["ref"] == "common/led-rect@1", n
        assert lamp["at"][1] > p[f"port-{n}"]["at"][1] + 11.0, n  # below the jack, not over it
    for n in range(49, 55):
        assert f"led-port-{n}" in p, n


def test_the_93108tc_fx3p_rear_has_console_two_management_ports_and_usb_between_fans_and_supplies():
    d = load(FX3P)
    p = placements(d, "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1"
    assert p["usb"]["ref"] == "std/usb-a@1"
    b = bays(d, "rear")
    assert b["fan-4"]["at"][0] < p["console"]["at"][0] < p["usb"]["at"][0] < b["psu-1"]["at"][0]


@pytest.mark.parametrize("name,fans", [(FX3P, 4), (GC, 3)])
def test_the_rear_has_two_supply_bays_and_the_guides_fan_bays_left_to_right(name, fans):
    b = bays(load(name), "rear")
    assert [k for k in b if k.startswith("psu-")] == ["psu-1", "psu-2"]
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, fans + 1)]
    assert [k for k in b if k.startswith("fan-")] == [f"fan-{i}" for i in range(1, fans + 1)]
    assert xs == sorted(xs)
    assert b["psu-1"]["at"][0] > xs[-1] and b["psu-1"]["at"][0] < b["psu-2"]["at"][0]
    pitch = [xs[i + 1] - xs[i] for i in range(fans - 1)]
    assert max(pitch) - min(pitch) < 0.05
    assert all(b[f"fan-{i}"]["group"] == "fans" for i in range(1, fans + 1))


@pytest.mark.parametrize("name", DEVICES)
def test_no_ear_and_no_logo_is_drawn_and_a_logo_zone_is_reserved(name):
    d = load(name)
    for view in ("front", "rear"):
        for p in placements(d, view).values():
            assert p["ref"] != "common/rack-ear@1"
        for s in d["views"][view].get("silkscreen") or []:
            # the maker's name is text in the model legend, as on the 93180YC-EX; no artwork
            if "cisco" in str(s.get("text", "")).lower():
                assert s["id"] == "silk-model" and s["text"].startswith("CISCO NEXUS "), s
            assert "logo" not in str(s.get("mark", "")).lower(), s
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1


# ------------------------------------------------------------ configurations


def _check_builds(name, builds, fan, pn_of):
    d = load(name)
    cf = d["configurations"]
    assert d["chassis"]["airflow"] == "front-to-back"
    defaults = [n for n, c in cf.items() if c.get("default")]
    assert len(defaults) == 1 and cf[defaults[0]]["kind"] == "base"
    fan_name = fan.split("/")[1].split("@")[0]
    for cname, (psu, power, exhaust) in builds.items():
        for prefix in pn_of:
            full = cname if prefix == "" else prefix + "-" + cname
            c = cf[full]
            assert list(c["part-numbers"]) == [pn_of[prefix]], full
            assert c["kind"] == ("base" if full == defaults[0] else "orderable"), full
            seated = c.get("bays") or {}
            default_psu = bays(d, "rear")["psu-1"]["default"]
            if psu != default_psu:
                assert seated == {"psu-1": psu, "psu-2": psu}, full
            else:
                assert not seated, full
            assert c.get("power") == power, full
            for bay in [b for b in bays(d, "rear") if b.startswith("fan-")]:
                assert bay not in seated  # the bay's own default is the family's one fan
            assert bays(d, "rear")["fan-1"]["default"] == fan
            attrs = c.get("component-attrs") or {}
            if exhaust:
                assert c["airflow"] == "back-to-front", full
                assert attrs[fan_name]["latch-finish"] == BLUE, full
                assert attrs[fan_name]["airflow"] == "back-to-front", full
                psu_name = psu.split("/")[1].split("@")[0]
                assert attrs[psu_name]["latch-finish"] == BLUE, full
                assert attrs[psu_name]["airflow"] == "back-to-front", full
            else:
                assert "airflow" not in c, full
                assert fan_name not in attrs, full
    expected = {n if p == "" else p + "-" + n for n in builds for p in pn_of}
    assert set(cf) == expected


def test_the_93108tc_fx3p_builds_seat_matching_supplies_and_fans_with_matching_airflow():
    _check_builds(FX3P, BUILDS_FX3P, FAN35,
                  {"": "N9K-C93108TC-FX3P", "fx3h": "N9K-C93108TC-FX3H"})


def test_the_9348gc_fx3_builds_seat_matching_supplies_and_fans_with_matching_airflow():
    _check_builds(GC, BUILDS_GC, SFAN30, {"": "N9K-C9348GC-FX3"})


@pytest.mark.parametrize("name,supplies,default,fan", [
    (FX3P, {PAC1100, PAC1900, PDC715}, PAC1100, FAN35),
    (GC, {PAC350, PHV350, PDC440, PDC715}, PAC350, SFAN30),
])
def test_the_bays_accept_only_the_supplies_and_fans_the_guide_names(name, supplies, default, fan):
    b = bays(load(name), "rear")
    for k in ("psu-1", "psu-2"):
        assert set(b[k]["accepts"]) == supplies
        assert b[k]["default"] == default
    for k in [k for k in b if k.startswith("fan-")]:
        assert b[k]["accepts"] == [fan]


# ------------------------------------------------------ components, ears, kits


def test_each_new_supply_is_one_component_named_by_its_part_number():
    root = LIB / "components/cisco"
    for part, model, watts, feed in (("nxa-pac-1100w", "NXA-PAC-1100W", 1100, "ac"),
                                     ("nxa-pac-1900w", "NXA-PAC-1900W", 1900, "ac"),
                                     ("nxa-pdc-715w", "NXA-PDC-715W", 715, "dc")):
        assert [p.name for p in root.iterdir() if p.name.startswith(part)] == [part]
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model
        assert c["class"] == "psu" and "size" in c["provenance"]
        assert c["attrs"]["power-output-w"] == watts and c["attrs"]["input"] == feed
    assert contract("nxa-pac-1100w")["attrs"]["weight-kg"] == 1.36
    assert contract("nxa-pac-1900w")["attrs"]["weight-kg"] == 1.63
    assert contract("nxa-fan-35cfm")["attrs"]["model"] == "NXA-FAN-35CFM"  # reused, not copied


def test_each_9348gc_supply_and_fan_is_one_component_named_by_its_part_number():
    root = LIB / "components/cisco"
    for part, model, watts, feed in (("nxa-pac-350w", "NXA-PAC-350W", 350, "ac"),
                                     ("nxa-phv-350w", "NXA-PHV-350W", 350, "hvac-hvdc"),
                                     ("nxa-pdc-440w", "NXA-PDC-440W", 440, "dc")):
        assert [p.name for p in root.iterdir() if p.name.startswith(part)] == [part]
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model
        assert c["class"] == "psu" and "size" in c["provenance"]
        assert c["attrs"]["power-output-w"] == watts and c["attrs"]["input"] == feed
        assert c["attrs"]["weight-kg"] == 1.2  # 2.64 lb in the guide's weights table
    fan = contract("nxa-sfan-30cfm")
    assert fan["class"] == "fan" and fan["attrs"]["model"] == "NXA-SFAN-30CFM"
    assert fan["attrs"]["rotors"] == 2 and fan["attrs"]["weight-kg"] == 0.12
    # the 715 W DC supply is shared by both guides: one component, not a copy per device
    assert [p.name for p in root.iterdir() if p.name.startswith("nxa-pdc-715w")] == ["nxa-pdc-715w"]


@pytest.mark.parametrize("name", DEVICES)
def test_the_ears_state_the_two_ways_without_a_number_and_without_a_default(name):
    ears = load(name)["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["recessed", "recessed"], name
    assert len({p["label"] for p in ears["positions"]}) == 2, name
    for p in ears["positions"]:
        assert "at" not in p and not p.get("default"), (name, p)


@pytest.mark.parametrize("name", DEVICES)
def test_the_listed_kit_is_the_one_the_guide_orders_and_it_resolves(name):
    assert [k["ref"] for k in load(name)["chassis"]["kits"]] == [KIT1]
    k = contract("nxk-acc-kit-1ru")
    assert k["kind"] == "kit" and k["configurations"][0]["racks"] == ["4-post"]


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_part_number_one_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Cisco"
    for pn in ("N9K-C93108TC-FX3P", "N9K-C93108TC-FX3H", "N9K-C9348GC-FX3"):
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Cisco" and doc["model"] == pn
        assert doc["u_height"] == 1.0


def test_the_exported_93108tc_fx3p_type_lists_the_54_ports_and_the_management_ports():
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Cisco/N9K-C93108TC-FX3P.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 55)} <= set(types)
    assert "port-55" not in types
    assert {types[f"port-{n}"] for n in range(1, 49)} == {"10gbase-t"}
    assert {types[f"port-{n}"] for n in range(49, 55)} == {"100gbase-x-qsfp28"}
