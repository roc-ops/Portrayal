"""The Juniper QFX10002-60C: the third fixed 2RU model of the QFX10002 guide.

The 60C shares the family's chassis envelope (Table 30) but has its own port panel (60 QSFP28 ports
in two bands of 30, Figure 11), its own management panel (Figure 22), a vertical power supply
numbering and a fan module of its own (JNP10002-FAN1, Table 3). The AC and DC builds and the spare
chassis share a front panel, so they are configurations of one device (Tables 1 and 3).
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
NAME = "qfx10002-60c"
DEVICE = LIB / "devices/juniper" / NAME / "device.yaml"
COMPONENTS = LIB / "components/juniper"
EXPORTS = LIB / "exports/netbox"

AC = "juniper/qfx10002-jpsu-1600w-ac-afo@1"
DC = "juniper/qfx10002-jpsu-1600w-dc-afo@1"
BLANK = "juniper/qfx10002-pwr-blnk@1"
FAN = "juniper/qfx10002-jnp10002-fan1@1"
BAYS = ("psu-0", "psu-1", "psu-2", "psu-3", "fan-0", "fan-1", "fan-2")

# Table 1 gives the AC and DC product numbers, Table 3 the spare chassis (JNP10002-60C).
CONFIGS = {"ac": "QFX10002-60C", "dc": "QFX10002-60C-DC", "s": "JNP10002-60C"}


def load():
    return yaml.safe_load(DEVICE.read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def placements(d, face):
    return ((d["views"][face].get("components") or {}).get("placements")) or []


def bays(d, face):
    return ((d["views"][face].get("components") or {}).get("bays")) or []


def seated(d, cfg, bay):
    """The module a configuration seats in a rear bay: its own entry, else the bay's default."""
    by = {b["id"]: b for b in bays(d, "rear")}
    return (d["configurations"][cfg].get("bays") or {}).get(bay, by[bay].get("default"))


def test_envelope_is_table_30():
    # Table 30: 3.46 in. (8.8 cm) high, 17.36 in. (44.1 cm) wide, 31 in. (78.7 cm) deep without the
    # handles of the fans and power supplies
    ch = load()["chassis"]
    assert (ch["width"], ch["height"], ch["depth"], ch["ru"]) == (441.0, 88.0, 787.0, 2)
    assert ch["airflow"] == "front-to-back"


def test_naming():
    d = load()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "QFX10002-60C"
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX10002"}


def test_front_ports_are_sixty_qsfp28_cages_numbered_from_zero():
    d = load()
    cages = {p["id"]: p for p in placements(d, "front") if re.fullmatch(r"port-\d+", p["id"])}
    assert sorted(cages, key=lambda i: int(i.split("-")[1])) == [f"port-{n}" for n in range(60)]
    assert {p["ref"] for p in cages.values()} == {"std/qsfp-ganged@1"}
    # Figure 11: two bands of two rows; the even port above the odd, ports 0 to 29 in the upper band
    # and 30 to 59 in the lower; five groups of three columns (one six-port cage) with a gutter
    ys = sorted({p["at"][1] for p in cages.values()})
    assert len(ys) == 4
    for n in range(60):
        c = cages[f"port-{n}"]
        assert c["rel-pos"] == n
        if n % 2 == 0:
            assert cages[f"port-{n + 1}"]["at"][0] == c["at"][0]
            assert cages[f"port-{n + 1}"]["at"][1] > c["at"][1]
    assert all(cages[f"port-{n}"]["at"][1] < ys[2] for n in range(30))
    assert all(cages[f"port-{n}"]["at"][1] >= ys[2] for n in range(30, 60))
    xs = sorted({p["at"][0] for p in cages.values()})
    assert len(xs) == 15
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if s < 20.0]) == 10 and len([s for s in steps if s > 30.0]) == 4


def test_all_sixty_ports_are_100g_and_declare_it():
    d = load()
    groups = d["groups"]
    speeds = {groups[g]["attrs"]["speed"] for g in groups if groups[g].get("role") == "traffic"}
    assert speeds == {"100g"}
    assert {groups[g]["attrs"]["media"] for g in groups if groups[g].get("role") == "traffic"} == {"qsfp28"}


def test_every_cage_has_one_triangle_lamp():
    d = load()
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    assert len(lamps) == 60
    assert {p["for"] for p in lamps} == {f"port-{n}" for n in range(60)}


def test_printed_port_numbers_are_the_first_of_each_group():
    d = load()
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"]
               if s.get("text", "").isdigit() and s.get("for", "").startswith("port-")}
    assert printed == {str(n) for n in (0, 6, 12, 18, 24, 1, 7, 13, 19, 25,
                                        30, 36, 42, 48, 54, 31, 37, 43, 49, 55)}


def test_front_management_panel():
    d = load()
    byid = {p["id"]: p["ref"] for p in placements(d, "front")}
    # Figure 22: USB, four status lamps, MGMT RJ-45 (em0), CON, MGMT SFP (em1), PTP Ethernet SFP,
    # and the PPS and 10 MHz SMB connectors. The 60C panel draws no reset button.
    assert byid["mgmt"] == "common/rj45-eth@1"
    assert byid["con"] == "std/rj45@2"
    assert byid["mgmt-sfp"] == byid["ptp-sfp"] == "std/sfp-ganged@1"
    assert byid["pps"] == byid["ten-mhz"] == "std/smb@1"
    assert byid["usb"] == "std/usb-a@1"
    assert {"led-pwr", "led-sts", "led-maj", "led-min"} <= set(byid)
    assert "reset" not in byid
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    # the photograph prints PWR, STS, MAJ, MIN, PTP and 10M, as the guide's drawing does
    assert {"MGMT", "CON", "PWR", "STS", "MAJ", "MIN", "PTP", "PPS", "10M", "QFX10002-60C"} <= legends


def test_the_front_has_no_wordmark_and_reserves_the_logo():
    d = load()
    texts = {s["text"] for v in d["views"].values() for s in (v.get("silkscreen") or []) if "text" in s}
    assert not {t for t in texts if t.upper() in ("JUNIPER", "NETWORKS")}, texts
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"].get("regions") or [])


def test_rear_bays_are_numbered_down_the_columns():
    d = load()
    by = {b["id"]: b for b in bays(d, "rear")}
    assert set(by) == set(BAYS)
    for i in ("fan-0", "fan-1", "fan-2"):
        assert by[i]["accepts"] == [FAN]
        assert by[i]["default"] == FAN
    for i in ("psu-0", "psu-1", "psu-2", "psu-3"):
        assert sorted(by[i]["accepts"]) == sorted([AC, DC, BLANK])
    at = {k: v["at"] for k, v in by.items()}
    # the guide: the 60C supply bays are numbered vertically from the top left to the bottom right
    assert at["psu-0"][0] == at["psu-1"][0] < at["psu-2"][0] == at["psu-3"][0]
    assert at["psu-0"][1] == at["psu-2"][1] < at["psu-1"][1] == at["psu-3"][1]
    assert at["fan-0"][0] < at["fan-1"][0] < at["fan-2"][0]


def test_configurations_part_numbers():
    d = load()
    cfgs = d["configurations"]
    assert {k: list(c["part-numbers"]) for k, c in cfgs.items()} == {k: [pn] for k, pn in CONFIGS.items()}
    assert all(c["kind"] == "orderable" for c in cfgs.values())
    assert cfgs["ac"]["default"] is True
    assert not any(c.get("default") for k, c in cfgs.items() if k != "ac")
    assert list(cfgs["ac"]["part-numbers"]) == [d["model"]]


def test_default_and_dc_builds_seat_four_supplies_and_three_fans():
    # Table 30: three fans and four AC (or four DC) power supplies installed
    d = load()
    for i in range(4):
        assert seated(d, "ac", f"psu-{i}") == AC
        assert seated(d, "dc", f"psu-{i}") == DC
    for i in range(3):
        assert seated(d, "ac", f"fan-{i}") == FAN
        assert seated(d, "dc", f"fan-{i}") == FAN


def test_the_spare_chassis_shows_every_bay_open():
    d = load()
    for bay in BAYS:
        assert seated(d, "s", bay) in ("", None), bay


def test_modules_airflow_matches_the_chassis():
    # Tables 17, 20 and 24: every module is port-to-FRU (AFO, front-to-back); the guide lists no
    # back-to-front supply or fan, so the device has no airflow configuration
    d = load()
    for cfg in d["configurations"]:
        for bay in BAYS:
            ref = seated(d, cfg, bay)
            if not ref:
                continue
            comp = component(ref.split("/", 1)[1].split("@")[0])
            if comp["class"] == "blank":
                continue
            assert (comp.get("attrs") or {})["airflow"] == "front-to-back", (cfg, bay, ref)


def test_the_fan_is_the_60c_module_with_its_own_part_number():
    fan = component("qfx10002-jnp10002-fan1")
    # Table 3 lists JNP10002-FAN1 for the 60C; the 72Q and 36Q fan keeps QFX10002-FAN-S
    assert fan["part-numbers"] == {"JNP10002-FAN1": {"part": "JNP10002-FAN1"}}
    assert fan["attrs"]["power-draw-max-w"] == 80
    assert fan["attrs"]["fans-per-module"] == 2
    other = component("qfx10002-fan-afo")
    assert "JNP10002-FAN1" not in other["part-numbers"]


def test_the_supplies_and_the_blank_are_the_ones_main_already_models():
    # one part number, one component: the 60C seats the family's supplies by their part numbers
    assert component("qfx10002-jpsu-1600w-ac-afo")["part-numbers"] == \
        {"JPSU-1600W-AC-AFO": {"part": "JPSU-1600W-AC-AFO"}}
    assert component("qfx10002-jpsu-1600w-dc-afo")["part-numbers"] == \
        {"JPSU-1600W-DC-AFO": {"part": "JPSU-1600W-DC-AFO"}}
    assert component("qfx10002-pwr-blnk")["part-numbers"] == \
        {"QFX10002-PWR-BLNK": {"part": "QFX10002-PWR-BLNK"}}


def test_dcim_export_has_one_device_type_per_orderable_configuration():
    exported = sorted(p.stem for p in (EXPORTS / "device-types/Juniper").glob("*.yaml")
                      if p.stem in CONFIGS.values())
    assert exported == sorted(CONFIGS.values())
    for pn in exported:
        doc = yaml.safe_load((EXPORTS / f"device-types/Juniper/{pn}.yaml").read_text())
        assert doc["u_height"] == 2.0
        assert doc["manufacturer"] == "Juniper"
        assert doc["airflow"] == "front-to-rear"


def test_the_fan_module_type_is_exported_under_its_part_number():
    doc = yaml.safe_load((EXPORTS / "module-types/Juniper/JNP10002-FAN1.yaml").read_text())
    assert doc["part_number"] == "JNP10002-FAN1"
