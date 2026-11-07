"""The Juniper QFX10002-36Q and QFX10002-72Q: two fixed 2RU deep-buffer switches on one chassis.

The two models share a chassis, rear panel and management panel; the guide gives one physical
specification table for the family (Table 30), so the envelope is the same for both. The front
panels differ (36 or 72 QSFP+ cages) and so does what ships in the four power supply bays (Table 30:
the 36Q ships two supplies and two blanks). The AC and DC builds and the spare chassis share a
front panel, so they are configurations of one device (Tables 1 and 3). The QFX10002-60C has its own
chassis and a later slice.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/juniper"
COMPONENTS = LIB / "components/juniper"
EXPORTS = LIB / "exports/netbox"

AC = "juniper/qfx10002-jpsu-1600w-ac-afo@1"
DC = "juniper/qfx10002-jpsu-1600w-dc-afo@1"
FAN = "juniper/qfx10002-fan-afo@1"
BLANK = "juniper/qfx10002-pwr-blnk@1"

# model -> (QSFP+ cages, rows of cages on the face, power supplies that ship)
MODELS = {
    "qfx10002-36q": (36, 2, 2),
    "qfx10002-72q": (72, 4, 4),
}

# Table 1 gives the AC and DC product numbers and Table 3 the spare chassis (-CHAS-S).
CONFIGS = {
    "qfx10002-36q": {"ac": "QFX10002-36Q", "dc": "QFX10002-36Q-DC", "s": "QFX10002-36Q-CHAS-S"},
    "qfx10002-72q": {"ac": "QFX10002-72Q", "dc": "QFX10002-72Q-DC", "s": "QFX10002-72Q-CHAS-S"},
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


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


@pytest.mark.parametrize("name", MODELS)
def test_envelope_is_table_30(name):
    # Table 30: 3.46 in. (8.8 cm) high, 17.36 in. (44.1 cm) wide, 31 in. (78.7 cm) deep without the
    # handles of the fans and power supplies. The 19 in. width is with the front brackets.
    ch = load(name)["chassis"]
    assert ch["width"] == 441.0
    assert ch["height"] == 88.0
    assert ch["depth"] == 787.0
    assert ch["ru"] == 2


@pytest.mark.parametrize("name", MODELS)
def test_naming(name):
    d = load(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX10002"}
    assert d["chassis"]["airflow"] == "front-to-back"


@pytest.mark.parametrize("name", MODELS)
def test_front_ports_are_qsfp_cages_numbered_from_zero(name):
    count, rows, _ = MODELS[name]
    cages = {p["id"]: p for p in placements(load(name), "front") if re.fullmatch(r"port-\d+", p["id"])}
    assert sorted(cages, key=lambda i: int(i.split("-")[1])) == [f"port-{n}" for n in range(count)]
    assert {p["ref"] for p in cages.values()} == {"std/qsfp-ganged@1"}
    # Figures 12 and 19: columns of two stacked cages, the even port above the odd one, in groups
    # of three columns (one 6XQSFP+ cage), with a gutter between the groups
    ys = sorted({p["at"][1] for p in cages.values()})
    assert len(ys) == rows
    for n in range(count):
        c = cages[f"port-{n}"]
        assert c["rel-pos"] == n
        if n % 2 == 0:
            assert cages[f"port-{n + 1}"]["at"][0] == c["at"][0]
            assert cages[f"port-{n + 1}"]["at"][1] > c["at"][1]
    xs = sorted({p["at"][0] for p in cages.values()})
    assert len(xs) == 18
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(19.0) == 12 and len([s for s in steps if s > 19.0]) == 5


@pytest.mark.parametrize("name", MODELS)
def test_every_cage_has_one_triangle_lamp(name):
    # Figure 17 and the text: each QSFP+ port has a single bicolour triangle LED
    count = MODELS[name][0]
    d = load(name)
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    assert len(lamps) == count
    assert {p["for"] for p in lamps} == {f"port-{n}" for n in range(count)}


@pytest.mark.parametrize("name", MODELS)
def test_front_management_panel(name):
    d = load(name)
    byid = {p["id"]: p["ref"] for p in placements(d, "front")}
    # Figure 21: MGMT RJ-45 (em0), CON, reset, status lamps, MGMT SFP (em1), PTP Ethernet SFP,
    # the PPS and 10 MHz SMB connectors and a USB port
    assert byid["mgmt"] == "common/rj45-eth@1"
    assert byid["con"] == "std/rj45@2"
    assert byid["mgmt-sfp"] == byid["ptp-sfp"] == "std/sfp-ganged@1"
    assert byid["pps"] == byid["ten-mhz"] == "std/smb@1"
    assert byid["usb"] == "std/usb-a@1"
    assert {"reset", "led-pwr", "led-sta", "led-mjr", "led-mnr"} <= set(byid)
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    # the photograph prints PWR, MJR, STA and MNR, PTP and 10M; the guide's drawing prints other words
    assert {"MGMT", "CON", "PWR", "MJR", "STA", "MNR", "PTP", "PPS", "10M", name.upper()} <= legends


@pytest.mark.parametrize("name", MODELS)
def test_the_front_has_no_wordmark_and_reserves_the_logo(name):
    d = load(name)
    texts = {s["text"] for v in d["views"].values() for s in (v.get("silkscreen") or []) if "text" in s}
    assert not {t for t in texts if t.upper() in ("JUNIPER", "NETWORKS")}, texts
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"].get("regions") or [])


@pytest.mark.parametrize("name", MODELS)
def test_rear_bays(name):
    d = load(name)
    by = {b["id"]: b for b in bays(d, "rear")}
    # Figures 4 and 5: four power supply bays numbered across from the top left, three fan modules
    assert set(by) == {"psu-0", "psu-1", "psu-2", "psu-3", "fan-0", "fan-1", "fan-2"}
    for i in ("fan-0", "fan-1", "fan-2"):
        assert by[i]["accepts"] == [FAN]
        assert by[i]["default"] == FAN
    # Table 3 and the install topic: AC or DC supply, or the QFX10002-PWR-BLNK cover
    for i in ("psu-0", "psu-1", "psu-2", "psu-3"):
        assert sorted(by[i]["accepts"]) == sorted([AC, DC, BLANK])
    xs = {b["id"]: b["at"] for b in by.values()}
    assert xs["psu-0"][1] == xs["psu-1"][1] < xs["psu-2"][1] == xs["psu-3"][1]
    assert xs["psu-0"][0] == xs["psu-2"][0] < xs["psu-1"][0] == xs["psu-3"][0]


@pytest.mark.parametrize("name", MODELS)
def test_configurations_part_numbers(name):
    d = load(name)
    cfgs = d["configurations"]
    assert {k: list(c["part-numbers"]) for k, c in cfgs.items()} == \
        {k: [pn] for k, pn in CONFIGS[name].items()}
    assert all(c["kind"] == "orderable" for c in cfgs.values())
    assert cfgs["ac"]["default"] is True
    assert not any(c.get("default") for k, c in cfgs.items() if k != "ac")
    assert list(cfgs["ac"]["part-numbers"]) == [d["model"]]


@pytest.mark.parametrize("name", MODELS)
def test_default_and_dc_builds_seat_what_the_guide_ships(name):
    _, _, supplies = MODELS[name]
    d = load(name)
    # Table 30: the 36Q ships two supplies and two blanks, the 72Q four supplies; Figure 5 draws the
    # 36Q's supplies in the lower bays
    fitted = [i for i in range(4) if seated(d, "ac", f"psu-{i}") == AC]
    assert len(fitted) == supplies
    if supplies == 2:
        assert fitted == [2, 3]
        assert {seated(d, "ac", "psu-0"), seated(d, "ac", "psu-1")} == {BLANK}
    for i in fitted:
        assert seated(d, "dc", f"psu-{i}") == DC
    for i in range(4):
        if i not in fitted:
            assert seated(d, "dc", f"psu-{i}") == BLANK
    for i in range(3):
        assert seated(d, "dc", f"fan-{i}") == FAN


@pytest.mark.parametrize("name", MODELS)
def test_the_spare_chassis_shows_every_bay_open(name):
    d = load(name)
    for bay in ("psu-0", "psu-1", "psu-2", "psu-3", "fan-0", "fan-1", "fan-2"):
        assert seated(d, "s", bay) in ("", None), bay


@pytest.mark.parametrize("name", MODELS)
def test_modules_airflow_matches_the_chassis(name):
    # Table 17, 20 and 24: every module is port-to-FRU (AFO, front-to-back), gold-handled, and the
    # guide lists no back-to-front build of either supply or the fan
    d = load(name)
    for cfg in d["configurations"]:
        for bay in ("psu-0", "psu-1", "psu-2", "psu-3", "fan-0", "fan-1", "fan-2"):
            ref = seated(d, cfg, bay)
            if not ref:
                continue
            comp = component(ref.split("/", 1)[1].split("@")[0])
            if comp["class"] == "blank":
                continue
            assert (comp.get("attrs") or {})["airflow"] == "front-to-back", (cfg, bay, ref)


def test_the_modules_carry_the_guides_part_numbers_and_power():
    ac, dc = component("qfx10002-jpsu-1600w-ac-afo"), component("qfx10002-jpsu-1600w-dc-afo")
    assert ac["part-numbers"] == {"JPSU-1600W-AC-AFO": {"part": "JPSU-1600W-AC-AFO"}}
    assert dc["part-numbers"] == {"JPSU-1600W-DC-AFO": {"part": "JPSU-1600W-DC-AFO"}}
    assert ac["attrs"]["power-output-w"] == dc["attrs"]["power-output-w"] == 1600
    fan = component("qfx10002-fan-afo")
    assert sorted(fan["part-numbers"]) == ["QFX10002-FAN", "QFX10002-FAN-S"]
    assert fan["attrs"]["power-draw-max-w"] == 80
    assert component("qfx10002-pwr-blnk")["part-numbers"] == \
        {"QFX10002-PWR-BLNK": {"part": "QFX10002-PWR-BLNK"}}


@pytest.mark.parametrize("name", MODELS)
def test_dcim_export_has_one_device_type_per_orderable_configuration(name):
    d = load(name)
    exported = sorted(p.stem for p in (EXPORTS / "device-types/Juniper").glob(f"{d['model']}*.yaml"))
    assert exported == sorted(CONFIGS[name].values())
    for pn in exported:
        doc = yaml.safe_load((EXPORTS / f"device-types/Juniper/{pn}.yaml").read_text())
        assert doc["u_height"] == 2.0
        assert doc["manufacturer"] == "Juniper"
        assert doc["airflow"] == "front-to-rear"


@pytest.mark.parametrize("pn", ["JPSU-1600W-AC-AFO", "JPSU-1600W-DC-AFO", "QFX10002-FAN",
                                "QFX10002-FAN-S", "QFX10002-PWR-BLNK"])
def test_module_types_are_exported_under_their_part_numbers(pn):
    doc = yaml.safe_load((EXPORTS / f"module-types/Juniper/{pn}.yaml").read_text())
    assert doc["part_number"] == pn
