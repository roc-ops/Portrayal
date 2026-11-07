"""The Juniper EX4650-48Y, from the EX4650 Switch Hardware Guide (published 2025-07-16).

One device for the one front panel the guide shows: 48 SFP28 ports and 8 QSFP28 ports. Its four
variants (AC or DC supplies, front-to-back AIR OUT or back-to-front AIR IN) are `orderable`
configurations of that device. Every field-replaceable unit is a part the library already holds under
its Juniper part number, so this slice adds no component.

What the guide fixes, and so what these tests hold:
  Table 9    the envelope: 1.72 in high, 17.36 in wide, 20.48 in deep, 1RU
  Tables 7, 8, 16   the four variants, and the supplies and fan modules each ships with
  Table 15   the fan module part numbers and the airflow of each
  Tables 18, 19, 22, 24   the supply part numbers (650 W AC and DC) and their airflow
  figures 6 and 9   the ports, their count and numbering, and what is on the rear
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4
NAME = "ex4650-48y"

# Table 7 and Table 18: configuration -> (part number, supply, fan module, airflow)
VARIANTS = {
    "ac-f2b": ("EX4650-48Y-AFO", "jpsu-650w-ac-ao", "qfx5110-fanafo", "front-to-back"),
    "ac-b2f": ("EX4650-48Y-AFI", "jpsu-650w-ac-ai", "qfx5110-fanafi", "back-to-front"),
    "dc-f2b": ("EX4650-48Y-DC-AFO", "qfx5100-jpsu-650w-dc-afo", "qfx5110-fanafo", "front-to-back"),
    "dc-b2f": ("EX4650-48Y-DC-AFI", "qfx5100-jpsu-650w-dc-afi", "qfx5110-fanafi", "back-to-front"),
}
ACCEPTS = {
    "psu": {"jpsu-650w-ac-ao", "jpsu-650w-ac-ai", "qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"},
    "fan": {"qfx5110-fanafo", "qfx5110-fanafi"},
}
MODELS = {"jpsu-650w-ac-ao": "JPSU-650W-AC-AO", "jpsu-650w-ac-ai": "JPSU-650W-AC-AI",
          "qfx5100-jpsu-650w-dc-afo": "JPSU-650W-DC-AFO", "qfx5100-jpsu-650w-dc-afi": "JPSU-650W-DC-AFI",
          "qfx5110-fanafo": "QFX5110-FANAFO", "qfx5110-fanafi": "QFX5110-FANAFI"}


def load_device():
    return yaml.safe_load((DEV / NAME / "device.yaml").read_text())


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

def test_the_envelope_is_table_9():
    ch = load_device()["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(1.72 * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(17.36 * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(20.48 * INCH, abs=0.1)
    assert ch["weight-kg"] == pytest.approx(10.75, abs=0.01)


def test_the_faces_are_sized_from_the_envelope():
    d = load_device()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_front_is_the_body_and_not_the_rack_face():
    """Table 9: the brackets extend 17.36 in to 19 in, so the body is what is drawn."""
    assert load_device()["views"]["front"]["size"]["w"] < 480


def test_the_names_are_as_printed():
    d = load_device()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "EX4650-48Y"
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4650"}


# --- the ports, per face -----------------------------------------------------

def cages(dev):
    out = {"sfp": [], "qsfp": []}
    for p in placements(dev, "front"):
        name = ref_name(p["ref"])
        if name == "sfp-ganged":
            out["sfp"].append(p)
        elif name == "qsfp-ganged":
            out["qsfp"].append(p)
    return out


def test_48_sfp28_and_8_qsfp28_cages_on_the_front():
    c = cages(load_device())
    assert len(c["sfp"]) == 48
    assert len(c["qsfp"]) == 8


def test_ports_are_numbered_0_to_55_as_printed():
    d = load_device()
    c = cages(d)
    assert sorted(number(p["id"]) for p in c["sfp"]) == list(range(48))
    assert sorted(number(p["id"]) for p in c["qsfp"]) == list(range(48, 56))
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(56)} <= printed


def test_the_groups_say_what_the_ports_are():
    g = load_device()["groups"]
    assert g["sfp28"]["attrs"] == {"media": "sfp28", "speed": "25g"}
    assert g["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    assert g["sfp28"]["role"] == g["qsfp28"]["role"] == "traffic"


def test_ports_sit_in_three_blocks_of_sfp28_then_the_qsfp28_block():
    c = cages(load_device())
    assert min(p["at"][0] for p in c["qsfp"]) > max(p["at"][0] for p in c["sfp"])
    y = {number(p["id"]): p["at"][1] for p in c["sfp"]}
    assert all(y[2 * k] < y[2 * k + 1] for k in range(24)), "even above odd, the printed order"
    assert all(p.get("rotate") == 180 for p in c["sfp"] if number(p["id"]) % 2)
    assert not any(p.get("rotate") for p in c["sfp"] if number(p["id"]) % 2 == 0)


def test_the_lamps_follow_the_guide_figure_6():
    """Two lamps beside each SFP28 numeral and four along each QSFP28 port."""
    d = load_device()
    ids = {p["id"] for p in placements(d, "front") if ref_name(p["ref"]) == "led-dot"}
    for n in range(48):
        assert f"led-port-{n}" in ids and f"led-port-{n}-speed" in ids
    for n in range(48, 56):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= ids
    assert len(ids) == 96 + 32


def test_the_rear_has_console_usb_and_two_management_jacks():
    d = load_device()
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    for jack in ("mgmt-c0", "mgmt-c1"):
        assert ref_name(by_id[jack]["ref"]) == "rj45-ganged-eth"
        assert by_id[jack]["attrs"]["speed"] == "1g"
    assert by_id["mgmt-c0"]["at"][1] < by_id["mgmt-c1"]["at"][1]
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "esd-rear-jack"} <= set(by_id)
    printed = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"ALM", "SYS", "MST", "ID", "CON", "C0", "C1", "RESET"} <= printed


def test_the_logo_is_reserved_and_not_drawn():
    d = load_device()
    assert any(r["id"] == "logo-zone" for r in d["views"]["rear"]["regions"])
    printed = {s["text"].upper() for v in ("front", "rear") for s in d["views"][v]["silkscreen"] if "text" in s}
    assert "JUNIPER" not in printed and "NETWORKS" not in printed


def test_the_fan_and_supply_slots_are_numbered_as_the_guide_numbers_them():
    """Fan slots 0 to 4, then supply slots 0 and 1, left to right."""
    b = {x["id"]: x for x in bays(load_device(), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(5)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] > b["fan-4"]["at"][0]
    assert b["psu-1"]["at"][0] > b["psu-0"]["at"][0]


# --- the configurations ------------------------------------------------------

def test_each_variant_is_an_orderable_configuration_with_its_part_number():
    cfgs = load_device()["configurations"]
    assert set(cfgs) == set(VARIANTS)
    for cid, (part, *_rest) in VARIANTS.items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}


def test_the_default_is_ac_front_to_back():
    cfgs = load_device()["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    cfg = dev["configurations"][cid]
    return {b["id"]: ref_name((cfg.get("bays") or {}).get(b["id"], b.get("default")))
            for b in bays(dev, "rear")}


@pytest.mark.parametrize("cid", sorted(VARIANTS))
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(cid):
    d = load_device()
    _part, psu, fan, airflow = VARIANTS[cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(5)} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    cfg = d["configurations"][cid]
    assert cfg.get("airflow", d["chassis"]["airflow"]) == airflow
    assert cfg.get("power", d["chassis"]["power"]) == cid.split("-")[0]


def test_a_bay_accepts_the_modules_the_guide_lists():
    for b in bays(load_device(), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == ACCEPTS["fan" if b["id"].startswith("fan-") else "psu"], b["id"]
        assert ref_name(b["default"]) in got


def test_bays_reserve_one_size_for_each_module_they_accept():
    for b in bays(load_device(), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            for axis in ("w", "h"):
                assert b["size"][axis] >= c[axis] - 0.05
                assert b["size"][axis] == pytest.approx(c[axis], abs=0.5)


# --- the field-replaceable units, all reused ---------------------------------

@pytest.mark.parametrize("part,model", sorted(MODELS.items()))
def test_a_unit_carries_the_part_number_the_guide_names(part, model):
    c = load_component(part)
    assert c["attrs"]["model"] == model
    assert c["kind"] == "module"


def test_this_slice_adds_no_component():
    """Every part the bays accept is a contract that already exists on main, by its part number."""
    for b in bays(load_device(), "rear"):
        for ref in b["accepts"]:
            assert (COMP / ref_name(ref) / "v1" / "contract.yaml").exists(), ref
    assert not list(COMP.glob("ex4650-*"))


def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_an_orange_one():
    """Tables 15, 18, 24: AIR OUT with an orange handle, AIR IN with a blue one."""
    for front, back in (("jpsu-650w-ac-ao", "jpsu-650w-ac-ai"),
                        ("qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"),
                        ("qfx5110-fanafo", "qfx5110-fanafi")):
        def handle(part):
            feats = load_component(part)["relief"]["features"]
            return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
        f, b = handle(front), handle(back)
        assert f != b
        r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
        assert bl > r and bl > g


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("cid", sorted(VARIANTS))
def test_the_dcim_device_types_export_one_per_orderable_configuration(cid):
    part = VARIANTS[cid][0]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {NAME}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_ex4650_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("EX4650-*.yaml")}
    assert got == {v[0] for v in VARIANTS.values()}
