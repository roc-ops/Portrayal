"""The Arista 7280CR3-32D4, a 1RU fixed switch router with 32 x 100G QSFP and 4 x 400G QSFP-DD (#1204, slice 1).

One device, `arista/7280cr3-32d4`. The 7280CR3K-32D4 and 7280CR3K-32D4A share its front panel
(guide figure C-4), size and weight (Table 1) and supplies (Table 4), so they are `kind: orderable`
configurations of it, each in its front-to-rear (-F) and rear-to-front (-R) builds. The expected
figures are Arista's: the 7280R3 Series Quick Start Guide (DOC-07041-01, Table 1 for the envelope,
Tables 3 and 4 for the supplies, Appendix C and D for the faces) and the 7280R3 Series Data Sheet
(03-0045-59, 11 August 2025: the 7280CR3-32D4 comparison table and its ordering information).
Each test reads the YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = "7280cr3-32d4"
AC, AC_R = "arista/7280cr3-pwr-1000-ac@1", "arista/7280cr3-pwr-1000-ac-rev@1"
DC, DC_R = "arista/7280cr3-pwr-1000-dc@1", "arista/7280cr3-pwr-1000-dc-rev@1"
FAN, FAN_R = "arista/7280cr3-fan@1", "arista/7280cr3-fan-rev@1"

# configuration -> (the part number it orders under, airflow); data sheet ordering information
ORDERABLE = {
    "f": ("DCS-7280CR3-32D4-F", "front-to-back"),
    "r": ("DCS-7280CR3-32D4-R", "back-to-front"),
    "k-f": ("DCS-7280CR3K-32D4-F", "front-to-back"),
    "k-r": ("DCS-7280CR3K-32D4-R", "back-to-front"),
    "k-a-f": ("DCS-7280CR3K-32D4A-F", "front-to-back"),
    "k-a-r": ("DCS-7280CR3K-32D4A-R", "back-to-front"),
}
MODULES = ("FAN-7011H-F", "FAN-7011H-R", "PWR-1011-AC-RED", "PWR-1011-AC-BLUE",
           "PWR-1011-DC-RED", "PWR-1011-DC-BLUE")


def load():
    return yaml.safe_load((LIB / "devices/arista" / DEV / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/arista" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


# ---------------------------------------------------------------- the envelope


def test_the_envelope_is_the_guides_table_1():
    """Table 1: 48.3 x 4.4 x 55.8 cm, 19 in over the ears and 1RU. The data sheet gives the body,
    43.99 x 4.37 x 55.83 cm; the width is the body's, the guide's figure being over the ears."""
    c = load()["chassis"]
    assert c["ru"] == 1
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(43.7, abs=0.5)
    assert c["depth"] == pytest.approx(558.0, abs=0.5)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)
    assert load()["attrs"]["physical"]["weight"].startswith("12.3 kg")


def test_every_face_is_sized_from_the_envelope():
    d = load()
    c = d["chassis"]
    v = d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


def test_the_maker_and_the_names_are_as_printed():
    d = load()
    assert d["manufacturer"] == "Arista"
    assert d["model"] == "7280CR3-32D4"
    assert d["portfolio"] == {"line": "7000 Series", "family": "7280CR3"}
    assert d["maturity"] == "modelled"


def test_the_arista_maker_is_in_the_registry():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert reg["arista"]["display"] == "Arista Networks"
    assert reg["arista"]["role"] == "both"


def test_the_device_has_a_layout_source_in_step_with_it():
    assert (LIB / "devices/arista" / DEV / "layout.yaml").is_file()


# ------------------------------------------------------------------ the front


def test_the_front_has_32_qsfp_cages_numbered_down_sixteen_columns():
    d = load()
    cages = {int(p["id"].split("-")[1]): p for p in placements(d, "front")
             if p["ref"] == "std/qsfp-ganged@1"}
    assert sorted(cages) == list(range(1, 33))
    for n, p in cages.items():
        assert p["rel-pos"] == n and p["group"] == "qsfp28"
        # the odd number is the upper cage, the even one below it and turned
        assert p.get("rotate", 0) == (180 if n % 2 == 0 else 0)
        if n % 2 == 1:
            assert p["at"][1] < cages[n + 1]["at"][1]
            assert p["at"][0] == cages[n + 1]["at"][0]
    xs = sorted({p["at"][0] for p in cages.values()})
    assert len(xs) == 16
    # inside a group of four columns the pitch is the registry's 19.0 mm
    for a, b in zip(xs[:3], xs[1:4]):
        assert b - a == pytest.approx(19.0, abs=0.02)
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}


def test_the_four_400g_qsfp_dd_cages_are_two_stacked_columns_numbered_33_to_36():
    d = load()
    dd = {p["id"]: p for p in placements(d, "front") if p["ref"] == "std/qsfp-dd@1"}
    assert sorted(dd) == ["port-33", "port-34", "port-35", "port-36"]
    assert dd["port-33"]["at"][0] == dd["port-34"]["at"][0]
    assert dd["port-35"]["at"][0] == dd["port-36"]["at"][0]
    assert dd["port-33"]["at"][0] < dd["port-35"]["at"][0]
    assert dd["port-33"]["at"][1] < dd["port-34"]["at"][1]
    assert dd["port-34"]["rotate"] == dd["port-36"]["rotate"] == 180
    qsfp = [p["at"][0] for p in placements(d, "front") if p["ref"] == "std/qsfp-ganged@1"]
    # figure C-4: the 400G columns sit between ports 15 and 17, in the middle of the face
    assert max(x for x in qsfp if x < dd["port-33"]["at"][0]) < dd["port-33"]["at"][0]
    assert min(x for x in qsfp if x > dd["port-35"]["at"][0]) > dd["port-35"]["at"][0]
    assert d["groups"]["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}


def test_every_cage_has_its_numeral_and_a_pair_of_lamps():
    d = load()
    printed = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
               if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert printed == {f"port-{n}": str(n) for n in range(1, 37)}
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    # figure C-4 draws two dots under each column, so two lamps a port
    assert len(lamps) == 72
    assert {p["for"] for p in lamps} == {f"port-{n}" for n in range(1, 37)}
    assert sorted(p["rel-pos"] for p in lamps) == list(range(1, 73))
    assert {p["id"][-1] for p in lamps} == {"a", "b"}


def test_the_front_carries_four_status_lamps_and_no_management_ports():
    d = load()
    ps = {p["id"]: p for p in placements(d, "front")}
    for pid in ("led-system", "led-fan", "led-ps1", "led-ps2"):
        assert pid in ps, pid
    ys = [ps[k]["at"][1] for k in ("led-system", "led-fan", "led-ps1", "led-ps2")]
    assert ys == sorted(ys)
    # figure C-4 draws the lamps at the right end, beyond every cage
    assert min(ps[k]["at"][0] for k in ("led-system", "led-fan", "led-ps1", "led-ps2")) > \
        max(p["at"][0] for p in placements(d, "front") if p["ref"] == "std/qsfp-ganged@1")
    assert not {"console", "usb", "mgmt"} & set(ps)


def test_the_front_prints_the_model_and_reserves_the_logo_zone():
    d = load()
    front = d["views"]["front"]
    assert "7280CR3-32D4" in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name


# ------------------------------------------------------------------- the rear


def test_the_rear_has_three_fan_bays_and_two_psu_bays_that_take_the_listed_modules():
    d = load()
    b = bays(d, "rear")
    assert sorted(b) == ["fan-1", "fan-2", "fan-3", "psu-1", "psu-2"]
    for i in range(1, 4):
        assert sorted(b[f"fan-{i}"]["accepts"]) == sorted([FAN, FAN_R])
        assert b[f"fan-{i}"]["default"] == FAN
    for i in (1, 2):
        assert sorted(b[f"psu-{i}"]["accepts"]) == sorted([AC, AC_R, DC, DC_R])
        assert b[f"psu-{i}"]["default"] == AC
    # figure D-2: a supply at each end, the three fans between them on an even pitch
    xs = [b[f"fan-{i}"]["at"][0] for i in (1, 2, 3)]
    assert xs[1] - xs[0] == pytest.approx(xs[2] - xs[1], abs=0.2)
    assert b["psu-1"]["at"][0] < xs[0] and xs[2] + 78.6 < b["psu-2"]["at"][0]


def test_the_rear_carries_the_management_console_and_usb_ports():
    ps = {p["id"]: p for p in placements(load(), "rear")}
    assert sorted(ps) == ["console", "mgmt", "usb"]
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["usb"]["ref"] == "std/usb-a@1"
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]


def test_the_modules_carry_the_data_sheets_part_numbers_and_airflow():
    want = {
        "7280cr3-fan": ("FAN-7011H-F", "fan", "front-to-back", None),
        "7280cr3-fan-rev": ("FAN-7011H-R", "fan", "back-to-front", None),
        "7280cr3-pwr-1000-ac": ("PWR-1011-AC-RED", "psu", "front-to-back", "ac"),
        "7280cr3-pwr-1000-ac-rev": ("PWR-1011-AC-BLUE", "psu", "back-to-front", "ac"),
        "7280cr3-pwr-1000-dc": ("PWR-1011-DC-RED", "psu", "front-to-back", "dc"),
        "7280cr3-pwr-1000-dc-rev": ("PWR-1011-DC-BLUE", "psu", "back-to-front", "dc"),
    }
    for name, (pn, cls, airflow, inp) in want.items():
        c = contract(name)
        assert list(c["part-numbers"]) == [pn] and c["class"] == cls, name
        assert c["attrs"]["airflow"] == airflow, name
        if cls == "psu":
            assert c["attrs"]["power-output-w"] == 1000 and c["attrs"]["input"] == inp
            assert c["size"] == {"w": 73.5, "h": 40.0}
    # the handle: red for an air-exit module, blue for an air-inlet one (guide section 2.1)
    for name, (pn, cls, airflow, inp) in want.items():
        finish = contract(name)["fields"]["handle-finish"]["default"].lower()
        r, g, b = (int(finish[i:i + 2], 16) for i in (1, 3, 5))
        assert (r > b) == (airflow == "front-to-back"), name


def test_the_new_components_are_family_prefixed_and_cite_a_size():
    root = LIB / "components/arista"
    names = sorted(p.name for p in root.iterdir() if p.name.startswith("7280cr3-"))
    assert names == ["7280cr3-fan", "7280cr3-fan-rev", "7280cr3-pwr-1000-ac",
                     "7280cr3-pwr-1000-ac-rev", "7280cr3-pwr-1000-dc", "7280cr3-pwr-1000-dc-rev"]
    for n in names:
        assert "size" in (contract(n).get("provenance") or {}), n


# ------------------------------------------------------------ configurations


def test_the_orderable_configurations_are_the_datasheets_f_and_r_part_numbers():
    cf = load()["configurations"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(ORDERABLE)
    for name, (pn, _) in ORDERABLE.items():
        assert list(cf[name]["part-numbers"]) == [pn], name
    # the DC builds are worked examples: the data sheet lists no DC part number
    for n in ("dc-f", "dc-r"):
        assert cf[n]["kind"] == "example" and "part-numbers" not in cf[n]
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]
    assert cf["base"]["kind"] == "base"


def test_each_configuration_seats_matching_supplies_and_fans_for_its_airflow():
    cf = load()["configurations"]
    for name, c in cf.items():
        bay = c.get("bays") or {}
        rear_to_front = c.get("airflow") == "back-to-front"
        dc = c.get("power") == "dc"
        psu = {(False, False): AC, (True, False): AC_R, (False, True): DC, (True, True): DC_R}[
            (rear_to_front, dc)]
        fan = FAN_R if rear_to_front else FAN
        if name in ("f", "k-f", "k-a-f", "base"):
            assert not bay, name       # the default seating is the AC, front-to-rear one
            continue
        assert bay["psu-1"] == bay["psu-2"] == psu, name
        if rear_to_front:
            assert {bay[f"fan-{i}"] for i in (1, 2, 3)} == {fan}, name
    for name, (pn, airflow) in ORDERABLE.items():
        assert cf[name].get("airflow", "front-to-back") == airflow, name
    assert load()["chassis"]["airflow"] == "front-to-back"


def test_the_k_a_build_states_its_own_figures_in_its_configurations():
    """Guide Table 4 and the data sheet's model comparison agree: 543 W / 865 W for the 7280CR3K-32D4A against
    535 W / 851 W. The data sheet gives it an eight-core CPU and a minimum EOS of 4.27.2; every K build has
    64 GB of memory, one value in its column. The device keeps the 7280CR3-32D4's figures."""
    d = load()
    cf = d["configurations"]
    for n in ("k-a-f", "k-a-r"):
        assert cf[n]["attrs"] == {
            "power": {"power-typical-w": 543, "power-max-w": 865},
            "platform": {"cpu": "Eight-Core x86", "memory": "64 GB"},
            "features": {"eos-license": "license group G3; minimum EOS 4.27.2"}}, n
        assert not re.search(r"\d+\s*W\b", cf[n]["description"]), n
    for n in ("k-f", "k-r"):
        assert cf[n]["attrs"] == {"platform": {"memory": "64 GB"}}, n
    for n in ("base", "f", "r", "dc-f", "dc-r"):
        assert "attrs" not in cf[n], n
    assert d["attrs"]["power"]["power-typical-w"] == 535
    assert d["attrs"]["power"]["power-max-w"] == 851
    assert not [g for g in d["gaps"] if g["what"] == "config-scoped-device-attrs"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_each_k_type_exports_its_own_memory_and_the_a_types_their_own_figures(target):
    folder = LIB / "exports" / target / "device-types" / "Arista"

    def doc(pn):
        return yaml.safe_load((folder / f"{pn}.yaml").read_text())

    def facts(pn):
        return (doc(pn)["comments"] + "\n")

    for pn in ("DCS-7280CR3K-32D4A-F", "DCS-7280CR3K-32D4A-R"):
        assert doc(pn)["description"].startswith("Arista 7280CR3K-32D4A - "), pn
        assert len(doc(pn)["description"]) <= 200
        for fact in ("power.power-typical-w: 543", "power.power-max-w: 865", "platform.cpu: Eight-Core x86",
                     "platform.memory: 64 GB", "features.eos-license: license group G3; minimum EOS 4.27.2"):
            assert f"- {fact}\n" in facts(pn), (pn, fact)
    for pn in ("DCS-7280CR3K-32D4-F", "DCS-7280CR3K-32D4-R"):
        assert "- platform.memory: 64 GB\n" in facts(pn), pn
        assert "- power.power-typical-w: 535\n" in facts(pn), pn
    for pn in ("DCS-7280CR3-32D4-F", "DCS-7280CR3-32D4-R"):
        assert "- platform.memory: 8 GB, 64 GB optional (7280CR3-32D4); 64 GB (7280CR3K-32D4 and -32D4A)\n" \
            in facts(pn), pn
        assert doc(pn)["description"].startswith("Arista 7280CR3-32D4 - "), pn


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_configuration_one_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    got = {p.stem for p in folder.glob("DCS-7280CR3*32D4*.yaml")}
    assert got == {pn for pn, _ in ORDERABLE.values()}
    for pn, _ in ORDERABLE.values():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == 1.0
    for pn in MODULES:
        mod = yaml.safe_load((LIB / "exports" / target / "module-types/Arista" / f"{pn}.yaml").read_text())
        assert mod["manufacturer"] == "Arista" and mod["part_number"] == pn


def test_the_exported_type_lists_the_36_ports_and_no_more():
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7280CR3-32D4-F.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 37)} <= set(types)
    assert "port-37" not in types and "port-0" not in types
    assert {types[f"port-{n}"] for n in range(1, 33)} == {"100gbase-x-qsfp28"}
    assert {types[f"port-{n}"] for n in range(33, 37)} == {"400gbase-x-qsfpdd"}
