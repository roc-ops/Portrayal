"""The Arista 7010TX-48 switch family, the first Arista devices in the library (#1204).

One device, `arista/7010tx-48`: 48 x 10/100/1000BASE-T and four 1/10/25G SFP cages on a 1RU
chassis. Its AC and DC builds, front-to-back and back-to-front, and the same four builds of the
-48C are `kind: orderable` configurations of that one front panel. The expected figures are Arista's:
the 7010 Series 1RU Quick Start Guide (PDOC-00061-08, Table 1 for the envelope, Table 3 for the
power supplies, Appendix C and D for the faces, Appendix E for the fan) and the 7010X Series
Data Sheet (03-0052-14, 20 Aug 2025: ordering information and the technical specifications).
Each test reads the YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = "7010tx-48"

# configuration -> (airflow, power feed, the part numbers it orders under); datasheet ordering table
CONFIGS = {
    "ac-f": ("front-to-back", "ac", ["DCS-7010TX-48-F"]),
    "ac-r": ("back-to-front", "ac", ["DCS-7010TX-48-R"]),
    "dc-f": ("front-to-back", "dc", ["DCS-7010TX-48-DC-F"]),
    "dc-r": ("back-to-front", "dc", ["DCS-7010TX-48-DC-R"]),
    "ac-c-f": ("front-to-back", "ac", ["DCS-7010TX-48C-F"]),
    "ac-c-r": ("back-to-front", "ac", ["DCS-7010TX-48C-R"]),
    "dc-c-f": ("front-to-back", "dc", ["DCS-7010TX-48C-DC-F"]),
    "dc-c-r": ("back-to-front", "dc", ["DCS-7010TX-48C-DC-R"]),
}


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
    """Table 1: 48.3 x 4.4 x 25.8 cm, which is 19 in over the ears. The data sheet gives the body,
    17.3 in (43.9 cm) between the ears, and 4.35 cm high; the depth is the guide's 25.8 cm."""
    c = load()["chassis"]
    assert c["ru"] == 1
    assert c["width"] == pytest.approx(439.0, abs=0.5)
    assert c["height"] == pytest.approx(43.5, abs=0.5)
    assert c["depth"] == pytest.approx(258.0, abs=0.5)
    # the ears carry the body from 439 out to the guide's 483 across the rack face
    assert (483.0 - c["width"]) / 2 == pytest.approx(22.0, abs=0.5)


def test_every_face_is_sized_from_the_envelope():
    d = load()
    c = d["chassis"]
    views = d["views"]
    for v in ("front", "rear", "rear-dc"):
        assert views[v]["size"] == {"w": c["width"], "h": c["height"]}, v
    assert views["top"]["size"] == {"w": c["width"], "h": c["depth"]}
    assert views["bottom"]["size"] == {"w": c["width"], "h": c["depth"]}
    assert views["left"]["size"] == {"w": c["depth"], "h": c["height"]}
    assert views["right"]["size"] == {"w": c["depth"], "h": c["height"]}


def test_the_maker_and_the_names_are_as_printed():
    d = load()
    assert d["manufacturer"] == "Arista"
    assert d["model"] == "7010TX-48"
    assert d["portfolio"] == {"line": "7000 Series", "family": "7010TX"}
    assert d["maturity"] == "modelled"


def test_the_arista_maker_is_in_the_registry():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert reg["arista"]["display"] == "Arista Networks"
    assert reg["arista"]["role"] == "both"


# ------------------------------------------------------------------ the faces


@pytest.mark.parametrize("view", ["front"])
def test_the_front_has_48_jacks_numbered_as_printed_in_four_blocks_of_six_columns(view):
    d = load()
    jacks = [p for p in placements(d, view) if p["ref"] == "common/rj45-ganged-eth@1"]
    assert sorted(int(p["id"].split("-")[1]) for p in jacks) == list(range(1, 49))
    by_n = {int(p["id"].split("-")[1]): p for p in jacks}
    for n, p in by_n.items():
        assert p["rel-pos"] == n and p["group"] == "rj45"
        # Figure C-2 numbers down each column then across: the odd number is the upper jack,
        # turned 180 so that its latch is up
        assert p.get("rotate", 0) == (180 if n % 2 == 1 else 0)
    # the column pitch is the registry's 0.550 in; a block is six columns, the blocks a gutter apart
    xs = sorted({round(p["at"][0], 2) for p in jacks})
    assert len(xs) == 24
    for a, b in zip(xs, xs[1:]):
        step = round(b - a, 2)
        assert step == pytest.approx(13.97, abs=0.01) or step == pytest.approx(21.32, abs=0.02), step
    assert by_n[1]["at"][1] < by_n[2]["at"][1]
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "1g"}


@pytest.mark.parametrize("view", ["front"])
def test_the_four_sfp_cages_are_ports_49_to_52_in_two_rows(view):
    d = load()
    cages = {int(p["id"].split("-")[1]): p for p in placements(d, view)
             if p["ref"] == "std/sfp-ganged@1"}
    assert sorted(cages) == [49, 50, 51, 52]
    # odd number above even, the first pair left of the second, the cages abutting at 14.25
    assert cages[49]["at"][0] == cages[50]["at"][0] and cages[51]["at"][0] == cages[52]["at"][0]
    assert cages[51]["at"][0] - cages[49]["at"][0] == pytest.approx(14.25, abs=0.01)
    assert cages[50]["at"][1] - cages[49]["at"][1] == pytest.approx(15.0, abs=0.01)
    for p in cages.values():
        assert p["group"] == "sfp28"
    assert d["groups"]["sfp28"]["attrs"] == {"media": "sfp28", "speed": "25g"}


@pytest.mark.parametrize("view", ["front"])
def test_the_front_carries_the_management_console_usb_and_the_three_lamps(view):
    d = load()
    ps = {p["id"]: p for p in placements(d, view)}
    for pid in ("mgmt", "console", "usb", "led-system", "led-fan", "led-ps"):
        assert pid in ps, pid
    # an Ethernet jack takes the library's lamped single jack, a console jack the bare housing (L76)
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["usb"]["ref"] == "std/usb-a@1"
    assert ps["mgmt"]["attrs"]["role"] == "mgmt" and ps["console"]["attrs"]["role"] == "console"
    # Figure C-2: management on top, USB between, console below
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    # one lamp each for the system, the fan tray and the power supplies, one above the next
    ys = [ps[k]["at"][1] for k in ("led-system", "led-fan", "led-ps")]
    assert ys == sorted(ys)
    # four lamps under the cages, one per cage
    assert len([p for p in placements(d, view) if p["id"].startswith("led-sfp-")]) == 4


@pytest.mark.parametrize("view", ["front"])
def test_the_front_prints_the_model_and_reserves_the_logo_zone(view):
    d = load()
    front = d["views"][view]
    texts = {s.get("text") for s in front["silkscreen"] if s.get("text")}
    assert "7010TX-48" in texts
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name


def test_the_numerals_are_printed_for_every_port():
    d = load()
    for view in ("front",):
        printed = {s["for"]: s["text"] for s in d["views"][view]["silkscreen"]
                   if str(s.get("for", "")).startswith("port-") and s.get("text")}
        assert printed == {f"port-{n}": str(n) for n in range(1, 53)}, view


@pytest.mark.parametrize("view", ["rear", "rear-dc"])
def test_no_power_supply_is_a_bay_because_the_guide_says_only_the_fan_is_field_replaceable(view):
    d = load()
    b = bays(d, view)
    assert set(b) == {"fan"}
    assert b["fan"]["accepts"] == ["arista/7010tx-fan@1"]
    assert b["fan"]["default"] == "arista/7010tx-fan@1"


def test_the_ac_rear_has_two_c14_inlets_and_the_dc_rear_two_terminal_blocks():
    d = load()
    ac = [p for p in placements(d, "rear") if p["ref"] == "std/c14-inlet@1"]
    dc = [p for p in placements(d, "rear-dc") if p["ref"] == "arista/7010tx-dc-terminal@1"]
    assert len(ac) == 2 and len(dc) == 2
    assert not [p for p in placements(d, "rear") if p["ref"].startswith("arista/7010tx-dc-")]
    assert not [p for p in placements(d, "rear-dc") if p["ref"] == "std/c14-inlet@1"]
    # PS1 on the left of the rear view, PS2 on the right, each with its own status lamp
    for view in ("rear", "rear-dc"):
        ps = {p["id"]: p for p in placements(d, view)}
        assert ps["led-ps1"]["at"][0] < 100 < ps["led-ps2"]["at"][0]
        assert ps["ground"]["ref"] == "common/ground-stud-pair-5-8-m4@1"


def test_the_two_rears_share_the_fan_slot_and_the_vent():
    d = load()
    a, b = bays(d, "rear")["fan"], bays(d, "rear-dc")["fan"]
    assert (a["at"], a["size"]) == (b["at"], b["size"])


# ----------------------------------------------------------- the fan module


def test_the_fan_module_is_fan_7010x_and_reverses_by_a_field():
    c = contract("7010tx-fan")
    assert c["class"] == "fan" and c["kind"] == "module"
    assert list(c["part-numbers"]) == ["FAN-7010X"]
    f = c["fields"]["airflow"]
    assert f["type"] == "choice" and f["options"] == ["front-to-back", "back-to-front"]
    assert f["default"] == "front-to-back"


def test_the_dc_terminal_has_two_poles():
    c = contract("7010tx-dc-terminal")
    assert c["class"] == "inlet"
    assert sorted(k for k in c["elements"] if k.startswith("pole-")) == ["pole-1", "pole-2"]


def test_the_new_components_are_family_prefixed_and_cite_a_size():
    root = LIB / "components/arista"
    # other Arista families add their own folders; only this family's are checked here
    names = sorted(p.name for p in root.iterdir() if p.name.startswith("7010tx-"))
    assert names, "no 7010tx- component folders"
    for n in names:
        c = contract(n)
        assert "size" in (c.get("provenance") or {}), n


# ------------------------------------------------------------ configurations


def test_the_configurations_are_the_eight_builds_with_the_datasheets_part_numbers():
    cf = load()["configurations"]
    assert set(cf) == set(CONFIGS)
    for name, (airflow, feed, pns) in CONFIGS.items():
        c = cf[name]
        assert c["kind"] == "orderable"
        assert sorted(c["part-numbers"]) == sorted(pns), name
        if airflow == "back-to-front":
            assert c["airflow"] == airflow, name   # a reversed build must say so
        else:
            assert c.get("airflow", "front-to-back") == "front-to-back", name
        assert c.get("power", "ac") == feed, name
    assert [n for n, c in cf.items() if c.get("default")] == ["ac-f"]


def test_each_build_seats_the_fan_turned_to_its_airflow_and_the_dc_ones_use_the_dc_rear():
    cf = load()["configurations"]
    for name, (airflow, feed, _) in CONFIGS.items():
        c = cf[name]
        attrs = (c.get("bay-attrs") or {}).get("fan") or {}
        if airflow == "back-to-front":
            assert attrs["airflow"] == airflow, name   # the fan is turned only by saying so
        else:
            assert attrs.get("airflow", "front-to-back") == "front-to-back", name
        views = c.get("views") or {}
        assert views.get("rear", "rear") == ("rear-dc" if feed == "dc" else "rear"), name
        assert "front" not in views, name


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_configuration_one_u_high(target):
    d = load()
    # the exporter writes one type per configuration, named by its first part number: each of
    # the eight builds, the -48C ones as configurations of their own, is a type
    want = {next(iter(v["part-numbers"])) for v in d["configurations"].values()
            if v["kind"] == "orderable"}
    assert want == {"DCS-7010TX-48-F", "DCS-7010TX-48-R", "DCS-7010TX-48-DC-F", "DCS-7010TX-48-DC-R",
                    "DCS-7010TX-48C-F", "DCS-7010TX-48C-R", "DCS-7010TX-48C-DC-F",
                    "DCS-7010TX-48C-DC-R"}
    folder = LIB / "exports" / target / "device-types" / "Arista"
    # other Arista families export beside these four; they must all be present, not alone
    got = {p.stem for p in folder.glob("*.yaml")}
    assert want <= got, want - got
    mod = yaml.safe_load((LIB / "exports" / target / "module-types/Arista/FAN-7010X.yaml").read_text())
    assert mod["manufacturer"] == "Arista" and mod["part_number"] == "FAN-7010X"
    for pn in want:
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista"
        assert doc["model"] == pn
        assert doc["u_height"] == 1.0


def test_the_exported_type_lists_the_52_ports():
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7010TX-48-F.yaml").read_text())
    names = {i["name"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 53)} <= names
    assert "port-53" not in names
