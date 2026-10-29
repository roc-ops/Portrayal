"""The Cisco Nexus 9364D-GX2A and 9348D-GX2A fixed switches, Nexus 9000 fixed switches batch 4.

The expected figures are Cisco's, read from the hardware installation guides: Cisco N9364D-GX2A
(First Published 2022-06-24, Last Modified 2026-09-16) and Cisco N9348D-GX2A (2022-07-04,
2026-07-28): the Overview port lists and callout tables and the Switch Dimensions, weights and
power-supply tables of appendix B. Each test reads the YAML a contributor edits, or the generated
export a DCIM user imports. The 9332D-GX2B, 9332D-H2R, 9364C-H1 and 93400LD-H1 are the next
batches'; the 9332D-GX2B waits for the 1100 W DC supply of the Nexus 9336C-FX2-E batch.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

D64 = "n9k-c9364d-gx2a"
D48 = "n9k-c9348d-gx2a"
DEVICES = [D64, D48]

# device -> (width, height, depth, rack units, weight kg): the guides' Switch Dimensions tables,
# inches converted as the guides print their centimetres (17.41 in = 44.23 cm; 29.82 in = 75.76
# cm; the 9364D's 3.45 in), and the weights tables' metric figures as printed (58 lb, 26.3 kg;
# 51.2 lb, 23.22 kg). The Clearance tables print the chassis depth as 29.78 in (75.65 cm) and
# the chassis width as 17.3 in: a second figure the guides do not explain, declared as a gap.
ENVELOPE = {
    D64: (442.3, 87.6, 757.6, 2, 26.3),
    D48: (442.3, 87.6, 757.6, 2, 23.22),
}

PAC = "cisco/nxa-pac-3200w@1"
PDC = "cisco/nxa-pdc-3200w@1"
FAN = "cisco/nxa-sfan-160cfm2@1"
KIT2 = "cisco/nxk-acc-kit2-2ru@1"

BLUE = "#50a2cf"

# configuration -> (supply, power feed, port-side exhaust?)
BUILDS = {
    D64: {
        "ac-3200w-port-side-intake": (PAC, ["ac", "hvdc"], False),
        "dc-3200w-port-side-intake": (PDC, ["dc", "hvdc"], False),
    },
    D48: {
        "ac-3200w-port-side-intake": (PAC, ["ac", "hvdc"], False),
        "ac-3200w-port-side-exhaust": (PAC, None, True),
        "dc-3200w-port-side-intake": (PDC, ["dc", "hvdc"], False),
    },
}


def load(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "layout.yaml").read_text())


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
    assert d["portfolio"] == {"line": "Nexus 9000", "family": "Nexus 9300", "series": "Nexus 9300-GX2"}
    assert d["maturity"] == "modelled"
    assert d["version"] == "1.0.0"
    assert d["chassis"].get("mount", "rack") == "rack"


def test_the_9348d_is_two_rack_units_against_its_own_dimension_row():
    """The guide's Overview says 2 RU and its dimension row says 1 RU; the figure's aspect agrees
    with the Overview, the height is the 9364D guide's row, and the provenance says so."""
    d = load(D48)
    c = d["chassis"]
    assert c["ru"] == 2
    assert c["height"] == 87.6 and c["height"] == load(D64)["chassis"]["height"]
    note = " ".join(d["provenance"]["rack-units"]["note"].split())
    assert d["provenance"]["rack-units"]["confidence"] == "estimated"
    for text in ("THE GUIDE SAYS 2 RU AND 1 RU", "2-rack unit (RU)", "1.72 inches (4.4 cm) (1 RU)",
                 "aspect of 5.04", "N9364D-GX2A guide's Switch Dimensions row", "3.45 in",
                 "A copied table is the other guide's table"):
        assert text in note, text
    gap = next(g for g in d["gaps"] if g["what"] == "size-figures")
    assert gap["reason"] == "sources-disagree" and gap["scope"] == ["front", "rear"]
    assert "1 RU" in gap["note"] and "29.78 in" in gap["note"] and "29.82 in" in gap["note"]


def test_the_9364d_height_and_ru_agree_with_its_figure_and_its_table():
    d = load(D64)
    assert (d["chassis"]["ru"], d["chassis"]["height"]) == (2, 87.6)
    assert "THE FIGURE AGREES WITH 2 RU" in " ".join(d["provenance"]["gate-1"]["note"].split())


@pytest.mark.parametrize("name", DEVICES)
def test_the_two_depths_are_declared_and_one_is_carried(name):
    d = load(name)
    gap = next(g for g in d["gaps"] if g["what"] == "size-figures")
    assert "29.78 in" in gap["note"] and "29.82 in" in gap["note"]
    assert d["chassis"]["depth"] == 757.6


# ------------------------------------------------------------------ the ports


def test_the_9364d_front_has_64_qsfp_dd_in_16_columns_of_stacked_pairs():
    p = placements(load(D64), "front")
    for n in range(1, 65):
        assert p[f"port-{n}"]["ref"] == "std/qsfp-dd@1", n
    assert "port-67" not in p and "port-0" not in p
    # a stacked pair: the odd port over the even, one column; two groups of sixteen columns
    for n in range(1, 64, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 33, 2)]
    assert len(xs) == 16
    assert {round(xs[i + 1] - xs[i], 2) for i in range(15)} == {23.72}
    assert p["port-33"]["at"][1] > p["port-2"]["at"][1] + 20.0
    assert p["port-65"]["ref"] == "std/sfp-ganged@1" and p["port-66"]["ref"] == "std/sfp-ganged@1"


def test_the_9348d_front_has_48_qsfp_dd_in_16_columns_of_three_numbered_down_each_column():
    p = placements(load(D48), "front")
    for n in range(1, 49):
        assert p[f"port-{n}"]["ref"] == "std/qsfp-dd@1", n
    assert "port-51" not in p and "port-0" not in p
    for c in range(16):
        col = [p[f"port-{3 * c + k}"]["at"] for k in (1, 2, 3)]
        assert col[0][0] == col[1][0] == col[2][0], c
        assert col[0][1] < col[1][1] < col[2][1], c
    xs = [p[f"port-{3 * c + 1}"]["at"][0] for c in range(16)]
    assert {round(xs[i + 1] - xs[i], 2) for i in range(15)} == {23.75}
    # the first two rows are a stacked pair and the third stands apart, as the figure draws them
    ys = [p[f"port-{k}"]["at"][1] for k in (1, 2, 3)]
    assert ys[1] - ys[0] < ys[2] - ys[1]
    assert p["port-49"]["ref"] == "std/sfp-ganged@1" and p["port-50"]["ref"] == "std/sfp-ganged@1"


@pytest.mark.parametrize("name", DEVICES)
def test_the_sfp_plus_pair_is_stacked_and_numbered_after_the_400g_ports(name):
    p = placements(load(name), "front")
    first = 65 if name == D64 else 49
    top, bottom = p[f"port-{first}"], p[f"port-{first + 1}"]
    assert top["at"][0] == bottom["at"][0] and top["at"][1] < bottom["at"][1]
    assert f"port-{first + 2}" not in p
    groups = layout(name)["groups"]
    assert groups["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_400g_groups_carry_the_cage_media_and_speed(name):
    groups = layout(name)["groups"]
    for k, g in groups.items():
        if k.startswith("qsfpdd-400g"):
            assert g["attrs"] == {"media": "qsfp-dd", "speed": "400g"}, k


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_out_of_band_block_at_the_left_and_the_chassis_lamps(name):
    p = placements(load(name), "front")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1" and p["mgmt-sfp"]["attrs"]["media"] == "sfp"
    assert p["usb"]["ref"] == "std/usb-a@1"
    assert p["port-1"]["at"][0] > max(p[k]["at"][0] for k in ("console", "mgmt-rj45", "mgmt-sfp", "usb"))
    for lamp in ("led-bcn", "led-sts", "led-env"):
        assert lamp in p, lamp


def test_the_9364d_has_a_triangle_lamp_per_lower_port_and_the_9348d_a_round_lamp_per_port():
    p64 = placements(load(D64), "front")
    for n in range(33, 65):
        assert p64[f"led-port-{n}"]["ref"] == "common/led-arrow-sm@1", n
    assert "led-port-1" not in p64
    p48 = placements(load(D48), "front")
    for n in range(1, 49):
        lamp = p48[f"led-port-{n}"]
        assert lamp["ref"] == "common/led-dot@1" and lamp["for"] == f"port-{n}", n
        assert lamp["at"][1] > p48[f"port-{n}"]["at"][1] + 10.0 or n % 3 != 0, n
    # three lamps per column, in the order of the ports they name
    for c in range(16):
        xs = [p48[f"led-port-{3 * c + k}"]["at"][0] for k in (1, 2, 3)]
        assert xs == sorted(xs) and len(set(xs)) == 3, c


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_four_fan_bays_left_to_right_then_two_supply_bays_stacked_at_the_right(name):
    b = bays(load(name), "rear")
    assert [k for k in b if k.startswith("fan-")] == [f"fan-{i}" for i in range(1, 5)]
    assert [k for k in b if k.startswith("psu-")] == ["psu-1", "psu-2"]
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, 5)]
    assert xs == sorted(xs)
    assert b["psu-1"]["at"][0] > xs[-1]
    assert b["psu-1"]["at"][0] == b["psu-2"]["at"][0] and b["psu-1"]["at"][1] < b["psu-2"]["at"][1]
    pitch = [xs[i + 1] - xs[i] for i in range(3)]
    assert max(pitch) - min(pitch) < 0.05
    assert all(b[f"fan-{i}"]["group"] == "fans" for i in range(1, 5))
    assert all(b[k]["group"] == "psus" for k in ("psu-1", "psu-2"))
    assert not placements(load(name), "rear").keys() - {"silk-mac"}


@pytest.mark.parametrize("name", DEVICES)
def test_no_ear_and_no_logo_is_drawn_and_a_logo_zone_is_reserved(name):
    d = load(name)
    assert "ears" not in d["chassis"]
    for view in ("front", "rear"):
        for p in placements(d, view).values():
            assert p["ref"] != "common/rack-ear@1"
        for s in d["views"][view].get("silkscreen") or []:
            assert "cisco" not in str(s.get("text", "")).lower(), s
            assert "logo" not in str(s.get("mark", "")).lower(), s
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1
    for view in ("top", "bottom", "left", "right"):
        assert d["views"][view].get("empty"), view


# ---------------------------------------------------------- redundancy groups


@pytest.mark.parametrize("name", DEVICES)
def test_the_fans_are_three_plus_one_and_the_supplies_one_plus_one(name):
    g = layout(name)["groups"]
    assert g["fans"]["attrs"]["redundancy"] == "3+1"
    assert g["psus"]["attrs"]["redundancy"] == "1+1"
    assert "100%" in g["fans"]["attrs"]["redundancy-note"]
    assert "2 minutes" in g["fans"]["attrs"]["redundancy-note"]


# ------------------------------------------------------------ configurations


@pytest.mark.parametrize("name", DEVICES)
def test_each_build_seats_matching_supplies_and_fans_with_matching_airflow(name):
    d = load(name)
    cf = d["configurations"]
    builds = BUILDS[name]
    assert set(cf) == set(builds)
    assert d["chassis"]["airflow"] == "front-to-back"
    defaults = [n for n, c in cf.items() if c.get("default")]
    assert defaults == ["ac-3200w-port-side-intake"] and cf[defaults[0]]["kind"] == "base"
    default_psu = bays(d, "rear")["psu-1"]["default"]
    assert default_psu == PAC
    for cname, (psu, power, exhaust) in builds.items():
        c = cf[cname]
        assert list(c["part-numbers"]) == [name.upper()], cname
        assert c["part-numbers"][name.upper()] == {"part": name.upper()}, cname
        assert c["kind"] == ("base" if cname == defaults[0] else "orderable"), cname
        seated = c.get("bays") or {}
        if psu != default_psu:
            assert seated == {"psu-1": psu, "psu-2": psu}, cname
        else:
            assert not seated, cname
        assert c.get("power") == power, cname
        for bay in [b for b in bays(d, "rear") if b.startswith("fan-")]:
            assert bay not in seated  # the bay's own default is the family's one fan
        attrs = c.get("component-attrs") or {}
        if exhaust:
            assert c["airflow"] == "back-to-front", cname
            for part in ("nxa-sfan-160cfm2", "nxa-pac-3200w"):
                assert attrs[part]["latch-finish"] == BLUE, cname
                assert attrs[part]["airflow"] == "back-to-front", cname
        else:
            assert "airflow" not in c and not attrs, cname


def test_the_9364d_guide_offers_port_side_intake_only_and_the_9348d_adds_the_exhaust_ac_build():
    assert set(load(D64)["configurations"]) == {"ac-3200w-port-side-intake", "dc-3200w-port-side-intake"}
    cf = load(D48)["configurations"]
    assert "ac-3200w-port-side-exhaust" in cf and "dc-3200w-port-side-exhaust" not in cf
    assert "exhaust" not in " ".join(load(D64)["configurations"])


@pytest.mark.parametrize("name", DEVICES)
def test_the_bays_accept_only_the_supplies_and_fans_the_guide_names(name):
    b = bays(load(name), "rear")
    for k in ("psu-1", "psu-2"):
        assert set(b[k]["accepts"]) == {PAC, PDC}
        assert b[k]["default"] == PAC
    for k in [k for k in b if k.startswith("fan-")]:
        assert b[k]["accepts"] == [FAN] and b[k]["default"] == FAN


# ------------------------------------------------------ components, ears, kits


def test_each_new_part_is_one_component_named_by_its_part_number():
    root = LIB / "components/cisco"
    for part, model, cls in (("nxa-sfan-160cfm2", "NXA-SFAN-160CFM2", "fan"),
                             ("nxa-pac-3200w", "NXA-PAC-3200W", "psu"),
                             ("nxa-pdc-3200w", "NXA-PDC-3200W", "psu")):
        assert [p.name for p in root.iterdir() if p.name.startswith(part)] == [part]
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model and c["class"] == cls
    assert contract("nxa-pac-3200w")["attrs"]["power-output-w"] == 3200
    assert contract("nxa-pac-3200w")["attrs"]["input"] == "ac"
    assert contract("nxa-pdc-3200w")["attrs"]["input"] == "dc"
    assert contract("nxa-pac-3200w")["attrs"]["weight-kg"] == 1.63
    assert contract("nxa-sfan-160cfm2")["attrs"]["weight-kg"] == 0.61


def test_the_fans_part_number_is_the_texts_and_the_label_is_declared_not_modelled():
    """The text prints NXA-SFAN-160CFM2; the weights row and the figure label drop the S."""
    root = LIB / "components/cisco"
    names = {p.name for p in root.iterdir()}
    assert "nxa-sfan-160cfm2" in names
    assert not {n for n in names if n.startswith("nxa-fan-160")}
    note = " ".join(contract("nxa-sfan-160cfm2")["provenance"]["part-number"].split())
    assert "PRINTED THREE WAYS" in note and "NXA-FAN-160CFM2PI" in note and "NXA-FAN-160CFM2-PI" in note
    for name in DEVICES:
        gap = next(g for g in load(name)["gaps"] if g["what"] == "fan-part-number-printed-three-ways")
        assert "NXA-FAN-160CFM2PI" in gap["note"] and "NXA-SFAN-160CFM2-PI" in gap["note"]


def test_the_9348d_guides_two_oddities_in_its_text_are_declared():
    gaps = {g["what"]: g for g in load(D48)["gaps"]}
    assert "typo" in gaps["fan-weight-row-says-intake-for-the-exhaust-fan"]["note"]
    assert "Port-side intake (blue) (NXA-SFAN-160CFM2-PE)" in \
        gaps["fan-weight-row-says-intake-for-the-exhaust-fan"]["note"]
    assert "NXA-PAC-3200-PE" in gaps["exhaust-supply-part-number-spelling"]["note"]
    assert "NXA-ACC-QDD-DC" in gaps["dust-cover-is-an-accessory"]["note"]
    assert not {p.name for p in (LIB / "components/cisco").iterdir() if "qdd-dc" in p.name}


def test_the_3000w_supply_is_named_by_the_9364d_guide_and_not_seated():
    d = load(D64)
    gap = next(g for g in d["gaps"] if g["what"] == "ac-3000w-supply-named-not-seated")
    assert "NXA-PAC-3000W-PI" in gap["note"] and "cisco/n9k-pac-3000w-b@1" in gap["note"]
    for k in ("psu-1", "psu-2"):
        assert all("3000" not in a for a in bays(d, "rear")[k]["accepts"])
    assert not {p.name for p in (LIB / "components/cisco").iterdir() if p.name == "nxa-pac-3000w"}
    for c in d["configurations"].values():
        assert not any("3000" in str(v) for v in (c.get("bays") or {}).values())


@pytest.mark.parametrize("name", DEVICES)
def test_the_listed_kit_is_the_one_the_guide_orders_and_it_resolves(name):
    assert [k["ref"] for k in load(name)["chassis"]["kits"]] == [KIT2]
    k = contract("nxk-acc-kit2-2ru")
    assert k["kind"] == "kit"
    # the second kit the guides name has no contents and no procedure: a gap and not a part
    gap = next(g for g in load(name)["gaps"] if g["what"] == "ears-not-dimensioned")
    assert "N9K-C9300-RMK" in gap["note"] and "no contents" in " ".join(gap["note"].split()) \
        or "N9K-C9300-RMK" in gap["wanted"]
    assert not {p.name for p in (LIB / "components/cisco").iterdir() if "c9300-rmk" in p.name}


def test_the_fan_has_no_power_draw_because_the_guides_print_none():
    """L29 stands on the fan: the guides print the whole switch only (appendix B), and the
    baseline records the warning for these two devices."""
    c = contract("nxa-sfan-160cfm2")
    assert "power-draw-max-w" not in c["attrs"] and c["attrs"]["power-absent"] == "not-published"
    assert "NOT PUBLISHED" in c["provenance"]["power"]
    import json
    base = json.loads((LIB / "lint-baseline.json").read_text())
    for name in DEVICES:
        assert base[f"devices/cisco/{name}/device.yaml"] == {"L29": 1}, name


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_chassis_part_number_two_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Cisco"
    for pn in ("N9K-C9364D-GX2A", "N9K-C9348D-GX2A"):
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Cisco" and doc["model"] == pn
        assert doc["u_height"] == 2.0
    assert not (folder / "N9K-C9364D-GX2A-DC.yaml").exists()


def test_the_exported_types_list_the_ports_by_cage():
    for pn, last_qsfp, sfp in (("N9K-C9364D-GX2A", 64, (65, 66)), ("N9K-C9348D-GX2A", 48, (49, 50))):
        doc = yaml.safe_load((LIB / f"exports/netbox/device-types/Cisco/{pn}.yaml").read_text())
        types = {i["name"]: i["type"] for i in doc["interfaces"]}
        assert {f"port-{n}" for n in range(1, last_qsfp + 1)} <= set(types), pn
        assert {types[f"port-{n}"] for n in range(1, last_qsfp + 1)} == {"400gbase-x-qsfpdd"}, pn
        assert {types[f"port-{n}"] for n in sfp} == {"10gbase-x-sfpp"}, pn
        assert f"port-{sfp[1] + 1}" not in types, pn


def test_the_three_new_modules_export():
    for part in ("nxa-sfan-160cfm2", "nxa-pac-3200w", "nxa-pdc-3200w"):
        found = list((LIB / "exports/netbox").rglob(f"*{part}*")) + list((LIB / "exports/netbox").rglob(
            f"*{part.upper()}*"))
        assert found, part


@pytest.mark.parametrize("name", DEVICES)
def test_the_committed_export_equals_the_exporters_own_output(name, tmp_path):
    dist = LIB / "dist"
    if not (dist / "listings.json").exists():
        pytest.skip("library/dist not built")
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/dcim_export.py"),
                        "--dist", str(dist), "--out", str(tmp_path), "--images", "--no-raster",
                        "--device", name], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    pn = name.upper()
    for target in ("netbox", "nautobot"):
        fresh = (tmp_path / target / "device-types/Cisco" / f"{pn}.yaml").read_text()
        committed = (LIB / "exports" / target / "device-types/Cisco" / f"{pn}.yaml").read_text()
        assert fresh == committed, (target, pn)


# ------------------------------------------------------------------ the lock


def test_the_lock_agrees_with_every_new_device_and_component():
    from portrayal import devicelock
    new = {f"cisco/{n}" for n in ("n9k-c9364d-gx2a", "n9k-c9348d-gx2a", "nxa-sfan-160cfm2",
                                  "nxa-pac-3200w", "nxa-pdc-3200w")}
    assert [f for f in devicelock.check(LIB) if f[0] in new] == []
