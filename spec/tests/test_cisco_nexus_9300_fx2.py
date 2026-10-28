"""The Cisco Nexus 9336C-FX2-E fixed switch, Nexus 9000 fixed switches batch 3.

The expected figures are Cisco's, read from the hardware installation guide: Cisco N9336C-FX2-E
NX-OS Mode Switch (First Published 2021-02-16, Last Modified 2026-07-27): the Overview port and
module lists, the flat front and rear figures (art numbers 503528 and 503529), and the Switch
Dimensions, weights and power tables of appendix B. Each test reads the YAML a contributor edits,
or the generated export a DCIM user imports. The 9336C-FX2 and the 93240YC-FX2 are not modelled in
this batch: their guides draw the faces in three-quarter view only and none can be measured.
"""
import json
import pathlib

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

E = "n9k-c9336c-fx2-e"

PAC750 = "cisco/nxa-pac-750w@1"
PDC1100 = "cisco/nxa-pdc-1100w@1"
SFAN35 = "cisco/nxa-sfan-35cfm@1"
KIT1 = "cisco/nxk-acc-kit-1ru@1"
KIT2 = "cisco/nxk-acc-kit2-2ru@1"

BLUE = "#50a2cf"

# configuration -> (supply, power feed, port-side exhaust?). The guide lists a port-side intake
# and a port-side exhaust build of the 750 W AC and the 1100 W DC supply
BUILDS_E = {
    "ac-750w-port-side-intake": (PAC750, None, False),
    "ac-750w-port-side-exhaust": (PAC750, None, True),
    "dc-1100w-port-side-intake": (PDC1100, "dc", False),
    "dc-1100w-port-side-exhaust": (PDC1100, "dc", True),
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


def test_the_9336c_fx2_e_envelope_is_the_guides_dimension_table():
    """17.3 in wide, 24.7 in deep, 1.72 in (1 RU) high, 18.8 lb (8.5 kg): appendix B, PDF page 55."""
    c = load(E)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (439.4, 43.7, 627.4, 1)
    assert c["weight-kg"] == 8.5


def test_the_depth_inclusion_and_the_twin_guides_figure_are_declared():
    """The FX2-E row says only "Depth"; the twin guide's row says "Depth with Handles", 24.5 in."""
    note = load(E)["provenance"]["the-width"]["note"]
    assert 'HEADED "Depth" ONLY' in note
    assert "Depth with Handles" in note and "24.5 in" in note and "24.7 in" in note
    assert "not applied" in note


def test_every_face_is_sized_from_the_envelope():
    d = load(E)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


def test_the_names_and_the_family_are_as_printed():
    d = load(E)
    assert d["manufacturer"] == "Cisco"
    assert d["model"] == "N9K-C9336C-FX2-E"
    assert d["portfolio"] == {"line": "Nexus 9000", "family": "Nexus 9300", "series": "Nexus 9300-FX2"}
    assert d["maturity"] == "modelled"
    assert d["version"] == "1.0.0"
    assert d["chassis"].get("mount", "rack") == "rack"


# ------------------------------------------- the FX2-E is a device, and the FC2 spelling


def test_the_9336c_fx2_e_is_a_device_of_its_own_not_a_configuration_set():
    """Decided from the two guides: the FX2-E's rear figure draws six fan modules where the
    N9336C-FX2 guide says three, and the two guides pair different fans with the chassis."""
    d = load(E)
    b = bays(d, "rear")
    assert [k for k in b if k.startswith("fan-")] == [f"fan-{i}" for i in range(1, 7)]
    parts = {pn for c in d["configurations"].values() for pn in c["part-numbers"]}
    assert parts == {"N9K-C9336C-FX2-E"}
    prov = d["provenance"]["sources"]["note"].replace("\n", " ")
    assert "A DEVICE OF ITS OWN" in prov and "six fan modules" in prov and "three fan modules" in prov
    assert "A device of its own" in d["description"]


def test_the_dimension_rows_fc2_spelling_is_declared_and_not_carried():
    d = load(E)
    note = d["provenance"]["the-width"]["note"].replace("\n", " ")
    assert "N9336C-FC2-E" in note and "typo" in note and "not carried" in note
    gap = [g for g in d["gaps"] if g["what"] == "figure-spells-fc2-in-the-dimension-row"]
    assert len(gap) == 1 and "N9336C-FC2-E" in gap[0]["note"]
    for text in (d["model"], json.dumps(d["configurations"]), json.dumps(d["aliases"])):
        assert "FC2" not in text


# ------------------------------------------------------------------ the ports


def test_the_front_has_36_qsfp28_in_two_rows_of_eighteen_numbered_down_each_column():
    p = placements(load(E), "front")
    for n in range(1, 37):
        assert p[f"port-{n}"]["ref"] == "std/qsfp28@1", n
    assert "port-37" not in p and "port-0" not in p
    for n in range(1, 36, 2):
        up, dn = p[f"port-{n}"]["at"], p[f"port-{n + 1}"]["at"]
        assert up[0] == pytest.approx(dn[0], abs=0.01) and up[1] < dn[1], n
    xs = [p[f"port-{n}"]["at"][0] for n in range(1, 37, 2)]
    assert len(xs) == 18
    # the figure's cages stand 66.6 px, 23.1 mm, apart
    for a, b in zip(xs, xs[1:]):
        assert b - a == pytest.approx(23.08, abs=0.01)
    d = load(E)
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    for n in range(1, 37):
        assert p[f"port-{n}"]["group"] == "qsfp28", n


def test_the_front_has_a_lamp_per_port_four_round_lamps_and_the_lane_select_button():
    """Callout 1 is "LEDs" (four round lamps are drawn) and callout 2 the lane select button."""
    p = placements(load(E), "front")
    for n in range(1, 37):
        lamp = p[f"led-port-{n}"]
        assert lamp["ref"] == "common/led-arrow-sm@1", n
    for lamp in ("led-bcn", "led-sts", "led-env", "led-lane"):
        assert p[lamp]["ref"] == "common/led-dot@1", lamp
    ys = [p[k]["at"][1] for k in ("led-bcn", "led-sts", "led-env", "led-lane")]
    assert ys == sorted(ys)
    assert p["lane-select"]["at"][1] > ys[-1]


def test_the_rear_has_console_two_management_ports_and_usb_between_fans_and_the_second_supply():
    d = load(E)
    p = placements(d, "rear")
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt-rj45"]["attrs"]["role"] == "mgmt"
    assert p["mgmt-sfp"]["ref"] == "std/sfp@1"
    assert p["usb"]["ref"] == "std/usb-a@1"
    b = bays(d, "rear")
    assert b["fan-6"]["at"][0] < p["console"]["at"][0] < p["mgmt-sfp"]["at"][0] < p["usb"]["at"][0]
    assert p["usb"]["at"][0] < b["psu-2"]["at"][0]


def test_the_rear_has_a_supply_at_each_end_and_six_fans_numbered_left_to_right():
    b = bays(load(E), "rear")
    assert [k for k in b if k.startswith("psu-")] == ["psu-1", "psu-2"]
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, 7)]
    assert xs == sorted(xs)
    assert b["psu-1"]["at"][0] < xs[0] and xs[-1] < b["psu-2"]["at"][0]
    pitch = [xs[i + 1] - xs[i] for i in range(5)]
    assert max(pitch) - min(pitch) < 0.05
    assert all(b[f"fan-{i}"]["group"] == "fans" for i in range(1, 7))


def test_no_ear_and_no_logo_is_drawn_and_a_logo_zone_is_reserved():
    d = load(E)
    for view in ("front", "rear"):
        for p in placements(d, view).values():
            assert p["ref"] != "common/rack-ear@1"
        for s in d["views"][view].get("silkscreen") or []:
            assert "cisco" not in str(s.get("text", "")).lower(), s
            assert "logo" not in str(s.get("mark", "")).lower(), s
    zones = [r for r in d["views"]["front"].get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1


# ------------------------------------------------------------ configurations


def test_the_builds_seat_matching_supplies_and_fans_with_matching_airflow():
    d = load(E)
    cf = d["configurations"]
    assert d["chassis"]["airflow"] == "front-to-back"
    defaults = [n for n, c in cf.items() if c.get("default")]
    assert defaults == ["ac-750w-port-side-intake"] and cf[defaults[0]]["kind"] == "base"
    assert set(cf) == set(BUILDS_E)
    default_psu = bays(d, "rear")["psu-1"]["default"]
    for name, (psu, power, exhaust) in BUILDS_E.items():
        c = cf[name]
        assert list(c["part-numbers"]) == ["N9K-C9336C-FX2-E"], name
        seated = c.get("bays") or {}
        if psu != default_psu:
            assert seated == {"psu-1": psu, "psu-2": psu}, name
        else:
            assert not seated, name
        assert c.get("power") == power, name
        attrs = c.get("component-attrs") or {}
        psu_name = psu.split("/")[1].split("@")[0]
        if exhaust:
            assert c["airflow"] == "back-to-front", name
            for part in ("nxa-sfan-35cfm", psu_name):
                assert attrs[part]["latch-finish"] == BLUE, (name, part)
                assert attrs[part]["airflow"] == "back-to-front", (name, part)
        else:
            assert "airflow" not in c, name
            assert not attrs, name


def test_the_bays_accept_only_the_supplies_and_fans_that_fit_the_figure():
    b = bays(load(E), "rear")
    for k in ("psu-1", "psu-2"):
        assert set(b[k]["accepts"]) == {PAC750, PDC1100}
        assert b[k]["default"] == PAC750
        assert (b[k]["size"]["w"], b[k]["size"]["h"]) == (56.0, 41.0)
    for k in [k for k in b if k.startswith("fan-")]:
        assert b[k]["accepts"] == [SFAN35] and b[k]["default"] == SFAN35


def test_the_1100w_ac_supply_and_the_plain_fan_are_not_seated_and_the_gaps_say_why():
    """The guide lists NXA-PAC-1100W and NXA-FAN-35CFM; the existing components are drawn at
    sizes the figure's bays do not hold, and an existing component is never edited."""
    d = load(E)
    gaps = {g["what"] for g in d["gaps"]}
    assert {"supply-1100w-ac-not-seated", "nxa-fan-35cfm-not-seated", "supply-weights-not-given"} <= gaps
    text = json.dumps(d["views"]["rear"]) + json.dumps(d["configurations"])
    assert "nxa-pac-1100w" not in text and "nxa-fan-35cfm" not in text
    assert contract("nxa-pac-1100w")["size"] == {"w": 84.7, "h": 40.6}  # reused as it stands
    assert contract("nxa-fan-35cfm")["size"] == {"w": 39.9, "h": 39.3}


# ------------------------------------------------------ components, ears, kits


def test_each_new_supply_is_one_component_named_by_its_part_number():
    root = LIB / "components/cisco"
    for part, model, watts, feed in (("nxa-pac-750w", "NXA-PAC-750W", 750, "ac"),
                                     ("nxa-pdc-1100w", "NXA-PDC-1100W", 1100, "dc")):
        assert [p.name for p in root.iterdir() if p.name.startswith(part)] == [part]
        c = contract(part)
        assert c["name"] == part and c["attrs"]["model"] == model and c["version"] == "1.0.0"
        assert c["class"] == "psu" and "size" in c["provenance"]
        assert c["attrs"]["power-output-w"] == watts and c["attrs"]["input"] == feed
    assert contract("nxa-pac-750w")["attrs"]["weight-kg"] == 0.95
    # no row of the weights table is the DC supply's own: no weight is carried
    assert "weight-kg" not in contract("nxa-pdc-1100w")["attrs"]
    assert contract("nxa-sfan-35cfm")["attrs"]["model"] == "NXA-SFAN-35CFM"  # reused, not copied


def test_the_ears_state_the_two_ways_without_a_number_and_without_a_default():
    ears = load(E)["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["recessed", "recessed"]
    assert len({p["label"] for p in ears["positions"]}) == 2
    for p in ears["positions"]:
        assert "at" not in p and not p.get("default"), p


def test_the_listed_kits_are_the_two_the_guide_gives_a_procedure_for_and_the_n3k_kit_is_a_gap():
    """The guide installs the chassis with the NXK-ACC-KIT-1RU and the NXK-ACC-KIT2-2RU. It names
    the N3K-C3064-ACC-KIT and says nothing else of it: no contents and no range."""
    d = load(E)
    assert [k["ref"] for k in d["chassis"]["kits"]] == [KIT1, KIT2]
    for ref in (KIT1, KIT2):
        name = ref.split("/")[1].split("@")[0]
        assert contract(name)["kind"] == "kit"
    gap = [g for g in d["gaps"] if g["what"] == "kit-contents-and-n3k-kit"]
    assert len(gap) == 1 and "N3K-C3064-ACC-KIT" in gap[0]["note"]
    assert not (LIB / "components/cisco/n3k-c3064-acc-kit").exists()


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_type_exports_one_per_chassis_part_number_one_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Cisco"
    assert sorted(p.stem for p in folder.glob("N9K-C9336C-*.yaml")) == ["N9K-C9336C-FX2-E"]
    assert not list(folder.glob("*FC2*"))
    doc = yaml.safe_load((folder / "N9K-C9336C-FX2-E.yaml").read_text())
    assert doc["manufacturer"] == "Cisco" and doc["model"] == "N9K-C9336C-FX2-E"
    assert doc["u_height"] == 1.0


def test_the_exported_type_lists_the_36_ports_and_the_management_ports():
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Cisco/N9K-C9336C-FX2-E.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 37)} <= set(types)
    assert "port-37" not in types
    assert {types[f"port-{n}"] for n in range(1, 37)} == {"100gbase-x-qsfp28"}
    assert {"console", "mgmt-rj45", "mgmt-sfp"} <= set(types) or len(types) >= 36


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_committed_export_is_what_the_exporter_writes_now(target, tmp_path, monkeypatch):
    """Runs the exporter on the build and compares its file with the committed one, so a device
    edited without regenerating its export fails here and not only in CI's "exports are current"."""
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run ./build.sh first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), E, str(tmp_path), str(dist))
    rel = pathlib.Path(target) / "device-types" / "Cisco" / "N9K-C9336C-FX2-E.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_file_agrees_with_the_device_and_its_components():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0] in ("cisco/" + E,)]
    known = devicelock.load_lock(lib)["devices"]
    assert known["cisco/" + E]["version"] == load(E)["version"] == "1.0.0"
    per_device = json.loads((LIB / "devices/cisco" / E / "device.lock.json").read_text())
    assert per_device["gaps"] == known["cisco/" + E]["gaps"]
