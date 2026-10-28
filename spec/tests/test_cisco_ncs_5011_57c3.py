"""The Cisco NCS 5011, NCS-57C3-MOD-S and NCS-57C3-MOD-HX match their hardware installation guides.

The NCS 5011 is in the Hardware Installation Guide for Cisco NCS 5000 Series Routers (first published 2015-12-23,
last modified 2019-01-31): its size and weight (Appendix C, Table 13), its ports (Chapter 1), and the supplies and fan
modules it takes (Tables 6 and 7). The 57C3 routers are in the Hardware Installation Guide for Cisco NCS 5700 Series
Fixed-Port Routers (first published 2021-06-23, last modified 2026-05-15): the variants and port counts (Table 2), the
dimensions (Figure 1) and the parts. The 5011's face figures are three-quarter views, so what is held to the guide
there is counts, sizes and part numbers, not positions.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools"))

from portrayal import devicelock  # noqa: E402

INCH = 25.4

# The devices of this batch, with the models as the guides print them.
DEVICES = {"ncs-5011": "NCS 5011", "ncs-57c3-mod-s": "NCS-57C3-MOD-S", "ncs-57c3-mod-hx": "NCS-57C3-MOD-HX"}
C3 = ["ncs-57c3-mod-s", "ncs-57c3-mod-hx"]

# Table 13 for the 5011, in inches as printed (H x W x D); Figure 1 and Figure 26 for the 57C3, in millimetres.
ENVELOPE = {
    "ncs-5011": {"h": 1.72 * INCH, "w": 17.3 * INCH, "d": 22.5 * INCH, "ru": 1},
    "ncs-57c3-mod-s": {"h": 130.88, "w": 438.4, "d": 318.77, "ru": 3},
    "ncs-57c3-mod-hx": {"h": 130.88, "w": 438.4, "d": 318.77, "ru": 3},
}

PSU_5011 = ["nc5k-pac-650w-fr", "nc5k-pac-650w-bk", "nc5k-pdc-930w-fr", "nc5k-pdc-930w-bk"]
FAN_5011 = ["ncs-5011-fn-fr", "ncs-5011-fn-bk"]
PSU_C3 = ["nc57-1600w-acfw", "nc57-1600w-dcfw", "nc57c3-ps-blnk"]


def device(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/cisco" / name / "v1/contract.yaml").read_text())


def ref_name(ref):
    return ref.split("/", 1)[1].split("@", 1)[0]


def bays(name, face):
    return {b["id"]: b for b in device(name)["views"][face]["components"]["bays"]}


def accepted(bay):
    return sorted(ref_name(r) for r in bay["accepts"])


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_envelope_is_the_guides(name):
    want, ch = ENVELOPE[name], device(name)["chassis"]
    assert ch["height"] == pytest.approx(want["h"], abs=0.1)
    assert ch["width"] == pytest.approx(want["w"], abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"], abs=0.1)
    assert ch["ru"] == want["ru"]
    assert ch.get("mount", "rack") == "rack"


def test_5011_front_has_thirty_two_qsfp28_numbered_from_one():
    placements = device("ncs-5011")["views"]["front"]["components"]["placements"]
    ports = [p for p in placements if str(p["id"]).startswith("port-")]
    assert {ref_name(p["ref"]) for p in ports} == {"qsfp28"}
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(1, 33))


def test_5011_management_and_console_are_on_the_fan_side_with_the_supplies():
    d = device("ncs-5011")
    front = {p["id"] for p in d["views"]["front"]["components"]["placements"]}
    rear = {p["id"] for p in d["views"]["rear"]["components"]["placements"]}
    assert {"console", "mgmt"} <= rear
    assert not ({"console", "mgmt"} & front)


@pytest.mark.parametrize("name", C3)
def test_57c3_front_is_48_sfp28_and_8_qsfp28_numbered_as_printed_from_zero(name):
    placements = device(name)["views"]["front"]["components"]["placements"]
    ports = [p for p in placements if str(p["id"]).startswith("port-")]
    by_cage = {}
    for p in ports:
        by_cage[ref_name(p["ref"])] = by_cage.get(ref_name(p["ref"]), 0) + 1
    assert by_cage == {"sfp-ganged": 48, "qsfp28": 8}
    numbers = {int(p["id"].split("-")[1]): ref_name(p["ref"]) for p in ports}
    assert sorted(numbers) == list(range(56))
    # Figure 19 prints 24 to 31 on the QSFP28 cages and the SFP28 numbers around them.
    assert [n for n, cage in sorted(numbers.items()) if cage == "qsfp28"] == list(range(24, 32))


@pytest.mark.parametrize("name", C3)
def test_57c3_timing_ports_are_two_din_one_sma_and_one_rj45(name):
    placements = {p["id"]: p for p in device(name)["views"]["front"]["components"]["placements"]}
    assert ref_name(placements["timing-1pps"]["ref"]) == "din-1-0-2-3"
    assert ref_name(placements["timing-10mhz"]["ref"]) == "din-1-0-2-3"
    assert ref_name(placements["timing-gnss"]["ref"]) == "sma"
    assert placements["timing-tod"]["attrs"]["media"] == "rj45-tod"


def test_5011_two_supply_bays_and_four_fan_bays_accept_the_guides_parts():
    b = bays("ncs-5011", "rear")
    assert sorted(b) == ["fan-1", "fan-2", "fan-3", "fan-4", "psu-1", "psu-2"]
    for bay in ("psu-1", "psu-2"):
        assert accepted(b[bay]) == sorted(PSU_5011)
    for bay in ("fan-1", "fan-2", "fan-3", "fan-4"):
        assert accepted(b[bay]) == sorted(FAN_5011)


@pytest.mark.parametrize("name,fans2,fans1,rp", [
    ("ncs-57c3-mod-s", "nc57-c3-fan2-fw", "nc57-c3-fan1-fw", "nc57-mod-rp2-e"),
    ("ncs-57c3-mod-hx", "nc57-c3-fan2-hx", "nc57-c3-fan1-hx", "nc57-mod-rp2-e-hx"),
])
def test_57c3_bays_accept_what_the_guide_lists_and_the_hx_only_its_own_parts(name, fans2, fans1, rp):
    front, rear = bays(name, "front"), bays(name, "rear")
    assert sorted(b for b in front if b.startswith("mpa")) == ["mpa-1", "mpa-2", "mpa-3"]
    for b in ("mpa-1", "mpa-2", "mpa-3"):
        assert accepted(front[b]) == ["nc55-mpa-blnk"]
    for b in ("rp-1", "rp-2"):
        assert accepted(front[b]) == sorted([rp, "nc57c3-rp-blnk"])
    for b in ("psu-1", "psu-2"):
        assert accepted(front[b]) == sorted(PSU_C3)
    # fan tray slots 0 and 1 take the 2x60 mm tray, slots 2 to 5 the 2x40 mm tray
    assert sorted(rear) == [f"fan-{i}" for i in range(6)]
    for i in range(6):
        assert accepted(rear[f"fan-{i}"]) == [fans2 if i < 2 else fans1]


@pytest.mark.parametrize("name", sorted(DEVICES))
def test_builds_have_no_part_numbers_one_default_and_base_only_on_it(name):
    cfgs = device(name)["configurations"]
    assert sum(1 for c in cfgs.values() if c.get("default")) == 1
    for cname, cfg in cfgs.items():
        assert not cfg.get("part-numbers"), cname
        assert cfg["kind"] == ("base" if cfg.get("default") else "example"), cname


def test_5011_builds_seat_one_airflow_throughout():
    d = device("ncs-5011")
    b = bays("ncs-5011", "rear")
    psu = {("ac", "front-to-back"): "nc5k-pac-650w-fr", ("ac", "back-to-front"): "nc5k-pac-650w-bk",
           ("dc", "front-to-back"): "nc5k-pdc-930w-fr", ("dc", "back-to-front"): "nc5k-pdc-930w-bk"}
    fan = {"front-to-back": "ncs-5011-fn-fr", "back-to-front": "ncs-5011-fn-bk"}
    cfgs = d["configurations"]
    assert sorted(cfgs) == ["ac-port-side-exhaust", "ac-port-side-intake", "dc-port-side-exhaust", "dc-port-side-intake"]
    for cname, cfg in cfgs.items():
        seated = {bay: ref_name((cfg.get("bays") or {}).get(bay) or b[bay]["default"]) for bay in b}
        assert seated == {"psu-1": psu[(cfg["power"], cfg["airflow"])], "psu-2": psu[(cfg["power"], cfg["airflow"])],
                          **{f"fan-{i}": fan[cfg["airflow"]] for i in range(1, 5)}}, cname
        assert contract(fan[cfg["airflow"]])["attrs"]["airflow"] == cfg["airflow"]


@pytest.mark.parametrize("name", C3)
def test_57c3_base_build_is_ac_with_blanks_and_the_dc_build_is_an_example(name):
    cfgs = device(name)["configurations"]
    assert sorted(cfgs) == ["ac-port-side-intake", "dc-port-side-intake"]
    assert cfgs["ac-port-side-intake"]["default"] and cfgs["ac-port-side-intake"]["source"].startswith("derived")
    assert {ref_name(v) for v in cfgs["dc-port-side-intake"]["bays"].values()} == {"nc57-1600w-dcfw"}
    front = bays(name, "front")
    for b in ("mpa-1", "mpa-2", "mpa-3"):
        assert ref_name(front[b]["default"]) == "nc55-mpa-blnk"
    assert device(name)["chassis"]["airflow"] == "front-to-back"


def test_the_supplies_and_fans_carry_the_guides_figures():
    assert contract("nc57-1600w-acfw")["attrs"]["power-output-w"] == 1600
    assert contract("nc57-1600w-dcfw")["attrs"]["power-output-w"] == 1600
    for part in ("nc5k-pac-650w-fr", "nc5k-pac-650w-bk"):
        assert contract(part)["attrs"]["power-output-w"] == 650
    for part in ("nc5k-pdc-930w-fr", "nc5k-pdc-930w-bk"):
        assert contract(part)["attrs"]["power-output-w"] == 930


def test_the_fan_redundancy_is_the_guides_wording():
    assert device("ncs-5011")["groups"]["fans"]["attrs"]["redundancy"] == "3+1"
    for name in C3:
        assert device(name)["groups"]["fans"]["attrs"]["redundancy"] == "n+1"


@pytest.mark.parametrize("name", sorted(DEVICES))
def test_sale_status_is_not_guessed(name):
    d = device(name)
    assert "eol" not in ((d.get("attrs") or {}).get("lifecycle") or {})
    assert any(g.get("what") == "sale-status" for g in d["gaps"])


@pytest.mark.parametrize("tool", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", sorted(DEVICES))
def test_dcim_device_type_is_one_per_chassis_at_the_guides_u_height(name, tool):
    # the builds are examples with no SKU, so no build-named device type is exported
    model = device(name)["model"]
    files = sorted((LIB / "exports" / tool / "device-types/Cisco").glob(f"{model}*.yaml"))
    types = [yaml.safe_load(f.read_text()) for f in files]
    assert [t["model"] for t in types] == [model], [f.name for f in files]
    assert types[0]["u_height"] == ENVELOPE[name]["ru"]


def test_the_lock_agrees_with_the_devices():
    findings = [f for f in devicelock.check(LIB) if f[0] in {f"cisco/{n}" for n in DEVICES} | set(DEVICES)]
    assert findings == []
