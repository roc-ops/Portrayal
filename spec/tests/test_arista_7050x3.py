"""The Arista 7050X3 line, four fixed switches (#1204, slice 1).

Devices, one per front panel, under `arista/`:

    7050cx3-32s       DCS-7050CX3-32S      32 QSFP100 and 2 SFP+, four fans, PWR-500AC / PWR-500-DC
    7050sx3-48yc12    DCS-7050SX3-48YC12   48 SFP25 and 12 QSFP100, four fans, PWR-500AC / PWR-500-DC
    7050sx3-48yc8     DCS-7050SX3-48YC8    48 SFP25 and 8 QSFP100, two fans, PWR-511-AC / PWR-511-DC
    7050tx3-48c8      DCS-7050TX3-48C8     48 10GBASE-T and 8 QSFP100, two fans, PWR-511-AC / PWR-511-DC

The expected figures are Arista's: the 7050 Series 1RU (Gen 3) Quick Start Guide (DOC-00141-08: Table 1
for the envelope, Tables 3 and 4 for the supplies and the power draw, Appendix C for the front faces,
Appendix D for the rear) and the 7050X3 Series Data Sheet (03-0040-46: the model comparison, the power
supply specifications and the spares list). Each test reads the YAML a contributor edits, or the
generated device.yaml beside it.
"""
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SFPG, QSFPG, RJ45G = ("std/sfp-ganged@1", "std/qsfp-ganged@1", "common/rj45-ganged-eth-plain@1")

P500 = ["arista/7050x3-pwr-500-ac@1", "arista/7050x3-pwr-500-dc@1"]
P511 = ["arista/7280r3-pwr-500-ac@1", "arista/7280r3-pwr-500-ac-rev@1",
        "arista/7280r3-pwr-500-dc@1", "arista/7280r3-pwr-500-dc-rev@1"]
F7000H = ["arista/7050x3-fan-7000h@1"]
F7011M = ["arista/7280r3-fan-m@1", "arista/7280r3-fan-m-rev@1"]

# name -> what the guide and the data sheet say of it. `ports` is {number: (cage ref, group)}.
DEVICES = {
    "7050cx3-32s": dict(
        model="7050CX3-32S", depth=406.0, guide_kg=8.8, typical=206, maximum=314,
        ports={**{n: (QSFPG, "qsfp28") for n in range(1, 33)}, 33: (SFPG, "sfp-plus"), 34: (SFPG, "sfp-plus")},
        speeds={"qsfp28": "100g", "sfp-plus": "10g"}, psu=P500, fan=F7000H, nfans=4, mgmt_view="front",
        disagree={"power": ("168", "343"), "weight": ("9.1",)}),
    "7050sx3-48yc12": dict(
        model="7050SX3-48YC12", depth=444.0, guide_kg=9.2, typical=170, maximum=325,
        ports={**{n: (SFPG, "sfp28") for n in range(1, 49)}, **{n: (QSFPG, "qsfp28") for n in range(49, 61)}},
        speeds={"sfp28": "25g", "qsfp28": "100g"}, psu=P500, fan=F7000H, nfans=4, mgmt_view="rear",
        disagree={}),
    "7050sx3-48yc8": dict(
        model="7050SX3-48YC8", depth=468.0, guide_kg=9.5, typical=165, maximum=345,
        ports={**{n: (SFPG, "sfp28") for n in range(1, 49)}, **{n: (QSFPG, "qsfp28") for n in range(49, 57)}},
        speeds={"sfp28": "25g", "qsfp28": "100g"}, psu=P511, fan=F7011M, nfans=2, mgmt_view="rear",
        disagree={"power": ("124", "301")}),
    "7050tx3-48c8": dict(
        model="7050TX3-48C8", depth=467.0, guide_kg=9.4, typical=212, maximum=346,
        ports={**{n: (RJ45G, "rj45") for n in range(1, 49)}, **{n: (QSFPG, "qsfp28") for n in range(49, 57)}},
        speeds={"rj45": "10g", "qsfp28": "100g"}, psu=P511, fan=F7011M, nfans=2, mgmt_view="rear",
        disagree={}),
}
NAMES = sorted(DEVICES)
NEW_PARTS = ["7050x3-pwr-500-ac", "7050x3-pwr-500-dc", "7050x3-fan-7000h"]


def load(name):
    return yaml.safe_load((LIB / "devices/arista" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/arista" / name / "layout.yaml").read_text())


def contract_of(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def ports(d):
    return {int(p["id"].split("-")[1]): p for p in placements(d, "front") if re.fullmatch(r"port-\d+", p["id"])}


# ------------------------------------------------------------------ the folders


@pytest.mark.parametrize("name", NAMES)
def test_the_device_folder_holds_a_layout_and_its_expansion(name):
    folder = LIB / "devices/arista" / name
    for f in ("layout.yaml", "device.yaml", "device.lock.json"):
        assert (folder / f).is_file(), f


def test_every_layout_expands_to_its_device_yaml():
    out = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/expand.py"), "--check"]
        + [str(LIB / "devices/arista" / n / "layout.yaml") for n in NAMES],
        capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stdout + out.stderr


# ------------------------------------------------------------------ the envelope


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_guides_table_1(name):
    """Table 1: 48.3 cm over the ears (the body between them is the data sheet's 44 cm), 1RU, and the
    depth the guide prints: 40.6, 44.4, 46.8 and 46.7 cm."""
    want = DEVICES[name]
    c = load(name)["chassis"]
    assert c["ru"] == 1
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(43.7, abs=0.1)
    assert c["depth"] == pytest.approx(want["depth"], abs=0.1)


@pytest.mark.parametrize("name", NAMES)
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


@pytest.mark.parametrize("name", NAMES)
def test_the_maker_and_the_names_are_as_printed(name):
    d = load(name)
    assert d["manufacturer"] == "Arista"
    assert d["model"] == DEVICES[name]["model"]
    assert d["portfolio"] == {"line": "7000 Series", "family": "7050X3"}
    assert d["maturity"] == "modelled"


# ------------------------------------------------------------------ the front


@pytest.mark.parametrize("name", NAMES)
def test_the_ports_are_the_guides_model_table(name):
    """The count, the cage and the speed of every port, numbered as the figure prints."""
    want, d = DEVICES[name], load(name)
    got = ports(d)
    assert sorted(got) == sorted(want["ports"])
    for n, (ref, group) in want["ports"].items():
        assert got[n]["ref"] == ref, n
        assert got[n]["group"] == group, n
    for group, speed in want["speeds"].items():
        assert d["groups"][group]["attrs"]["speed"] == speed, group


@pytest.mark.parametrize("name", NAMES)
def test_the_management_ports_are_on_the_face_the_figures_put_them(name):
    """Figure C-13 draws the CX3-32S management, USB and console ports on the front; the other three fronts
    draw none, and the rear panels D-2 and D-3 carry them."""
    d = load(name)
    here, there = DEVICES[name]["mgmt_view"], {"front": "rear", "rear": "front"}[DEVICES[name]["mgmt_view"]]
    ids = {p["id"] for p in placements(d, here)}
    assert {"mgmt", "usb", "console"} <= ids
    assert not {"mgmt", "usb", "console"} & {p["id"] for p in placements(d, there)}


@pytest.mark.parametrize("name", NAMES)
def test_the_four_system_lamps_are_on_the_front(name):
    ids = {p["id"] for p in placements(load(name), "front")}
    assert {"led-system", "led-fan", "led-ps1", "led-ps2"} <= ids


# ------------------------------------------------------------------ the rear


@pytest.mark.parametrize("name", NAMES)
def test_the_supplies_and_fans_are_the_ones_the_tables_name(name):
    """Table 4 lists PWR-500AC and PWR-500-DC for the CX3-32S and SX3-48YC12 and PWR-511-AC and -DC for the
    other two; the data sheet gives four fans to the first pair and two to the second."""
    want, d = DEVICES[name], load(name)
    b = bays(d, "rear")
    psus = [k for k in b if k.startswith("psu-")]
    fans = [k for k in b if k.startswith("fan-")]
    assert len(psus) == 2 and len(fans) == want["nfans"]
    for k in psus:
        assert set(b[k]["accepts"]) == set(want["psu"])
        assert b[k]["default"] == want["psu"][0]
    for k in fans:
        assert set(b[k]["accepts"]) == set(want["fan"])
        assert b[k]["default"] == want["fan"][0]


def test_the_supplies_and_fans_are_shared_inside_each_pair():
    for pair in (("7050cx3-32s", "7050sx3-48yc12"), ("7050sx3-48yc8", "7050tx3-48c8")):
        a, b = (bays(load(n), "rear") for n in pair)
        assert a["psu-1"]["accepts"] == b["psu-1"]["accepts"] == a["psu-2"]["accepts"]
        assert a["fan-1"]["accepts"] == b["fan-1"]["accepts"]


@pytest.mark.parametrize("name", NAMES)
def test_every_seatable_part_resolves_and_is_one_maker_part_number(name):
    d = load(name)
    refs = {r for b in bays(d, "rear").values() for r in b["accepts"]}
    assert refs
    for ref in refs:
        c = contract_of(ref)
        assert c["part-numbers"], ref


def test_one_maker_part_number_is_one_component():
    seen = {}
    for p in sorted((LIB / "components/arista").glob("*/v*/contract.yaml")):
        for pn in (yaml.safe_load(p.read_text()).get("part-numbers") or {}):
            seen.setdefault(pn, []).append(p.parent.parent.name)
    for part in ("PWR-500AC-F", "PWR-500-DC-F", "FAN-7000H-F", "PWR-511-AC-RED", "FAN-7011M-F"):
        assert len(seen.get(part, [])) == 1, (part, seen.get(part))


@pytest.mark.parametrize("name", NEW_PARTS)
def test_a_new_part_states_its_output_or_leaves_the_gap(name):
    c = contract_of(f"arista/{name}@1")
    if c["class"] == "psu":
        assert c["attrs"]["power-output-w"] == 500
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert (LIB / "components/arista" / name / "v1/skins/default.svg").is_file()


# ------------------------------------------------------------------ the DCIM

ORDERABLE = {
    "7050cx3-32s": ["DCS-7050CX3-32S-F"],
    "7050sx3-48yc12": ["DCS-7050SX3-48YC12-F"],
    "7050sx3-48yc8": ["DCS-7050SX3-48YC8-F", "DCS-7050SX3-48YC8-R"],
    "7050tx3-48c8": ["DCS-7050TX3-48C8-F", "DCS-7050TX3-48C8-R"],
}


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_exports_one_type_per_orderable_configuration_and_none_for_an_example(target):
    """The data sheet's ordering information lists -F for the CX3-32S and SX3-48YC12 and -F and -R for the
    other two; the DC builds are examples with no part number and export nothing."""
    folder = LIB / "exports" / target / "device-types" / "Arista"
    got = {p.stem for p in folder.glob("DCS-7050*X3-*.yaml")}
    assert got == {pn for pns in ORDERABLE.values() for pn in pns}


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_dcim_types_are_one_ru_with_every_port(target, name):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    ports = DEVICES[name]["ports"]
    for pn in ORDERABLE[name]:
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == 1.0, pn
        names = {i["name"] for i in doc["interfaces"]}
        assert {f"port-{n}" for n in ports} <= names, pn
        assert f"port-{max(ports) + 1}" not in names, pn


# ------------------------------------------------------------------ power and weight


@pytest.mark.parametrize("name", NAMES)
def test_the_power_and_weight_are_the_guides(name):
    """Table 4 (typical / maximum) and Table 1 (weight), stated as the guide prints them."""
    want, d = DEVICES[name], load(name)
    pw = d["attrs"]["power"]
    assert pw["power-typical-w"] == want["typical"]
    assert pw["power-max-w"] == want["maximum"]
    assert f"{want['guide_kg']} kg" in d["attrs"]["physical"]["weight"]


@pytest.mark.parametrize("name", NAMES)
def test_a_disagreement_with_the_data_sheet_is_recorded_with_both_figures(name):
    """The guide and the data sheet differ on power for the CX3-32S and SX3-48YC8 and on weight for the
    CX3-32S; they agree for the others (and the SX3-48YC8's 9.5 and 9.45 kg are one weight to a rounding)."""
    d = load(name)
    gaps = {g["what"]: g for g in d.get("gaps") or []}
    for what, figures in DEVICES[name]["disagree"].items():
        assert gaps[what]["reason"] == "sources-disagree", what
        for f in figures:
            assert f in gaps[what]["note"], (what, f)
    for what in ("power", "weight"):
        if what not in DEVICES[name]["disagree"]:
            assert what not in gaps or gaps[what]["reason"] != "sources-disagree", what


@pytest.mark.parametrize("name", NAMES)
def test_what_no_document_prints_is_a_gap(name):
    """The guide draws the rears generically and does not say which model uses which; it measures no
    ear; and it draws no PWR-511-DC, PWR-500-DC, FAN-7011M or FAN-7000H face of its own."""
    gaps = {g["what"] for g in load(name).get("gaps") or []}
    assert {"rear-mapping", "rack-ears", "front-legends", "psu-faces"} <= gaps


@pytest.mark.parametrize("name", NAMES)
def test_every_position_is_estimated_and_none_is_called_verified(name):
    d = load(name)
    assert d["maturity"] == "modelled"
    assert d["provenance"]["gate-1-front"]["confidence"] == "estimated"
    assert d["provenance"]["gate-1-rear"]["confidence"] == "estimated"
