"""The Arista 7280CR3A-24D12, 7280CR3A-48D6 and 7280CR3A-72, the rest of the 7280R3A (#1204, slice 1).

Three devices, one per front panel: `arista/7280cr3a-24d12` (1RU), `arista/7280cr3a-48d6` and
`arista/7280cr3a-72` (2RU). The M and K builds (and the 24D12's K secure-boot build) share their
base model's face, size, weight and supplies (7280R3A Quick Start Guide, DOC-07042-01, Table 1),
so they are `kind: orderable` configurations of it, with front-to-rear (-F) and rear-to-front (-R)
builds as the data sheet's ordering information lists them. The expected figures are Arista's: the
guide (Table 1 for the envelope, Table 4 for the supplies, Appendix D for the rear) and the 7280R3A
Series Data Sheet (04-0040-26, 15 April 2025: the model comparison tables and the ordering
information). The guide draws no front figure for these three, so every front position is read off
the data sheet's photographs and is `estimated`; the counts and groupings are what these tests hold.
Each test reads the YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

R3_AC = "arista/7280r3-pwr-1500-ac@1"            # PWR-1511-AC-RED
R3_DC = "arista/7280r3-pwr-1500-dc@1"            # PWR-1511-DC-RED
X4_DC_REV = "arista/7050x4-pwr-1500-dc-rev@1"    # PWR-1511-DC-BLUE
A_1511_REV = "arista/7280cr3a-pwr-1511-ac-rev@1"  # PWR-1511-AC-BLUE
X4_AC = "arista/7050x4-pwr-1500-ac@1"            # PWR-1512-AC-RED
X4_AC_REV = "arista/7050x4-pwr-1500-ac-rev@1"    # PWR-1512-AC-BLUE
A_1513 = "arista/7280cr3a-pwr-1513-ac@1"
A_1513_REV = "arista/7280cr3a-pwr-1513-ac-rev@1"
FAN_1U, FAN_1U_REV = "arista/7280cr3-fan@1", "arista/7280cr3-fan-rev@1"      # FAN-7011H-F / -R
FAN_2U, FAN_2U_REV = "arista/7280dr3a-fan@1", "arista/7050x4-fan-7012h-rev@1"  # FAN-7012H-RED / -BLUE

# device -> everything the guide's Table 1 and the data sheet say about it
DEVICES = {
    "7280cr3a-24d12": dict(
        model="7280CR3A-24D12", ru=1, height=43.7, depth=592.0, weight=14.8, fans=3,
        psu_ac=R3_AC, psu_ac_rev=A_1511_REV, psu_dc=R3_DC, psu_dc_rev=X4_DC_REV,
        psu_accepts=[R3_AC, A_1511_REV, R3_DC, X4_DC_REV],
        fan=FAN_1U, fan_rev=FAN_1U_REV,
        typical=346, maximum=845,
        orderable={
            "f": "DCS-7280CR3A-24D12-F", "r": "DCS-7280CR3A-24D12-R",
            "m-f": "DCS-7280CR3AM-24D12-F", "m-r": "DCS-7280CR3AM-24D12-R",
            "k-f": "DCS-7280CR3AK-24D12-F", "k-r": "DCS-7280CR3AK-24D12-R",
            "ks-f": "DCS-7280CR3AK-24D12-S-F", "ks-r": "DCS-7280CR3AK-24D12-S-R",
        }),
    "7280cr3a-48d6": dict(
        model="7280CR3A-48D6", ru=2, height=87.9, depth=683.8, weight=22.0, fans=4,
        psu_ac=X4_AC, psu_ac_rev=X4_AC_REV, psu_dc=R3_DC, psu_dc_rev=X4_DC_REV,
        psu_accepts=[X4_AC, X4_AC_REV, R3_DC, X4_DC_REV],
        fan=FAN_2U, fan_rev=FAN_2U_REV,
        typical=388, maximum=979,
        orderable={
            "f": "DCS-7280CR3A-48D6-F", "r": "DCS-7280CR3A-48D6-R",
            "m-f": "DCS-7280CR3AM-48D6-F", "m-r": "DCS-7280CR3AM-48D6-R",
            "k-f": "DCS-7280CR3AK-48D6-F", "k-r": "DCS-7280CR3AK-48D6-R",
        }),
    "7280cr3a-72": dict(
        model="7280CR3A-72", ru=2, height=87.9, depth=686.9, weight=22.4, fans=4,
        psu_ac=X4_AC, psu_ac_rev=X4_AC_REV, psu_dc=R3_DC, psu_dc_rev=X4_DC_REV,
        psu_accepts=[X4_AC, X4_AC_REV, A_1513, A_1513_REV, R3_DC, X4_DC_REV],
        fan=FAN_2U, fan_rev=FAN_2U_REV,
        typical=406, maximum=754,
        orderable={
            "f": "DCS-7280CR3A-72-F", "r": "DCS-7280CR3A-72-R",
            "m-f": "DCS-7280CR3AM-72-F", "m-r": "DCS-7280CR3AM-72-R",
            "k-f": "DCS-7280CR3AK-72-F", "k-r": "DCS-7280CR3AK-72-R",
        }),
}
# the cages each face carries, from the data sheet's model comparison table: (ref, ids)
PORTS = {
    "7280cr3a-24d12": [("std/qsfp-ganged@1", range(1, 25)), ("std/qsfp-dd@1", range(25, 37))],
    "7280cr3a-48d6": [("std/qsfp-ganged@1", range(1, 49)), ("std/qsfp-dd@1", range(49, 55)),
                      ("std/osfp@1", range(55, 56))],
    "7280cr3a-72": [("std/qsfp-ganged@1", range(1, 73))],
}
ALL = sorted(DEVICES)


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def contract(ref):
    name = ref.split("@")[0].split("/", 1)[1]
    return yaml.safe_load((LIB / "components/arista" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def ports(d):
    return {p["id"]: p for p in placements(d, "front") if p["id"].startswith("port-")}


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("dev", ALL)
def test_the_envelope_is_the_guides_table_1(dev):
    """Table 1 gives 48.3 x 4.4 (1RU) or 8.8 (2RU) x depth cm over the ears; the data sheet gives the
    body, 43.99 cm wide. The width is the body's, the height and depth the data sheet's."""
    want, c = DEVICES[dev], load(dev)["chassis"]
    assert c["ru"] == want["ru"]
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(44.0 if want["ru"] == 1 else 88.0, abs=0.5)
    assert c["height"] == want["height"] and c["depth"] == want["depth"]
    assert c["weight-kg"] == pytest.approx(want["weight"], abs=0.05)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)


@pytest.mark.parametrize("dev", ALL)
def test_every_face_is_sized_from_the_envelope(dev):
    d = load(dev)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


@pytest.mark.parametrize("dev", ALL)
def test_the_maker_and_the_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Arista"
    assert d["model"] == DEVICES[dev]["model"]
    assert d["portfolio"] == {"line": "7000 Series", "family": "7280R3A"}
    assert {"name": "DCS-" + d["model"], "kind": "marketing"} in d["aliases"]
    assert d["maturity"] == "modelled"


@pytest.mark.parametrize("dev", ALL)
def test_the_power_draw_is_the_data_sheets_because_the_guide_says_tbd(dev):
    p = load(dev)["attrs"]["power"]
    assert p["power-draw-typical-w"] == DEVICES[dev]["typical"]
    assert p["power-draw-max-w"] == DEVICES[dev]["maximum"]


# ------------------------------------------------------------------ the front


@pytest.mark.parametrize("dev", ALL)
def test_each_face_has_the_cages_the_data_sheet_counts_numbered_as_the_ids_say(dev):
    d = load(dev)
    got = ports(d)
    want_ids = {f"port-{n}": ref for ref, ns in PORTS[dev] for n in ns}
    assert sorted(got, key=lambda i: int(i.split("-")[1])) == sorted(want_ids, key=lambda i: int(i.split("-")[1]))
    for pid, ref in want_ids.items():
        assert got[pid]["ref"] == ref, pid
        assert got[pid]["rel-pos"] == int(pid.split("-")[1]) or got[pid]["group"] == "osfp-ls-400g", pid
    # the media of each group is what the data sheet names
    g = d["groups"]
    assert g["qsfp28-100g"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    if dev != "7280cr3a-72":
        assert g["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}
    if dev == "7280cr3a-48d6":
        assert g["osfp-ls-400g"]["attrs"] == {"media": "osfp", "speed": "400g"}
        assert got["port-55"]["rotate"] == 90
    else:
        assert not [p for p in got.values() if p["ref"] == "std/osfp@1"]


@pytest.mark.parametrize("dev", ALL)
def test_stacked_cages_pair_the_odd_port_over_the_even_one_and_turn_the_lower_over(dev):
    got = ports(load(dev))
    for ref in ("std/qsfp-ganged@1", "std/qsfp-dd@1"):
        mine = {int(i.split("-")[1]): p for i, p in got.items() if p["ref"] == ref}
        for n in sorted(mine):
            if n % 2 == 1:
                upper, lower = mine[n], mine[n + 1]
                assert upper["at"][0] == lower["at"][0], n
                assert upper["at"][1] < lower["at"][1], n
                assert upper.get("rotate", 0) == 0 and lower.get("rotate") == 180, n


def test_the_24d12_has_three_blocks_of_six_columns_with_the_400g_in_the_middle():
    got = ports(load("7280cr3a-24d12"))
    xs = {n: got[f"port-{n}"]["at"][0] for n in range(1, 37)}
    left = sorted({xs[n] for n in range(1, 13)})
    right = sorted({xs[n] for n in range(13, 25)})
    mid = sorted({xs[n] for n in range(25, 37)})
    assert len(left) == len(right) == len(mid) == 6
    assert left[-1] < mid[0] and mid[-1] < right[0]
    # the registry's ganged pitch inside a block; the QSFP-DD cages are spread wider
    for a, b in zip(left, left[1:]):
        assert b - a == pytest.approx(19.0, abs=0.02)
    for a, b in zip(mid, mid[1:]):
        assert b - a == pytest.approx(25.45, abs=0.02)
    # two rows on one grid in every block
    assert len({got[f"port-{n}"]["at"][1] for n in range(1, 25, 2)}) == 1
    assert len({got[f"port-{n}"]["at"][1] for n in range(25, 37, 2)}) == 1


@pytest.mark.parametrize("dev,blocks", [("7280cr3a-48d6", 6), ("7280cr3a-72", 9)])
def test_the_2ru_faces_are_blocks_of_two_columns_and_four_rows(dev, blocks):
    got = ports(load(dev))
    qsfp = {int(i.split("-")[1]): p for i, p in got.items() if p["ref"] == "std/qsfp-ganged@1"}
    assert len(qsfp) == blocks * 8
    assert len({p["at"][1] for p in qsfp.values()}) == 4          # four rows
    cols = sorted({p["at"][0] for p in qsfp.values()})
    assert len(cols) == blocks * 2
    pairs = list(zip(cols[0::2], cols[1::2]))                     # a block is two columns
    assert all(b - a == pytest.approx(19.0, abs=0.02) for a, b in pairs)
    gutters = [cols[i + 1] - cols[i] for i in range(1, len(cols) - 1, 2)]
    assert len({round(g, 2) for g in gutters}) <= 2 and min(gutters) > 19.0
    # the upper band of rows is numbered first, the lower band after it
    rows = sorted({p["at"][1] for p in qsfp.values()})
    upper = {n for n, p in qsfp.items() if p["at"][1] in rows[:2]}
    assert upper == set(range(1, blocks * 4 + 1))
    for a, b in zip(rows, rows[1:]):
        assert b - a == pytest.approx(15.1, abs=0.02)


@pytest.mark.parametrize("dev", ALL)
def test_every_port_has_a_lamp_and_the_front_carries_four_status_lamps(dev):
    d = load(dev)
    ps = {p["id"]: p for p in placements(d, "front")}
    lamps = [p for p in ps.values() if p["id"].startswith("led-port-")]
    for pid in ports(d):
        mine = [p for p in lamps if p["for"] == pid]
        assert len(mine) == (2 if dev == "7280cr3a-24d12" and int(pid.split("-")[1]) <= 24 else 1), pid
    for lid, target in (("led-system", "chassis"), ("led-fan", None), ("led-ps1", "rear/psu-1"),
                        ("led-ps2", "rear/psu-2")):
        assert lid in ps, lid
        if target:
            assert ps[lid]["for"] == target
    assert ps["led-fan"]["for"] == [f"rear/fan-{i}" for i in range(1, DEVICES[dev]["fans"] + 1)]


@pytest.mark.parametrize("dev", ALL)
def test_the_front_carries_console_usb_management_and_timing(dev):
    ps = {p["id"]: p for p in placements(load(dev), "front")}
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["usb"]["ref"] == "std/usb-a@1"
    assert ps["tod"]["ref"] == "std/usb-c@1"
    assert ps["pps"]["ref"] == ps["clk-10mhz"]["ref"] == "std/smb@1"
    if dev == "7280cr3a-72":
        # a row at the top right: the management port, the USB port, then the console
        assert ps["mgmt"]["at"][0] < ps["usb"]["at"][0] < ps["console"]["at"][0]
    else:
        assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    assert min(ps[k]["at"][0] for k in ("mgmt", "usb", "console")) > 340


@pytest.mark.parametrize("dev", ALL)
def test_the_front_prints_no_logo_and_reserves_the_logo_zone(dev):
    d = load(dev)
    front = d["views"]["front"]
    texts = {str(s.get("text", "")) for s in front["silkscreen"]}
    assert d["model"] in texts
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name


@pytest.mark.parametrize("dev", ALL)
def test_everything_read_off_a_photograph_says_so(dev):
    """The guide has no front figure, so the front is estimated and its provenance says which
    photograph, the scale anchor and the measure."""
    d = load(dev)
    prov = d["provenance"]
    for key in ("gate-1-front", "front-ports", "port-numbering", "port-lamps", "status-lamps",
                "management-ports", "timing"):
        assert prov[key]["confidence"] == "estimated", key
    note = prov["gate-1-front"]["note"]
    assert "DATA SHEET'S PHOTOGRAPH" in note and "px/mm" in note and "440.0 mm" in note
    assert any(g["what"] == "front-from-photograph" for g in d["gaps"])


# ------------------------------------------------------------------- the rear


@pytest.mark.parametrize("dev", ALL)
def test_the_rear_has_the_fan_and_psu_bays_that_take_the_listed_modules(dev):
    want, d = DEVICES[dev], load(dev)
    b = bays(d, "rear")
    fans = want["fans"]
    assert sorted(b) == sorted([f"fan-{i}" for i in range(1, fans + 1)] + ["psu-1", "psu-2"])
    for i in range(1, fans + 1):
        assert b[f"fan-{i}"]["accepts"] == [want["fan"], want["fan_rev"]]
        assert b[f"fan-{i}"]["default"] == want["fan"]
    for i in (1, 2):
        assert b[f"psu-{i}"]["accepts"] == want["psu_accepts"]
        assert b[f"psu-{i}"]["default"] == want["psu_ac"]
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, fans + 1)]
    assert xs == sorted(xs)
    if want["ru"] == 2:
        # figure D-3: the supplies stand one above the other at the right, and a grounding strip
        # with two studs separates fan 1 from fan 2
        assert b["psu-1"]["at"][0] == b["psu-2"]["at"][0] > b[f"fan-{fans}"]["at"][0]
        assert b["psu-1"]["at"][1] < b["psu-2"]["at"][1]
        assert [p["id"] for p in placements(d, "rear")] == ["ground-1", "ground-2"]
    else:
        # figure D-2: a supply at each end of the 1RU rear, three fans between
        assert b["psu-1"]["at"][0] < b["fan-1"]["at"][0] and b["psu-2"]["at"][0] > b["fan-3"]["at"][0]


@pytest.mark.parametrize("dev", ALL)
def test_the_modules_carry_the_data_sheets_part_numbers_and_airflow(dev):
    want = DEVICES[dev]
    red = {"PWR-1511-AC-RED": R3_AC, "PWR-1511-DC-RED": R3_DC, "PWR-1512-AC-RED": X4_AC,
           "PWR-1513-AC-RED": A_1513, "FAN-7011H-F": FAN_1U, "FAN-7012H-RED": FAN_2U}
    blue = {"PWR-1511-AC-BLUE": A_1511_REV, "PWR-1511-DC-BLUE": X4_DC_REV, "PWR-1512-AC-BLUE": X4_AC_REV,
            "PWR-1513-AC-BLUE": A_1513_REV, "FAN-7011H-R": FAN_1U_REV, "FAN-7012H-BLUE": FAN_2U_REV}
    used = set(want["psu_accepts"]) | {want["fan"], want["fan_rev"]}
    for pn, ref in {**red, **blue}.items():
        if ref not in used:
            continue
        c = contract(ref)
        assert pn in c["part-numbers"], (pn, ref)
        # a red handle is an air-exit module and a blue one an air-inlet module (guide section 2.1)
        assert c["attrs"]["airflow"] == ("front-to-back" if pn in red else "back-to-front"), pn
        assert c["class"] in ("psu", "fan")
    for ref in (R3_AC, X4_AC, A_1513):
        assert contract(ref)["attrs"]["power-output-w"] == 1500 and contract(ref)["attrs"]["input"] == "ac"
    for ref in (A_1511_REV, X4_AC_REV, A_1513_REV):
        assert contract(ref)["fields"]["handle-finish"]["default"] == "#3d7bd6"
    for ref in (R3_DC, X4_DC_REV):
        assert contract(ref)["attrs"]["input"] == "dc"
    assert contract(A_1513)["attrs"]["input-note"].startswith("200 - 240 VAC, 8.5 A")


def test_only_the_part_numbers_main_lacks_became_components():
    root = LIB / "components/arista"
    mine = sorted(p.name for p in root.iterdir() if p.name.startswith("7280cr3a-"))
    assert mine == ["7280cr3a-pwr-1511-ac-rev", "7280cr3a-pwr-1513-ac", "7280cr3a-pwr-1513-ac-rev"]
    for n in mine:
        c = contract(f"arista/{n}")
        assert "size" in c["provenance"] and "face" in c["provenance"], n
        assert c["size"] == {"w": 73.5, "h": 40.0}


# ------------------------------------------------------------ configurations


@pytest.mark.parametrize("dev", ALL)
def test_the_orderable_configurations_are_the_datasheets_part_numbers(dev):
    cf = load(dev)["configurations"]
    want = DEVICES[dev]["orderable"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(want)
    for name, pn in want.items():
        assert list(cf[name]["part-numbers"]) == [pn], name
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]
    for n, c in cf.items():
        if c["kind"] == "example":
            assert "part-numbers" not in c, n


@pytest.mark.parametrize("dev", ALL)
def test_each_configuration_seats_matching_supplies_and_fans_with_matching_airflow(dev):
    want, cf = DEVICES[dev], load(dev)["configurations"]
    fans = [f"fan-{i}" for i in range(1, want["fans"] + 1)]
    for name, c in cf.items():
        seats = c.get("bays") or {}
        if name == "r" or name.endswith("-r"):
            # a rear-to-front build: blue supplies and blue fans, and the airflow said
            assert c["airflow"] == "back-to-front", name
            assert all(seats[f] == want["fan_rev"] for f in fans), name
            blue = want["psu_dc_rev"] if name == "dc-r" else (
                A_1513_REV if name == "ac1513-r" else want["psu_ac_rev"])
            assert seats["psu-1"] == seats["psu-2"] == blue, name
        elif name.startswith("dc-"):
            assert c["power"] == "dc" and seats == {"psu-1": want["psu_dc"], "psu-2": want["psu_dc"]}
        elif name == "ac1513-f":
            assert seats == {"psu-1": A_1513, "psu-2": A_1513}
        else:
            # the base chassis and every -F build: the bays' defaults, red and front-to-rear
            assert seats == {} and "airflow" not in c, name
    assert load(dev)["chassis"]["airflow"] == "front-to-back"
    assert cf["dc-f"]["kind"] == cf["dc-r"]["kind"] == "example"


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", ALL)
def test_the_dcim_types_export_one_per_orderable_configuration_at_the_guides_height(dev, target):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    want = set(DEVICES[dev]["orderable"].values())
    stem = DEVICES[dev]["model"].replace("7280CR3A-", "")           # 24D12, 48D6 or 72
    got = {p.stem for p in folder.glob("DCS-7280CR3A*-*.yaml")
           if p.stem.split("-", 2)[2].replace("-S", "").rsplit("-", 1)[0] == stem}
    assert got == want
    for pn in want:
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == float(DEVICES[dev]["ru"])


def test_the_exported_types_list_each_faces_ports_and_no_more():
    folder = LIB / "exports/netbox/device-types/Arista"
    for dev, pn in (("7280cr3a-24d12", "DCS-7280CR3A-24D12-F"), ("7280cr3a-48d6", "DCS-7280CR3A-48D6-F"),
                    ("7280cr3a-72", "DCS-7280CR3A-72-F")):
        types = {i["name"]: i["type"] for i in yaml.safe_load((folder / f"{pn}.yaml").read_text())["interfaces"]}
        last = {"7280cr3a-24d12": 36, "7280cr3a-48d6": 55, "7280cr3a-72": 72}[dev]
        assert {f"port-{n}" for n in range(1, last + 1)} <= set(types), dev
        assert f"port-{last + 1}" not in types and "port-0" not in types, dev
    types = {i["name"]: i["type"] for i in yaml.safe_load(
        (folder / "DCS-7280CR3A-48D6-F.yaml").read_text())["interfaces"]}
    assert {types[f"port-{n}"] for n in range(49, 55)} == {"400gbase-x-qsfpdd"}
    assert types["port-55"] == "400gbase-x-osfp"
    assert {types[f"port-{n}"] for n in range(1, 49)} == {types["port-1"]}
