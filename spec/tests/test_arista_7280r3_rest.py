"""The rest of the Arista 7280R3 that the first slice left out: the 7280TR3-40C6 and the 7280SR3E-40YC6-M (#1204).

The 7280TR3-40C6 is a device of its own: the guide has no front figure for it and the data sheet's photograph
shows a face of 40 RJ-45 jacks and six QSFP cages that no other model has, so every front position is
`estimated` and its provenance says how. The 7280SR3E-40YC6-M shares the 7280SR3-40YC6's face (guide Figure C-7
is captioned for both), so it is a configuration of `arista/7280sr3-40yc6` (already there from the first slice)
and no device of its own. The expected figures are Arista's: the 7280R3 Series Quick Start Guide (DOC-07041-01:
Table 1 for the envelope, Table 4 for the power draw and the supplies, Appendix D for the rear) and the 7280R3
Series Data Sheet (03-0045-59: the model comparison, the ordering information and the photograph).
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = "7280tr3-40c6"

PSU = {"ac": "arista/7280r3-pwr-500-ac@1", "ac-rev": "arista/7280r3-pwr-500-ac-rev@1",
       "dc": "arista/7280r3-pwr-500-dc@1", "dc-rev": "arista/7280r3-pwr-500-dc-rev@1"}
FAN = {"fwd": "arista/7280r3-fan-m@1", "rev": "arista/7280r3-fan-m-rev@1"}


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def ports(d, ref, lo, hi):
    out = {}
    for p in placements(d, "front"):
        if p["ref"] == ref and p["id"].startswith("port-"):
            n = int(p["id"].split("-")[1])
            if lo <= n <= hi:
                out[n] = p
    return out


JACK, QSFP = "common/rj45-ganged-eth-plain@1", "std/qsfp-ganged@1"


# ---------------------------------------------------------------- the envelope


def test_the_envelope_is_the_guides_table_1_and_the_data_sheets_body():
    """Table 1 gives 48.3 x 4.4 x 46.9 cm over the ears and 9.6 kg; the data sheet gives the body between
    them, 43.99 cm, and 9.57 kg."""
    d = load(DEV)
    c = d["chassis"]
    assert c["ru"] == 1
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(43.7, abs=0.3)
    assert c["depth"] == pytest.approx(469.0, abs=0.5)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)
    assert d["attrs"]["physical"]["weight"].startswith("9.57 kg")
    assert (d["attrs"]["power"]["power-typical-w"], d["attrs"]["power"]["power-max-w"]) == (186, 242)


def test_every_face_is_sized_from_the_envelope_and_the_names_are_as_printed():
    d = load(DEV)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    assert v["front"]["size"] == v["rear"]["size"] == {"w": c["width"], "h": c["height"]}
    assert v["top"]["size"] == v["bottom"]["size"] == {"w": c["width"], "h": c["depth"]}
    assert v["left"]["size"] == v["right"]["size"] == {"w": c["depth"], "h": c["height"]}
    assert d["manufacturer"] == "Arista" and d["model"] == "7280TR3-40C6"
    assert d["portfolio"] == {"line": "7000 Series", "family": "7280TR3"}
    assert {"name": "DCS-7280TR3-40C6", "kind": "marketing"} in d["aliases"]
    assert d["maturity"] == "modelled"
    assert (LIB / "devices/arista" / DEV / "layout.yaml").is_file()


# ------------------------------------------------------------------ the front


def test_the_front_has_forty_jacks_in_five_blocks_of_four_two_rows_deep():
    d = load(DEV)
    jacks = ports(d, JACK, 1, 40)
    assert sorted(jacks) == list(range(1, 41))
    assert len(ports(d, "std/rj45-ganged@2", 1, 40)) == 0     # an Ethernet jack, not a console jack (L76)
    for n, p in jacks.items():
        assert p["rel-pos"] == n and p["group"] == "rj45", n
        assert p["attrs"] == {"media": "rj45", "speed": "10g"}, n
    # the odd number is the upper jack; the upper is the registry's mirror of the lower (turned 180)
    for n in range(1, 40, 2):
        up, low = jacks[n], jacks[n + 1]
        assert up["at"][0] == low["at"][0] and up["at"][1] < low["at"][1], n
        assert up.get("rotate") == 180 and not low.get("rotate"), n
    cols = sorted({p["at"][0] for p in jacks.values()})
    assert len(cols) == 20
    steps = [round(b - a, 2) for a, b in zip(cols, cols[1:])]
    assert steps.count(13.97) == 15                          # the registry's ganged-jack pitch inside a block
    assert len([s for s in steps if s > 13.97]) == 4         # four gutters between five blocks
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "10g"}


def test_the_front_has_six_qsfp_cages_in_three_stacked_columns_numbered_after_the_jacks():
    d = load(DEV)
    cages = ports(d, QSFP, 41, 46)
    assert sorted(cages) == list(range(41, 47))
    for n in (41, 43, 45):
        up, low = cages[n], cages[n + 1]
        assert up["at"][0] == low["at"][0] and up["at"][1] < low["at"][1], n
        assert not up.get("rotate") and low.get("rotate") == 180, n    # belly to belly
    assert sorted({p["at"][0] for p in cages.values()}) == pytest.approx([339.25, 365.15, 391.05], abs=0.05)
    assert all(p["group"] == "qsfp28" for p in cages.values())
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    # no port beyond 46, and the cages sit to the right of every jack
    ids = {p["id"] for p in placements(d, "front") if p["id"].startswith("port-")}
    assert ids == {f"port-{n}" for n in range(1, 47)}
    assert min(p["at"][0] for p in cages.values()) > max(p["at"][0] for p in ports(d, JACK, 1, 40).values()) + 12.7


def test_the_management_ports_are_stacked_at_the_front_and_not_at_the_rear():
    """The data sheet's photograph shows an RJ-45, a USB port and an RJ-45 at the right of the face (as Figure
    C-5 draws them for the 7280CR3-36S); Figure D-1's management block is not drawn on this rear."""
    d = load(DEV)
    ps = {p["id"]: p for p in placements(d, "front")}
    assert {"mgmt", "usb", "console"} <= set(ps)
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["usb"]["ref"] == "std/usb-a@1"
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    assert min(ps[i]["at"][0] for i in ("mgmt", "usb", "console")) > 400.0
    assert not {"mgmt", "usb", "console"} & {p["id"] for p in placements(d, "rear")}
    assert d["groups"]["mgmt"]["role"] == "management"
    assert [g for g in d["gaps"] if g["what"] == "rear-mgmt-position"]


def test_four_status_lamps_stand_at_the_far_right_clear_of_every_port():
    d = load(DEV)
    ps = {p["id"]: p for p in placements(d, "front")}
    ids = ("led-system", "led-fan", "led-ps1", "led-ps2")
    assert [ps[i]["rel-pos"] for i in ids] == [1, 2, 3, 4]
    assert all(ps[i]["group"] == "status-leds" for i in ids)
    assert all(ps[i]["at"][0] > 430.0 for i in ids)
    # no per-port lamp is modelled: the photograph does not resolve one, and the gap says so
    assert not [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    assert [g for g in d["gaps"] if g["what"] == "port-lamps"]


def test_the_front_prints_the_model_reserves_the_logo_zone_and_draws_no_wordmark():
    d = load(DEV)
    front = d["views"]["front"]
    assert "7280TR3-40C6" in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name
    # a numeral that cannot be read in the photograph is not printed
    assert not [s for s in front["silkscreen"] if str(s.get("for", "")).startswith("port-")]


def test_every_figure_read_off_the_photograph_is_estimated_and_says_how():
    d = load(DEV)
    prov = d["provenance"]
    gate = prov["gate-1-front"]
    assert gate["confidence"] == "estimated"
    for word in ("photograph", "0.895 px/mm", "440.0", "43.7", "dark-run"):
        assert word in gate["note"], word
    for key in ("front-ports", "port-numbering", "status-lamps", "management-block", "vents", "colour"):
        assert prov[key]["confidence"] == "estimated", key
    assert [g for g in d["gaps"] if g["what"] == "front-photo-only"]
    assert "NO FRONT FIGURE" in prov["sources"]["note"]


# ------------------------------------------------------------------- the rear


def test_the_rear_has_two_supply_bays_and_two_fan_bays_taking_the_guides_modules():
    d = load(DEV)
    b = bays(d, "rear")
    assert sorted(b) == ["fan-1", "fan-2", "psu-1", "psu-2"]
    for i in (1, 2):
        assert sorted(b[f"psu-{i}"]["accepts"]) == sorted(PSU.values())
        assert b[f"psu-{i}"]["default"] == PSU["ac"]
        assert sorted(b[f"fan-{i}"]["accepts"]) == sorted(FAN.values())
        assert b[f"fan-{i}"]["default"] == FAN["fwd"]
    # the supplies sit at the ends and the fans between them
    assert b["psu-1"]["at"][0] < b["fan-1"]["at"][0] < b["fan-2"]["at"][0] < b["psu-2"]["at"][0]
    assert placements(d, "rear") == []
    for ref in list(PSU.values()) + list(FAN.values()):
        ns, name = ref.split("@")[0].split("/")
        assert (LIB / "components" / ns / name / "v1/contract.yaml").is_file(), ref


def test_no_component_is_added_for_a_part_number_main_already_models():
    """PWR-511 and FAN-7011M are the 7280SR3-40YC6's: one part number, one component."""
    root = LIB / "components/arista"
    seen = {}
    for p in root.iterdir():
        c = yaml.safe_load((p / "v1/contract.yaml").read_text())
        for pn in (c.get("part-numbers") or {}):
            seen.setdefault(pn, []).append(p.name)
    assert not {pn: n for pn, n in seen.items() if len(n) > 1}, "a part number is modelled twice"
    assert [pn for pn in seen if pn.startswith("PWR-511-") or pn.startswith("FAN-7011M")]
    assert not [p.name for p in root.iterdir() if "tr3" in p.name]


# ------------------------------------------------------------ configurations


def test_the_orderable_configurations_are_the_data_sheets_f_and_r_part_numbers():
    cf = load(DEV)["configurations"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == {"f", "r"}
    assert list(cf["f"]["part-numbers"]) == ["DCS-7280TR3-40C6-F"]
    assert list(cf["r"]["part-numbers"]) == ["DCS-7280TR3-40C6-R"]
    assert [n for n, c in cf.items() if c.get("default")] == ["base"] and cf["base"]["kind"] == "base"
    for n in ("dc-f", "dc-r"):
        assert cf[n]["kind"] == "example" and "part-numbers" not in cf[n], n
    # the data sheet lists no K, M, A or -S form of this model
    assert not [n for n in cf if n.startswith(("k", "m", "a", "s"))]


def test_each_configuration_seats_the_supply_and_fan_of_its_airflow_and_handle_colour():
    cf = load(DEV)["configurations"]
    assert cf["f"].get("airflow", "front-to-back") == "front-to-back" and not cf["f"].get("bays")
    r = cf["r"]
    assert r["airflow"] == "back-to-front"
    assert r["bays"] == {"psu-1": PSU["ac-rev"], "psu-2": PSU["ac-rev"], "fan-1": FAN["rev"], "fan-2": FAN["rev"]}
    assert cf["dc-f"]["power"] == "dc" and cf["dc-f"]["bays"] == {"psu-1": PSU["dc"], "psu-2": PSU["dc"]}
    assert cf["dc-r"]["bays"] == {"psu-1": PSU["dc-rev"], "psu-2": PSU["dc-rev"],
                                  "fan-1": FAN["rev"], "fan-2": FAN["rev"]}
    # red handles for an air-exit module, blue for an air-inlet one (guide section 2.1)
    for ref, red in ((PSU["ac"], True), (PSU["ac-rev"], False), (FAN["fwd"], True), (FAN["rev"], False)):
        ns, name = ref.split("@")[0].split("/")
        c = yaml.safe_load((LIB / "components" / ns / name / "v1/contract.yaml").read_text())
        h = c["fields"]["handle-finish"]["default"].lower()
        rr, bb = int(h[1:3], 16), int(h[5:7], 16)
        assert (rr > bb) == red, ref
        assert c["attrs"]["airflow"] == ("front-to-back" if red else "back-to-front"), ref


# ------------------------------------------------- the SR3E-40YC6-M configuration


def test_the_sr3e_40yc6_m_is_a_configuration_of_the_sr3_40yc6_and_not_a_device_of_its_own():
    """Guide Figure C-7 is captioned for both models: one front panel, so one device."""
    names = {p.name for p in (LIB / "devices/arista").iterdir()}
    assert "7280sr3-40yc6" in names and not [n for n in names if "sr3e" in n]
    cf = load("7280sr3-40yc6")["configurations"]
    assert cf["m-f"]["kind"] == cf["m-r"]["kind"] == "orderable"
    assert list(cf["m-f"]["part-numbers"]) == ["DCS-7280SR3E-40YC6-M-F"]
    assert list(cf["m-r"]["part-numbers"]) == ["DCS-7280SR3E-40YC6-M-R"]
    assert cf["m-r"]["airflow"] == "back-to-front"
    assert not [g for g in load("7280sr3-40yc6")["gaps"] if g["what"] == "config-scoped-device-attrs"]
    assert cf["m-f"]["attrs"]["platform"]["memory"] == "32 GB"
    assert cf["m-r"]["attrs"]["platform"]["memory"] == "32 GB"


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("pn", ["DCS-7280TR3-40C6-F", "DCS-7280TR3-40C6-R"])
def test_the_dcim_types_export_one_per_orderable_configuration_at_one_unit(pn, target):
    path = LIB / "exports" / target / "device-types/Arista" / f"{pn}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["manufacturer"] == "Arista" and doc["model"] == pn
    assert doc["u_height"] == 1.0


def test_the_exported_type_lists_every_front_port_once():
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Arista/DCS-7280TR3-40C6-F.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 47)} <= set(types)
    assert "port-47" not in types and "port-0" not in types
    assert {types[f"port-{n}"] for n in range(41, 47)} == {"100gbase-x-qsfp28"}
    assert len({types[f"port-{n}"] for n in range(1, 41)}) == 1
