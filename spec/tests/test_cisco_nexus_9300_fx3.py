"""The Cisco Nexus 9300-FX3 fixed switches, Nexus 9000 fixed switches batch 1.

Three devices: `cisco/n9k-c93180yc-fx3` (the 93180YC-FX3, with the 93180YC-FX3H as configurations of
it, because the guide draws one front and one rear for both), `cisco/n9k-c93180yc-fx3s` and
`cisco/n9k-c93108tc-fx3`. The expected figures are Cisco's, read from the hardware installation
guides: Cisco N93180YC-FX3 (First Published 2021-02-16, Last Modified 2026-07-27), Cisco
N93180YC-FX3S (2020-07-22, 2026-07-27) and Cisco N93108TC-FX3 (2023-12-14, 2026-07-16): the
Overview port lists and callout tables, the Switch Dimensions and weights tables of appendix B,
and the kit text of the rack-mounting chapter. Each test reads the YAML a contributor edits, or
the generated export a DCIM user imports.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

FX3, FX3S, TC = "n9k-c93180yc-fx3", "n9k-c93180yc-fx3s", "n9k-c93108tc-fx3"
DEVICES = [FX3, FX3S, TC]

# device -> (width, height, depth, rack units, weight kg): the guides' Switch Dimensions table,
# inches converted, and the weights table's metric figure as printed
ENVELOPE = {
    FX3: (439.4, 43.7, 495.3, 1, 9.52),    # 17.3 x 1.72 x 19.5 in; 21 lb (9.52 kg)
    FX3S: (439.4, 43.7, 495.3, 1, 9.52),   # the same row, the FX3S guide's own table
    TC: (439.4, 43.7, 454.7, 1, 7.1),      # 17.3 x 1.72 x 17.9 in; 15.8 lb (7.1 kg)
}

PAC650 = "cisco/nxa-pac-650w@1"
PAC500 = "cisco/nxa-pac-500w@1"
PUV = "cisco/n9k-puv-1200w@1"
PDC = "cisco/nxa-pdc-930w@1"
FAN35 = "cisco/nxa-fan-35cfm@1"
SFAN35 = "cisco/nxa-sfan-35cfm@1"
KIT1 = "cisco/nxk-acc-kit-1ru@1"
KIT2 = "cisco/nxk-acc-kit2-2ru@1"

# configuration -> (supply, power feed, port-side exhaust?). The guides' Overview lists, for
# every supply, a port-side intake and a port-side exhaust build; the 1200 W HVAC/HVDC supply
# has one part for both directions
BUILDS_650 = {
    "ac-650w-port-side-intake": (PAC650, None, False),
    "ac-650w-port-side-exhaust": (PAC650, None, True),
    "hvac-hvdc-1200w-port-side-intake": (PUV, ["ac", "hvdc"], False),
    "hvac-hvdc-1200w-port-side-exhaust": (PUV, ["ac", "hvdc"], True),
    "dc-930w-port-side-intake": (PDC, "dc", False),
    "dc-930w-port-side-exhaust": (PDC, "dc", True),
}
BUILDS_500 = {
    "ac-500w-port-side-intake": (PAC500, None, False),
    "ac-500w-port-side-exhaust": (PAC500, None, True),
    "hvac-hvdc-1200w-port-side-intake": (PUV, ["ac", "hvdc"], False),
    "hvac-hvdc-1200w-port-side-exhaust": (PUV, ["ac", "hvdc"], True),
    "dc-930w-port-side-intake": (PDC, "dc", False),
    "dc-930w-port-side-exhaust": (PDC, "dc", True),
}

BLUE = "#50a2cf"


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


@pytest.mark.parametrize("name", [FX3, FX3S])
def test_the_sfp28_front_has_48_sfp28_then_6_qsfp28_numbered_down_each_column(name):
    p = placements(load(name), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "std/sfp-ganged@1", n
    for n in range(49, 55):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-55" not in p and "port-0" not in p
    # odd on the upper row, even beneath it, and the next column to the right
    for n in range(1, 54, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 49, 2)]
    assert xs == sorted(xs) and len(set(xs)) == 24
    # the SFP28 columns step 14.25 inside a group of twelve, and a gutter splits the two groups
    for i in range(11):
        assert xs[i + 1] - xs[i] == pytest.approx(14.25, abs=0.01)
        assert xs[i + 13] - xs[i + 12] == pytest.approx(14.25, abs=0.01)
    assert xs[12] - xs[11] > 14.25 + 3.0


@pytest.mark.parametrize("name", [FX3, FX3S])
def test_the_sfp28_front_carries_the_timing_jacks_and_lamps_the_guide_names(name):
    p = placements(load(name), "front")
    assert p["clk-1pps"]["ref"] == "std/smb@1" and p["clk-10mhz"]["ref"] == "std/smb@1"
    assert p["gnss-ant"]["ref"] == "std/sma@1"
    # callout 3: the LEDs, BCN, STS and ENV first
    for lamp in ("led-bcn", "led-sts", "led-env"):
        assert lamp in p, lamp
    for n in range(1, 55):
        assert f"led-port-{n}" in p, n


@pytest.mark.parametrize("name", [FX3, FX3S])
def test_the_sfp28_rear_has_console_mgmt_tod_and_usb_and_no_sfp_management(name):
    p = placements(load(name), "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["tod-rj45"]["attrs"]["role"] == "timing"
    assert p["usb"]["ref"] == "std/usb-a@1"
    assert "mgmt-sfp" not in p


def test_the_93108tc_front_has_48_rj45_then_6_qsfp28():
    p = placements(load(TC), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "common/rj45-ganged-eth-plain@1", n
    for n in range(49, 55):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-55" not in p and "port-0" not in p
    for n in range(1, 54, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 49, 2)]
    # three groups of eight columns on the ganged-jack pitch, 13.97, with a gutter between
    for g in range(3):
        for i in range(7):
            assert xs[8 * g + i + 1] - xs[8 * g + i] == pytest.approx(13.97, abs=0.01)
    assert xs[8] - xs[7] > 13.97 + 5.0 and xs[16] - xs[15] > 13.97 + 5.0
    for lamp in ("led-bcn", "led-sts", "led-env"):
        assert lamp in p, lamp
    for n in range(1, 55):
        assert f"led-port-{n}" in p, n


def test_the_93108tc_rear_has_console_two_management_ports_and_usb():
    p = placements(load(TC), "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1"
    assert p["usb"]["ref"] == "std/usb-a@1"
    assert "tod-rj45" not in p and "led-bcn-rear" in p and "led-sts-rear" in p


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_two_supply_bays_and_four_fan_bays_left_to_right(name):
    b = bays(load(name), "rear")
    assert [k for k in b if k.startswith("psu-")] == ["psu-1", "psu-2"]
    fans = [b[f"fan-{i}"]["at"][0] for i in range(1, 5)]
    assert fans == sorted(fans)
    assert b["psu-1"]["at"][0] < fans[0] and fans[3] < b["psu-2"]["at"][0]
    pitch = [fans[i + 1] - fans[i] for i in range(3)]
    assert max(pitch) - min(pitch) < 0.05
    assert all(b[f"fan-{i}"]["group"] == "fans" for i in range(1, 5))


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


def _flat(ref_or_map):
    return ref_or_map


@pytest.mark.parametrize("name,builds,fan,pn", [
    (FX3, BUILDS_650, FAN35, "N9K-C93180YC-FX3"),
    (FX3S, BUILDS_650, FAN35, "N9K-C93180YC-FX3S"),
    (TC, BUILDS_500, SFAN35, "N9K-C93108TC-FX3"),
])
def test_each_build_seats_matching_supplies_and_fans_with_matching_airflow(name, builds, fan, pn):
    d = load(name)
    cf = d["configurations"]
    mine = {n: c for n, c in cf.items() if not n.startswith("fx3h-")}
    assert set(mine) == set(builds)
    assert [n for n, c in cf.items() if c.get("default")] == ["base" if "base" in cf else next(
        n for n, c in cf.items() if c.get("kind") == "base")]
    assert d["chassis"]["airflow"] == "front-to-back"
    fan_name = fan.split("/")[1].split("@")[0]
    for cname, (psu, power, exhaust) in builds.items():
        c = mine[cname]
        assert list(c["part-numbers"]) == [pn], cname
        seated = c.get("bays") or {}
        if psu != PAC650 and psu != PAC500:
            assert seated == {"psu-1": psu, "psu-2": psu}, cname
        assert c.get("power") == power, cname
        for bay in ("fan-1", "fan-2", "fan-3", "fan-4"):
            assert bay not in seated  # the bay's own default is the family's one fan
        assert bays(d, "rear")["fan-1"]["default"] == fan
        if exhaust:
            assert c["airflow"] == "back-to-front", cname
            attrs = c["component-attrs"]
            assert attrs[fan_name]["latch-finish"] == BLUE, cname
            assert attrs[fan_name]["airflow"] == "back-to-front", cname
            psu_name = psu.split("/")[1].split("@")[0]
            if psu != PUV:
                assert attrs[psu_name]["latch-finish"] == BLUE, cname
                assert attrs[psu_name]["airflow"] == "back-to-front", cname
            else:
                assert psu_name not in attrs  # one white supply for both directions
        else:
            assert "airflow" not in c, cname
            assert fan_name not in (c.get("component-attrs") or {}), cname


def test_the_93180yc_fx3h_is_a_configuration_of_the_fx3_with_its_own_part_number():
    cf = load(FX3)["configurations"]
    h = {n: c for n, c in cf.items() if n.startswith("fx3h-")}
    assert {n[len("fx3h-"):] for n in h} == set(BUILDS_650)
    for n, c in h.items():
        assert list(c["part-numbers"]) == ["N9K-C93180YC-FX3H"], n
        assert c["kind"] == "orderable", n


@pytest.mark.parametrize("name", DEVICES)
def test_the_bays_accept_only_the_supplies_and_fans_the_guides_name(name):
    b = bays(load(name), "rear")
    ac = PAC500 if name == TC else PAC650
    fan = SFAN35 if name == TC else FAN35
    for k in ("psu-1", "psu-2"):
        assert set(b[k]["accepts"]) == {ac, PUV, PDC}
        assert b[k]["default"] == ac
    for i in range(1, 5):
        assert b[f"fan-{i}"]["accepts"] == [fan]


# ------------------------------------------------------ components, ears, kits


def test_each_supply_and_fan_the_guides_name_is_one_component_named_by_its_part_number():
    root = LIB / "components/cisco"
    assert [p.name for p in root.iterdir() if p.name.startswith("nxa-pac-650w")] == ["nxa-pac-650w"]
    for part, model in (("nxa-fan-35cfm", "NXA-FAN-35CFM"), ("nxa-sfan-35cfm", "NXA-SFAN-35CFM"),
                        ("nxa-pac-500w", "NXA-PAC-500W"), ("nxa-pdc-930w", "NXA-PDC-930W"),
                        ("n9k-puv-1200w", "N9K-PUV-1200W")):
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model
        assert c["class"] in ("psu", "fan") and "size" in c["provenance"]
    assert contract("nxa-fan-35cfm")["attrs"]["weight-kg"] == 0.12
    assert contract("nxa-sfan-35cfm")["attrs"]["weight-kg"] == 0.13
    assert contract("nxa-pac-500w")["attrs"]["power-output-w"] == 500
    assert contract("nxa-pdc-930w")["attrs"]["power-output-w"] == 930
    assert contract("n9k-puv-1200w")["attrs"]["power-output-w"] == 1230


def test_the_ears_state_the_two_ways_without_a_number_and_without_a_default():
    """Figure 503557 draws the bracket at two places and gives neither a dimension nor says which
    ships; the text gives clearances (3 in for cables, 1 in for module handles), not setbacks."""
    for name in DEVICES:
        ears = load(name)["chassis"]["ears"]
        assert [p["name"] for p in ears["positions"]] == ["recessed", "recessed"], name
        assert len({p["label"] for p in ears["positions"]}) == 2, name
        for p in ears["positions"]:
            assert "at" not in p and not p.get("default"), (name, p)


@pytest.mark.parametrize("name,kits", [(FX3, [KIT1]), (FX3S, [KIT1, KIT2]), (TC, [KIT1, KIT2])])
def test_the_listed_kits_are_the_ones_the_guide_names_and_each_resolves(name, kits):
    listed = [k["ref"] for k in load(name)["chassis"]["kits"]]
    assert listed == kits
    for ref in kits:
        k = yaml.safe_load((LIB / "components" / ref.split("@")[0] / "v1/contract.yaml").read_text())
        assert k["kind"] == "kit" and k["configurations"][0]["racks"] == ["4-post"]
    k1 = yaml.safe_load((LIB / "components/cisco/nxk-acc-kit-1ru/v1/contract.yaml").read_text())
    assert [(p["id"], p["count"]) for p in k1["parts"]] == [
        ("front-bracket", 2), ("rear-bracket", 2), ("slider-rail", 2)]
    assert k1["configurations"][0]["depth"] == [584.2, 762.0]  # 23.0 to 30.0 in


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_part_number_one_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Cisco"
    want = {"N9K-C93180YC-FX3", "N9K-C93180YC-FX3H", "N9K-C93180YC-FX3S", "N9K-C93108TC-FX3"}
    # the glob also finds batch 2's types, which test_cisco_nexus_9300_fx3p_fxp.py holds
    batch2 = {"N9K-C93108TC-FX3P", "N9K-C93108TC-FX3H", "N9K-C9348GC-FX3"}
    got = {p.stem for p in folder.glob("N9K-C93*-FX3*.yaml")} - batch2
    assert got == want
    for pn in want:
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Cisco" and doc["model"] == pn
        assert doc["u_height"] == 1.0


def test_the_exported_93180yc_fx3h_type_is_front_to_rear(tmp_path):
    """Run the exporter rather than read the committed file: the airflow comes from
    which build names the type, and only a fresh run shows that choice."""
    dist = LIB / "dist"
    if not (dist / "listings.json").exists():
        pytest.skip("library/dist not built")
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/dcim_export.py"),
                        "--dist", str(dist), "--out", str(tmp_path), "--no-raster",
                        "--device", FX3], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    doc = yaml.safe_load((tmp_path / "netbox/device-types/Cisco/N9K-C93180YC-FX3H.yaml").read_text())
    assert doc["airflow"] == "front-to-rear"


def test_the_exported_93108tc_type_lists_the_54_ports_and_the_management_ports():
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Cisco/N9K-C93108TC-FX3.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 55)} <= set(types)
    assert "port-55" not in types
    assert {types[f"port-{n}"] for n in range(1, 49)} == {"10gbase-t"}
    assert {types[f"port-{n}"] for n in range(49, 55)} == {"100gbase-x-qsfp28"}
